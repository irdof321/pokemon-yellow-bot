
from game.data.data import  POKEMON_TYPES, FUNCTION_CODE_EFFECT
from dataclasses import dataclass
from game.data.decoder import decode_pkm_text
import json

from game.data.ram_reader import MoveROMBank


# --- Trouver l'offset juste après la n-ième occurrence de 0x50
def _offset_after_n_terms(buf: bytes | bytearray, byte: int, n: int) -> int | None:
    if n <= 0:
        return 0
    start = 0
    for _ in range(n):
        # si buf est bytearray/bytes, .find est supporté et renvoie -1 si absent
        p = buf.find(byte, start) if isinstance(buf, (bytes, bytearray)) else -1
        if p == -1:
            return None
        start = p + 1
    return start  # début de la (n+1)-ième chaîne

def _move_name_ptr_current_bank(pyboy, move_id: int, table_base: int = 0x4000) -> int:
    if move_id <= 0:
        return -1
    # scanner tout le bank mappé en 0x4000–0x7FFF
    bank_window = bytes(pyboy.memory[0x4000:0x8000])
    start = _offset_after_n_terms(bank_window, 0x50, move_id - 1)
    if start is None:
        # bank mauvais ou table tronquée
        raise ValueError(
            f"Not enough 0x50 terminators in current bank for move_id={move_id} "
            f"(check bank or table bounds)."
        )
    return start  # offset relatif à table_base (0x4000)

def _read_move_name_current_bank(pyboy, move_id: int, table_base: int = 0x4000, cap: int = 24) -> str:
    if move_id == 0:
        return "NA"
    start = _move_name_ptr_current_bank(pyboy, move_id, table_base=table_base)
    if start < 0:
        return "NA"
    raw = pyboy.memory[table_base + start : table_base + start + cap]
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
        if id <=0:
            return Move.load_from_bytes([0,0,0,0,0,0])
        move_bank = MoveROMBank()

        new_move = Move.load_from_bytes(move_bank.get_move_bytes(id))

        new_move.name = move_bank.get_move_name(id,decode_pkm_text)

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