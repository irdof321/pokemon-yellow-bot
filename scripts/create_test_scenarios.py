"""Builds a small set of HAND-CRAFTED (not randomized) battle scenarios
where the "correct" play is knowable ahead of time -- a super-effective
move sitting right there, an active Pokemon with no realistic chance that
should be switched out immediately, and so on. Complements the aggregate
win_rate/truncation_rate metrics (which say "how often" but not "at what")
with a small, human-checkable set: play them yourself to see what YOU'D
do, or later point watch_agent.py-style tooling at them to see if the
agent makes the same obvious calls.

Saves each as tests/fixtures/scenarios/<name>.state + a matching .json
describing what's set up and what the expected right move is (same
fixture+json convention as tests/fixtures/*.json elsewhere in this repo).

Move IDs are looked up dynamically by (type, min power) instead of
hardcoded from memory -- see find_move_of_type -- so this stays correct
even if move-ID assumptions were ever wrong, and prints exactly what it
picked for a human to sanity-check.

Usage:
    python scripts/create_test_scenarios.py
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.core.emulator import EmulatorSession
from game.core.version import GameVersion
from game.data.helpers import write_u8, write_u16
from game.data.move import Move
from game.data.ram_reader import MainPokemonData, MoveROMBank
from game.scenes.battle_scene import create_battle_scene
from game.training.battle_randomizer import (
    ALL_MOVE_IDS,
    BASE_STATS,
    FIXTURES_DIR,
    OPPONENT_PARTY_INDEX_BYTE,
    OPPONENT_PARTY_NICKNAME,
    OPPONENT_PARTY_SLOT_BLOCKS,
    PARTY_INDEX_BYTE,
    PARTY_SLOT_BLOCKS,
    _rel_field,
    mutate_enemy_to,
    mutate_party_slot_to,
    mutate_player_active_to,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "scenarios")

# Dex numbers for well-known, unambiguously single/dual-typed Gen1 species --
# picked specifically to avoid any Gen1 type-chart edge cases (e.g. nothing
# Ghost/Psychic-related, where Gen1 famously has a real bug).
CHARMANDER, BULBASAUR, SQUIRTLE, PIDGEY, RATTATA, GEODUDE, CATERPIE = 4, 1, 7, 16, 19, 74, 10


def find_move_of_type(session, type_name: str, min_power: int = 1, max_power: int = 999) -> int:
    """First move ID (scanning in ID order, so the result is deterministic)
    matching a type and power range. min_power=0 finds a status move
    instead (useful for a deliberately weak filler)."""
    for mid in ALL_MOVE_IDS:
        mv = Move.load_from_id(session, mid)
        if mv.type.upper() == type_name.upper() and min_power <= mv.power <= max_power:
            return mid
    raise ValueError(f"no move found for type={type_name} power in [{min_power},{max_power}]")


def set_player_active(session, target_dex: int, level: int, dv: int, move_ids: list) -> None:
    """Writes slot 1 (the active battler) to BOTH of its two live copies --
    the battle struct (D009+, what actually drives this fight) AND the
    party struct's own slot-1 entry (D16B+, what the party list / PKMN
    menu reads). randomize_battle() already does both for exactly this
    reason (see its own comment); this script's first version only called
    mutate_player_active_to() and skipped mutate_party_slot_to(1, ...),
    so the battle itself used the right Pokemon but the party list still
    showed whatever the base fixture originally had in slot 1 -- found via
    manual play (2026-09-11), not caught by this script's own verification
    since that only checked on_battle (battle struct), never party[0]."""
    mutate_party_slot_to(session, 1, target_dex, level, dv, move_ids)
    mutate_player_active_to(session, target_dex, level, dv, move_ids)


def set_enemy_active(session, target_dex: int, level: int, dv: int, move_ids: list) -> None:
    """Opponent-side counterpart to set_player_active(): once the opponent
    HAS a roster (a trainer battle, not a wild one), its active battler
    also has two live copies -- the battle struct (Enemy* fields, what
    actually drives this fight) AND OPPONENT_PARTY_SLOT_BLOCKS[1] (what
    the opponent's OWN party list, i.e. enemy_party[0] in to_dict(),
    reads). Same duplicate-struct pattern as set_player_active, mirrored
    for the other side -- randomize_battle() does the same thing for a
    trainer's opponent roster."""
    mutate_party_slot_to(session, 1, target_dex, level, dv, move_ids,
                          slot_blocks=OPPONENT_PARTY_SLOT_BLOCKS, index_bytes=OPPONENT_PARTY_INDEX_BYTE,
                          nicknames=OPPONENT_PARTY_NICKNAME)
    mutate_enemy_to(session, target_dex, level, dv, move_ids)


