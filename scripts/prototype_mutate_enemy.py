"""Prototype (not the final module yet -- see the conversation for the plan)
for randomizing a whole battle: our whole party (bench included, not just
the active battler), the enemy, with varied levels.

Two distinct modes -- pick one, they don't mix:

  python scripts/prototype_mutate_enemy.py
      AUTO mode (default): the script itself submits one move through the
      real game menu, as a demo that the pipeline works end-to-end. Just
      watch -- don't touch the keyboard, nothing is waiting for you.

  python scripts/prototype_mutate_enemy.py --manual
      MANUAL mode: mutates the battle, then YOU play with the keyboard
      (PyBoy's own controls). The script only prints a snapshot of what our
      own code sees every ~10 real seconds, so you can compare it against
      what you see on screen. Close the window or Ctrl+C to stop.

Optional fixture name and --seed also accepted -- see --help.
"""
import argparse
import json
import os
import random
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8")  # names like "Nidoran(female)" break Windows' default console codepage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.core.emulator import EmulatorSession  # noqa: E402
from game.core.loop import EmulatorLoop  # noqa: E402
from game.core.version import GameVersion  # noqa: E402
from game.data.data import POKDX_ID_TO_NAME, POKEMON_ROM_ID_TO_PKDX_ID, POKEMON_TYPES  # noqa: E402
from game.data.decoder import decode_pkm_text, encode_pkm_text  # noqa: E402
from game.data.helpers import write_bytes, write_u8, write_u16  # noqa: E402
from game.data.pokemon import POKEMON_LAYOUT_PARTY  # noqa: E402
from game.data.ram_reader import MainPokemonData, MemoryData, MoveROMBank  # noqa: E402
from game.scenes.battle_scene import create_battle_scene  # noqa: E402
from game.scenes.commands import BattleCommand  # noqa: E402
from game.scenes.scene_controller import SceneController  # noqa: E402
from game.services.scene_manger_service import SceneManagerService  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")

with open(os.path.join(os.path.dirname(__file__), "base_stats_gen1.json"), encoding="utf-8") as f:
    BASE_STATS = {e["dex"]: e for e in json.load(f)}

PKDX_TO_ROM_ID = {v: k for k, v in POKEMON_ROM_ID_TO_PKDX_ID.items()}
TYPE_NAME_TO_ID = {name.upper(): tid for tid, name in POKEMON_TYPES.items()}
TYPE_NAME_TO_ID["PSYCHIC_TYPE"] = TYPE_NAME_TO_ID["PSYCHIC"]

PARTY_SLOT_BLOCKS = {
    1: MainPokemonData.Pokemon1, 2: MainPokemonData.Pokemon2, 3: MainPokemonData.Pokemon3,
    4: MainPokemonData.Pokemon4, 5: MainPokemonData.Pokemon5, 6: MainPokemonData.Pokemon6,
}
PARTY_INDEX_BYTE = {
    1: MainPokemonData.PartyPokemon1, 2: MainPokemonData.PartyPokemon2, 3: MainPokemonData.PartyPokemon3,
    4: MainPokemonData.PartyPokemon4, 5: MainPokemonData.PartyPokemon5, 6: MainPokemonData.PartyPokemon6,
}
PARTY_NICKNAME = {
    1: MainPokemonData.Nickname1, 2: MainPokemonData.Nickname2, 3: MainPokemonData.Nickname3,
    4: MainPokemonData.Nickname4, 5: MainPokemonData.Nickname5, 6: MainPokemonData.Nickname6,
}

