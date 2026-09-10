"""Confirms selecting move 1 from a non-ready cursor position (main menu on
FIGHT, not yet in the move list) actually plays the right move and returns
to the ready main menu.

Verified via PP decrease rather than MainPokemonData.BattlePlayerMove's raw
value: BattlePlayerMove's exact encoding (0-based menu id vs internal move
number) hasn't been empirically confirmed, so asserting on it would be a
guess. PP decrementing by exactly 1 on the selected move's slot -- and not on
any other slot -- is something we already know for certain from Move/PP
handling in pokemon.py, and it's a strictly stronger check anyway (it proves
the *correct* move was used, not just that *some* selection completed).
"""
from game.data.ram_reader import MainPokemonData
from game.scenes.battle_scene import create_battle_scene
from game.scenes.commands import BattleCommand


def test_select_move_1_from_fight_menu(load_fixture, drive_scene):
    session = load_fixture("battle_must_go_on_fight.state")
    scene = create_battle_scene(session, 0)

    before = scene.to_dict()["on_battle"]["moves"]
    assert before[0]["name"] == "SCRATCH"  # move names decode raw from ROM text, always upper-case
    scratch_pp_before = before[0]["pp"]  # (remaining, max)

    cmd = BattleCommand(kind="move", move_index=1)
    completed = drive_scene(session, scene, cmd, max_frames=6000)

    assert completed, "move 1 selection never completed within the frame budget"
    assert cmd.done_event.is_set()
    assert scene.is_ready_main_menu

    after = scene.to_dict()["on_battle"]["moves"]
    scratch_pp_after = after[0]["pp"]
    assert scratch_pp_after == (scratch_pp_before[0] - 1, scratch_pp_before[1]), (
        f"expected Scratch's PP to drop by exactly 1, was {scratch_pp_before}, now {scratch_pp_after}"
    )
    # Other moves' PP should be untouched.
    assert after[1]["pp"] == before[1]["pp"]  # Growl
    assert after[2]["pp"] == before[2]["pp"]  # Ember

    # Not asserted (encoding unconfirmed), just recorded for future reference:
    raw = session.read_memory(MainPokemonData.BattlePlayerMove)
    print(f"\nBattlePlayerMove after selecting move_index=1: {raw[0] if raw else None!r}")
