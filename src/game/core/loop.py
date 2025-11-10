"""Main loop driving the emulator and background services."""
from __future__ import annotations

from typing import Iterable

from game.core.emulator import EmulatorSession
from game.services.service import Service
from game.utils.time_utils import has_expired, monotonic, seconds_from_now



class EmulatorLoop:
    def __init__(self, session: EmulatorSession, services: Iterable[Service], *, button_cooldown: float = 1.0, clock=monotonic):
        self.session = session
        self.services = list(services)
        self.button_cooldown = button_cooldown
        self.clock = clock
        self._next_button_time = clock()

    def run(self) -> None:
        for service in self.services:
            service.start()

        self.session.logger.info("Starting emulator loop")

        try:
            while True:
                running = self.session.tick_once()
                now = self.clock()

                if not running:
                    self.session.logger.info("Emulator stopped running")
                    break

                self._maybe_pop_button(now)

                for service in self.services:
                    service.tick(now)
        finally:
            self.session.logger.info("Emulator loop finished")

    # ------------------------------------------------------------------
    def _maybe_pop_button(self, now: float) -> None:
        if not has_expired(self._next_button_time, clock=lambda: now):
            return

        button = self.session.pop_button()
        if button is None:
            self._next_button_time = now + self.button_cooldown
            return
        self.session.logger.debug("Processing button {}", button)
        self.session.press_button(button)
        self._next_button_time = seconds_from_now(self.button_cooldown, clock=lambda: now)


__all__ = ["EmulatorLoop", "Service"]