# Same 3 dicts, opponent trainer's roster instead of ours (0xD8A4-0xD9AB
# block + 0xD89D-0xD8A2 index array + the "_Alt" nickname block) -- only
# meaningful for a trainer battle (BattleType.TRAINER), a wild battle has no
# opponent roster to speak of.
OPPONENT_PARTY_SLOT_BLOCKS = {
    1: MainPokemonData.OpponentPokemonData1, 2: MainPokemonData.OpponentPokemonData2,
    3: MainPokemonData.OpponentPokemonData3, 4: MainPokemonData.OpponentPokemonData4,
    5: MainPokemonData.OpponentPokemonData5, 6: MainPokemonData.OpponentPokemonData6,
}
OPPONENT_PARTY_INDEX_BYTE = {
    1: MainPokemonData.OpponentPokemon1, 2: MainPokemonData.OpponentPokemon2,
    3: MainPokemonData.OpponentPokemon3, 4: MainPokemonData.OpponentPokemon4,
    5: MainPokemonData.OpponentPokemon5, 6: MainPokemonData.OpponentPokemon6,
}
OPPONENT_PARTY_NICKNAME = {
    1: MainPokemonData.Nickname1_Alt, 2: MainPokemonData.Nickname2_Alt, 3: MainPokemonData.Nickname3_Alt,
    4: MainPokemonData.Nickname4_Alt, 5: MainPokemonData.Nickname5_Alt, 6: MainPokemonData.Nickname6_Alt,
}


def write_species_name(md, target_dex: int) -> None:
    """Writes the species' default nickname (its own name, uppercase --
    Gen1's convention when you don't rename a Pokemon) into a name-shaped
    field (11 bytes: PlayerPokemonName, EnemyName, or a party slot's
    NicknameN). Without this, a field that already had a DIFFERENT
    Pokemon's name (or, worse, an empty/zeroed party slot never given a
    nickname before) keeps showing that stale or garbage text after the
    species/stats/moves change underneath it -- purely cosmetic (nothing in
    this project's own reading, i.e. the RL observation, uses raw name
    text), but confusing to look at while manually testing."""
    name = POKDX_ID_TO_NAME.get(target_dex, {"en": "?"}).get("en", "?").upper()
    length = md.end_address - md.start_address + 1
    try:
        write_bytes(md, encode_pkm_text(name, length))
    except ValueError:
        pass  # a name with no Gen1 encoding for one of its characters -- leave the field as-is rather than crash


def calc_stat(base: int, dv: int, level: int) -> int:
    return ((base + dv) * 2 * level) // 100 + 5


def calc_hp(base: int, dv: int, level: int) -> int:
    return ((base + dv) * 2 * level) // 100 + level + 10


def find_move_id_by_name(session, target_name: str) -> int:
    bank = MoveROMBank(session)
    for move_id in range(1, 166):
        raw = bank.get_move_name_bytes(move_id)
        name = decode_pkm_text(list(raw)).strip().upper()
        if name.replace(" ", "").replace("-", "") == target_name.replace("_", "").replace(" ", ""):
            return move_id
    raise ValueError(f"move {target_name!r} not found")


def _rel_field(base_addr: int, key: str) -> MemoryData:
    s_rel, e_rel = POKEMON_LAYOUT_PARTY[key]
    return MemoryData(base_addr + s_rel, base_addr + e_rel - 1)


def mutate_battle_active(session, md_species, md_type1, md_type2, md_level, md_hp_cur, md_hp_max,
                          md_atk, md_def, md_spd, md_spc, md_dv1, md_dv2,
                          md_moves, md_pp, target_dex: int, level: int, dv: int) -> None:
    """Shared write logic for the currently-active battle Pokemon (either
    side) -- addresses differ (enemy: scattered named fields; player:
    offsets within the D009-D030 struct), passed in explicitly rather than
    hardcoded so this one function covers both."""
    stats = BASE_STATS[target_dex]
    rom_id = PKDX_TO_ROM_ID[target_dex]
    type1_id = TYPE_NAME_TO_ID[stats["type1"]]
    type2_id = TYPE_NAME_TO_ID[stats["type2"]]

    max_hp = calc_hp(stats["hp"], dv, level)
    attack = calc_stat(stats["attack"], dv, level)
    defense = calc_stat(stats["defense"], dv, level)
    speed = calc_stat(stats["speed"], dv, level)
    special = calc_stat(stats["special"], dv, level)

    move_names = (stats["level1_moves"] + ["NO_MOVE"] * 4)[:4]
    move_ids = [find_move_id_by_name(session, n) if n != "NO_MOVE" else 0 for n in move_names]
    move_pps = [MoveROMBank(session).get_move_bytes(mid)[5] if mid != 0 else 0 for mid in move_ids]

    write_u8(md_species, rom_id)
    write_u8(md_type1, type1_id)
    write_u8(md_type2, type2_id)
    write_u8(md_level, level)
    write_u16(md_hp_max, max_hp)
    write_u16(md_hp_cur, max_hp)
    write_u16(md_atk, attack)
    write_u16(md_def, defense)
    write_u16(md_spd, speed)
    write_u16(md_spc, special)
    write_u8(md_dv1, (dv << 4) | dv)
    write_u8(md_dv2, (dv << 4) | dv)
    for i, (mv, md) in enumerate(zip(move_ids, md_moves)):
        write_u8(md, mv)
    for pp, md in zip(move_pps, md_pp):
        write_u8(md, pp)

    return move_names[0]  # the move we'll actually use in the demo below


