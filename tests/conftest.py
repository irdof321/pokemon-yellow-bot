"""Shared pytest fixtures for tests that load a real PyBoy state."""
import sys
from pathlib import Path

import pytest
from loguru import logger as _loguru_logger

from game.core.emulator import EmulatorSession
from game.core.version import GameVersion
from game.data.ram_reader import MoveROMBank
from game.scenes.battle_scene import MenuLocation

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# --visual is meant to be watched with -s: without this, every DEBUG-level
# log in the project (every button pop, every "scene not ready" skip -- see
# game.core.loop / game.services.scene_manger_service) floods the console
# right alongside the [visual] lines below, drowning out the one thing
# that's actually useful to watch. Only applied when --visual is passed --
# non-visual runs don't print to a human, so their default level doesn't
# matter.
def _quiet_debug_logging_for_visual() -> None:
    _loguru_logger.remove()
    _loguru_logger.add(sys.stderr, level="INFO")


def pytest_addoption(parser):
    parser.addoption(
        "--visual",
        action="store_true",
        default=False,
        help=(
            "Run drive_scene/drive_until-based tests with a real SDL2 window "
            "(instead of headless) and print menu state changes as they "
            "happen, so you can watch what a test is actually doing. Same "
            "test bodies either way -- only load_fixture's window and "
            "_SceneDriver's logging change. Real SDL2 paces itself at ~60fps, "
            "so a test takes roughly as long to watch as the in-game action "
            "it drives -- use --visual-speed to speed that up."
        ),
    )
    parser.addoption(
        "--visual-speed",
        type=float,
        default=1.0,
        help=(
            "Emulation speed multiplier for --visual (ignored without it): "
            "1=real-time (default), 0=unlimited (too fast to watch, but "
            "still shows the window and [visual] logs), e.g. 5 for 5x. "
            "Uses PyBoy's own set_emulation_speed()."
        ),
    )


@pytest.fixture
def load_fixture(request):
    """Returns a loader: load_fixture("some_state.state", version=GameVersion.RED)
    -> an EmulatorSession with that save state already loaded. Headless
    (window="null") by default; pass --visual on the pytest command line to
    get a real SDL2 window instead, for manual observation.

    Resets the MoveROMBank singleton first -- it caches ROM move data from
    whichever EmulatorSession constructed it first, and silently keeps
    serving that stale data to every later EmulatorSession otherwise
    (harmless as long as every fixture uses the same ROM/version, but reset
    here so test order/ROM mixing can never cause stale reads).
    """
    visual = request.config.getoption("--visual")
    window = "SDL2" if visual else "null"
    speed = request.config.getoption("--visual-speed")
    if visual:
        _quiet_debug_logging_for_visual()

    def _load(state_name: str, version: GameVersion = GameVersion.RED) -> EmulatorSession:
        MoveROMBank._instance = None
        state_path = FIXTURES_DIR / state_name
        session = EmulatorSession(version, save_state_path=str(state_path), window=window)
        assert session.load_state_from_disk(), f"fixture {state_name} failed to load from {state_path}"
        if visual:
            session.set_emulation_speed(speed)
        return session

    yield _load


# Human-readable labels for --visual, keyed by (menu_top, phase) so the same
# top-left coordinate (e.g. (5,12), shared by the moves list AND post-move
# messages) can still describe what's actually happening. menu_id's meaning
# depends on which screen it's on (FIGHT/ITEM vs PKMN/RUN column, or a move
# slot), so it's folded into the label per-case rather than printed raw.
def _describe_scene_state(scene) -> str:
    top = scene.menu_top
    phase = scene._phase
    menu_id = scene.menu_id

    if top == MenuLocation.MAIN_MENU_LEFT.value:
        return "main menu: FIGHT" if menu_id == 0 else "main menu: ITEM"
    if top == MenuLocation.MAIN_MENU_RIGHT.value:
        return "main menu: PKMN" if menu_id == 0 else "main menu: RUN"
    if top == MenuLocation.POKEMON_SELECTION.value:
        return f"party-select screen (cursor on slot {menu_id})"
    if top == MenuLocation.POKEMON_SUB_MENU.value:
        return "SWITCH / STATS / CANCEL popup"
    if top == MenuLocation.MOVES_OR_TEXT.value:
        if phase == "select_move":
            return f"choosing a move (cursor on slot {menu_id})"
        return "watching battle text / animation"

    if phase == "idle":
        return "idle"
    return f"phase={phase} menu_top={top} menu_id={menu_id}"  # fallback, unrecognized screen


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

    def __init__(self, visual: bool = False):
        self.now = 0.0
        # --visual: print menu_top/menu_id/phase every time it changes, same
        # idea as scripts/debug_cursor_oscillation.py's monitor thread, but
        # inline since drive_until() isn't threaded -- lets you follow along
        # with the SDL2 window instead of staring at a silent test.
        self.visual = visual
        self._last_seen = None

    def _log_if_visual(self, scene) -> None:
        if not self.visual:
            return
        snapshot = (scene.menu_top, scene.menu_id, scene._phase)
        if snapshot != self._last_seen:
            print(f"    [visual] t={self.now:6.2f}s  {_describe_scene_state(scene)}")
            self._last_seen = snapshot

    def drive_until(self, session, scene, condition, *, max_frames: int = 6000) -> bool:
        if self.visual:
            print(f"    [visual] waiting for condition (up to {max_frames} frames)...")
        for frame in range(1, max_frames + 1):
            session.tick_once()
            self.now += self.FRAME_DT
            if frame % self.POP_EVERY == 0:
                button = session.pop_button()
                if button is not None:
                    session.press_button(button)
            if frame % self.UPDATE_EVERY == self.UPDATE_OFFSET:
                scene.update(self.now)
                self._log_if_visual(scene)
                if condition():
                    if self.visual:
                        print(f"    [visual] condition met at t={self.now:.2f}s")
                    return True
        if self.visual:
            print(f"    [visual] condition NEVER met within {max_frames} frames")
        return False

    def drive_scene(self, session, scene, command, *, max_frames: int = 6000) -> bool:
        scene.enqueue_command(command)
        return self.drive_until(session, scene, command.done_event.is_set, max_frames=max_frames)


@pytest.fixture
def scene_driver(request):
    """A _SceneDriver with its own persistent synthetic clock, shared across
    every drive_until()/drive_scene() call made with it in one test. Verbose
    (menu state logging) when --visual is passed -- see load_fixture and
    _SceneDriver's docstring."""
    return _SceneDriver(visual=request.config.getoption("--visual"))


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
