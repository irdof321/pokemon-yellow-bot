# tests/test_pokemon.py
import pytest
from data.decoder import decode_pkm_text
from data.pokemon import PokemonBattleSlot, PokemonParty, POKEMON_LAYOUT_BATTLE, POKEMON_ROM_ID_TO_PKDX_ID
from data.ram_reader import MemoryData, MainPokemonData
from data.move import Move, _read_move_name_current_bank
from data.helpers import select_rom_bank
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
    data[POKEMON_LAYOUT_BATTLE["number"][0]] = 42
    # level
    data[POKEMON_LAYOUT_BATTLE["level"][0]] = 50
    # current_hp = 1234 (0x04D2) -> hi, lo = [0x04, 0xD2]
    data[POKEMON_LAYOUT_BATTLE["current_hp"][0]:POKEMON_LAYOUT_BATTLE["current_hp"][1]] = bytes([0x04, 0xD2])
    # max_hp = 1300 (0x0514) -> [0x05, 0x14]
    data[POKEMON_LAYOUT_BATTLE["max_hp"][0]:POKEMON_LAYOUT_BATTLE["max_hp"][1]] = bytes([0x05, 0x14])
    # moves
    data[POKEMON_LAYOUT_BATTLE["moves"][0]:POKEMON_LAYOUT_BATTLE["moves"][1]] = bytes([1, 2, 3, 4])
    # dvs
    data[POKEMON_LAYOUT_BATTLE["dvs"][0]:POKEMON_LAYOUT_BATTLE["dvs"][1]] = bytes([0xAB, 0xCD])
    # pp
    data[POKEMON_LAYOUT_BATTLE["pp"][0]:POKEMON_LAYOUT_BATTLE["pp"][1]] = bytes([10, 20, 30, 40])
    return data


def test_pokemon_parsing(monkeypatch=None):
    # Monkeypatch decode_pkm_text to avoid charset logic
    import data.pokemon
    data.pokemon.decode_pkm_text = lambda seq, stop_at_terminator=True: "TESTMON"

    # Prepare memory
    mem = DummyPyBoy().memory
    MemoryData.set_shift(0x0)
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
ROM_PATH   = "games/PokemonRed.gb"
# STATE_PATH = "games/Rouge/PokemonTestClassPokemon.state"
STATE_PATH = "games/Rouge/PokemonRed.Test1.state"

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
    MemoryData.set_shift(0x0)

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
        ]
        for name in md_candidates:
            if hasattr(MainPokemonData, name):
                MD = getattr(MainPokemonData, name)
                break
        else:
            pytest.skip("Aucun MemoryData pour un Pokémon (ex. SavedData.Pokemon1SlotBattle) n’a été trouvé.")

        # Construit l’objet à partir de la RAM. Red => is_yellow=False
        mon = PokemonBattleSlot.from_memory(pyboy, MD, is_yellow=False)

        # --- Assertions principales (basées sur tes captures) ---
        assert mon.number == 129, f"Expected Squirtle(0xb1), got {mon.number}" 
        # le décodage Gen1 peut varier selon ton mapping — on tolère un 'startswith'
        mon.status
        assert mon.nickname.startswith("MAGIKARP"), f"Got nickname: {mon.nickname}"
        assert mon.name == "Magikarp", f"Expected Wartortle, got {mon.name}"
        assert mon.level == 14, f"Expected level 14, got {mon.level}"
        assert mon.current_hp == 34 and mon.max_hp == 34, f"Expected 23/49, got {mon.current_hp}/{mon.max_hp}"
        assert mon.types[0] == "Water", f"Expected type1 Water, got {mon.types[0]}"

    # Load second pokemon in party (Daradagnan)
        md2 = getattr(MainPokemonData, "Pokemon2", None)
        if md2 is None:
            pytest.skip("No MemoryData for second Pokémon found in MainPokemonData. Skipping second Pokémon test.")
        mon2 = PokemonParty.from_memory(pyboy, md2, is_yellow=False)
        assert mon2.number == 15, f"Expected Dragonite(0xF5), got {mon2.number}"
        assert mon2.nickname.startswith("BEEDRIL"), f"Got name: {mon2.nickname}"
        assert mon2.name == "Beedrill", f"Expected Beedrill, got {mon2.name}"
        assert mon2.level == 10, f"Expected level 12, got {mon2.level}"
        assert mon2.current_hp == 35 and mon2.max_hp == 35, f"Expected 39/39, got {mon2.current_hp}/{mon2.max_hp}"
        assert mon2.types[0] == "Bug", f"Expected type1 Bug, got {mon2.types[0]}"
        assert mon2.types[1] == "Poison", f"Expected type2 Poison, got {mon2.types[1]}"

    finally:
        pyboy.stop()

# --- Constantes mémoire Gen 1 (RB/Y) ---
PARTY_BASE_ADDR    = 0xD16B
PARTY_STRUCT_LEN   = 0x2C  # 44 bytes
NICK_BASE_ADDR     = 0xD2B5
NICK_LEN           = 0x0B  # 11 bytes (terminator 0x50 possible)
CF1A               = 0xCF1A  # seuil de décalage Yellow
PYBOY_WRAM_SHIFT   = 0x5     # décalage PyBoy WRAM

