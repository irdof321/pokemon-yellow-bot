
from game.data.data import  POKEMON_TYPES, FUNCTION_CODE_EFFECT
from dataclasses import dataclass
from game.data.helpers import select_rom_bank
from game.data.decoder import decode_pkm_text
import json



def find_index(li : list, number,max_occ=999999):
    try:
        if max_occ == 0:
            return 0
        idx = li.index(number)
        max_occ -=1
        return idx + 1 + find_index(li[idx+1:],number,max_occ)
    except ValueError:
        return 0

# --- Find start of the Nth (1-based) 0x50-terminated string in the *current* bank
def _move_name_ptr_current_bank(pyboy, move_id: int, table_base: int = 0x4000) -> int:
    """
    Return a pointer (address) to the start of the Nth move name in the
    *currently selected* ROM bank. No bank selection here.
    - move_id: 1-based (0 => empty slot).
    - table_base: where the concatenated names start (0x4000 in this bank).
    """
    if move_id <= 0:
        return -1  # empty / NA
    idx = find_index(pyboy.memory[0x4000:0x460F],0x50,move_id-1)
    
    return  idx   # now at the first byte of the requested name

# --- Read+decode one move name from the *current* bank (no constants, no bank switch)
def _read_move_name_current_bank(pyboy, move_id: int, table_base: int = 0x4000, cap: int = 24) -> str:
    """
    Decode the move name at the current bank using only the ID:
    - Walk to the Nth string via terminators, then read a small window.
    - Your decode_pkm_text() stops at 0x50, so 'cap' is just a safe upper bound.
    """
    if move_id == 0:
        return "NA"
    start = _move_name_ptr_current_bank(pyboy, move_id, table_base=table_base)
    if start < 0:
        return "NA"
    raw = pyboy.memory[0x4000+start:0xB060F]
    return decode_pkm_text(raw, stop_at_terminator=True)



@dataclass
class Move:
    def __init__(self):
        self.name = "Unknown"
        self.id = -1
        self._effect = -1
        self.power = -1
        self._type = -1
        self._accuracy = -1
        self.pp = -1
        self._remaining_pp = -1
        return
    
    @staticmethod
    def load_from_id(pyboy, id : int):
        if id > 0xFF:
            raise ValueError("id must be contained in [0x0:0xFF]")
        
        select_rom_bank(pyboy,0xE)
        new_move = Move.load_from_bytes(pyboy.memory[0x4000+(id-1)*6:0x4000+id*6])

        select_rom_bank(pyboy,0x2C)
        new_move.name = _read_move_name_current_bank(pyboy, new_move.id)

        return new_move


    @staticmethod
    def load_from_bytes(li : list) :
        new_move = Move()
        new_move.id = li[0]
        if new_move.id == 0:
            new_move._effect = -1
            new_move.power = -1
            new_move._type = -1
            new_move._accuracy = -1
            new_move.pp = -1
            new_move._remaining_pp = -1
        else:
            new_move._effect = li[1]
            new_move.power = li[2]
            new_move._type = li[3]
            new_move._accuracy = li[4]
            new_move.pp = li[5]
            new_move._remaining_pp = new_move.pp
        return new_move


    @property
    def effect(self):
        return FUNCTION_CODE_EFFECT.get(self._effect, "(undefined effect – game crash)")
    
    @property
    def type(self):
        return POKEMON_TYPES.get(self._type, "Unknown")

    @property
    def accuracy(self):
        return self._accuracy/255*100
    
    def set_remaining_pp(self,rem_pp : int):
        if rem_pp > self.pp :
            rem_pp = self.pp
        if rem_pp < 0 :
            rem_pp = 0
        self._remaining_pp = rem_pp

    def get_remaining_pp(self) -> int:
        return self._remaining_pp
    
    def __str__(self):
        if self.id == 0:
            return "{EMPTY SLOT}"
        else:
            return """
    "name": {},
    "id" : {},
    "effect" : {},
    "power" : {},
    "type": {},
    "accuracy" : {},
    "pp" : {}/{}

        """.format(self.name,self.id,self.effect,self.power,self.type,self.accuracy,self._remaining_pp,self.pp)

    def to_dict(self):
        return {
            "name" : self.name,
            "effect" : self.effect,
            "power" : self.power,
            "type" : self.type,
            "accuracy" : self.accuracy,
            "pp" : (self._remaining_pp,self.pp)
        }

    def to_json(self, indent: int = 4) -> str:
        if self.id == 0:
            return "{EMPTY SLOT}"
        return json.dumps(self.to_dict(), indent=indent)