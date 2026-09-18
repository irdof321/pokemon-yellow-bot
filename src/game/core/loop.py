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
        capture_hotkey: bool = False,
        capture_key_scancode: int = 62,  # sdl2.SDL_SCANCODE_F5 -- unused by PyBoy's own key map
        capture_dir: str = "tests/fixtures",
    ):
        self.session = session
        self.services = list(services)
        self.button_cooldown = button_cooldown
        self.service_tick_interval = service_tick_interval
        self.clock = clock
        self._next_button_time = clock()

        # Manual-play helper (app.py only, not training/tests): press F5 to
        # save the current state to its own uniquely-named fixture file --
        # for building up a library of battle-start captures while playing,
        # without ever overwriting an earlier one. Off by default: only
        # meaningful with a real SDL2 window and a human at the keyboard.
        self.capture_hotkey = capture_hotkey
        self.capture_key_scancode = capture_key_scancode
        self.capture_dir = capture_dir
        self._capture_key_was_down = False

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

                # Advance the clock if it's frame-driven (FrameClock, used
                # for training) rather than real wall-clock time (the
                # default) -- see FrameClock's docstring. A no-op for the
                # default monotonic clock, which has no tick().
                if hasattr(self.clock, "tick"):
                    self.clock.tick()

                now = self.clock()
                if frame % 60 == 0:
                    self._maybe_pop_button(now)
                if self.capture_hotkey:
                    self._maybe_capture_state()
                running = self.session.tick_once()

                if not running:
                    self.session.logger.info("Emulator stopped running")
                    break


        finally:
            self.session.logger.info("Emulator loop finished")

            # Stop the services thread and wait for it to actually stop
            # ticking before calling quit() on services, otherwise quit()
            # can run concurrently with a service's tick() (e.g. tearing
            # down state tick() is mid-way through reading).
            self._stop_services.set()
            if self._services_thread is not None:
                time_before_join = self.clock()
                self._services_thread.join(timeout=10.0)
                elapsed = self.clock() - time_before_join
                if self._services_thread.is_alive():
                    self.session.logger.error(
                        f"Services thread did not terminate within timeout (waited {elapsed:.2f} seconds)"
                    )
                else:
                    self.session.logger.info(
                        f"Services thread terminated within {elapsed:.2f} seconds"

                    )

            for service in self.services:
                try:
                    service.quit()
                except Exception:
                    self.session.logger.exception(
                        "Error in service.quit for %r", service
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

    def _maybe_capture_state(self) -> None:
        """Edge-detects capture_key_scancode (F5 by default) via raw SDL2
        keyboard state -- deliberately NOT going through PyBoy's own
        WindowEvent/button pipeline (that's a fixed, closed set of events,
        see WindowEvent in pyboy.utils; there's no slot in it for "save to
        a new uniquely-named file", only its built-in STATE_SAVE, which
        always overwrites the same <rom>.state). Polling SDL_GetKeyboardState
        ourselves works alongside PyBoy's own event handling without
        conflicting with it. Only meaningful with a real SDL2 window (see
        capture_hotkey on __init__); silently does nothing if SDL2 isn't
        available or has no video subsystem (e.g. headless training runs
        that mistakenly left capture_hotkey on)."""
        try:
            import sdl2

            keys = sdl2.SDL_GetKeyboardState(None)
            is_down = bool(keys[self.capture_key_scancode])
        except Exception:
            return

        if is_down and not self._capture_key_was_down:
            self.session.capture_battle_state(self.capture_dir)
        self._capture_key_was_down = is_down


__all__ = ["EmulatorLoop", "Service"]
