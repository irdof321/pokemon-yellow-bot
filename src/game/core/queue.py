"""Thread-safe queue abstraction used for button events."""
from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Deque, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class ThreadSafeQueue(Generic[T]):
    """Simple thread-safe FIFO queue based on :class:`collections.deque`."""

    def __init__(self, initial: Optional[Iterable[T]] = None) -> None:
        self._queue: Deque[T] = deque(initial or [])
        self._lock = Lock()

    def append(self, item: T) -> None:
        with self._lock:
            self._queue.append(item)

    def pop(self) -> Optional[T]:
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def __len__(self) -> int:  # pragma: no cover - trivial wrapper
        with self._lock:
            return len(self._queue)

    def __iter__(self) -> Iterator[T]:  # pragma: no cover - only used for debugging
        with self._lock:
            return iter(list(self._queue))

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()

    def __repr__(self) -> str:
        with self._lock:
            items = ", ".join(repr(x) for x in self._queue)
        return f"ThreadSafeQueue([{items}])"


__all__ = ["ThreadSafeQueue"]
