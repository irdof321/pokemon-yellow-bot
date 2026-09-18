"""Core, reusable battle-randomization logic -- mutates a REAL loaded battle
state's RAM in place (species/level/stats/moves/PP/name, for every slot on
both sides) into a fully synthetic scenario, so an RL training loop gets
effectively unlimited scenario diversity out of a small number of real
captured base fixtures.

Design decisions (agreed across a long back-and-forth -- see conversation):
  - Moves are picked FULLY AT RANDOM from all valid moves, not constrained to
    what the species could plausibly know. What the agent needs to learn is
    "given these move/type numbers, play well" -- not species-move trivia.
    Consistent, well-formed DATA (real power/accuracy/type/PP) is what
    matters, not plausibility of the species+move pairing.
  - Levels are drawn in MATCHED BANDS: both sides' whole rosters are leveled
    near the same randomly-picked band (+/- a small spread), not fully
    independently. Fully independent levels would produce too many
    "unwinnable no matter what" or "trivial no matter what" episodes --
    either way, the outcome stops depending on the agent's actual decisions,
    which wastes training signal.
  - Party SIZE (1-6) is independently random per side (not matched) -- a
    wild battle's opponent is always exactly 1 (no roster to speak of).
  - Stats themselves already reflect real game mechanics for free: real
    per-species base stats (data/base_stats_gen1.json, parsed from
    pret/pokered's own data/pokemon/base_stats/*.asm) + the real Gen1 stat
    formula + a random DV (0-15, same as the real game). "Stat exp" (a small
    real-game bonus from battling) is left at 0 everywhere, same as a
    freshly-encountered wild Pokemon -- a known, deliberate simplification.

No pre-generated dataset: rather than materializing thousands of .state
files upfront (storage that only grows, and a finite pool an RL training run
would eventually exhaust/repeat), a future reset() calls
load_random_base_battle() at the start of every episode -- picks one of a
small set of real base fixtures, loads it fresh, and randomizes it live, in
memory, never touching disk for the result. Not reproducible by default
(every call is a fresh random draw), but pass the same `rng` seed to get the
exact same draw back -- see load_random_base_battle's docstring.
"""
import json
import os

from game.core.emulator import EmulatorSession
from game.core.version import GameVersion
from game.data.data import POKDX_ID_TO_NAME, POKEMON_ROM_ID_TO_PKDX_ID, POKEMON_TYPES
from game.data.decoder import encode_pkm_text
from game.data.helpers import write_bytes, write_u8, write_u16
from game.data.pokemon import POKEMON_LAYOUT_PARTY
from game.data.ram_reader import MainPokemonData, MemoryData, MoveROMBank
from game.scenes.battle_scene import create_battle_scene

with open(os.path.join(os.path.dirname(__file__), "base_stats_gen1.json"), encoding="utf-8") as _f:
    BASE_STATS = {e["dex"]: e for e in json.load(_f)}

ALL_DEX = list(BASE_STATS.keys())

