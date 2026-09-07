"""Shared pytest fixtures for tests that load a real PyBoy state."""
from pathlib import Path

import pytest

from game.core.emulator import EmulatorSession
from game.core.version import GameVersion
from game.data.ram_reader import MoveROMBank

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture():
    """Returns a loader: load_fixture("some_state.state", version=GameVersion.RED)
    -> a headless EmulatorSession with that save state already loaded.

    Resets the MoveROMBank singleton first -- it caches ROM move data from
    whichever EmulatorSession constructed it first, and silently keeps
    serving that stale data to every later EmulatorSession otherwise
    (harmless as long as every fixture uses the same ROM/version, but reset
    here so test order/ROM mixing can never cause stale reads).
    """
    def _load(state_name: str, version: GameVersion = GameVersion.RED) -> EmulatorSession:
        MoveROMBank._instance = None
        state_path = FIXTURES_DIR / state_name
        session = EmulatorSession(version, save_state_path=str(state_path), window="null")
        assert session.load_state_from_disk(), f"fixture {state_name} failed to load from {state_path}"
        return session

    yield _load
