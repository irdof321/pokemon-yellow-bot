"""Confirms MenuCurrentPartyIndex (0xCC2F) is 0-based, using EXISTING fixtures
(every one of them has party slot 1 already active with no switch having
occurred, so this needed no new capture -- empirically confirmed 2026-09-07).

This file used to also have a second test that printed raw (X,Y) coordinates
for the party-select screen and the SWITCH/STATS/CANCEL sub-menu, to help
hand-fill MenuLocation.POKEMON_SELECTION / POKEMON_SUB_MENU. That job is
done (both are confirmed: (0,1) and (12,12) -- see BattleScene.MenuLocation)
and the actual behavior they enable is covered end-to-end by
test_battle_switch_execution.py, so it didn't belong here labeled as a
"test" -- it never asserted anything, it was a one-off discovery tool. Moved
to scripts/discover_switch_menu_coords.py, updated to use the fixtures that
actually exist now (battle_party_select_screen.state, ratata_just_died.state)
instead of the never-captured placeholder names this file used to reference.
"""
import pytest

from game.data.ram_reader import MainPokemonData

EXISTING_SLOT1_ACTIVE_FIXTURES = [
    "wild_charmander_vs_rattata.state",
    "battle_vs_blue_player_1pkm.state",
    "battle_must_go_on_fight.state",
    "wild_ratatta_par.state",
]


@pytest.mark.parametrize("state_name", EXISTING_SLOT1_ACTIVE_FIXTURES)
def test_menu_current_party_index_is_zero_based(load_fixture, state_name):
    session = load_fixture(state_name)
    raw = session.read_memory(MainPokemonData.MenuCurrentPartyIndex)
    value = raw[0] if raw else None
    # Every one of these fixtures has slot 1 (the first party member) active,
    # with no switch ever having occurred -- so a 0-based index reads 0.
    assert value == 0, (
        f"{state_name}: expected MenuCurrentPartyIndex=0 (0-based, slot 1 active), "
        f"got {value!r} -- if this ever fails, the indexing base assumption in "
        f"BattleScene.eligible_switch_slots (active_slot = raw + 1) needs revisiting."
    )