# Moves whose animation/menu flow spans more than one turn, or opens an extra
# submenu -- BattleScene's phase-detection logic assumes one command resolves
# in one turn, and doesn't recognize these. Confirmed via a random-policy
# diagnostic (2026-09-11, 40 episodes): MIMIC (opens a "pick which opposing
# move to copy" submenu) and SKY ATTACK (two-turn charge) alone accounted for
# 5 of 7 truncated (timed-out) episodes -- a concern real enough to have
# prompted an earlier is_locked_into_move feature for scripted/manual play,
# then reverted as "rare enough to skip" for that use case. It stops being
# rare once movesets are drawn uniformly at random across all 165 moves,
# every episode, at RL training scale: a meaningful fraction of episodes hit
# ONE of these and get thrown away as wasted training data. Excluded
# wholesale by mechanism (not just the 2 directly observed), since the rest
# share the same "spans multiple turns or opens an extra menu" root cause.
_MULTI_TURN_OR_MENU_MOVE_IDS = {
    13,   # RAZOR WIND  -- two-turn charge
    19,   # FLY         -- two-turn (invulnerable then strike)
    20,   # BIND        -- traps user+target 2-5 turns
    35,   # WRAP        -- traps user+target 2-5 turns
    37,   # THRASH      -- locked 3-4 turns, then confusion
    63,   # HYPER BEAM  -- forced recharge turn after
    76,   # SOLARBEAM   -- two-turn charge
    80,   # PETAL DANCE -- locked 3-4 turns, then confusion
    83,   # FIRE SPIN   -- traps user+target 2-5 turns
    91,   # DIG         -- two-turn charge (invulnerable then strike)
    99,   # RAGE        -- locks user into repeating it once used
    102,  # MIMIC       -- opens an extra move-selection submenu
    117,  # BIDE        -- multi-turn charge then release
    118,  # METRONOME   -- calls a random OTHER move, which could itself be one of these
    128,  # CLAMP       -- traps user+target 2-5 turns
    130,  # SKULL BASH  -- two-turn charge
    143,  # SKY ATTACK  -- two-turn charge
}
ALL_MOVE_IDS = [mid for mid in range(1, 166) if mid not in _MULTI_TURN_OR_MENU_MOVE_IDS]  # Gen1 has 165 defined moves, minus the ones above

PKDX_TO_ROM_ID = {v: k for k, v in POKEMON_ROM_ID_TO_PKDX_ID.items()}
TYPE_NAME_TO_ID = {name.upper(): tid for tid, name in POKEMON_TYPES.items()}
TYPE_NAME_TO_ID["PSYCHIC_TYPE"] = TYPE_NAME_TO_ID["PSYCHIC"]  # pokered's disambiguated name for the type (vs the move of the same name)

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
# Same 3, opponent trainer's roster instead of ours (0xD8A4-0xD9AB block +
# 0xD89D-0xD8A2 index array + the "_Alt" nickname block) -- meaningless for
# a wild battle, which has no opponent roster to speak of.
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


def calc_stat(base: int, dv: int, level: int) -> int:
    return ((base + dv) * 2 * level) // 100 + 5


def calc_hp(base: int, dv: int, level: int) -> int:
    return ((base + dv) * 2 * level) // 100 + level + 10


def exp_for_level(growth_rate: str, level: int) -> int:
    """Real Gen1 EXP-curve formulas (one of 4 per species, see
    growth_rate in base_stats_gen1.json) -- the minimum total EXP needed to
    BE at `level`. Needed because we set level/stats directly without ever
    touching the party struct's own 3-byte `experience` counter (found the
    hard way, 2026-09-10): a Pokemon we set to "level 30" but whose stored
    EXP still said "level 5" would win a battle, gain a small amount of
    EXP, and the game -- using ITS OWN stored EXP as ground truth, not the
    level byte we wrote -- would recompute/snap the level back down to
    what that stale EXP actually corresponds to. Writing an EXP value that
    matches the level we assign keeps the game's own logic consistent with
    what we set, instead of fighting it on the next level-up."""
    n = level
    if growth_rate == "GROWTH_FAST":
        return int(0.8 * n ** 3)
    if growth_rate == "GROWTH_MEDIUM_FAST":
        return n ** 3
    if growth_rate == "GROWTH_MEDIUM_SLOW":
        return max(0, int(1.2 * n ** 3 - 15 * n ** 2 + 100 * n - 140))
    if growth_rate == "GROWTH_SLOW":
        return int(1.25 * n ** 3)
    raise ValueError(f"unknown growth rate {growth_rate!r}")


