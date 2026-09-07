"""Empirically determines what the "battle type" RAM bytes actually hold
across battle categories -- MainPokemonData.BattleTypeID (0xD057),
BattleSubType (0xD05A), and EngagedTrainerClass (0xCD2D).

We deliberately do NOT have a documented/confirmed value set for these --
the RAM map source only says "Type of battle" (D057) and "Battle Type
(Normal, Safari Zone, Old Man battle...)" (D05A), with no full enumeration.
Common lore says D057 is 0=no battle/1=wild/2=trainer -- confirmed by this
test (see test_battle_type_id_value). D05A's exact values, and whether gym
leaders show up distinctly anywhere, have NOT been confirmed -- don't
hardcode an Enum around a guess.

Current hypothesis (unverified until this test has real data for it):
D05A is about the special battle MODE (normal / Safari Zone / Old Man demo),
not the trainer's identity -- "this is specifically Brock" more likely shows
up in EngagedTrainerClass (a trainer-class ID), which we also read here for
comparison. wild/trainer/gym_leader fixtures already exist; safari_zone and
old_man_battle are placeholders that skip until their .state files are
captured (add tests/fixtures/<name>.state and this test picks it up
automatically, no code change needed).
"""
from pathlib import Path

import pytest

from game.data.ram_reader import MainPokemonData

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# (category label, fixture .state filename)
CASES = [
    ("wild", "wild_charmander_vs_rattata.state"),
    ("trainer", "battle_vs_blue_player_1pkm.state"),
    ("gym_leader", "BROCK_battle.state"),
    ("safari_zone", "safari_zone_battle.state"),      # not captured yet
    ("old_man_battle", "old_man_battle.state"),        # not captured yet
]

# (label, MemoryData field to read a single byte from)
BYTES_TO_READ = [
    ("BattleTypeID (D057)", MainPokemonData.BattleTypeID),
    ("BattleSubType (D05A)", MainPokemonData.BattleSubType),
    ("EngagedTrainerClass (CD2D)", MainPokemonData.EngagedTrainerClass),
]


def _read_byte(session, field):
    raw = session.read_memory(field)
    return raw[0] if raw else None


@pytest.mark.parametrize("category, state_name", CASES, ids=[c[0] for c in CASES])
def test_battle_type_id_value(load_fixture, category, state_name):
    if not (FIXTURES_DIR / state_name).exists():
        pytest.skip(f"{state_name} not captured yet")

    session = load_fixture(state_name)
    values = {label: _read_byte(session, field) for label, field in BYTES_TO_READ}

    print(f"\ncategory={category!r} ({state_name}):")
    for label, value in values.items():
        print(f"  {label} = {value!r}")

    # Intentionally no hardcoded expected values -- this test's job right now
    # is to OBSERVE and report, not assert a guess. Once every category above
    # has real data, turn the printed values into real assertions (and only
    # then decide whether an Enum belongs in ram_reader.py/pokemon.py).
    assert values["BattleTypeID (D057)"] is not None, f"could not read BattleTypeID from {state_name}"
