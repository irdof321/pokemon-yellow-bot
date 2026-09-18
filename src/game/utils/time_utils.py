"""Time-related helpers used by services and the game loop."""
from __future__ import annotations

import time
from typing import Protocol


class SupportsTimeMonotonic(Protocol):
    def __call__(self) -> float: ...


def monotonic() -> float:
    """Return the current monotonic time."""
    return time.monotonic()


def seconds_from_now(seconds: float, *, clock: SupportsTimeMonotonic = time.monotonic) -> float:
    """Return ``clock() + seconds``.  Useful for scheduling events."""
    return clock() + seconds


def has_expired(deadline: float, *, clock: SupportsTimeMonotonic = time.monotonic) -> bool:
    """Return ``True`` when ``clock()`` has reached the deadline."""
    return clock() >= deadline


class FrameClock:
    """A clock measured in emulated Game Boy frames instead of real
    wall-clock time -- __call__() returns elapsed *simulated* seconds
    (frame_count / fps), not time.monotonic(). Pass an instance of this as
    EmulatorLoop's `clock=` for training: every cooldown (button_cooldown,
    service_tick_interval, BattleScene's own internal ones) keeps working
    exactly the same, except the "seconds" it counts elapse as fast as
    PyBoy can simulate frames instead of being capped by a real
    time.sleep()-paced wall clock. Not for anything a human is watching --
    use the default real clock (time.monotonic, EmulatorLoop's default) for
    that, same as app.py/production today.

    fps defaults to 60 as an approximation of the real Game Boy refresh
    rate (~59.73 Hz, from PyBoy's own FRAME_CYCLES=70224 at the GB's
    4.194304 MHz clock) -- already the same approximation
    tests/conftest.py's _SceneDriver has used throughout this project's
    whole fast-test-harness, proven fine in practice against the
    multi-hundred-ms safety margins involved here.

    EmulatorLoop calls tick() once per emulated frame (see run()) -- this
    class doesn't advance itself on its own.
    """

    def __init__(self, fps: float = 60.0):
        self._frame = 0
        self._fps = fps

    def tick(self) -> None:
        self._frame += 1

    def __call__(self) -> float:
        return self._frame / self._fps


__all__ = ["monotonic", "seconds_from_now", "has_expired", "FrameClock"]