def find_status_move(session, exclude_types: tuple = ()) -> int:
    """A 0-power (non-damaging) move, for a deliberately weak/irrelevant
    filler slot -- exclude_types avoids accidentally picking one that's
    still relevant to the scenario's own point."""
    for mid in ALL_MOVE_IDS:
        mv = Move.load_from_id(session, mid)
        if mv.power == 0 and mv.type.upper() not in {t.upper() for t in exclude_types}:
            return mid
    raise ValueError("no status move found")


def find_damaging_moves(session, rng: random.Random, count: int, exclude_ids: set = frozenset()) -> list:
    """count DISTINCT real damaging moves (power > 0), excluding exclude_ids
    -- for a moveset meant to be entirely real attacks, no 0-power status
    filler at all (unlike the other scenarios' build_typed_moveset /
    find_status_move fillers)."""
    candidates = [mid for mid in ALL_MOVE_IDS if mid not in exclude_ids]
    rng.shuffle(candidates)
    picked = []
    for mid in candidates:
        if Move.load_from_id(session, mid).power > 0:
            picked.append(mid)
            if len(picked) == count:
                return picked
    raise ValueError(f"could not find {count} damaging moves excluding {exclude_ids}")


def find_move_by_name(session, name: str) -> int:
    """Exact-name lookup (spellings confirmed empirically against the ROM,
    2026-09-11, e.g. 'POISONPOWDER' has no space but 'STUN SPORE' does --
    not guessed) -- for a SPECIFIC status effect (sleep/poison/paralysis)
    rather than just any 0-power move."""
    for mid in ALL_MOVE_IDS:
        mv = Move.load_from_id(session, mid)
        if mv.name.strip().upper() == name.upper():
            return mid
    raise ValueError(f"no move named {name!r} found")


def build_typed_moveset(session, rng: random.Random, own_type: str, status_move_name: str) -> list:
    """4 moves for a Pokemon that's meant to have a real, usable same-type
    attack: one damaging move of own_type and one specific status move
    (sleep/poison/paralysis -- see find_move_by_name), placed at RANDOM,
    DISTINCT slots (not always 1-then-2) so a caller can't just always
    press slot 1 without looking, plus 2 fully-random fillers in whatever
    slots are left."""
    own_move = find_move_of_type(session, own_type, min_power=1)
    status_move = find_move_by_name(session, status_move_name)
    fillers = [rng.choice(ALL_MOVE_IDS) for _ in range(2)]

    slots = [None, None, None, None]
    own_slot, status_slot = rng.sample(range(4), 2)
    slots[own_slot] = own_move
    slots[status_slot] = status_move
    remaining = [i for i in range(4) if slots[i] is None]
    for i, filler in zip(remaining, fillers):
        slots[i] = filler
    return slots, own_slot + 1  # 1-based slot the caller should pick


def new_session(base_fixture: str) -> tuple:
    MoveROMBank._instance = None
    session = EmulatorSession(GameVersion.RED, save_state_path=os.path.join(FIXTURES_DIR, base_fixture), window="null")
    if not session.load_state_from_disk():
        raise RuntimeError(f"base fixture failed to load: {base_fixture}")
    scene = create_battle_scene(session, 0)
    return session, scene


