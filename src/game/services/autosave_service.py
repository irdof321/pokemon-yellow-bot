"""Service responsible for periodically saving the emulator state."""
from __future__ import annotations

from game.core.emulator import EmulatorSession
from game.utils.time_utils import has_expired, seconds_from_now


class AutosaveService:
    def __init__(self, session: EmulatorSession, logger, interval_seconds: float = 1.0):
        self.session = session
        self.logger = logger
        self.interval = interval_seconds
        self._next_save_at = seconds_from_now(self.interval)

    def start(self) -> None:
        self.logger.debug("Autosave service initialising")
        self.session.load_state_from_disk()
        self._next_save_at = seconds_from_now(self.interval)

    def tick(self, now: float) -> None:
        if not has_expired(self._next_save_at, clock=lambda: now):
            return
        self.logger.debug("Saving emulator state")
        try:
            self.session.save_state_to_disk()
            self.logger.info("Game state saved")
        finally:
            self._next_save_at = seconds_from_now(self.interval, clock=lambda: now)


__all__ = ["AutosaveService"]
