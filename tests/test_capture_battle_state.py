"""Tests for the F5 manual-capture hotkey: EmulatorSession.capture_battle_state()
(real PyBoy, real file writes) and EmulatorLoop's edge-detection of the key
(fake session, mocked SDL2 keyboard state -- no real window/keyboard needed)."""
import glob
import os
from unittest.mock import patch

from loguru import logger

from game.core.loop import EmulatorLoop


def test_capture_battle_state_writes_a_uniquely_named_file(load_fixture, tmp_path):
    session = load_fixture("wild_ratatta_par.state")

    path1 = session.capture_battle_state(str(tmp_path))
    path2 = session.capture_battle_state(str(tmp_path))

    assert os.path.isfile(path1)
    assert os.path.isfile(path2)
    assert path1 != path2, "two captures must never collide on the same filename"

    captured = sorted(glob.glob(str(tmp_path / "battle_*.state")))
    assert len(captured) == 2


class _FakeSession:
    """Minimal stand-in for EmulatorSession: just what EmulatorLoop's
    capture-hotkey logic touches."""

    def __init__(self, run_frames: int = 10):
        self.logger = logger
        self._remaining_frames = run_frames
        self.capture_calls = []

    def tick_once(self) -> bool:
        self._remaining_frames -= 1
        return self._remaining_frames > 0

    def pop_button(self):
        return None

    def press_button(self, button) -> None:
        pass

    def capture_battle_state(self, directory: str) -> str:
        self.capture_calls.append(directory)
        return f"{directory}/fake.state"


def _fake_keyboard_state(pressed_on_frames: set, frame_counter: dict, scancode: int):
    """Returns a callable matching sdl2.SDL_GetKeyboardState's signature
    (ignores its `numkeys` arg) -- a dict-like array where `scancode` reads
    as pressed exactly on the frames listed in `pressed_on_frames`."""

    class _Keys(dict):
        def __getitem__(self, key):
            return 1 if (key == scancode and frame_counter["n"] in pressed_on_frames) else 0

    def _get_keyboard_state(_numkeys):
        return _Keys()

    return _get_keyboard_state


def test_capture_hotkey_fires_once_per_press_not_once_per_frame_while_held():
    """Holding the key down across several ticks (frame 2, 3, 4) must
    capture exactly once, on the rising edge -- not once per frame."""
    session = _FakeSession(run_frames=8)
    loop = EmulatorLoop(session, services=[], capture_hotkey=True, capture_key_scancode=62)

    frame_counter = {"n": 0}
    original_tick_once = session.tick_once

    def counting_tick_once():
        frame_counter["n"] += 1
        return original_tick_once()

    session.tick_once = counting_tick_once

    with patch(
        "sdl2.SDL_GetKeyboardState",
        side_effect=_fake_keyboard_state({2, 3, 4}, frame_counter, scancode=62),
    ):
        loop.run()

    assert session.capture_calls == ["tests/fixtures"], (
        f"expected exactly one capture (rising edge only), got {session.capture_calls}"
    )


def test_capture_hotkey_disabled_by_default():
    """capture_hotkey defaults to False -- headless/training/test runs must
    never touch SDL2 keyboard state at all."""
    session = _FakeSession(run_frames=5)
    loop = EmulatorLoop(session, services=[])  # capture_hotkey not passed

    with patch("sdl2.SDL_GetKeyboardState") as mock_get_state:
        loop.run()

    mock_get_state.assert_not_called()
