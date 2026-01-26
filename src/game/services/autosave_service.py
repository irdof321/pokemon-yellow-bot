"""Service responsible for periodically saving the emulator state."""
from __future__ import annotations

from game.core.emulator import EmulatorSession
from game.services.service import Service
from game.utils.time_utils import has_expired, seconds_from_now

from threading import Lock


class AutosaveService(Service):
    def __init__(self, session: EmulatorSession, logger, interval_seconds: float = 1.0):
        self.session = session
        self.logger = logger
        self.interval = interval_seconds
        self._next_save_at = seconds_from_now(self.interval)
        self._save_gate = Lock()

    def start(self) -> None:
        self.logger.debug("Autosave service initialising")
        self.session.load_state_from_disk()
        self._next_save_at = seconds_from_now(self.interval)

    def tick(self, now: float) -> None:
        if not has_expired(self._next_save_at, clock=lambda: now):
            return
        self.logger.debug("Saving emulator state")
        try:
            with self._save_gate:
                self.session.save_state_to_disk()
                self.logger.info("Game state saved")
        finally:
            self._next_save_at = seconds_from_now(self.interval, clock=lambda: now)

    def quit(self) -> None:
        
        self.logger.info("Waiting for ongoing save to complete before quitting...")
        with self._save_gate:
            pass  # Just acquire and release to ensure no save is ongoing
        self.logger.info("Save completed. Quitting AutosaveService.")


__all__ = ["AutosaveService"]