def save_scenario(session, name: str, description: str, expected: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    state_path = os.path.join(OUT_DIR, f"{name}.state")
    with open(state_path, "wb") as fh:
        session.write_live_state(fh)
    json_path = os.path.join(OUT_DIR, f"{name}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"description": description, "expected": expected}, fh, indent=2)
    print(f"Saved {state_path}")
    session.stop(save=False)


def scenario_super_effective_move():
    """Opponent is pure Grass/Poison (Bulbasaur) -- a Fire move is a clean
    2x, no Gen1 type-chart edge cases. Player's active is a Fire type
    (Charmander) with that Fire move in slot 1 and three deliberately
    non-damaging fillers in 2-4, so slot 1 is unambiguously the right
    pick -- no need to compare damage rolls, just "is it the attacking
    move at all"."""
    session, scene = new_session("wild.state")
    level = 20

    fire_move = find_move_of_type(session, "FIRE", min_power=1)
    filler1 = find_status_move(session, exclude_types=("FIRE",))
    filler2 = find_status_move(session, exclude_types=("FIRE",))
    filler3 = find_status_move(session, exclude_types=("FIRE",))
    moves = [fire_move, filler1, filler2, filler3]

    set_player_active(session, CHARMANDER, level, 8, moves)
    mutate_enemy_to(session, BULBASAUR, level, 8, [filler1, filler2, filler3, filler1])

    move_name = Move.load_from_id(session, fire_move).name
    print(f"  fire move picked: {move_name} (id {fire_move})")

    save_scenario(
        session, "01_super_effective_move",
        "Player's active (Charmander) has a Fire move in slot 1 against a "
        "Grass/Poison opponent (Bulbasaur) at the same level. Slots 2-4 are "
        "non-damaging filler moves.",
        {"correct_action": "move", "move_slot": 1, "reason": f"{move_name} is super-effective (Fire vs Grass); the other 3 slots don't damage at all"},
    )


def scenario_must_switch_no_chance():
    """Player's active (a level-5 Caterpie) is hopelessly outclassed by a
    much higher level opponent -- no move it has changes that outcome.
    Party slot 2 (a level-40 Charmander, same level as the opponent) has a
    WATER move -- double super-effective against Geodude's Rock/Ground
    typing (2x vs Rock, 2x vs Ground), a genuinely winnable fight, not
    just "same level". Correct play: switch to slot 2 immediately rather
    than attack with slot 1.

    First version of this scenario gave the rescuer a Fire move instead --
    found via manual play (2026-09-11) that Fire is resisted by Rock, so
    the "safe" switch target wasn't actually safe. Lesson: a rescuer needs
    its move checked against the SPECIFIC opponent's type(s), not just
    picked to vaguely match the rescuer's own species."""
    session, scene = new_session("wild.state")

    weak_moves = [find_status_move(session) for _ in range(4)]
    set_player_active(session, CATERPIE, 5, 8, weak_moves)
    water_move = find_move_of_type(session, "WATER", min_power=1)
    mutate_party_slot_to(session, 2, CHARMANDER, 40, 8, [water_move] + weak_moves[:3])
    mutate_enemy_to(session, GEODUDE, 40, 8, weak_moves)

    move_name = Move.load_from_id(session, water_move).name
    save_scenario(
        session, "02_must_switch_no_chance",
        "Player's active (Caterpie, level 5) is 35 levels below the "
        "opponent (Geodude, level 40) -- no move available changes the "
        f"outcome. Party slot 2 (Charmander, level 40) has {move_name} in "
        "slot 1, double super-effective against Geodude's Rock/Ground typing.",
        {"correct_action": "switch", "party_slot": 2, "reason": f"slot 1 (Caterpie, L5) cannot realistically win against a L40 opponent no matter what move is picked; slot 2 (Charmander, L40) has {move_name}, super-effective against Rock/Ground"},
    )


def scenario_defensive_switch_low_hp():
    """Player's active is healthy-typed and same level as the opponent,
    but at critically low current HP -- one more hit plausibly ends the
    battle. Party slot 2 (Pidgey) is at full HP AND has a real Normal
    move, so switching to it is an actual winnable continuation, not just
    a stall -- Rattata (opponent) is pure Normal, no resistance to worry
    about. Correct play: switch to preserve the team rather than risk
    fainting for no gain.

    First version gave Pidgey 4 status moves (0 damage), so "switch" didn't
    lead anywhere -- found via manual play (2026-09-11): a rescuer needs to
    be able to actually finish the fight, not just survive one turn."""
    session, scene = new_session("wild.state")
    level = 30
    weak_moves = [find_status_move(session) for _ in range(4)]
    rescuer_move = find_move_of_type(session, "NORMAL", min_power=1)

    set_player_active(session, SQUIRTLE, level, 8, weak_moves)
    # current_hp set low AFTER set_player_active (which sets both copies to
    # full max_hp) -- same pattern battle_randomizer itself documents:
    # write the derived stat first, then override current_hp specifically.
    # Both copies again (battle struct AND party struct slot 1), same
    # reason set_player_active exists at all -- otherwise the party
    # menu/PKMN screen would show slot 1 back at full HP.
    write_u16(MainPokemonData.PlayerCurrentHP, 3)
    write_u16(_rel_field(PARTY_SLOT_BLOCKS[1].start_address, "current_hp"), 3)

    mutate_party_slot_to(session, 2, PIDGEY, level, 8, [rescuer_move] + weak_moves[:3])
    mutate_enemy_to(session, RATTATA, level, 8, weak_moves)

    move_name = Move.load_from_id(session, rescuer_move).name
    save_scenario(
        session, "03_defensive_switch_low_hp",
        "Player's active (Squirtle, level 30) is at 3 HP against a "
        "same-level opponent (Rattata, pure Normal) -- one more hit "
        f"plausibly faints it. Party slot 2 (Pidgey, level 30) is at full "
        f"HP and has {move_name} (slot 1) to actually fight back.",
        {"correct_action": "switch", "party_slot": 2, "reason": "slot 1 is one hit from fainting for no benefit; slot 2 is healthy and can actually win, not just stall"},
    )


def scenario_easy_closeout():
    """Opponent is at 1 HP -- literally any damaging move ends the battle
    this turn. Player's active is healthy. Correct play: use any
    damaging move (slot 1 here) rather than switch or use a status move."""
    session, scene = new_session("wild.state")
    level = 25
    weak_moves = [find_status_move(session) for _ in range(3)]
    damaging = find_move_of_type(session, "NORMAL", min_power=1)

    set_player_active(session, SQUIRTLE, level, 8, [damaging] + weak_moves)
    mutate_enemy_to(session, RATTATA, level, 8, weak_moves + [weak_moves[0]])
    write_u16(MainPokemonData.EnemyHP, 1)

    move_name = Move.load_from_id(session, damaging).name
    save_scenario(
        session, "04_easy_closeout",
        f"Opponent (Rattata, level {level}) is at 1 HP. Player's active "
        f"(Squirtle, same level, healthy) has a damaging move ({move_name}) "
        "in slot 1.",
        {"correct_action": "move", "move_slot": 1, "reason": "opponent is at 1 HP -- any damaging move wins immediately"},
    )


def scenario_switch_then_sweep():
    """A full 3-vs-4 trainer battle -- the starter type triangle on both
    sides. Opponent roster: Squirtle/Water (ACTIVE), Charmander/Fire,
    Bulbasaur/Grass. Player roster: Charmander/Fire (ACTIVE -- a
    DELIBERATELY bad matchup, resisted by the opponent's Water lead),
    Squirtle/Water, Bulbasaur/Grass, plus a very-low-level Rattata/Normal
    filler in slot 4 that isn't meant to be used. Correct FIRST play:
    switch away from the resisted Fire active to the Grass teammate
    (super-effective against the opponent's Water lead) rather than
    attack into a bad matchup. What the opponent sends out next (Fire or
    Grass) determines whether a SECOND switch is later correct too, but
    that depends on how the fight actually plays out (who lands a hit
    first, whether a status move connects) -- this scenario, like the
    others, only anchors "expected" to the first decision; the full
    roster is stated upfront so whoever plays it (human or agent) has the
    same information a real trainer encounter gives at turn 1.

    Uses trainer.state (not wild.state) since a wild battle has no
    opponent roster to speak of -- both sides' slot 1 need BOTH of their
    live copies written (see set_player_active / set_enemy_active),
    exactly like randomize_battle() does for a real trainer fight.

    Every trio member's moveset comes from build_typed_moveset(): a real
    damaging move of its OWN type sits at a RANDOM slot (not always slot
    1, per the user's ask) alongside one genuine status move
    (sleep/poison/paralysis) and 2 random fillers -- "just press slot 1"
    is not a safe shortcut here."""
    session, scene = new_session("trainer.state")
    rng = random.Random(5)
    level = 30
    filler_level = 5
    dv = 10

    # --- player roster: Fire (active, bad matchup), Water, Grass, low-level Normal filler ---
    fire_moves, fire_slot = build_typed_moveset(session, rng, "FIRE", "SLEEP POWDER")
    set_player_active(session, CHARMANDER, level, dv, fire_moves)

    water_moves, water_slot = build_typed_moveset(session, rng, "WATER", "POISONPOWDER")
    mutate_party_slot_to(session, 2, SQUIRTLE, level, dv, water_moves)

    grass_moves, grass_slot = build_typed_moveset(session, rng, "GRASS", "STUN SPORE")
    mutate_party_slot_to(session, 3, BULBASAUR, level, dv, grass_moves)

    filler_moves, _ = build_typed_moveset(session, rng, "NORMAL", "THUNDER WAVE")
    mutate_party_slot_to(session, 4, RATTATA, filler_level, dv, filler_moves)

    write_u8(MainPokemonData.PartyCount, 4)
    write_u8(PARTY_INDEX_BYTE[5], 0xFF)

    # --- opponent roster: Water (active), Fire, Grass -- the same triangle, mirrored ---
    e_water_moves, e_water_slot = build_typed_moveset(session, rng, "WATER", "SLEEP POWDER")
    set_enemy_active(session, SQUIRTLE, level, dv, e_water_moves)

    e_fire_moves, e_fire_slot = build_typed_moveset(session, rng, "FIRE", "POISONPOWDER")
    mutate_party_slot_to(session, 2, CHARMANDER, level, dv, e_fire_moves,
                          slot_blocks=OPPONENT_PARTY_SLOT_BLOCKS, index_bytes=OPPONENT_PARTY_INDEX_BYTE,
                          nicknames=OPPONENT_PARTY_NICKNAME)

    e_grass_moves, e_grass_slot = build_typed_moveset(session, rng, "GRASS", "STUN SPORE")
    mutate_party_slot_to(session, 3, BULBASAUR, level, dv, e_grass_moves,
                          slot_blocks=OPPONENT_PARTY_SLOT_BLOCKS, index_bytes=OPPONENT_PARTY_INDEX_BYTE,
                          nicknames=OPPONENT_PARTY_NICKNAME)

    write_u8(MainPokemonData.OpponentPartyCount, 3)
    write_u8(OPPONENT_PARTY_INDEX_BYTE[4], 0xFF)

    save_scenario(
        session, "05_switch_then_sweep",
        f"3v4 trainer battle. Opponent (level {level}): Squirtle/Water "
        f"ACTIVE (own move in slot {e_water_slot}), Charmander/Fire (own "
        f"move in slot {e_fire_slot}), Bulbasaur/Grass (own move in slot "
        f"{e_grass_slot}). Player (level {level} except the filler): "
        f"Charmander/Fire ACTIVE (own move in slot {fire_slot}), Squirtle/"
        f"Water (own move in slot {water_slot}), Bulbasaur/Grass (own move "
        f"in slot {grass_slot}), plus a level-{filler_level} Rattata/Normal "
        "filler in slot 4. Every trio member (both sides) also carries one "
        "genuine status move (sleep/poison/paralysis) mixed into its "
        "moveset, at a random slot.",
        {
            "correct_action": "switch", "party_slot": 3,
            "reason": "player's active (Charmander, Fire) is resisted by the opponent's active "
                      "(Squirtle, Water); party slot 3 (Bulbasaur, Grass) is super-effective against "
                      "Water -- switch there first rather than attacking into the bad matchup",
        },
    )


def scenario_overwhelming_level_advantage():
    """The mirror image of scenario_must_switch_no_chance: instead of the
    PLAYER being hopelessly outclassed, the OPPONENT's whole roster is --
    3 Rattata, all level 5, against the player's 3 Pokemon all at level
    50. Every moveset here (both sides, all 4 slots) is a REAL damaging
    move -- no 0-power status filler at all, per the user's ask, since the
    point isn't move quality or type reasoning (a 45-level gap already
    guarantees a win against a plain Rattata regardless of which slot is
    picked). The actual point is a MULTI-TURN one, not a first-move one
    like the other scenarios: after KOing one of the opponent's 3
    Rattata, does the agent needlessly switch its own (still healthy,
    massively favored) active Pokemon instead of just continuing to
    attack? "expected" below is only the first turn (for consistency with
    the other scenarios' json shape), but the real thing to watch when
    playing this one all the way through is whether it EVER switches --
    it never has a good reason to."""
    session, scene = new_session("trainer.state")
    rng = random.Random(6)
    level = 50
    opp_level = 5
    dv = 10

    fire_move = find_move_of_type(session, "FIRE", min_power=1)
    fire_fillers = find_damaging_moves(session, rng, 3, exclude_ids={fire_move})
    set_player_active(session, CHARMANDER, level, dv, [fire_move] + fire_fillers)

    water_move = find_move_of_type(session, "WATER", min_power=1)
    water_fillers = find_damaging_moves(session, rng, 3, exclude_ids={water_move})
    mutate_party_slot_to(session, 2, SQUIRTLE, level, dv, [water_move] + water_fillers)

    grass_move = find_move_of_type(session, "GRASS", min_power=1)
    grass_fillers = find_damaging_moves(session, rng, 3, exclude_ids={grass_move})
    mutate_party_slot_to(session, 3, BULBASAUR, level, dv, [grass_move] + grass_fillers)

    write_u8(MainPokemonData.PartyCount, 3)
    write_u8(PARTY_INDEX_BYTE[4], 0xFF)

    opp_moves = find_damaging_moves(session, rng, 4)
    set_enemy_active(session, RATTATA, opp_level, dv, opp_moves)
    mutate_party_slot_to(session, 2, RATTATA, opp_level, dv, opp_moves,
                          slot_blocks=OPPONENT_PARTY_SLOT_BLOCKS, index_bytes=OPPONENT_PARTY_INDEX_BYTE,
                          nicknames=OPPONENT_PARTY_NICKNAME)
    mutate_party_slot_to(session, 3, RATTATA, opp_level, dv, opp_moves,
                          slot_blocks=OPPONENT_PARTY_SLOT_BLOCKS, index_bytes=OPPONENT_PARTY_INDEX_BYTE,
                          nicknames=OPPONENT_PARTY_NICKNAME)

    write_u8(MainPokemonData.OpponentPartyCount, 3)
    write_u8(OPPONENT_PARTY_INDEX_BYTE[4], 0xFF)

    move_name = Move.load_from_id(session, fire_move).name
    save_scenario(
        session, "06_overwhelming_level_advantage",
        f"3v3 trainer battle. Opponent: 3x Rattata, all level {opp_level}, "
        "all 4 move slots real damaging attacks (no status moves anywhere "
        f"in this scenario). Player: Charmander/Fire ACTIVE (level {level}, "
        f"{move_name} in slot 1), Squirtle/Water (level {level}), Bulbasaur/"
        f"Grass (level {level}) -- same, all 4 slots deal damage. A "
        "45-level gap on every matchup.",
        {
            "correct_action": "move", "move_slot": 1,
            "reason": f"a {level - opp_level}-level advantage over a plain Rattata means any damaging move wins "
                      "comfortably; the real question is across the WHOLE fight, not just turn 1 -- after KOing "
                      "one of the opponent's 3 Rattata, does the agent ever switch its own healthy, massively "
                      "favored active Pokemon instead of continuing to attack? It never needs to.",
        },
    )


def main() -> None:
    scenario_super_effective_move()
    scenario_must_switch_no_chance()
    scenario_defensive_switch_low_hp()
    scenario_easy_closeout()
    scenario_switch_then_sweep()
    scenario_overwhelming_level_advantage()
    print(f"\nAll scenarios saved under {OUT_DIR}")


if __name__ == "__main__":
    main()
