"""Shared pytest fixtures for tests that load a real PyBoy state."""
from pathlib import Path

import pytest

from game.core.emulator import EmulatorSession
from game.core.version import GameVersion
from game.data.ram_reader import MoveROMBank

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture():
    """Returns a loader: load_fixture("some_state.state", version=GameVersion.RED)
    -> a headless EmulatorSession with that save state already loaded.

    Resets the MoveROMBank singleton first -- it caches ROM move data from
    whichever EmulatorSession constructed it first, and silently keeps
    serving that stale data to every later EmulatorSession otherwise
    (harmless as long as every fixture uses the same ROM/version, but reset
    here so test order/ROM mixing can never cause stale reads).
    """
    def _load(state_name: str, version: GameVersion = GameVersion.RED) -> EmulatorSession:
        MoveROMBank._instance = None
        state_path = FIXTURES_DIR / state_name
        session = EmulatorSession(version, save_state_path=str(state_path), window="null")
        assert session.load_state_from_disk(), f"fixture {state_name} failed to load from {state_path}"
        return session

    yield _load


class _SceneDriver:
    """Advances a session + scene together the way EmulatorLoop +
    SceneManagerService would in production. Holds a SYNTHETIC clock
    (advanced by 1/60s per frame) instead of real time.monotonic()/sleep():
    BattleScene's input cooldown (_input_cooldown = 0.20s) is checked against
    whatever `now` gets passed to update(), and a tight Python loop over
    headless (window="null", unlimited-speed) PyBoy frames completes in
    milliseconds of *real* wall-clock time -- nowhere near enough for a
    real-time cooldown to ever elapse. Advancing a fake clock in lockstep
    with simulated frames keeps the timing logic correct while letting the
    test run as fast as the CPU allows.

    Critically, `now` is instance state, NOT reset per call: BattleScene's
    own _next_input_allowed_at is real state on the scene that keeps
    advancing across separate commands, so a driver used for multiple
    commands in one test (e.g. a 3-turn sequence) must keep advancing the
    SAME clock across all of them -- restarting it at 0.0 for command 2
    would make it look like ages had passed since command 1's last input,
    letting a second button queue up before the first had even been
    processed by the emulator (this was a real bug caught while writing
    test_battle_move_edge_cases.py's 3-turn rotation test: it caused a
    stray extra A press that silently re-selected the wrong move).

    scene.update() is called far more often than buttons are popped/pressed
    (every UPDATE_EVERY frames vs every POP_EVERY frames), and deliberately
    OFFSET so an update() call never lands on the exact same frame as a
    pop+press. This mirrors production: EmulatorLoop pops/presses buttons on
    the main thread every button_cooldown, while SceneManagerService calls
    scene.update() independently, on its own thread, every poll_interval --
    genuinely decoupled, never synchronized to the same instant.

    An earlier version of this driver called scene.update() at the SAME
    frame % 60 == 0 check as the pop/press, every single cycle -- always in
    lockstep, never decoupled. That let scene.update()'s decision logic run
    immediately after a button had JUST been physically pressed, before that
    press had a single tick to register in RAM, so its next decision was
    based on stale state. This reproduced as a real, confusing bug: selecting
    move_index=2/3 made the cursor wander into an unrelated menu (menu_top
    values never seen in the real threaded system) and never converge --
    while the exact same scenario worked correctly through the real
    EmulatorLoop/SceneManagerService (see scripts/debug_cursor_oscillation.py),
    proving it was this driver's timing that was unfaithful, not a real
    BattleScene bug. Simply calling update() more often, without the offset,
    does NOT fix it: 60 is itself a multiple of smaller update intervals, so
    naive "more frequent" checks still land exactly on pop frames every time.
    """

    FRAME_DT = 1 / 60
    POP_EVERY = 60      # matches production's ~1s-scale button cadence
    UPDATE_EVERY = 6    # matches production's much faster, independent poll cadence
    UPDATE_OFFSET = 3   # guarantees update frames never coincide with pop frames

    def __init__(self):
        self.now = 0.0

    def drive_until(self, session, scene, condition, *, max_frames: int = 6000) -> bool:
        for frame in range(1, max_frames + 1):
            session.tick_once()
            self.now += self.FRAME_DT
            if frame % self.POP_EVERY == 0:
                button = session.pop_button()
                if button is not None:
                    session.press_button(button)
            if frame % self.UPDATE_EVERY == self.UPDATE_OFFSET:
                scene.update(self.now)
                if condition():
                    return True
        return False

    def drive_scene(self, session, scene, command, *, max_frames: int = 6000) -> bool:
        scene.enqueue_command(command)
        return self.drive_until(session, scene, command.done_event.is_set, max_frames=max_frames)


@pytest.fixture
def scene_driver():
    """A _SceneDriver with its own persistent synthetic clock, shared across
    every drive_until()/drive_scene() call made with it in one test."""
    return _SceneDriver()


@pytest.fixture
def drive_until(scene_driver):
    """drive_until(session, scene, condition, max_frames=6000) -> bool."""
    return scene_driver.drive_until


@pytest.fixture
def drive_scene(scene_driver):
    """drive_scene(session, scene, command, max_frames=6000) -> bool.

    Safe to call multiple times in one test (e.g. a multi-turn sequence) --
    each call keeps advancing the same _SceneDriver's clock. Also safe to
    mix with the `drive_until` fixture in the same test: both depend on
    `scene_driver`, and pytest resolves that to the same cached instance
    within a single test, so they share one clock either way.
    """
    return scene_driver.drive_scene
