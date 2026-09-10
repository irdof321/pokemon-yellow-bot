"""Debug harness for the cursor-oscillation / wrong-move-selected bugs found by
tests/test_real_wiring_end_to_end.py and tests/test_battle_move_edge_cases.py
(both xfail there, not fixed):

Selecting a move through the REAL threaded EmulatorLoop + SceneManagerService +
SceneController (not the fast BattleScene-direct drive_scene/drive_until
harness used everywhere else in the test suite) can fail in two ways
depending on move_index: scene.menu_id can get stuck oscillating/clamped and
never reach the target (command times out), or it can settle on the WRONG
move entirely (command completes, but the wrong move's PP drops). Pass which
moves to test as command-line arguments; they're submitted IN ORDER, one
after the other, in the SAME battle/scene, so you can watch several in a row
without restarting the script.

How to use this:
1. python scripts/debug_cursor_oscillation.py [move_index ...] [fixture.state]
   All arguments are optional. Default: moves 1, 2, 3 in order, on
   battle_must_go_on_fight.state. e.g.:
   `python scripts/debug_cursor_oscillation.py 2` -> just move 2
   `python scripts/debug_cursor_oscillation.py 1 2 3` -> all three, in order
   `python scripts/debug_cursor_oscillation.py 2 3 battle_user_mult_and_adv_mult.state`
2. Or run one of the "Debug: move_index=..." configs from the Run and Debug
   panel (.vscode/launch.json) / F5, to add breakpoints in
   src/game/scenes/battle_scene.py -- BattleScene._execute_move, around the
   `cur`/`target_id` comparison (the DOWN/UP/confirm branch), is the natural
   place to inspect what's being decided each time.
3. A real PyBoy window opens (window="SDL2", not headless) so you can watch
   the actual screen. Every menu_top/menu_id/phase change is logged to the
   console as it happens (from a separate monitor thread), clearly labelled
   with which move was requested, so you don't have to rely on the window
   alone to follow what's going on.

Threading note: loop.run() runs on the MAIN thread here, like src/app.py does
in production -- it's the thread that creates the PyBoy/SDL2 window (see
EmulatorSession(...) below), and on Windows that same thread must keep
pumping it via tick_once() or the window freezes ("Not Responding") and stops
taking keyboard input too. The "wait for scene / submit command / print
result" work and the menu-state monitor both run on their own background
threads instead; the worker thread calls session.stop() when it's done so
loop.run() on the main thread returns on its own.

When a breakpoint hits, VS Code's debugger pauses the whole process (all
threads), so you can inspect scene.menu_top / scene.menu_id / scene._phase /
cmd from the Variables/Watch panel without anything racing ahead while you
look.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.core.emulator import EmulatorSession  # noqa: E402
from game.core.loop import EmulatorLoop  # noqa: E402
from game.core.version import GameVersion  # noqa: E402
from game.data.ram_reader import MainPokemonData, MoveROMBank  # noqa: E402
from game.scenes.commands import BattleCommand  # noqa: E402
from game.scenes.scene_controller import SceneController  # noqa: E402
from game.services.scene_manger_service import SceneManagerService  # noqa: E402
from game.utils.logging_config import setup_logging  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")


class _FakeMQTTClient:
    """SceneManagerService only ever calls .publish() -- no real broker needed."""

    def publish(self, topic, payload, qos: int = 0, retain: bool = False) -> None:
        pass


def _monitor_menu_state(scene_manager: SceneManagerService, stop: threading.Event, current: dict) -> None:
    """Runs on its own background thread for the WHOLE run (all moves in the
    sequence), printing every menu_top/menu_id/phase change it sees as it
    happens. `current["move_index"]` is updated by _drive_command between
    moves so each line stays labelled with whichever move is being tested
    right now."""
    last_seen = None
    while not stop.is_set():
        scene = scene_manager.current_scene
        if scene is not None and scene.menu_top is not None:
            snapshot = (scene.menu_top, scene.menu_id, scene._phase)
            if snapshot != last_seen:
                print(
                    f"    [monitor] (requested move_index={current['move_index']}) "
                    f"menu_top={scene.menu_top} menu_id={scene.menu_id} phase={scene._phase}"
                )
                last_seen = snapshot
        time.sleep(0.05)


def _submit_one_move(
    session: EmulatorSession,
    scene_manager: SceneManagerService,
    controller: SceneController,
    move_index: int,
    current: dict,
) -> None:
    """Submits a single move command and prints its before/after/result --
    one step of the sequence run by _drive_command below."""
    current["move_index"] = move_index
    scene = scene_manager.current_scene
    moves_before = scene.to_dict()["on_battle"]["moves"]

    print("=" * 70)
    print(f"  SUBMITTING move_index={move_index}")
    print("=" * 70)
    print(f"Moves before: {[(m['name'], m['pp']) for m in moves_before]}")

    cmd = BattleCommand(kind="move", move_index=move_index)
    # Generous timeout: a debugger paused on a breakpoint doesn't stop the
    # wall clock, but it also doesn't matter here -- step() just waits longer.
    observation, reward, done, info = controller.step(cmd, timeout=120.0)

    timed_out = info.get("timeout") is True
    moves_after = observation.get("on_battle", {}).get("moves", [])

    print("-" * 70)
    print(f"  RESULT for requested move_index={move_index}")
    print("-" * 70)
    print("timed out:", timed_out)
    print("info:", info)

    if not timed_out and moves_before and moves_after:
        changed = [
            (before["name"], before["pp"][0], after["pp"][0])
            for before, after in zip(moves_before, moves_after)
            if before["pp"][0] != after["pp"][0]
        ]
        if changed:
            for name, pp_before, pp_after in changed:
                print(f"  >>> ACTUALLY USED: {name} (PP {pp_before} -> {pp_after}) <<<")
        else:
            print("  >>> NO move's PP changed -- nothing was actually confirmed <<<")

        raw = session.read_memory(MainPokemonData.BattlePlayerMove)
        print(f"  BattlePlayerMove (raw ROM move id) after selection: {raw[0] if raw else None!r}")

    print(f"Moves after:  {[(m['name'], m['pp']) for m in moves_after]}")
    print()


def _drive_command(
    session: EmulatorSession,
    scene_manager: SceneManagerService,
    controller: SceneController,
    move_indices: list,
) -> None:
    """Runs on a background thread while the main thread owns loop.run() (and
    the SDL2 window). Submits each move in move_indices IN ORDER, one after
    the other (each controller.step() blocks until that command completes or
    times out before the next one is submitted). Always calls session.stop()
    before returning, even on an early-failure/exception path, so the main
    thread's loop.run() is guaranteed to exit on its own once this thread is
    done."""
    current = {"move_index": move_indices[0]}
    monitor_stop = threading.Event()
    monitor = threading.Thread(
        target=_monitor_menu_state, args=(scene_manager, monitor_stop, current), daemon=True
    )
    try:
        print("Waiting for the battle scene to appear...")
        deadline = time.monotonic() + 5.0
        while scene_manager.current_scene is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if scene_manager.current_scene is None:
            print("ERROR: no battle scene appeared within 5s")
            return

        scene = scene_manager.current_scene
        print(f"Battle scene ready. menu_top={scene.menu_top} menu_id={scene.menu_id}")
        print(f"Sequence to submit, in order: {move_indices}")
        print("(set your breakpoint in _execute_move before this line runs, or let it")
        print(" hit naturally once BattleScene starts driving the first command)")

        monitor.start()

        for move_index in move_indices:
            _submit_one_move(session, scene_manager, controller, move_index, current)
    finally:
        monitor_stop.set()
        session.stop(save=False)


def main() -> None:
    # Positional args are: move indices to submit IN ORDER (default 1 2 3),
    # optionally followed by a fixture filename (must not look like an int).
    # e.g. `python debug_cursor_oscillation.py 1 2 3 battle_user_mult_and_adv_mult.state`
    args = sys.argv[1:]
    fixture_name = "battle_must_go_on_fight.state"
    if args and not args[-1].isdigit():
        fixture_name = args[-1]
        args = args[:-1]
    move_indices = [int(a) for a in args] if args else [1, 2, 3]
    fixture_path = os.path.join(FIXTURES_DIR, fixture_name)

    # INFO instead of the project default (DEBUG) to keep the console readable
    # while you're watching breakpoints -- full detail still goes to logs/.
    logger = setup_logging(level="INFO")
    MoveROMBank._instance = None

    session = EmulatorSession(
        GameVersion.RED, logger=logger, save_state_path=fixture_path, window="SDL2"
    )
    assert session.load_state_from_disk(), f"fixture failed to load from {fixture_path}"

    # Production-speed timings (EmulatorLoop/SceneManagerService defaults), not the
    # fast ones used in tests/test_real_wiring_end_to_end.py -- this script exists
    # to WATCH the SDL2 window and see what happens with your own eyes, so it
    # needs to run slow enough to follow.
    scene_manager = SceneManagerService(session, _FakeMQTTClient(), logger, poll_interval=0.5)
    controller = SceneController(scene_manager, logger)
    loop = EmulatorLoop(
        session, services=[scene_manager], button_cooldown=1.0, service_tick_interval=0.1
    )

    worker = threading.Thread(
        target=_drive_command, args=(session, scene_manager, controller, move_indices), daemon=True
    )
    worker.start()

    # Main thread owns loop.run() -- and therefore the PyBoy/SDL2 window,
    # since it's the thread that created it above. Matches src/app.py.
    # Returns on its own once the worker thread calls session.stop().
    loop.run()

    worker.join(timeout=15.0)
    print("Done.")


if __name__ == "__main__":
    main()
