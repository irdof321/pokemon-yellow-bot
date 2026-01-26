"""Main loop driving the emulator and background services."""
from __future__ import annotations

from typing import Iterable
import threading
import time  # pour sleep léger dans le thread services

from game.core.emulator import EmulatorSession
from game.services.service import Service
from game.utils.time_utils import has_expired, monotonic, seconds_from_now


class EmulatorLoop:
    def __init__(
        self,
        session: EmulatorSession,
        services: Iterable[Service] = (),
        *,
        button_cooldown: float = 1.0,
        service_tick_interval: float = 0.1,  # <-- nouveau: intervalle des services
        clock=monotonic,
    ):
        self.session = session
        self.services = list(services)
        self.button_cooldown = button_cooldown
        self.service_tick_interval = service_tick_interval
        self.clock = clock
        self._next_button_time = clock()

        # Gestion du thread des services
        self._services_thread: threading.Thread | None = None
        self._stop_services = threading.Event()

    # ------------------------------------------------------------------
    def _services_loop(self) -> None:
        """ Loop to run services in a separate thread. """
        self.session.logger.info("Starting services loop")
        try:
            next_tick = self.clock()
            while not self._stop_services.is_set():
                now = self.clock()
                if now >= next_tick:
                    for service in self.services:
                        try:
                            service.tick(now)
                        except Exception:
                            # Here we catch all exceptions to avoid killing the thread
                            self.session.logger.exception(
                                "Error in service.tick for %r", service
                            )
                    next_tick = now + self.service_tick_interval

                #small sleep to avoid busy-waiting
                time.sleep(0.001)
        finally:
            self.session.logger.info("Services loop stopped")

    # ------------------------------------------------------------------
    def run(self) -> None:
        for service in self.services:
            service.start()

        self.session.logger.info("Starting emulator loop")

        # Start the thread before entering the main loop
        self._stop_services.clear()
        self._services_thread = threading.Thread(
            target=self._services_loop
        )
        self._services_thread.start()
        frame = 0
        try:
            while True:
                frame += 1

                now = self.clock()
                if frame % 60 == 0:
                    self._maybe_pop_button(now)
                running = self.session.tick_once()

                if not running:
                    self.session.logger.info("Emulator stopped running")
                    break


        finally:
            self.session.logger.info("Emulator loop finished")

            # Stop the services thread
            self._stop_services.set()
            for service in self.services:
                try:
                    service.quit()
                except Exception:
                    self.session.logger.exception(
                        "Error in service.quit for %r", service
                    )
            if self._services_thread is not None:
                time_before_join = self.clock()
                self._services_thread.join(timeout=10.0)
                elapsed = self.clock() - time_before_join
                if self._services_thread.is_alive():
                    self.session.logger.error(
                        "Services thread did not terminate within timeout (waited %.2f seconds)",
                        elapsed,
                    )
                else:
                    self.session.logger.info(
                        "Services thread terminated after %.2f seconds", elapsed
                    )
        

    # ------------------------------------------------------------------
    def _maybe_pop_button(self, now: float) -> None:
        if not has_expired(self._next_button_time, clock=lambda: now):
            return

        button = self.session.pop_button()
        if button is None:
            self._next_button_time = now + self.button_cooldown
            return
        self.session.logger.debug("Processing button {}", button)
        self.session.logger.debug("Queued buttons: {}", self.session.buttons)
        self.session.press_button(button)
        self._next_button_time = seconds_from_now(
            self.button_cooldown, clock=lambda: now
        )


__all__ = ["EmulatorLoop", "Service"]
