"""Helpers around PyBoy save states."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import shutil


@dataclass(slots=True)
class SaveStateManager:
    """Helper responsible for loading and saving emulator state files, keeping rotating backups."""

    rom_path: str
    custom_state_path: Optional[str] = None
    max_backups: int = 5  # <-- how many .bak_<n> to keep

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

        # --- Rotate existing backups ---
        # Delete the oldest if it exists
        oldest = state_path.with_suffix(state_path.suffix + f".bak_{self.max_backups}")
        if oldest.exists():
            oldest.unlink()

        # Shift all backups from n -> n+1
        for n in range(self.max_backups - 1, 0, -1):
            src = state_path.with_suffix(state_path.suffix + f".bak_{n}")
            dst = state_path.with_suffix(state_path.suffix + f".bak_{n + 1}")
            if src.exists():
                src.rename(dst)

        # Backup the current .state as .bak_1 (if it exists)
        if state_path.exists():
            bak1 = state_path.with_suffix(state_path.suffix + ".bak_1")
            shutil.copy2(state_path, bak1)

        # --- Save new state ---
        with state_path.open("wb") as fh:
            emulator.save_state(fh)
