import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass(slots=True)
class SaveStateManager:
    """
    Save state manager with rotating backups.

    Backup policy:
      - Current state: <rom>.state   (always the most recent, never .bak)
      - Backups:       <rom>.state.bak_1 (most recent backup, previous .state)
                       ...
                       <rom>.state.bak_5 (oldest backup)
    """
    rom_path: str
    custom_state_path: Optional[str] = None
    max_backups: int = 5  # number of .bak_n files to keep (excluding .state)

    @property
    def path(self) -> Path:
        """Return the base path for the main .state file."""
        if self.custom_state_path:
            return Path(self.custom_state_path)
        return Path(f"{self.rom_path}.state")

    def _bak_path(self, n: int) -> Path:
        """Helper: build a safe backup file path like <rom>.state.bak_n."""
        return self.path.with_name(self.path.name + f".bak_{n}")

    def load(self, emulator) -> bool:
        """Load the latest state into the emulator, if it exists."""
        state_path = self.path
        if not state_path.exists():
            return False
        with state_path.open("rb") as fh:
            emulator.load_state(fh)
        return True

    def save(self, emulator) -> None:
        """Save the current emulator state and rotate backups safely."""
        state_path = self.path
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # --- Rotate backups ---
        # 1) Remove the oldest backup (.bak_max) if it exists
        oldest = self._bak_path(self.max_backups)
        if oldest.exists():
            oldest.unlink()

        # 2) Shift all backups: .bak_(n) → .bak_(n+1)
        for n in range(self.max_backups - 1, 0, -1):
            src = self._bak_path(n)
            dst = self._bak_path(n + 1)
            if src.exists():
                src.replace(dst)

        # 3) Backup the current .state as .bak_1 (if present)
        if state_path.exists():
            shutil.copy2(state_path, self._bak_path(1))

        # --- Save new state (atomic write) ---
        tmp_path = state_path.with_name(state_path.name + ".tmpwrite")
        try:
            with tmp_path.open("wb") as fh:
                emulator.save_state(fh)
                fh.flush()
                os.fsync(fh.fileno())
            # Atomically replace the old .state with the new one
            os.replace(tmp_path, state_path)
        finally:
            # Clean up in case something failed before the replacement
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
__all__ = ["SaveStateManager"]