from abc import ABC, abstractmethod
import pyboy
from typing import Any, ClassVar, List, Dict, Literal, Optional, Tuple
from data.decoder import decode_pkm_text
from data.helpers import  read_list, read_str_from_md, read_u16, read_u16_mem, read_u8, read_u8_mem
from data.ram_reader import MainPokemonData, MemoryData
from data.move import Move
from data.data import POKDX_ID_TO_NAME, POKEMON_ROM_ID_TO_PKDX_ID, POKEMON_TYPES


# Helper for 3-byte EXP (big-ish, hi..lo in memory order)
def read_u24(raw: List[int], sl: tuple[int, int]) -> int:
    b0, b1, b2 = raw[sl[0]:sl[1]]  # [hi, mid, lo]
    return (b0 << 16) | (b1 << 8) | b2
from dataclasses import dataclass
from typing import List, Dict

# Helper for 3-byte EXP (big-ish, hi..lo in memory order)
def read_u24(raw: List[int], sl: tuple[int, int]) -> int:
    b0, b1, b2 = raw[sl[0]:sl[1]]  # [hi, mid, lo]
    return (b0 << 16) | (b1 << 8) | b2




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


# --- In-battle slot (D009..D030) ---
POKEMON_LAYOUT_BATTLE = {
    "name":       (0, 11),   # 11 bytes, Gen1 text
    "number":     (11, 12),  # species/ROM id
    "current_hp": (12, 14),  # u16 LE
    "status":     (15, 16),
    "type1":      (16, 17),
    "type2":      (17, 18),
    "moves":      (19, 23),  # 4 bytes
    "dvs":        (23, 25),  # [ATK/DEF][SPD/SPC] (2 bytes)
    "level":      (25, 26),
    "max_hp":     (26, 28),  # u16 LE
    "attack":     (28, 30),  # u16 LE
    "defense":    (30, 32),  # u16 LE
    "speed":      (32, 34),  # u16 LE
    "special":    (34, 36),  # u16 LE
    "pp":         (36, 40),  # 4 bytes (PP1..PP4)
}
BATTLE_STRUCT_LEN = 40  # bytes
BATTLE_NAME_LEN   = 11

# --- Party/Save struct (D16B..D272) ---
# Offsets relatifs au début du Pokémon (44 octets)
POKEMON_LAYOUT_PARTY = {
    "id":             (0, 1),     # species/ROM id
    "current_hp":     (1, 3),     # u16 LE

    # 'Level' fantôme (D16E) -> pas le vrai niveau utilisé pour les stats
    "level_shadow":   (3, 4),

    "status":         (4, 5),
    "type1":          (5, 6),
    "type2":          (6, 7),
    "catch_rate_g2":  (7, 8),     # catch rate / held item if traded to Gen2

    "moves":          (8, 12),    # 4 bytes (Move1..Move4)

    "trainer_id":     (12, 14),   # u16 LE
    "experience":     (14, 17),   # 3 bytes big-ish integer (hi..lo)

    # EVs (u16 LE each)
    "hp_ev":          (17, 19),
    "attack_ev":      (19, 21),
    "defense_ev":     (21, 23),
    "speed_ev":       (23, 25),
    "special_ev":     (25, 27),

    # IVs/DVs (2 bytes, nibbles)
    # byte1: ATK (hi nibble), DEF (lo nibble)
    # byte2: SPD (hi), SPC (lo)
    "ivs":            (27, 29),

    # PP bytes (PP1..PP4)
    "pp":             (29, 33),

    # VRAI niveau + stats dérivées
    "level":          (33, 34),
    "max_hp":         (34, 36),   # u16 LE
    "attack":         (36, 38),   # u16 LE
    "defense":        (38, 40),   # u16 LE
    "speed":          (40, 42),   # u16 LE
    "special":        (42, 44),   # u16 LE

    "name":           (44, 55),   # 11 bytes, Gen1 text (not in battle struct)
}
PARTY_STRUCT_LEN = 44  # bytes



def parse_status(b: int) -> List[str]:
    #Only one status can be active at a time in Gen I
    #If it is a sleep status, the 3 first of the mask are used to know what counter it is
    # it can be from 7 to 0 max turns sleep and 0 means not asleep
    # A number between 0 and 7 is choosen randomly
    if b & 0b00000111:
        return [f"Sleep ({7-(b & 0b00000111)}/7)"]
    status = [status for bit, status in STATUS_BIT_MASKS.items() if b & bit and bit != 0b00000111]
    if len(status) == 0:
        status = ["Healty"]
    return status


def parse_dvs(b1: int, b2: int) -> Dict[str, int]:
    return {
        "attack":  (b1 >> 4) & 0xF,
        "defense": b1 & 0xF,
        "speed":   (b2 >> 4) & 0xF,
        "special": b2 & 0xF,
    }