def pick_matched_levels(rng, n_player: int, n_opponent: int, *,
                         level_min=5, level_max=65, relative_spread=0.04) -> tuple:
    """Both rosters leveled near the SAME randomly-picked band -- see the
    module docstring for why this matters more than it might seem. Returns
    (player_levels, opponent_levels), each a plain list of ints.

    Per-slot deviation from the band is Gaussian, not uniform, and its
    spread SCALES WITH the band (sigma = band * relative_spread) rather than
    being a fixed number of levels -- found the hard way (2026-09-10):
    a fixed +/-6 uniform spread let one teammate land at level 38 while
    another landed at 23 in the SAME team. +/-6 sounds small, but a 15-level
    gap AT THOSE LEVELS is a huge relative difference (Gen1 stats scale
    close to linearly with level, so 38 vs 23 is roughly a 1.6x power gap,
    not just "15 levels") -- one dead-weight teammate that can't
    meaningfully participate. Two fixes at once: Gaussian instead of
    uniform makes wide-spread draws rare rather than as likely as small
    ones, and scaling sigma with the band keeps the RELATIVE spread (not the
    absolute level count) roughly constant whether the band is 10 or 80.

    relative_spread=0.04 chosen by sweeping 0.03-0.15 and checking the
    within-team max-min gap over 2000 draws of a 6-member team (the worst
    case -- more members means a wider expected range even at the same
    sigma, since it's an order statistic): 0.04 gave 0/2000 draws with a
    gap >= 15, median gap 3, worst-case 12 -- still real variety, but the
    38-vs-23 scenario that prompted this essentially can't happen anymore."""
    band = rng.randint(level_min, level_max)
    sigma = max(1.0, band * relative_spread)

    def draw(n):
        return [max(2, min(100, round(rng.gauss(band, sigma)))) for _ in range(n)]

    return draw(n_player), draw(n_opponent)


def pick_random_moveset(rng) -> list:
    """4 distinct move IDs, fully at random -- see the module docstring for
    why plausibility doesn't matter here."""
    return rng.sample(ALL_MOVE_IDS, 4)


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


def _rel_field(base_addr: int, key: str) -> MemoryData:
    s_rel, e_rel = POKEMON_LAYOUT_PARTY[key]
    return MemoryData(base_addr + s_rel, base_addr + e_rel - 1)


def _write_computed_pokemon(session, target_dex: int, level: int, dv: int, move_ids: list) -> dict:
    """Computes everything derived from (species, level, dv, moves) once --
    shared by every write-site below (battle-active struct, party struct,
    opponent roster struct) so they can never disagree with each other."""
    stats = BASE_STATS[target_dex]
    move_pps = [MoveROMBank(session).get_move_bytes(mid)[5] for mid in move_ids]
    return {
        "rom_id": PKDX_TO_ROM_ID[target_dex],
        "type1_id": TYPE_NAME_TO_ID[stats["type1"]],
        "type2_id": TYPE_NAME_TO_ID[stats["type2"]],
        "max_hp": calc_hp(stats["hp"], dv, level),
        "attack": calc_stat(stats["attack"], dv, level),
        "defense": calc_stat(stats["defense"], dv, level),
        "speed": calc_stat(stats["speed"], dv, level),
        "special": calc_stat(stats["special"], dv, level),
        "move_ids": move_ids,
        "move_pps": move_pps,
    }


def mutate_battle_active(session, md_species, md_type1, md_type2, md_level, md_hp_cur, md_hp_max,
                          md_atk, md_def, md_spd, md_spc, md_dv1, md_dv2,
                          md_moves, md_pp, target_dex: int, level: int, dv: int, move_ids: list) -> None:
    """Shared write logic for the currently-active battle Pokemon (either
    side) -- addresses differ (enemy: scattered named fields; player:
    offsets within the D009-D030 struct), passed in explicitly rather than
    hardcoded so this one function covers both."""
    c = _write_computed_pokemon(session, target_dex, level, dv, move_ids)
    write_u8(md_species, c["rom_id"])
    write_u8(md_type1, c["type1_id"])
    write_u8(md_type2, c["type2_id"])
    write_u8(md_level, level)
    write_u16(md_hp_max, c["max_hp"])
    write_u16(md_hp_cur, c["max_hp"])
    write_u16(md_atk, c["attack"])
    write_u16(md_def, c["defense"])
    write_u16(md_spd, c["speed"])
    write_u16(md_spc, c["special"])
    write_u8(md_dv1, (dv << 4) | dv)
    write_u8(md_dv2, (dv << 4) | dv)
    for mv, md in zip(c["move_ids"], md_moves):
        write_u8(md, mv)
    for pp, md in zip(c["move_pps"], md_pp):
        write_u8(md, pp)


