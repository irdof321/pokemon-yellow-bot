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


__all__ = ["monotonic", "seconds_from_now", "has_expired"]