def mutate_enemy_to(session, target_dex: int, level: int, dv: int) -> str:
    md = MainPokemonData
    first_move = mutate_battle_active(
        session, md.EnemyPokemonID, md.EnemyType1, md.EnemyType2, md.EnemyLevel,
        md.EnemyHP, md.EnemyMaxHP, md.EnemyAttack, md.EnemyDefense, md.EnemySpeed, md.EnemySpecial,
        md.EnemyIVsAtkDef, md.EnemyIVsSpdSpc,
        [md.EnemyMove1, md.EnemyMove2, md.EnemyMove3, md.EnemyMove4],
        [md.EnemyPP1, md.EnemyPP2, md.EnemyPP3, md.EnemyPP4],
        target_dex, level, dv,
    )
    write_u8(md.EnemyPokemonID2, PKDX_TO_ROM_ID[target_dex])
    write_u8(md.EnemyLevel2, level)  # EnemyLevel ("DO NOT WORK") is a dead duplicate -- EnemyPokemon.level reads THIS one
    write_u8(md.EnemyCatchRate, BASE_STATS[target_dex]["catch_rate"])
    write_u8(md.EnemyBaseExp, BASE_STATS[target_dex]["base_exp"])
    write_species_name(md.EnemyName, target_dex)
    return first_move


def mutate_player_active_to(session, target_dex: int, level: int, dv: int) -> str:
    md = MainPokemonData
    result = mutate_battle_active(
        session, md.PlayerPokemonNumber, md.PlayerType1, md.PlayerType2, md.PlayerLevel,
        md.PlayerCurrentHP, md.PlayerMaxHP, md.PlayerAttack, md.PlayerDefense, md.PlayerSpeed, md.PlayerSpecial,
        md.PlayerDVsAtkDef, md.PlayerDVsSpdSpc,
        [md.PlayerMove1, md.PlayerMove2, md.PlayerMove3, md.PlayerMove4],
        [md.PlayerPP1, md.PlayerPP2, md.PlayerPP3, md.PlayerPP4],
        target_dex, level, dv,
    )
    write_species_name(md.PlayerPokemonName, target_dex)
    return result


