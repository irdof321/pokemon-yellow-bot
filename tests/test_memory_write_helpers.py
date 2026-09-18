"""Tests for game.data.helpers's RAM write helpers -- write_u8/write_u16/
write_bytes had no coverage at all before this (found via a real bug: see
write_u16's docstring for the byte-order mismatch this test would have
caught immediately)."""
from game.data.helpers import read_u16_mem, read_u8_mem, write_bytes, write_u8, write_u16
from game.data.ram_reader import MainPokemonData


def test_write_u16_round_trips_through_the_real_read_path(load_fixture):
    """The point of this test: write via write_u16, read back via
    read_u16_mem (the same function every _u16 accessor in the project
    uses) -- they must agree, not just "write_u16 does something"."""
    session = load_fixture("wild_ratatta_par.state")

    write_u16(MainPokemonData.EnemyMaxHP, 17)
    assert read_u16_mem(MainPokemonData.EnemyMaxHP) == 17

    write_u16(MainPokemonData.EnemyMaxHP, 4352)  # would be the OLD bug's silent output for 17
    assert read_u16_mem(MainPokemonData.EnemyMaxHP) == 4352

    write_u16(MainPokemonData.EnemyMaxHP, 300)  # exercises both bytes non-trivially
    assert read_u16_mem(MainPokemonData.EnemyMaxHP) == 300


def test_write_u8_round_trips(load_fixture):
    session = load_fixture("wild_ratatta_par.state")
    write_u8(MainPokemonData.EnemyLevel2, 42)
    assert read_u8_mem(MainPokemonData.EnemyLevel2) == 42
