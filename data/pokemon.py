import pyboy
from dataclasses import dataclass
from typing import List, Dict
from data.decoder import decode_pkm_text
from data.ram_reader import MemoryData, SavedData

# --- Status flags ---
STATUS_BIT_MASKS = {
    0b00000001: "Sleep counter 1",
    0b00000010: "Sleep counter 2",
    0b00000100: "Sleep counter 3",
    0b00001000: "Poisoned",
    0b00010000: "Burned",
    0b00100000: "Frozen",
    0b01000000: "Paralyzed"
}

# --- Pokémon types (Gen I) ---
POKEMON_TYPES = {
    0: "Normal",
    1: "Fighting",
    2: "Flying",
    3: "Poison",
    4: "Ground",
    5: "Rock",
    6: "Bird",   # unused
    7: "Bug",
    8: "Ghost",
    9: "Steel",  # placeholder in some tables
    20: "Fire",
    21: "Water",
    22: "Grass",
    23: "Electric",
    24: "Psychic",
    25: "Ice",
    26: "Dragon"
}

# --- Attribute layout inside the struct ---
POKEMON_LAYOUT = {
    "name":       (0, 11),
    "number":     (11, 12),
    "current_hp": (12, 14),
    "status":     (15, 16),
    "type1":      (16, 17),
    "type2":      (17, 18),
    "moves":      (19, 23),
    "dvs":        (23, 25),  # attack/defense, speed/special
    "level":      (25, 26),
    "max_hp":     (26, 28),
    "attack":     (28, 30),
    "defense":    (30, 32),
    "speed":      (32, 34),
    "special":    (34, 36),
    "pp":         (36, 40)
}

# --- Helpers for decoding ---
def read_u8(raw: List[int], sl: tuple[int, int]) -> int:
    return raw[sl[0]]

def read_u16(raw: List[int], sl: tuple[int, int]) -> int:
    hi, lo = raw[sl[0]:sl[1]]
    return lo | (hi << 8)

def read_str(raw: List[int], sl: tuple[int, int]) -> str:
    return decode_pkm_text(raw[sl[0]:sl[1]], stop_at_terminator=True)

def read_list(raw: List[int], sl: tuple[int, int]) -> List[int]:
    return raw[sl[0]:sl[1]]

def parse_status(b: int) -> List[str]:
    return [status for bit, status in STATUS_BIT_MASKS.items() if b & bit]

def parse_dvs(b1: int, b2: int) -> Dict[str, int]:
    return {
        "attack":  (b1 >> 4) & 0xF,
        "defense": b1 & 0xF,
        "speed":   (b2 >> 4) & 0xF,
        "special": b2 & 0xF,
    }

# --- Pokémon wrapper class ---
@dataclass
class Pokemon:
    raw: List[int]
    memory_address: int
    pyboy: 'pyboy.PyBoy'

    @classmethod
    def from_memory(cls, pyboy: 'pyboy.PyBoy', data: MemoryData, is_yellow=True) -> 'Pokemon':
        """Load a Pokémon struct directly from PyBoy memory."""
        shift = 0x5
        fixed = SavedData.get_pkm_yellow_addresses(data) if is_yellow else data
        raw_data = list(pyboy.memory[fixed.start_address + shift : fixed.end_address + 1 + shift])
        return cls(raw_data, fixed.start_address, pyboy)

    # --- Properties ---
    @property
    def name(self) -> str:
        return read_str(self.raw, POKEMON_LAYOUT["name"])

    @property
    def number(self) -> int:
        return read_u8(self.raw, POKEMON_LAYOUT["number"])

    @property
    def current_hp(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT["current_hp"])

    @property
    def max_hp(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT["max_hp"])

    @property
    def level(self) -> int:
        return read_u8(self.raw, POKEMON_LAYOUT["level"])

    @property
    def status(self) -> List[str]:
        return parse_status(read_u8(self.raw, POKEMON_LAYOUT["status"]))

    @property
    def types(self) -> tuple[str, str]:
        t1 = POKEMON_TYPES.get(read_u8(self.raw, POKEMON_LAYOUT["type1"]), "Unknown")
        t2 = POKEMON_TYPES.get(read_u8(self.raw, POKEMON_LAYOUT["type2"]), "Unknown")
        return (t1, t2)

    @property
    def moves(self) -> List[int]:
        return read_list(self.raw, POKEMON_LAYOUT["moves"])

    @property
    def pp(self) -> List[int]:
        return read_list(self.raw, POKEMON_LAYOUT["pp"])

    @property
    def dvs(self) -> Dict[str, int]:
        b1, b2 = self.raw[23], self.raw[24]
        return parse_dvs(b1, b2)

    @property
    def attack(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT["attack"])

    @property
    def defense(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT["defense"])

    @property
    def speed(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT["speed"])

    @property
    def special(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT["special"])

    # --- Setters (write directly to WRAM) ---
    def set_level(self, new_level: int):
        self.pyboy.memory[self.memory_address + 0x5 + 25-1] = new_level
        self._reload_memory()

    def _reload_memory(self):
        shift = 0x5
        self.raw = list(self.pyboy.memory[self.memory_address + shift : self.memory_address + shift + len(self.raw)])

    # --- Pretty-print ---
    def __str__(self):
        return (
            f"Name: {self.name}, "
            f"Level: {self.level}, "
            f"HP: {self.current_hp}/{self.max_hp}, "
            f"Type: {self.types[0]}/{self.types[1]}, "
            f"Status: {', '.join(self.status) if self.status else 'Healthy'}"
        )