def mutate_party_slot_to(
    session, slot: int, target_dex: int, level: int, dv: int,
    slot_blocks=PARTY_SLOT_BLOCKS, index_bytes=PARTY_INDEX_BYTE, nicknames=PARTY_NICKNAME,
) -> None:
    """Bench member -- separate 44-byte struct (POKEMON_LAYOUT_PARTY), plus
    its own entry in the compact 6-byte species-index array PartyPokemonN
    (used by the party-list menu; the full struct is what matters once that
    Pokemon becomes active, same duplicate-fields pattern as the enemy).
    Same layout for the opponent trainer's roster, just different base
    addresses -- pass OPPONENT_PARTY_SLOT_BLOCKS/OPPONENT_PARTY_INDEX_BYTE/
    OPPONENT_PARTY_NICKNAME to mutate their team instead of ours."""
    base = slot_blocks[slot].start_address
    stats = BASE_STATS[target_dex]
    rom_id = PKDX_TO_ROM_ID[target_dex]
    type1_id = TYPE_NAME_TO_ID[stats["type1"]]
    type2_id = TYPE_NAME_TO_ID[stats["type2"]]

    max_hp = calc_hp(stats["hp"], dv, level)
    attack = calc_stat(stats["attack"], dv, level)
    defense = calc_stat(stats["defense"], dv, level)
    speed = calc_stat(stats["speed"], dv, level)
    special = calc_stat(stats["special"], dv, level)

    move_names = (stats["level1_moves"] + ["NO_MOVE"] * 4)[:4]
    move_ids = [find_move_id_by_name(session, n) if n != "NO_MOVE" else 0 for n in move_names]
    move_pps = [MoveROMBank(session).get_move_bytes(mid)[5] if mid != 0 else 0 for mid in move_ids]

    write_u8(index_bytes[slot], rom_id)
    write_u8(_rel_field(base, "id"), rom_id)
    write_species_name(nicknames[slot], target_dex)
    write_u16(_rel_field(base, "current_hp"), max_hp)
    write_u8(_rel_field(base, "type1"), type1_id)
    write_u8(_rel_field(base, "type2"), type2_id)
    write_u8(_rel_field(base, "level"), level)
    write_u16(_rel_field(base, "max_hp"), max_hp)
    write_u16(_rel_field(base, "attack"), attack)
    write_u16(_rel_field(base, "defense"), defense)
    write_u16(_rel_field(base, "speed"), speed)
    write_u8(_rel_field(base, "ivs"), (dv << 4) | dv)  # atk/def nibble; leave spd/spc byte as-is
    moves_s, _ = POKEMON_LAYOUT_PARTY["moves"]
    pp_s, _ = POKEMON_LAYOUT_PARTY["pp"]
    for i, mv in enumerate(move_ids):
        write_u8(MemoryData(base + moves_s + i, base + moves_s + i), mv)
    for i, pp in enumerate(move_pps):
        write_u8(MemoryData(base + pp_s + i, base + pp_s + i), pp)


def _mutate_roster(session, rng, all_dex, before_roster: list, target_size: int,
                    slot_blocks, index_bytes, nicknames, count_field) -> list:
    """Shared logic for growing/shrinking + re-rolling a whole 6-slot roster
    (ours or the opponent trainer's) -- writes count_field + a 0xFF
    terminator if the size changed, then mutates every slot 1..target_size.
    Returns the list of {"dex", "level"} picks, slot 1 first."""
    original_size = len(before_roster)
    if target_size != original_size:
        write_u8(count_field, target_size)
        if target_size < 6:
            write_u8(index_bytes[target_size + 1], 0xFF)  # terminator

    baseline_level = before_roster[0]["level"] if before_roster else 10
    picks = []
    for slot in range(1, target_size + 1):
        dex = rng.choice(all_dex)
        if slot <= len(before_roster):
            slot_level = max(2, before_roster[slot - 1]["level"] + rng.randint(-2, 3))
        else:
            slot_level = max(2, baseline_level + rng.randint(-2, 3))  # brand new slot, no "before" to vary from
        dv = rng.randint(0, 15)
        mutate_party_slot_to(session, slot, dex, slot_level, dv,
                              slot_blocks=slot_blocks, index_bytes=index_bytes, nicknames=nicknames)
        picks.append({"dex": dex, "level": slot_level, "dv": dv})
    return picks


