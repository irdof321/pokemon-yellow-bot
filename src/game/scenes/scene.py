"""Battle scene helpers."""
from __future__ import annotations

from dataclasses import dataclass

from game.core.emulator import EmulatorSession


@dataclass
class Scene:
    session: EmulatorSession
    battle_id: int

    def __post_init__(self) -> None:
        self.logger = self.session.logger

    def update(self, now: float) -> None:
        raise NotImplementedError()

    def _refresh(self) -> None:
        raise NotImplementedError()

    def to_dict(self) -> dict:
        raise NotImplementedError()
    
    def is_ready(self) -> bool:
        raise NotImplementedError()


__all__ = ["Scene"]