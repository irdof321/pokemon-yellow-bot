"""Game version utilities."""
from __future__ import annotations

from enum import Enum, auto
from typing import Dict


class GameVersion(Enum):
    RED = auto()
    BLUE = auto()
    YELLOW = auto()

    @property
    def rom_path(self) -> str:
        return ROM_PATHS[self]

    @property
    def is_yellow(self) -> bool:
        return self is GameVersion.YELLOW


ROM_PATHS: Dict[GameVersion, str] = {
    GameVersion.RED: "games/PokemonRed.gb",
    GameVersion.BLUE: "games/PokemonBleu.gb",
    GameVersion.YELLOW: "games/PokemonJaune.gb",
}


def version_from_choice(choice: str) -> GameVersion:
    normalized = choice.strip().lower()
    if normalized in {"r", "red"}:
        return GameVersion.RED
    if normalized in {"b", "blue"}:
        return GameVersion.BLUE
    if normalized in {"y", "yellow"}:
        return GameVersion.YELLOW
    raise ValueError(f"Unknown game version choice: {choice!r}")


__all__ = ["GameVersion", "ROM_PATHS", "version_from_choice"]
