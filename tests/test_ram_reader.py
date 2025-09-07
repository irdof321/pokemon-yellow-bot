# tests/test_ram_reader.py
import pytest
from data.ram_reader import MemoryData, DataType
from game import PokemonGame, GameVersion


def test_memorydata_shift_applied_on_init():
    # default shift = 0x5
    m = MemoryData(0x1000, 0x100F, "test")
    assert m.start_address == 0x1000 + 0x5
    assert m.end_address   == 0x100F + 0x5


def test_set_shift_changes_future_instances_only():
    MemoryData.set_shift(0x4)
    m = MemoryData(0x2000, 0x2001)
    assert m.start_address == 0x2000 + 0x4
    # reset for other tests
    MemoryData.set_shift(0x5)


def test_yellow_rule_applied_on_shifted_addresses(monkeypatch):
    """
    In Yellow: variables at >= 0xCF1A (WRAM) are shifted -1 vs Red/Blue.
    In our implementation the addresses are already shifted by MemoryData.shift,
    so we compare against 0xCF1A + shift.
    """
    MemoryData.set_shift(0x5)
    threshold = 0xCF1A + MemoryData.shift

    game = object.__new__(PokemonGame)   # create dummy without __init__
    game.rom_name = "games/PokemonJaune.gb"

    # region entirely below threshold -> unchanged
    a = MemoryData(0xCF19, 0xCF19)
    fixed = game.get_data(a)  # this returns bytes normally, so we mock
    # Instead of running emulator, patch SavedPokemonData.get_data
    monkeypatch.setattr("data.ram_reader.SavedPokemonData.get_data", lambda self, e: e)

    a_fixed = game.get_data(a)
    assert a_fixed.start_address == a.start_address
    assert a_fixed.end_address == a.end_address

    # region starting before threshold but ending after -> only end shifts -1
    b = MemoryData(0xCF19, 0xCF1A)
    b_fixed = game.get_data(b)
    assert b_fixed.start_address == b.start_address
    assert b_fixed.end_address == b.end_address - 1

    # region entirely >= threshold -> both shift -1
    c = MemoryData(0xCF1A, 0xCF20)
    c_fixed = game.get_data(c)
    assert c_fixed.start_address == c.start_address - 1
    assert c_fixed.end_address == c.end_address - 1