class Pokemon(ABC):
    # attribut de classe optionnel si tu veux y mettre un handle global
    game: ClassVar[Optional['pyboy.PyBoy']] = None

    # Local helpers
    def _u8(self, md: 'MemoryData') -> int:  return read_u8_mem(md)
    def _u16(self, md: 'MemoryData') -> int: return read_u16_mem(md)

    def __init__(self, pyboy: 'pyboy.PyBoy', is_yellow: bool):
        if Pokemon.game is None:
            Pokemon.game = pyboy
        # caches optionnels
        self._cache: Dict[str, Any] = {}

    # --- API commune que les enfants doivent fournir ---
    @property 
    @abstractmethod
    def species_id(self) -> int: ...
    @property
    def number(self) -> int:
        return POKEMON_ROM_ID_TO_PKDX_ID.get(self.species_id, 0)
    @property
    def name(self) -> str:
        return POKDX_ID_TO_NAME.get(self.number, {"en": "Unknown"}).get("en", "Unknown")
    @property 
    @abstractmethod
    def level(self) -> int: ...
    @property 
    @abstractmethod
    def current_hp(self) -> int: ...
    @property 
    @abstractmethod
    def max_hp(self) -> int: ...
    @property 
    @abstractmethod
    def status(self) -> List[str]: ...
    @property 
    @abstractmethod
    def types(self) -> Tuple[str, str]: ...
    @property
    @abstractmethod
    def moves(self) -> List[Move]: ...


    # Hooks génériques
    def refresh(self):
        """Par défaut, invalide le cache. Les enfants rechargent ce qu'il faut."""
        self._cache.clear()

    # Outil commun d’inspection
    def to_dict(self) -> Dict[str, Any]:
        t1, t2 = self.types
        return {
            "dex": self.number,
            "name": self.name,
            "level": self.level,
            "hp": (self.current_hp, self.max_hp),
            "types": (t1, t2),
            "status": self.status,
            "moves": [m.to_dict() for m in self.moves]
        }

    def __str__(self) -> str:
        t1, t2 = self.types
        st = self.status
        return (f"{self.name} (#{self.number:03d}) | "
                f"L{self.level} | HP {self.current_hp}/{self.max_hp} | "
                f"{t1}/{t2} | "
                f"Status: {', '.join(st) if st else 'Healthy'}")


