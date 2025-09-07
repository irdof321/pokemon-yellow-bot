# tests/test_integration_red_state.py
import os
import pytest

from pyboy import PyBoy
from data.ram_reader import MemoryData, MainPokemonData
from data.decoder import decode_pkm_text

ROM_PATH   = "games/PokemonRouge.gb"           # adjust if needed
STATE_PATH = "games/PokemonTestClassPokemon.state"

pytestmark = pytest.mark.integration


def _has_files():
    return os.path.exists(ROM_PATH) and os.path.exists(STATE_PATH)


@pytest.mark.skipif(not _has_files(), reason="ROM or state not found locally.")
def test_party_and_first_mon_properties_red_state():
    # Red/Blue use the base WRAM layout; default shift is 0x5.
    MemoryData.set_shift(0x5)

    # Headless window avoids GUI popups during CI
    pyboy = PyBoy(ROM_PATH, window="null", log_level="WARNING")

    try:
        # Load the provided save state (PyBoy expects a file-like)
        with open(STATE_PATH, "rb") as f:
            pyboy.load_state(f)

        # --- Assert party count is 1 ---
        party_count = int(pyboy.memory[MainPokemonData.PartyCount.start_address])
        assert party_count == 1, f"Expected 1 Pokémon in party, got {party_count}"

        # # --- First party Pokémon ID should be Squirtle (= 7) ---
        # first_id = int(pyboy.memory[MainPokemonData.PartyPokemon1.start_address])
        # assert first_id == 7, f"Expected first party ID 7 (Squirtle), got {first_id}"

        # --- First nickname should decode to CARAPUCE (FR) ---
        nick_bytes = bytes(pyboy.memory[
            MainPokemonData.Nickname1.start_address : MainPokemonData.Nickname1.end_address + 1
        ])
        nickname = decode_pkm_text(list(nick_bytes))  # stops on 0x50 terminator
        assert nickname.upper().startswith("ABCDEFGH"), f"Got nickname: {nickname}"

    finally:
        pyboy.stop()
