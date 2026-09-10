"""Confirms the state machine navigates on its own from a just-started battle
(trainer intro dialogue still on screen, no menu reachable yet) to the ready
FIGHT/PKMN/ITEM/RUN main menu, without any command being submitted -- purely
BattleScene's idle behavior (_ensure_ready_main_menu).
"""
from game.scenes.battle_scene import create_battle_scene


def test_reaches_ready_main_menu_from_battle_start(load_fixture, drive_until):
    session = load_fixture("battle_start_must_go_to_menu.state")
    scene = create_battle_scene(session, 0)

    assert not scene.is_ready(), "fixture should start away from the ready main menu"

    reached = drive_until(session, scene, scene.is_ready, max_frames=6000)

    assert reached, "never reached the ready main menu within the frame budget"
    assert scene.is_ready_main_menu