class PartyPokemon(Pokemon):
    # slot -> (block, nickname) MemoryData
    SLOT_BLOCKS: ClassVar[Dict[int, Tuple['MemoryData','MemoryData']]] = {
        1: (MainPokemonData.Pokemon1, MainPokemonData.Nickname1),
        2: (MainPokemonData.Pokemon2, MainPokemonData.Nickname2),
        3: (MainPokemonData.Pokemon3, MainPokemonData.Nickname3),
        4: (MainPokemonData.Pokemon4, MainPokemonData.Nickname4),
        5: (MainPokemonData.Pokemon5, MainPokemonData.Nickname5),
        6: (MainPokemonData.Pokemon6, MainPokemonData.Nickname6),
    }

    def __init__(self, pyboy: 'pyboy.PyBoy', slot: int, is_yellow: bool = True):
        super().__init__(pyboy, is_yellow)
        if slot not in self.SLOT_BLOCKS:
            raise ValueError("slot must be in 1..6")
        self.slot = slot
        md_block, _ = self.SLOT_BLOCKS[self.slot]
        self._base_addr = md_block.start_address  # début du struct (44 octets)

    # --------------- helpers RAM (live-read) ----------------
    def _abs_range(self, key: str) -> Tuple[int, int]:
        """Retourne les adresses absolues [start, end_excl) en RAM pour un champ du layout."""
        s_rel, e_rel = POKEMON_LAYOUT_PARTY[key]   # offsets relatifs au bloc
        return self._base_addr + s_rel, self._base_addr + e_rel

    def _rb(self, key: str) -> List[int]:
        s, e = self._abs_range(key)
        return list(MemoryData.game.memory[s:e])

    def _read_u8(self, key: str) -> int:
        raw = self._rb(key)               # attend au moins 1 octet
        return read_u8(raw, (0, 1))       # utilise ton helper

    def _read_u16(self, key: str) -> int:
        raw = self._rb(key)               # 2 octets, layout fourni hi..lo (cf. tes helpers)
        return read_u16(raw, (0, 2))

    def _write_u8(self, key: str, value: int):
        s, _ = self._abs_range(key)
        MemoryData.game.memory[s] = value & 0xFF

    def _write_u8_list_slot(self, key: str, idx: int, value: int):
        s, _ = self._abs_range(key)
        MemoryData.game.memory[s + idx] = value & 0xFF

    # ---------------- Core fields ---------------------------
    @property
    def name(self) -> str:
        # Pokédex name (pas le nickname)
        return POKDX_ID_TO_NAME.get(self.number, {"en": "Unknown", "fr": "Inconnu"}).get("en", "Unknown")

    @property
    def nickname(self) -> str:
        # nickname stocké ailleurs (11 octets), on le lit à la volée
        _, nick_md = self.SLOT_BLOCKS[self.slot]
        raw = MemoryData.game.read_bytes(nick_md)  # Yellow-fix inside
        return decode_pkm_text(raw, stop_at_terminator=True)

    @property
    def species_id(self) -> int:
        return self._read_u8("id")

    @property
    def number(self) -> int:
        """National Pokédex number (via ROM->Dex map)."""
        return POKEMON_ROM_ID_TO_PKDX_ID.get(self.species_id, 0)

    @property
    def current_hp(self) -> int:
        return self._read_u16("current_hp")

    @property
    def max_hp(self) -> int:
        return self._read_u16("max_hp")

    @property
    def level(self) -> int:
        return self._read_u8("level")

    @property
    def status(self) -> List[str]:
        return parse_status(self._read_u8("status"))

    @property
    def types(self) -> tuple[str, str]:
        t1 = POKEMON_TYPES.get(self._read_u8("type1"), "Unknown")
        t2 = POKEMON_TYPES.get(self._read_u8("type2"), "Unknown")
        return (t1, t2)

    # --------------- Moves / PP -----------------------------
    @property
    def moves(self) -> List[int]:
        # 4 octets, ids de moves        
        move_ids = (self._rb("moves"), (0, 4))
        move_list = []
        
        for id, pp in zip(move_ids,self.pp) :
            m = Move.load_from_id(self.game,id)
            m.set_remaining_pp(pp)
            move_list.append(m)
            
        return move_list

    @property
    def pp(self) -> List[int]:
        # 4 octets, PP par move
        return read_list(self._rb("pp"), (0, 4))

    # --------------- Stats ---------------------------------
    @property
    def attack(self) -> int:
        return self._read_u16("attack")

    @property
    def defense(self) -> int:
        return self._read_u16("defense")

    @property
    def speed(self) -> int:
        return self._read_u16("speed")

    @property
    def special(self) -> int:
        return self._read_u16("special")

    # --------------- IDs / EXP ------------------------------
    @property
    def trainer_id(self) -> int:
        return self._read_u16("trainer_id")

    @property
    def experience(self) -> int:
        # u24 big-ish : [hi, mid, lo] dans la slice
        raw = self._rb("experience")
        return read_u24(raw, (0, 3))

    # --------------- EVs / IVs ------------------------------
    @property
    def evs(self) -> Dict[str, int]:
        return {
            "hp":      self._read_u16("hp_ev"),
            "attack":  self._read_u16("attack_ev"),
            "defense": self._read_u16("defense_ev"),
            "speed":   self._read_u16("speed_ev"),
            "special": self._read_u16("special_ev"),
        }

    @property
    def ivs(self) -> Dict[str, int]:
        iv_raw = self._rb("ivs")  # 2 octets
        iv_b1, iv_b2 = iv_raw[0], iv_raw[1]
        return parse_dvs(iv_b1, iv_b2)

    # --------------- Misc ----------------------------------
    @property
    def level_shadow(self) -> int:
        """Byte 'shadow' de niveau (non canonique, ex. D16E)."""
        return self._read_u8("level_shadow")

    @property
    def catch_rate_g2(self) -> int:
        """Catch rate (Gen1) / devient Held Item en Gen2 après trade."""
        return self._read_u8("catch_rate_g2")

    # --------------- Setters --------------------------------
    def set_level(self, new_level: int):
        self._write_u8("level", new_level)

    def set_move(self, slot_idx: int, move_id: int):
        assert 0 <= slot_idx < 4
        self._write_u8_list_slot("moves", slot_idx, move_id)

    def set_pp(self, slot_idx: int, new_pp: int):
        assert 0 <= slot_idx < 4
        self._write_u8_list_slot("pp", slot_idx, new_pp & 0xFF)

    # --------------- Pretty-print ---------------------------
    def __str__(self):
        t1, t2 = self.types
        st = self.status
        return (
            f"{self.nickname} (Dex #{self.number:03d}:{self.name}) | "
            f"L{self.level} | HP {self.current_hp}/{self.max_hp} | "
            f"{t1}/{t2} | Status: {', '.join(st) if st else 'Healthy'}"
        )
    





