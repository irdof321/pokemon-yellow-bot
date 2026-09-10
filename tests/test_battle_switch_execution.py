"""End-to-end switch execution tests -- mirrors test_battle_move_selection.py /
test_battle_move_edge_cases.py, but for BattleCommand(kind="switch").

FORCED_STATE (ratata_just_died.state) is captured: active Pokemon (a
nicknamed Rattata, party slot 6) has just fainted -- HP is 0, but the save
is at the "<name> fainted!" message, menu_top=(5,12), NOT yet at the actual
party-select screen. Reaching (0,1) (is_forced_switch_pending becoming True)
requires driving forward first: the game shows "<name> fainted!" then "Use
next POKeMON? YES/NO" (YES default) before opening the party list, and
_ensure_ready_main_menu now presses A through both automatically as soon as
current_hp == 0 -- regardless of whether a switch command has been decided
yet. test_forced_switch_after_faint_activates_correct_pokemon drives that
idle advance itself before submitting the switch command, so it also
exercises that fix, not just _execute_switch's phase 2-4.

VOLUNTARY_STATE (battle_party_select_screen.state) is captured: a full
6-member party (Charmander active, Caterpie, Pikachu, 3x Rattata, see its
.json), saved at the ready main menu (FIGHT, menu_id=0) -- the party-select
screen itself is reached by driving from there (FIGHT -> PKMN -> A), not
baked into the save. 6 members means switch tests can rotate across several
different slots instead of a single alive/dead pair -- see
test_switch_rotation_across_multiple_slots below.

Also note: even once those fixtures exist, _execute_switch still bails out
immediately (returns True/"completed" without touching the game) as long as
MenuLocation.POKEMON_SELECTION / POKEMON_SUB_MENU stay at their (-1,-1)
sentinel -- see the explicit error log at the top of _execute_switch. Use
test_switch_menu_coords.py::test_switch_menu_coords (already written) to read
the real coordinates off those fixtures first, then patch MenuLocation by
hand. Until that patch happens, the tests below will FAIL LOUDLY (wrong
species_id) rather than silently pass -- that failure is the signal that the
code-side patch is still needed, not a bug in these tests.

IMPORTANT, learned from the moves side of this codebase: _execute_switch
computes `target_index = party_slot - 1`, the SAME style of calculation that
turned out to be wrong for moves (BattleScene._execute_move needed
target_id = move_index, NOT move_index - 1 -- see its docstring). Don't
assume switch's formula is correct by analogy to moves, or to itself. These
tests are written to empirically CONFIRM OR REFUTE it against real RAM --
each assertion checks the ACTUAL resulting active Pokemon by identity
(species_id), not just "did some switch happen" -- so an off-by-one shows up
as a clear, specific failure (wrong species_id) rather than a false pass.
"""
from pathlib import Path

import pytest

from game.data.ram_reader import MainPokemonData
from game.scenes.battle_scene import create_battle_scene
from game.scenes.commands import BattleCommand

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VOLUNTARY_STATE = "battle_party_select_screen.state"
FORCED_STATE = "ratata_just_died.state"


def _require_fixture(name: str) -> None:
    if not (FIXTURES_DIR / name).exists():
        pytest.skip(f"{name} not captured yet -- see tests/fixtures/README.md")


def test_voluntary_switch_to_slot_2_activates_correct_pokemon(load_fixture, drive_scene):
    """Submits BattleCommand(kind='switch', party_slot=2) from the main
    battle menu (voluntary path: FIGHT -> PKMN -> party list -> SWITCH) and
    confirms the ACTIVE Pokemon afterwards is exactly the one that was in
    slot 2 beforehand -- not slot 1 or slot 3, which is exactly what an
    off-by-one in target_index would produce."""
    _require_fixture(VOLUNTARY_STATE)
    session = load_fixture(VOLUNTARY_STATE)
    scene = create_battle_scene(session, 0)

    target_slot = 2
    assert len(scene.player_party) >= target_slot, (
        f"{VOLUNTARY_STATE} needs at least {target_slot} party members for this test"
    )
    assert target_slot in scene.eligible_switch_slots, (
        f"{VOLUNTARY_STATE} should have slot {target_slot} alive and not already active"
    )
    expected_species = scene.player_party[target_slot - 1].species_id

    cmd = BattleCommand(kind="switch", party_slot=target_slot)
    completed = drive_scene(session, scene, cmd, max_frames=6000)

    assert completed, f"switch to party_slot={target_slot} never completed"
    assert scene.is_ready_main_menu

    assert scene.player_active.species_id == expected_species, (
        f"active Pokemon after switching to party_slot={target_slot} has "
        f"species_id={scene.player_active.species_id}, expected {expected_species} "
        "(slot 2's species before the switch) -- if this instead matches slot 1 or "
        "slot 3's species, that's the same off-by-one class of bug already found "
        "and fixed in _execute_move (see its docstring)."
    )