def mutate_whole_battle(session, scene, rng, target_party_size: int = None,
                         target_opponent_party_size: int = None) -> dict:
    """Mutates our whole party (bench included) + the enemy in place --
    for a trainer battle, also the opponent's WHOLE roster (not just the
    currently-active one), keeping opponent-roster slot 1 and the
    currently-active enemy in sync (same duplicate-fields pattern as our
    own slot 1, see _mutate_roster's docstring and mutate_whole_battle's
    inline comment below). Returns {"enemy": {...}, "party": [...],
    "opponent_party": [...] or None if this wasn't a trainer battle} for
    callers that want to print/label things afterward.

    target_party_size / target_opponent_party_size, if given and different
    from the fixture's own count, grow (or shrink) that roster -- see
    _mutate_roster. Slots beyond the fixture's original count have no
    "before" level to vary from, so they're leveled near that roster's
    slot 1 instead."""
    before = scene.to_dict()
    all_dex = list(BASE_STATS.keys())
    is_trainer_battle = before["battle_type"] == "trainer"

    party_size = target_party_size if target_party_size is not None else len(scene.player_party)
    party_picks = _mutate_roster(
        session, rng, all_dex, before["party"], party_size,
        PARTY_SLOT_BLOCKS, PARTY_INDEX_BYTE, PARTY_NICKNAME, MainPokemonData.PartyCount,
    )
    # Slot 1 (the active battler) exists in TWO places at once -- the battle
    # struct (D009+, used DURING this fight) and its own party struct
    # (D16B+, what "party" in to_dict() reads, i.e. what feeds the
    # observation vector) -- found by actually checking to_dict()["party"]
    # after mutating only the battle struct: it still showed the OLD
    # Pokemon. Both must get the SAME species/level/dv, not independently
    # re-randomized, or the two views of "slot 1" would disagree.
    p1 = party_picks[0]
    mutate_player_active_to(session, p1["dex"], p1["level"], p1["dv"])

    opponent_picks = None
    if is_trainer_battle:
        opponent_size = target_opponent_party_size if target_opponent_party_size is not None else len(scene.enemy_party)
        opponent_picks = _mutate_roster(
            session, rng, all_dex, before["enemy_party"], opponent_size,
            OPPONENT_PARTY_SLOT_BLOCKS, OPPONENT_PARTY_INDEX_BYTE, OPPONENT_PARTY_NICKNAME,
            MainPokemonData.OpponentPartyCount,
        )
        e1 = opponent_picks[0]
        mutate_enemy_to(session, e1["dex"], e1["level"], e1["dv"])
        enemy_dex, enemy_level = e1["dex"], e1["level"]
    else:
        enemy_level = max(2, before["enemy"]["level"] + rng.randint(-2, 3))
        enemy_dex = rng.choice(all_dex)
        mutate_enemy_to(session, enemy_dex, enemy_level, dv=rng.randint(0, 15))

    return {
        "enemy": {"dex": enemy_dex, "level": enemy_level},
        "party": party_picks,
        "opponent_party": opponent_picks,
    }


def print_before_after(before, scene_after) -> None:
    after = scene_after.to_dict()
    print(f"BEFORE enemy:     {before['enemy']['name']} (level {before['enemy']['level']})")
    print(f"BEFORE active:    {before['on_battle']['name']} (level {before['on_battle']['level']})")
    print(f"BEFORE party:     {[p['name'] for p in before['party']]}")
    if before["battle_type"] == "trainer":
        print(f"BEFORE opp. team: {[(p['name'], p['level']) for p in before['enemy_party']]}")
    print()
    print(f"AFTER enemy:      {after['enemy']['name']} (level {after['enemy']['level']}), moves {[m['name'] for m in after['enemy']['moves'] if m['name'] != 'Unknown']}")
    print(f"AFTER active:     {after['on_battle']['name']} (level {after['on_battle']['level']}), moves {[m['name'] for m in after['on_battle']['moves'] if m['name'] != 'Unknown']}")
    print(f"AFTER party:      {[(p['name'], p['level']) for p in after['party']]}")
    if after["battle_type"] == "trainer":
        print(f"AFTER opp. team:  {[(p['name'], p['level']) for p in after['enemy_party']]}")
        print(f"  (enemy_remaining_count: {after['enemy_remaining_count']})")
    print()


def run_manual(session, scene) -> None:
    """YOU play, using the keyboard directly (PyBoy's own SDL2 key mapping --
    nothing here reads your input or decides anything for you). This
    function only ticks the emulator and prints a snapshot of what our own
    code sees every ~10 real seconds, so you can compare what you're looking
    at on screen against what BattleScene/to_dict() reports -- e.g. open the
    FIGHT menu yourself and check the move names/PP shown here match what
    you see in-game."""
    print("Manual mode: play with the keyboard yourself (arrows, Z=A, X=B, Enter=Start).")
    print("Snapshot prints every 10s. Close the window (or Ctrl+C) to stop.\n")

    now = 0.0
    last_print = time.monotonic()
    try:
        while session.tick_once():
            now += 1 / 60
            if time.monotonic() - last_print >= 10.0:
                scene.update(now)
                d = scene.to_dict()
                print(f"[t+{time.monotonic() - last_print:.0f}s snapshot]")
                print(f"  phase={scene._phase} menu_top={scene.menu_top} menu_id={scene.menu_id}")
                print(f"  enemy:  {d['enemy']['name']} HP={d['enemy']['hp']}")
                print(f"  active: {d['on_battle']['name']} HP={d['on_battle']['hp']} "
                      f"moves={[(m['name'], m['pp']) for m in d['on_battle']['moves']]}")
                print(flush=True)
                last_print = time.monotonic()
    except KeyboardInterrupt:
        print("\nStopped by user.")


