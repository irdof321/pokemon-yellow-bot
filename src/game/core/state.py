"""Helpers around PyBoy save states."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class SaveStateManager:
    """Small helper responsible for loading and saving emulator state files."""

    rom_path: str
    custom_state_path: Optional[str] = None

    @property
    def path(self) -> Path:
        if self.custom_state_path:
            return Path(self.custom_state_path)
        return Path(f"{self.rom_path}.state")

    def load(self, emulator) -> bool:
        state_path = self.path
        if not state_path.exists():
            return False
        with state_path.open("rb") as fh:
            emulator.load_state(fh)
        return True

    def save(self, emulator) -> None:
        state_path = self.path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("wb") as fh:
            emulator.save_state(fh)


__all__ = ["SaveStateManager"]
