
from typing import List

from data.decoder import decode_pkm_text
from data.ram_reader import MemoryData


def select_rom_bank(pyboy, bank: int) -> None:
    bank &= 0x7F
    pyboy.memory[0x6000] = 0x00
    # pyboy.memory[0x4000] = (bank >> 5) & 0x03
    pyboy.memory[0x2000] = bank 


# --- Helpers for decoding ---
def read_u8(raw: List[int], sl : tuple[int, int]  = [0]) -> int:
    return raw[sl[0]]

def read_u16(raw: List[int], sl: tuple[int, int]  = [0,2]) -> int:
    hi, lo = raw[sl[0]:sl[1]]
    return lo | (hi << 8)

def read_str(raw: List[int], sl: tuple[int, int]) -> str:
    return decode_pkm_text(raw[sl[0]:sl[1]], stop_at_terminator=True)

def read_str_from_md(md : MemoryData):
    read_str(MemoryData.game.memory[md.start_address:md.end_address], [0,md.end_address -  md.start_address])


def read_list(raw: List[int], sl: tuple[int, int]) -> List[int]:
    return raw[sl[0]:sl[1]]