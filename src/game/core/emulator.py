"""PyBoy wrapper used by the modernised game loop."""
from __future__ import annotations

from typing import Iterable, Optional

from loguru import logger as _loguru_logger
from pyboy import PyBoy

from game.core.queue import ThreadSafeQueue
from game.core.state import SaveStateManager
from game.core.version import GameVersion, ROM_PATHS, version_from_choice
from game.data.data import GBAButton
from game.data.ram_reader import MemoryData, MoveROMBank, SavedPokemonData


class EmulatorSession(PyBoy):
    """Thin wrapper around :class:`pyboy.PyBoy` adding project specific helpers."""

    def __init__(self, version: GameVersion, *, logger=_loguru_logger, save_state_path: str | None = None):
        super().__init__(ROM_PATHS[version], window="SDL2", log_level="INFO", sound_emulated=False)
        self.version = version
        self.logger = logger
        self.save_state_ma = SaveStateManager(ROM_PATHS[version], save_state_path)
        self.buttons: ThreadSafeQueue[GBAButton] = ThreadSafeQueue()
        MemoryData.set_shift(0x0)
        MemoryData.set_game(self)
        MoveROMBank(self)
        self.is_running = False

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_choice(cls, choice: str, *, logger=_loguru_logger, save_state_path: str | None = None) -> "EmulatorSession":
        version = version_from_choice(choice)
        return cls(version, logger=logger,save_state_path= save_state_path)

    # ------------------------------------------------------------------
    # Button queue helpers
    # ------------------------------------------------------------------
    def enqueue_button(self, button: GBAButton) -> None:
        self.buttons.append(button)
        # for i in range(60):
        #     self.buttons.append(GBAButton.PASS)

    def pop_button(self) -> Optional[GBAButton]:
        return self.buttons.pop()

    def clear_buttons(self) -> None:
        self.buttons.clear()

    def press_button(self, button: GBAButton) -> None:
        if button is GBAButton.PASS:
            return
        # super().button(button.value)
        self.button(str(button.value).lower(), delay=2)

    # ------------------------------------------------------------------
    # Save-state helpers
    # ------------------------------------------------------------------
    def load_state_from_disk(self) -> bool:
        try:
            loaded = self.save_state_ma.load(self)
            if loaded:
                self.logger.info("Save state loaded from {}", self.save_state_ma.path)
            return loaded
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.exception("Failed to load save state: {}", exc)
            return False

    def save_state_to_disk(self) -> None:
        try:
            self.save_state_ma.save(self)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.exception("Failed to save state: {}", exc)
            raise

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------
    def read_memory(self, elem: MemoryData) -> bytes:
        elem = MemoryData.get_pkm_yellow_addresses(elem)
        return SavedPokemonData.get_data(self, elem)

    # ------------------------------------------------------------------
    # Loop helpers
    # ------------------------------------------------------------------
    def tick_once(self) -> bool:
        self.is_running = self.tick()
        return self.is_running


__all__ = ["EmulatorSession"]
