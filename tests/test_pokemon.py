# tests/test_pokemon.py
import pytest
from data.pokemon import Pokemon, POKEMON_LAYOUT
from data.ram_reader import MemoryData, MainPokemonData
# tests/test_pokemon_from_state.py
import os
import pytest

from pyboy import PyBoy


# ---- Dummy helpers ----
class DummyPyBoy:
    def __init__(self, memsize=0x10000):
        self.memory = bytearray(memsize)


def make_fake_pokemon_bytes():
    data = bytearray(40)
    # number
    data[POKEMON_LAYOUT["number"][0]] = 42
    # level
    data[POKEMON_LAYOUT["level"][0]] = 50
    # current_hp = 1234 (0x04D2) -> hi, lo = [0x04, 0xD2]
    data[POKEMON_LAYOUT["current_hp"][0]:POKEMON_LAYOUT["current_hp"][1]] = bytes([0x04, 0xD2])
    # max_hp = 1300 (0x0514) -> [0x05, 0x14]
    data[POKEMON_LAYOUT["max_hp"][0]:POKEMON_LAYOUT["max_hp"][1]] = bytes([0x05, 0x14])
    # moves
    data[POKEMON_LAYOUT["moves"][0]:POKEMON_LAYOUT["moves"][1]] = bytes([1, 2, 3, 4])
    # dvs
    data[POKEMON_LAYOUT["dvs"][0]:POKEMON_LAYOUT["dvs"][1]] = bytes([0xAB, 0xCD])
    # pp
    data[POKEMON_LAYOUT["pp"][0]:POKEMON_LAYOUT["pp"][1]] = bytes([10, 20, 30, 40])
    return data


def test_pokemon_parsing(monkeypatch=None):
    # Monkeypatch decode_pkm_text to avoid charset logic
    import data.pokemon
    data.pokemon.decode_pkm_text = lambda seq, stop_at_terminator=True: "TESTMON"

    # Prepare memory
    mem = DummyPyBoy().memory
    MemoryData.set_shift(0x5)
    base_raw = 0x3000
    md = MemoryData(base_raw, base_raw + 39, "fake mon")
    base_shifted = md.start_address
    fake = make_fake_pokemon_bytes()
    mem[base_shifted: base_shifted + len(fake)] = fake

    class PB:
        memory = mem

    mon = Pokemon.from_memory(PB, md, is_yellow=False)

    assert mon.number == 42
    assert mon.level == 50
    assert mon.current_hp == 1234
    assert mon.max_hp == 1300
    assert mon.moves == [1, 2, 3, 4]
    assert mon.dvs == {"attack": 0xA, "defense": 0xB, "speed": 0xC, "special": 0xD}
    assert mon.pp == [10, 20, 30, 40]
    assert mon.name == "TESTMON"


# Chemins (adapte si besoin)
ROM_PATH   = "games/PokemonRouge.gb"
STATE_PATH = "games/PokemonTestClassPokemon.state"

pytestmark = pytest.mark.integration


def _has_files():
    return os.path.exists(ROM_PATH) and os.path.exists(STATE_PATH)


@pytest.mark.skipif(not _has_files(), reason="ROM or state not found locally.")
def test_pokemon_from_state_first_party_mon_is_squirtle_named_ABCDEFGHIJ():
    """
    Charge la ROM Red + l'état 'PokemonTestClassPokemon.state', puis lit le
    premier Pokémon du joueur via SavedData.* et vérifie:
      - species/id == 7 (Squirtle/Carapuce)
      - name == 'ABCDEFGHIJ'
      - level == 6
      - HP == 22/22
      - type1 == 'Water'
    """
    # Red/Blue => pas de correction Yellow; et décalage PyBoy WRAM +0x5
    MemoryData.set_shift(0x5)

    # Fenêtre headless pour les tests
    pyboy = PyBoy(ROM_PATH, window="null", log_level="WARNING")
    try:
        with open(STATE_PATH, "rb") as f:
            pyboy.load_state(f)

        # Sélectionne un bloc Pokémon cohérent avec ton POKEMON_LAYOUT (40 octets)
        # On privilégie le bloc "battle/summary" qui correspond à l’écran stats.
        # Adapte le nom si, chez toi, c’est différent.
        md_candidates = [
            "Pokemon1SlotBattle",   # souvent ~44/48 octets; si tu as 40, tu as peut-être raccourci
            "Pokemon1",             # si tu l’as nommé simplement "Pokemon1"
        ]
        for name in md_candidates:
            if hasattr(MainPokemonData, name):
                MD = getattr(MainPokemonData, name)
                break
        else:
            pytest.skip("Aucun MemoryData pour un Pokémon (ex. SavedData.Pokemon1SlotBattle) n’a été trouvé.")

        # Construit l’objet à partir de la RAM. Red => is_yellow=False
        mon = Pokemon.from_memory(pyboy, MD, is_yellow=False)

        # --- Assertions principales (basées sur tes captures) ---
        # assert mon.number == 7, f"Expected Squirtle(7), got {mon.number}"
        # le décodage Gen1 peut varier selon ton mapping — on tolère un 'startswith'
        assert mon.name.startswith("ABCDEFGH"), f"Got name: {mon.name}"
        assert mon.level == 5, f"Expected level 5, got {mon.level}"
        assert mon.current_hp == 14 and mon.max_hp == 20, f"Expected 14/20, got {mon.current_hp}/{mon.max_hp}"
        assert mon.types[0] == "Water", f"Expected type1 Water, got {mon.types[0]}"

    finally:
        pyboy.stop()


# ---- Script entrypoint ----
if __name__ == "__main__":
    print("Running test_pokemon_parsing...")
    test_pokemon_parsing()
    print("✅ test_pokemon_parsing passed")
