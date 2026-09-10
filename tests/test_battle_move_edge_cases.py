"""battle_user_mult_and_adv_mult.state: Charmander (active) has only 3 moves
(Scratch/Growl/Ember) -- slot 4 is empty.
"""
from dataclasses import dataclass

from game.data.ram_reader import MainPokemonData
from game.scenes.battle_scene import create_battle_scene, filter_eligible_move_slots
from game.scenes.commands import BattleCommand

STATE_NAME = "battle_user_mult_and_adv_mult.state"


def _pp(scene, slot_index: int):
    return scene.to_dict()["on_battle"]["moves"][slot_index]["pp"]


@dataclass
class FakeMove:
    id: int


def test_filter_eligible_move_slots_excludes_empty_ids():
    moves = [FakeMove(id=33), FakeMove(id=45), FakeMove(id=52), FakeMove(id=0)]
    assert filter_eligible_move_slots(moves) == [1, 2, 3]


def test_filter_eligible_move_slots_all_empty():
    moves = [FakeMove(id=0)] * 4
    assert filter_eligible_move_slots(moves) == []


def test_eligible_move_slots_on_real_fixture(load_fixture):
    """Charmander here has Scratch/Growl/Ember and an empty 4th slot (see
    module docstring) -- confirms eligible_move_slots against real RAM, not
    just fake objects."""
    session = load_fixture(STATE_NAME)
    scene = create_battle_scene(session, 0)
    assert scene.eligible_move_slots == [1, 2, 3]


def test_move_4_does_not_complete_no_such_slot(load_fixture, drive_scene):
    """Move 4 has no real slot for this Pokemon. BattleScene itself still has
    no internal validation -- enforcement lives at the BattleService boundary
    (mirroring eligible_switch_slots), not inside BattleScene -- so enqueueing
    directly onto the scene like this test does, bypassing BattleService
    entirely, still drives the cursor toward a menu_id that never appears and
    never completes. The actual guard is exercised at the service level: see
    filter_eligible_move_slots and BattleService._on_battle_message's
    eligible_move_slots check.
    """
    session = load_fixture(STATE_NAME)
    scene = create_battle_scene(session, 0)

    cmd = BattleCommand(kind="move", move_index=4)
    completed = drive_scene(session, scene, cmd, max_frames=600)

    assert not completed, (
        "move_index=4 unexpectedly completed when enqueued directly on the scene "
        "-- BattleScene's own execution logic apparently changed; this test only "
        "covers the scene layer, not the BattleService-level rejection."
    )


def test_move_1_selects_scratch(load_fixture, drive_scene):
    """Sanity baseline: move_index=1 works correctly -- this is the same case
    already covered on a different fixture in test_battle_move_selection.py,
    repeated here as a baseline alongside the other move indices below."""
    session = load_fixture(STATE_NAME)
    scene = create_battle_scene(session, 0)
    scratch_pp_before = _pp(scene, 0)[0]

    cmd = BattleCommand(kind="move", move_index=1)
    assert drive_scene(session, scene, cmd, max_frames=6000)
    assert scene.is_ready_main_menu

    assert _pp(scene, 0)[0] == scratch_pp_before - 1
    assert session.read_memory(MainPokemonData.BattlePlayerMove)[0] == 10  # Scratch's ROM move ID


def test_move_2_selects_growl_not_scratch(load_fixture, drive_scene):
    session = load_fixture(STATE_NAME)
    scene = create_battle_scene(session, 0)
    scratch_pp_before = _pp(scene, 0)[0]
    growl_pp_before = _pp(scene, 1)[0]

    cmd = BattleCommand(kind="move", move_index=2)
    assert drive_scene(session, scene, cmd, max_frames=6000)
    assert scene.is_ready_main_menu

    assert _pp(scene, 0)[0] == scratch_pp_before, "Scratch's PP should NOT have moved"
    assert _pp(scene, 1)[0] == growl_pp_before - 1, "Growl's PP should have dropped by 1"


def test_three_turn_rotation_move1_move2_move1(load_fixture, drive_scene):
    session = load_fixture(STATE_NAME)
    scene = create_battle_scene(session, 0)

    scratch_pp = _pp(scene, 0)[0]
    growl_pp = _pp(scene, 1)[0]

    for move_index, slot_index in [(1, 0), (2, 1), (1, 0)]:
        cmd = BattleCommand(kind="move", move_index=move_index)
        completed = drive_scene(session, scene, cmd, max_frames=6000)
        assert completed, f"turn selecting move_index={move_index} never completed"
        assert scene.is_ready_main_menu, f"not back at ready main menu after move_index={move_index}"

        if slot_index == 0:
            scratch_pp -= 1
        else:
            growl_pp -= 1
        assert _pp(scene, 0)[0] == scratch_pp
        assert _pp(scene, 1)[0] == growl_pp