def rb_yellow_addr(addr: int, is_yellow: bool) -> int:
    return addr - 1 if is_yellow and addr >= CF1A else addr



def nickname_slot_base(i: int) -> int:
    return NICK_BASE_ADDR + (i-1) * NICK_LEN



@pytest.mark.skipif(not _has_files(), reason="ROM or state not found locally.")
def test_party_order_matches_menu_screenshot():
    # RB => pas de Yellow-shift, mais on garde la fct pour compat
    is_yellow = False

    # important pour l'accès direct .memory (PyBoy WRAM +0x5)
    MemoryData.set_shift(0x5)

    pyboy = PyBoy(ROM_PATH, window="null", log_level="WARNING")
    try:
        with open(STATE_PATH, "rb") as f:
            pyboy.load_state(f)

        # Attendus (issus de ta capture)
        expected = [
            # slot, dex, nickname, level, (cur,max), type1, type2
            (1, 129, "MAGIKARP",   14, (34, 34), "Water", "Water"),
            (2,  15, "BEEDRILL",   10, (35, 35), "Bug", "Poison"),
            (3,  16, "PIDGEY",     14, (39, 39), "Normal", "Flying"),
            (4,  21, "SPEAROW",     7, (23, 23), "Normal", "Flying"),
            (5,  35, "CLEFAIRY",   12, (39, 39), "Normal", "Normal"),
            (6,   5, "CHARMELEON", 22, (53, 61), "Fire",  "Fire"),
        ]

        for slot, dex, nick, lvl, (hp, hpmax), t1, t2 in expected:
            # 1) Lire le Pokémon Party depuis la RAM
            md = MainPokemonData.get_main_pkm_for_party_slot(slot)
            mon = PokemonParty.from_memory(pyboy, md, is_yellow=is_yellow)

            # 3) Asserts
            assert mon.number == dex, f"slot {slot}: expected dex {dex}, got {mon.number}"
            assert mon.level == lvl,  f"slot {slot}: expected L{lvl}, got L{mon.level}"
            assert mon.current_hp == hp and mon.max_hp == hpmax, \
                f"slot {slot}: expected HP {hp}/{hpmax}, got {mon.current_hp}/{mon.max_hp}"

            # Le décodeur supprime le terminator; la capture montre parfois un '_' final,
            # on tolère ça en comparant en uppercase et en ignorant '_' terminaux.
            assert mon.nickname.upper().rstrip('_') == nick, \
                f"slot {slot}: expected nickname '{nick}', got '{mon.nickname}'"

            # Types : certains mon auront type2=None (ex. Rondoudou en Gen1)
            got_t1, got_t2 = mon.types
            assert got_t1 == t1, f"slot {slot}: expected type1 {t1}, got {got_t1}"
            if t2:
                assert got_t2 == t2, f"slot {slot}: expected type2 {t2}, got {got_t2}"



    finally:
        pyboy.stop()


def test_moves():
    """
    Quick integration test:
      - Boots a saved state
      - Selects the ROM bank that holds the move-name table
      - Reads party slot #2
      - Verifies a few canonical move names by ID
      - Prints the monster name, its move IDs and their decoded names
    """
    pyboy = PyBoy(ROM_PATH, window="null", log_level="WARNING")
    try:
        # Load deterministic state
        with open("games/Rouge/PokemonRed.TestMove.gb.state", "rb") as f:
            pyboy.load_state(f)

        # Map the bank containing the concatenated move names (adjust if needed)
        select_rom_bank(pyboy, 0x2C)

        # Read the Pokémon in party slot #2
        md = md_for_party_slot(2)
        mon = PokemonParty.from_memory(pyboy, md, is_yellow=False)
        print(f"Pokémon: {mon.name}")

        # Helper: resolve a list of move IDs to their names from the *current* bank
        def get_move_names(move_ids: list[int]) -> list[str]:
            return [_read_move_name_current_bank(pyboy, mid) for mid in move_ids]

        # Sanity check: first few move IDs against known strings
        probe_ids = [0, 1, 2, 3]
        probe_names = get_move_names(probe_ids)
        assert probe_names == ["NA", "POUND", "KARATE CHOP", "DOUBLESLAP"], probe_names

        # Actual moves of the Pokémon (IDs + names)
        move_ids = mon.moves
        print(f"Move IDs: {move_ids}")

        names = get_move_names(move_ids)
        print("\n".join(names))

        # Expected names for this saved state
        assert names[0] == "POISON STING"
        assert names[1] == "STRING SHOT"
        assert names[2] == "NA"
        assert names[3] == "NA"

        # Test Move details
        
        moves_list = []
        for move_id in move_ids:
            if move_id > 0:
                moves_list.append(Move.load_from_id(pyboy,move_id))

        
        print(moves_list[0])

    finally:
        pyboy.stop()


if __name__ == "__main__":
    print("Running test_pokemon_parsing...")
    test_pokemon_parsing()
    print("✅ test_pokemon_parsing passed")