def run_auto(session, scene, mutation_info: dict) -> None:
    """The script drives one move by itself (real production wiring:
    EmulatorLoop + SceneManagerService + SceneController, real timing) --
    for confirming the pipeline works end-to-end without you touching
    anything. This is a demo, not something to run when YOU want to play."""
    print("Auto mode: the script itself will submit move_index=1 -- just watch.\n")

    class _FakeMQTTClient:
        def publish(self, *a, **kw):
            pass

    scene_manager = SceneManagerService(session, _FakeMQTTClient(), session.logger, poll_interval=0.5)
    controller = SceneController(scene_manager, session.logger)
    loop = EmulatorLoop(session, services=[scene_manager], button_cooldown=0.5, service_tick_interval=0.1)

    def _drive():
        print("Waiting for the battle scene...")
        deadline = time.monotonic() + 5.0
        while scene_manager.current_scene is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if scene_manager.current_scene is None:
            print("ERROR: no battle scene appeared")
            session.stop(save=False)
            return

        cmd = BattleCommand(kind="move", move_index=1)
        print("Submitting move_index=1 (our active Pokemon's first move slot)...")
        observation, reward, done, info = controller.step(cmd, timeout=60.0)
        print(f"Result: timeout={info.get('timeout')}, done={done}, reward={reward}")
        moves_after = observation.get("on_battle", {}).get("moves", [])
        print(f"Moves after: {[(m['name'], m['pp']) for m in moves_after]}")
        print("Leave the window open to keep looking, or close it to exit.")
        while session.tick_once():
            pass

    worker = threading.Thread(target=_drive, daemon=True)
    worker.start()
    loop.run()
    worker.join(timeout=5.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fixture", nargs="?", default="wild_charmander_vs_rattata.state")
    parser.add_argument(
        "--manual", action="store_true",
        help="You play with the keyboard yourself; the script only mutates + reports a snapshot every 10s. "
             "Without this flag, the script drives one move itself as a demo -- it will NOT wait for your input.",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for the random species/level picks (default: 42, reproducible).")
    parser.add_argument(
        "--party-size", type=int, default=None, choices=range(1, 7), metavar="1-6",
        help="Force OUR party to this many Pokemon (grows or shrinks it, writing PartyCount) instead of "
             "keeping whatever the fixture already has. E.g. --party-size 3 for a team of 3 to test switching.",
    )
    parser.add_argument(
        "--opponent-party-size", type=int, default=None, choices=range(1, 7), metavar="1-6",
        help="Force the OPPONENT TRAINER's whole roster to this many Pokemon (trainer battles only -- "
             "ignored on a wild fixture, which has no roster to speak of). E.g. --opponent-party-size 4 "
             "for a 4-Pokemon gym leader team.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    MoveROMBank._instance = None
    session = EmulatorSession(
        GameVersion.RED,
        save_state_path=os.path.join(FIXTURES_DIR, args.fixture),
        window="SDL2",
    )
    assert session.load_state_from_disk(), f"fixture failed to load: {args.fixture}"

    scene = create_battle_scene(session, 0)
    before_dict = scene.to_dict()  # static snapshot -- must be captured BEFORE mutating
    mutate_whole_battle(
        session, scene, rng,
        target_party_size=args.party_size,
        target_opponent_party_size=args.opponent_party_size,
    )
    scene_after = create_battle_scene(session, 0)
    print_before_after(before_dict, scene_after)

    if args.manual:
        run_manual(session, scene_after)
    else:
        run_auto(session, scene_after, {})

    session.stop(save=False)
    print("Done.")


if __name__ == "__main__":
    main()