def mutate_enemy_to(session, target_dex: int, level: int, dv: int, move_ids: list) -> None:
    md = MainPokemonData
    mutate_battle_active(
        session, md.EnemyPokemonID, md.EnemyType1, md.EnemyType2, md.EnemyLevel,
        md.EnemyHP, md.EnemyMaxHP, md.EnemyAttack, md.EnemyDefense, md.EnemySpeed, md.EnemySpecial,
        md.EnemyIVsAtkDef, md.EnemyIVsSpdSpc,
        [md.EnemyMove1, md.EnemyMove2, md.EnemyMove3, md.EnemyMove4],
        [md.EnemyPP1, md.EnemyPP2, md.EnemyPP3, md.EnemyPP4],
        target_dex, level, dv, move_ids,
    )
    write_u8(md.EnemyPokemonID2, PKDX_TO_ROM_ID[target_dex])
    write_u8(md.EnemyLevel2, level)  # EnemyLevel ("DO NOT WORK") is a dead duplicate -- EnemyPokemon.level reads THIS one
    write_u8(md.EnemyCatchRate, BASE_STATS[target_dex]["catch_rate"])
    write_u8(md.EnemyBaseExp, BASE_STATS[target_dex]["base_exp"])
    write_species_name(md.EnemyName, target_dex)


def mutate_player_active_to(session, target_dex: int, level: int, dv: int, move_ids: list) -> None:
    md = MainPokemonData
    mutate_battle_active(
        session, md.PlayerPokemonNumber, md.PlayerType1, md.PlayerType2, md.PlayerLevel,
        md.PlayerCurrentHP, md.PlayerMaxHP, md.PlayerAttack, md.PlayerDefense, md.PlayerSpeed, md.PlayerSpecial,
        md.PlayerDVsAtkDef, md.PlayerDVsSpdSpc,
        [md.PlayerMove1, md.PlayerMove2, md.PlayerMove3, md.PlayerMove4],
        [md.PlayerPP1, md.PlayerPP2, md.PlayerPP3, md.PlayerPP4],
        target_dex, level, dv, move_ids,
    )
    write_species_name(md.PlayerPokemonName, target_dex)