class EnemyPokemon(Pokemon):
    def __init__(self, pyboy: 'pyboy.PyBoy', is_yellow: bool = True):
        super().__init__(pyboy, is_yellow)

    # Impl API
    @property
    def species_id(self) -> int:
        return self._u8(MainPokemonData.EnemyPokemonID2)

    @property
    def level(self) -> int:
        return self._u8(MainPokemonData.EnemyLevel2)  # la canonique

    @property
    def current_hp(self) -> int:
        return self._u16(MainPokemonData.EnemyHP)

    @property
    def max_hp(self) -> int:
        return self._u16(MainPokemonData.EnemyMaxHP)

    @property
    def status(self) -> List[str]:
        return parse_status(self._u8(MainPokemonData.EnemyStatus))

    @property
    def types(self) -> Tuple[str, str]:
        t1 = POKEMON_TYPES.get(self._u8(MainPokemonData.EnemyType1), "Unknown")
        t2 = POKEMON_TYPES.get(self._u8(MainPokemonData.EnemyType2), "Unknown")
        return (t1, t2)

    @property
    def pp(self) -> List[int]:
        return [
            self._u8(MainPokemonData.EnemyPP1),
            self._u8(MainPokemonData.EnemyPP2),
            self._u8(MainPokemonData.EnemyPP3),
            self._u8(MainPokemonData.EnemyPP4)
        ]

    # Exemples d’infos supplémentaires spécifiques Enemy
    @property
    def moves(self) -> List[int]:
        move_ids =  [
            self._u8(MainPokemonData.EnemyMove1),
            self._u8(MainPokemonData.EnemyMove2),
            self._u8(MainPokemonData.EnemyMove3),
            self._u8(MainPokemonData.EnemyMove4),
        ]
        move_list = []
        
        for id, pp in zip(move_ids,self.pp) :
            m = Move.load_from_id(self.game,id)
            m.set_remaining_pp(pp)
            move_list.append(m)
            
        return move_list
    

class PlayerPokemonBattle(Pokemon):

    def __init__(self, pyboy: 'pyboy.PyBoy', is_yellow: bool = True):
        super().__init__(pyboy, is_yellow)

    @property
    def name(self) -> str:
        return read_str_from_md(MainPokemonData.PlayerPokemonName)
    
    @property
    def current_hp(self):
        return self._u16(MainPokemonData.PlayerCurrentHP)
    
    @property 
    def max_hp(self) -> int: 
        return self._u16(MainPokemonData.PlayerMaxHP)
    
    def species_id(self) -> int:
        return self._u8(MainPokemonData.PlayerPokemonNumber)
    
    @property 
    def level(self) -> int: 
        return self._u8(MainPokemonData.PlayerLevel)

    @property 
    def status(self) -> List[str]:
        return parse_status(self._u8(MainPokemonData.PlayerStatus))
    
    @property 
    def types(self) -> Tuple[str, str]:
        t1 = POKEMON_TYPES.get(self._u8(MainPokemonData.PlayerType1), "Unknown")
        t2 = POKEMON_TYPES.get(self._u8(MainPokemonData.PlayerType2), "Unknown")
        return (t1, t2)

    @property
    def pp(self) -> List[int]:
        return [
            self._u8(MainPokemonData.PlayerPP1),
            self._u8(MainPokemonData.PlayerPP2),
            self._u8(MainPokemonData.PlayerPP3),
            self._u8(MainPokemonData.PlayerPP4)
        ]
    
    @property
    def moves(self) -> List[int]:
        move_ids =  [
            self._u8(MainPokemonData.PlayerMove1),
            self._u8(MainPokemonData.PlayerMove2),
            self._u8(MainPokemonData.PlayerMove3),
            self._u8(MainPokemonData.PlayerMove4),
        ]
        move_list = []
        
        for id, pp in zip(move_ids,self.pp) :
            m = Move.load_from_id(self.game,id)
            m.set_remaining_pp(pp)
            move_list.append(m)
            
        return move_list


class PokemonFactory:
    """Simple constructors for EnemyPokemon and PartyPokemon."""

    @staticmethod
    def enemy(pyboy: 'pyboy.PyBoy', *, is_yellow: bool = True) -> EnemyPokemon:
        return EnemyPokemon(pyboy, is_yellow=is_yellow)

    @staticmethod
    def party(pyboy: 'pyboy.PyBoy', slot: int, *, is_yellow: bool = True) -> PartyPokemon:
        if not (1 <= slot <= 6):
            raise ValueError("slot must be in 1..6")
        return PartyPokemon(pyboy, slot=slot, is_yellow=is_yellow)

    @staticmethod
    def create(
        pyboy: 'pyboy.PyBoy',
        source: Literal["enemy", "party"],
        *,
        slot: Optional[int] = None,
        is_yellow: bool = True,
    ) -> Pokemon:
        if source == "enemy":
            return PokemonFactory.enemy(pyboy, is_yellow=is_yellow)
        if source == "party":
            if slot is None:
                raise ValueError("slot is required when source='party'")
            return PokemonFactory.party(pyboy, slot=slot, is_yellow=is_yellow)
        raise ValueError("source must be 'enemy' or 'party'")