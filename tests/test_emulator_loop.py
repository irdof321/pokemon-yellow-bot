"""Unit tests for EmulatorLoop's shutdown ordering (no real PyBoy needed)."""
import threading
import time

from loguru import logger

from game.core.loop import EmulatorLoop


class _FakeSession:
    """Minimal stand-in for EmulatorSession: just what EmulatorLoop touches."""

    def __init__(self, run_frames: int = 1):
        self.logger = logger
        self._remaining_frames = run_frames

    def tick_once(self) -> bool:
        self._remaining_frames -= 1
        return self._remaining_frames > 0

    def pop_button(self):
        return None

    def press_button(self, button) -> None:
        pass


class _SlowTickingService:
    """A service whose tick() sleeps, so it's reliably still running when
    the main loop's finally block starts tearing things down."""

    def __init__(self, tick_duration: float = 0.2):
        self.tick_duration = tick_duration
        self.started = False
        self.quit_called = threading.Event()
        self.tick_in_progress = threading.Event()
        self.quit_seen_during_tick = False

    def start(self) -> None:
        self.started = True

    def tick(self, now: float) -> None:
        self.tick_in_progress.set()
        time.sleep(self.tick_duration)
        if self.quit_called.is_set():
            self.quit_seen_during_tick = True
        self.tick_in_progress.clear()

    def quit(self) -> None:
        self.quit_called.set()


def test_quit_waits_for_services_thread_to_stop_ticking():
    """quit() must never run concurrently with a service's tick(): the
    services thread has to actually stop before quit() is called on any
    service, otherwise quit() can tear down state tick() is mid-read of."""
    service = _SlowTickingService(tick_duration=0.2)
    session = _FakeSession(run_frames=1)
    loop = EmulatorLoop(session, services=[service], service_tick_interval=0.01)

    # Make the service's slow tick() start before the main loop's finally
    # block runs, by giving the services thread a head start.
    original_tick_once = session.tick_once

    def tick_once_with_wait():
        service.tick_in_progress.wait(timeout=2.0)
        return original_tick_once()

    session.tick_once = tick_once_with_wait

    loop.run()

    assert service.started
    assert service.quit_called.is_set()
    assert not service.quit_seen_during_tick, (
        "quit() ran while tick() was still executing -- shutdown ordering regression"
    )