def test_switch_rotation_across_multiple_slots(load_fixture, drive_scene):
    """Switches through several different party slots in the SAME battle, one
    after another -- not just a single pair. This is exactly the kind of
    coverage that caught the target_id off-by-one for moves: rotating
    between only 2 slots could hide an off-by-one that happens to land on
    the right neighbor by luck. Uses battle_party_select_screen.state's full
    6-member party (Charmander active, Caterpie, Pikachu, 3x Rattata).

    The rotation deliberately jumps around (3, then 5, then 2, then back to
    1) instead of a simple 1<->2 back-and-forth, so an off-by-one lands on a
    visibly wrong species at some point rather than a coincidentally correct
    neighbor."""
    _require_fixture(VOLUNTARY_STATE)
    session = load_fixture(VOLUNTARY_STATE)
    scene = create_battle_scene(session, 0)

    assert len(scene.player_party) == 6, f"{VOLUNTARY_STATE} should have a full 6-member party"
    species_by_slot = {i: p.species_id for i, p in enumerate(scene.player_party, start=1)}

    for target_slot in (3, 5, 2, 1):
        assert target_slot in scene.eligible_switch_slots, (
            f"party_slot={target_slot} should be eligible before this switch "
            f"(eligible_switch_slots={scene.eligible_switch_slots})"
        )

        cmd = BattleCommand(kind="switch", party_slot=target_slot)
        completed = drive_scene(session, scene, cmd, max_frames=6000)

        assert completed, f"switch to party_slot={target_slot} never completed"
        assert scene.is_ready_main_menu, f"not back at ready main menu after switching to {target_slot}"
        assert scene.player_active.species_id == species_by_slot[target_slot], (
            f"after switching to party_slot={target_slot}, active species_id="
            f"{scene.player_active.species_id}, expected {species_by_slot[target_slot]} "
            f"(slot {target_slot}'s species before any switching started) -- if this instead "
            "matches a NEIGHBORING slot's species, that's the same off-by-one class of bug "
            "already found and fixed in _execute_move (see its docstring)."
        )
        assert target_slot not in scene.eligible_switch_slots, (
            f"the slot we just switched TO ({target_slot}) should no longer be eligible"
        )


def test_voluntary_switch_updates_menu_current_party_index(load_fixture, drive_scene):
    """MenuCurrentPartyIndex (0xCC2F) is used elsewhere (eligible_switch_slots)
    as a 0-based active-slot indicator -- confirms it actually updates to the
    new active slot after a real switch, not just that the switch happened."""
    _require_fixture(VOLUNTARY_STATE)
    session = load_fixture(VOLUNTARY_STATE)
    scene = create_battle_scene(session, 0)

    target_slot = 2
    assert target_slot in scene.eligible_switch_slots

    cmd = BattleCommand(kind="switch", party_slot=target_slot)
    assert drive_scene(session, scene, cmd, max_frames=6000)

    raw = session.read_memory(MainPokemonData.MenuCurrentPartyIndex)
    active_slot_after = (raw[0] + 1) if raw else None
    assert active_slot_after == target_slot, (
        f"MenuCurrentPartyIndex reads slot {active_slot_after} after switching to "
        f"{target_slot} -- expected it to track the new active slot (0-based)."
    )


def test_voluntary_switch_updates_eligible_slots(load_fixture, drive_scene):
    """After switching to slot 2, slot 2 must no longer be an eligible switch
    target (it's now the active Pokemon)."""
    _require_fixture(VOLUNTARY_STATE)
    session = load_fixture(VOLUNTARY_STATE)
    scene = create_battle_scene(session, 0)

    target_slot = 2
    assert target_slot in scene.eligible_switch_slots

    cmd = BattleCommand(kind="switch", party_slot=target_slot)
    assert drive_scene(session, scene, cmd, max_frames=6000)

    assert target_slot not in scene.eligible_switch_slots, (
        "the slot we just switched TO should no longer be an eligible switch target"
    )


def test_forced_switch_after_faint_activates_correct_pokemon(load_fixture, drive_until, drive_scene):
    """FORCED_STATE is saved at the "<name> fainted!" message, not yet at the
    party-select screen -- first drive the idle advance (no command active)
    through "fainted!" and "Use next POKeMON? YES/NO" to confirm
    _ensure_ready_main_menu's current_hp==0 branch actually gets there on its
    own. Then submit a switch command for an eligible slot and confirm it
    completes correctly and brings in a Pokemon that's actually alive."""
    _require_fixture(FORCED_STATE)
    session = load_fixture(FORCED_STATE)
    scene = create_battle_scene(session, 0)

    assert scene.player_active.current_hp == 0, f"{FORCED_STATE} should start with a fainted active Pokemon"

    reached = drive_until(session, scene, lambda: scene.is_forced_switch_pending, max_frames=3000)
    assert reached, (
        "never reached the forced party-select screen from the 'fainted!' message -- "
        "_ensure_ready_main_menu's current_hp==0 branch should press A through both "
        "'fainted!' and 'Use next POKeMON?' on its own, with no command active"
    )

    eligible = scene.eligible_switch_slots
    assert eligible, f"{FORCED_STATE} needs at least one alive, non-active party member"
    target_slot = eligible[0]
    expected_species = scene.player_party[target_slot - 1].species_id

    cmd = BattleCommand(kind="switch", party_slot=target_slot)
    completed = drive_scene(session, scene, cmd, max_frames=6000)

    assert completed, f"forced switch to party_slot={target_slot} never completed"
    assert scene.player_active.species_id == expected_species, (
        f"active Pokemon after the forced switch has species_id="
        f"{scene.player_active.species_id}, expected {expected_species}"
    )
    assert scene.player_active.current_hp > 0, "the newly active Pokemon must not be fainted"