def mutate_party_slot_to(
    session, slot: int, target_dex: int, level: int, dv: int, move_ids: list,
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
    c = _write_computed_pokemon(session, target_dex, level, dv, move_ids)

    write_u8(index_bytes[slot], c["rom_id"])
    write_u8(_rel_field(base, "id"), c["rom_id"])
    write_species_name(nicknames[slot], target_dex)
    write_u16(_rel_field(base, "current_hp"), c["max_hp"])
    write_u8(_rel_field(base, "type1"), c["type1_id"])
    write_u8(_rel_field(base, "type2"), c["type2_id"])
    write_u8(_rel_field(base, "level"), level)
    exp = exp_for_level(BASE_STATS[target_dex]["growth_rate"], level)
    exp_md = _rel_field(base, "experience")
    write_bytes(exp_md, [(exp >> 16) & 0xFF, (exp >> 8) & 0xFF, exp & 0xFF])  # 3 bytes, big-endian (matches read_u24)
    write_u16(_rel_field(base, "max_hp"), c["max_hp"])
    write_u16(_rel_field(base, "attack"), c["attack"])
    write_u16(_rel_field(base, "defense"), c["defense"])
    write_u16(_rel_field(base, "speed"), c["speed"])
    write_u8(_rel_field(base, "ivs"), (dv << 4) | dv)  # atk/def nibble; leave spd/spc byte as-is
    moves_s, _ = POKEMON_LAYOUT_PARTY["moves"]
    pp_s, _ = POKEMON_LAYOUT_PARTY["pp"]
    for i, mv in enumerate(c["move_ids"]):
        write_u8(MemoryData(base + moves_s + i, base + moves_s + i), mv)
    for i, pp in enumerate(c["move_pps"]):
        write_u8(MemoryData(base + pp_s + i, base + pp_s + i), pp)


def _mutate_roster(session, rng, levels: list, slot_blocks, index_bytes, nicknames, count_field, original_size: int) -> list:
    """Writes count_field + a 0xFF terminator (Gen1 party lists are
    terminated that way, not just by the count byte -- leaving stale bytes
    from the fixture past the new size risks a phantom extra "member" made
    of garbage) if the size changed, then mutates every slot with its own
    random species/moves at the given (already matched-band) level. Returns
    the list of {"dex", "level", "dv"} picks, slot 1 first."""
    target_size = len(levels)
    if target_size != original_size:
        write_u8(count_field, target_size)
        if target_size < 6:
            write_u8(index_bytes[target_size + 1], 0xFF)  # terminator

    picks = []
    for slot, level in enumerate(levels, start=1):
        dex = rng.choice(ALL_DEX)
        dv = rng.randint(0, 15)
        move_ids = pick_random_moveset(rng)
        mutate_party_slot_to(session, slot, dex, level, dv, move_ids,
                              slot_blocks=slot_blocks, index_bytes=index_bytes, nicknames=nicknames)
        picks.append({"dex": dex, "level": level, "dv": dv, "move_ids": move_ids})
    return picks


def randomize_battle(session, scene, rng, *, is_wild: bool,
                      player_party_size: int = None, opponent_party_size: int = None) -> dict:
    """Randomizes the WHOLE battle in place: our whole party (bench
    included) + the opponent's whole roster (or just the single wild
    encounter) -- fully random species/moves, matched-band levels, random
    party sizes (1-6 each side, opponent forced to 1 for a wild battle).

    player_party_size / opponent_party_size, if given, override the random
    1-6 draw (mainly for tests -- reproducible sizes). Returns
    {"player": [...], "opponent": [...]} picks, slot 1 first each,
    for callers that want to print/label things afterward.
    """
    original_player_size = len(scene.player_party)
    original_opponent_size = len(scene.enemy_party) if not is_wild else 1

    n_player = player_party_size if player_party_size is not None else rng.randint(1, 6)
    n_opponent = 1 if is_wild else (opponent_party_size if opponent_party_size is not None else rng.randint(1, 6))

    player_levels, opponent_levels = pick_matched_levels(rng, n_player, n_opponent)

    player_picks = _mutate_roster(
        session, rng, player_levels,
        PARTY_SLOT_BLOCKS, PARTY_INDEX_BYTE, PARTY_NICKNAME, MainPokemonData.PartyCount,
        original_player_size,
    )
    # Slot 1 (the active battler) exists in TWO places at once -- the battle
    # struct (D009+, used DURING this fight) and its own party struct
    # (D16B+, what "party" in to_dict() reads, i.e. what feeds the
    # observation vector). Both must get the SAME species/level/dv/moves,
    # not independently re-rolled, or the two views of "slot 1" would
    # disagree (found empirically -- see git history for this file).
    p1 = player_picks[0]
    mutate_player_active_to(session, p1["dex"], p1["level"], p1["dv"], p1["move_ids"])

    if is_wild:
        e1_dex, e1_level, e1_dv = rng.choice(ALL_DEX), opponent_levels[0], rng.randint(0, 15)
        e1_moves = pick_random_moveset(rng)
        mutate_enemy_to(session, e1_dex, e1_level, e1_dv, e1_moves)
        opponent_picks = [{"dex": e1_dex, "level": e1_level, "dv": e1_dv, "move_ids": e1_moves}]
    else:
        opponent_picks = _mutate_roster(
            session, rng, opponent_levels,
            OPPONENT_PARTY_SLOT_BLOCKS, OPPONENT_PARTY_INDEX_BYTE, OPPONENT_PARTY_NICKNAME,
            MainPokemonData.OpponentPartyCount, original_opponent_size,
        )
        e1 = opponent_picks[0]
        # Same slot-1 duplication as ours, see the comment above.
        mutate_enemy_to(session, e1["dex"], e1["level"], e1["dv"], e1["move_ids"])

    return {"player": player_picks, "opponent": opponent_picks}


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures", "battles")

# The 4 real base fixtures a future reset() draws from -- one wild
# encounter, one regular trainer, one gym leader, one rival (Blue), chosen
# because each plays out differently (a gym leader's roster/AI isn't like a
# regular trainer's). (name, is_wild) -- is_wild is also re-derived from the
# fixture's own battle_type at load time as a safety check, not trusted
# blindly from this table alone.
BASE_FIXTURES = [
    ("wild.state", True),
    ("trainer.state", False),
    ("gym_leader.state", False),
    ("blue.state", False),
]


def load_random_base_battle(rng, *, fixtures_dir: str = FIXTURES_DIR, base_fixtures: list = BASE_FIXTURES,
                             player_party_size: int = None, opponent_party_size: int = None,
                             window: str = "null"):
    """The function a future reset() calls at the start of every episode:
    picks one of the base fixtures at random, loads it fresh (a new
    EmulatorSession every time -- these are cheap, and this way nothing
    carries over from a previous episode), and randomizes it live. Never
    touches disk for the *result* -- nothing is saved. Headless by default
    (window="null", what training wants); pass window="SDL2" for a real
    window -- see scripts/play_random_battle.py, which does exactly that to
    let a human look at (and play) a randomized battle.

    Reproducible if you want it to be: `rng` is YOUR random.Random instance,
    passed in rather than created here -- seed it yourself
    (random.Random(seed)) for the exact same sequence of draws across runs;
    leave it seeded from entropy (random.Random()) for genuine randomness
    during real training.

    Returns (session, scene, picks) -- session/scene are the now-mutated,
    ready-to-play battle (same objects create_battle_scene always returns);
    picks is randomize_battle()'s own return value (what was chosen, for
    logging)."""
    fixture_name, expected_wild = rng.choice(base_fixtures)

    MoveROMBank._instance = None
    session = EmulatorSession(
        GameVersion.RED,
        save_state_path=os.path.join(fixtures_dir, fixture_name),
        window=window,
    )
    if not session.load_state_from_disk():
        raise RuntimeError(f"base fixture failed to load: {fixture_name}")

    scene = create_battle_scene(session, 0)
    is_wild = scene.to_dict()["battle_type"] == "wild"
    if is_wild != expected_wild:
        session.logger.warning(
            "{}: expected is_wild={} from BASE_FIXTURES but battle_type says {} -- using the real reading",
            fixture_name, expected_wild, "wild" if is_wild else "trainer",
        )

    picks = randomize_battle(
        session, scene, rng, is_wild=is_wild,
        player_party_size=player_party_size, opponent_party_size=opponent_party_size,
    )

    # BattleScene builds self.player_party/enemy_party ONCE, at construction
    # time, from whatever PartyCount/OpponentPartyCount read THEN -- if
    # randomize_battle() just changed the roster size, `scene` above still
    # holds the OLD, now-stale-length lists. Re-construct so the returned
    # scene actually reflects the new size (found empirically: to_dict()
    # kept showing the original party length no matter what size was
    # randomized to).
    scene = create_battle_scene(session, 0)
    return session, scene, picks
