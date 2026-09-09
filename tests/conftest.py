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

    scene.update() is only called every 60 frames, right after that
    interval's button pop/press -- NOT every frame. Production never calls
    it faster than SceneManagerService's poll_interval (0.5s); calling it
    every single frame let _can_enqueue_input() see an empty button queue
    and enqueue a second button before the first one had even been
    processed by a single tick_once(), overshooting the cursor. One state
    check per 60-frame window gives each press a full second (simulated) to
    actually register in RAM before the next one is considered.
    """

    FRAME_DT = 1 / 60

    def __init__(self):
        self.now = 0.0

    def drive_until(self, session, scene, condition, *, max_frames: int = 6000) -> bool:
        for frame in range(1, max_frames + 1):
            session.tick_once()
            self.now += self.FRAME_DT
            if frame % 60 == 0:
                button = session.pop_button()
                if button is not None:
                    session.press_button(button)
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
