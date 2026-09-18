"""Helper functions for reading data from the emulator memory."""
from __future__ import annotations

from typing import List, Tuple

from game.data.decoder import decode_pkm_text
from game.data.ram_reader import MemoryData



def read_u8(raw: List[int], sl: Tuple[int, int] = (0, 1)) -> int:
    return raw[sl[0]]


def read_u16(raw: List[int], sl: Tuple[int, int] = (0, 2)) -> int:
    hi, lo = raw[sl[0]:sl[1]]
    return lo | (hi << 8)


def read_str(raw: List[int], sl: Tuple[int, int]) -> str:
    return decode_pkm_text(raw[sl[0]:sl[1]], stop_at_terminator=True)


def read_str_from_md(md: MemoryData) -> str:
    data = MemoryData.game.memory[md.start_address : md.end_address + 1]
    return read_str(list(data), (0, md.end_address - md.start_address + 1))


def read_list(raw: List[int], sl: Tuple[int, int]) -> List[int]:
    return raw[sl[0]:sl[1]]


def fix(md: MemoryData, is_yellow: bool) -> MemoryData:
    return MemoryData.get_pkm_yellow_addresses(md) if is_yellow else md


def read_bytes(md: MemoryData) -> List[int]:
    return list(MemoryData.game.memory[md.start_address : md.end_address + 1])


def read_u8_mem(md: MemoryData) -> int:
    return read_u8(read_bytes(md), (0, 1))


def read_u16_mem(md: MemoryData) -> int:
    return read_u16(read_bytes(md), (0, 2))


def write_bytes(md: MemoryData, data: List[int]) -> None:
    MemoryData.game.memory[md.start_address : md.end_address + 1] = bytes(data)


def write_u8(md: MemoryData, value: int) -> None:
    MemoryData.game.memory[md.start_address] = value & 0xFF


def write_u16(md: MemoryData, value: int) -> None:
    """Mirrors read_u16/read_u16_mem's byte order exactly: high byte at
    start_address, low byte at start_address + 1. Found and fixed
    2026-09-10 -- this function wrote the opposite order (low byte first),
    silently never caught before because nothing had exercised it: writing
    HP=17 (0x0011) produced memory bytes [0x11, 0x00], which read_u16
    (hi,lo = raw[0],raw[1]; return lo | (hi<<8)) then decoded back as
    0x1100 = 4352. Every *read* path in this project (_u16/read_u16_mem)
    already treats the first byte as high/second as low, proven correct by
    every HP/stat value seen all session -- this write side just didn't
    match it."""
    hi = (value >> 8) & 0xFF
    lo = value & 0xFF
    MemoryData.game.memory[md.start_address] = hi
    MemoryData.game.memory[md.start_address + 1] = lo


__all__ = [
    "read_u8",
    "read_u16",
    "read_str",
    "read_str_from_md",
    "read_list",
    "fix",
    "read_bytes",
    "read_u8_mem",
    "read_u16_mem",
    "write_bytes",
    "write_u8",
    "write_u16",
]
