"""Helpers to read the in-game menu state from memory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from game.data.helpers import read_u16_mem, read_u8_mem
from game.data.ram_reader import MainPokemonData


@dataclass
class MenuState:
    cursor_y_top: int
    cursor_x_top: int
    selected_item_id: int
    hidden_tile_under_cursor: int
    last_item_id: int
    key_bitmask: int
    previous_item_id: int
    last_party_cursor_pos: int
    last_item_cursor_pos: int
    last_battle_cursor_pos: int
    current_party_index: int
    cursor_tile_ptr: int
    first_displayed_item_id: int
    select_highlight: int

    @property
    def cursor_pos_top(self) -> Tuple[int, int]:
        return (self.cursor_x_top, self.cursor_y_top)

    @property
    def has_select_highlight(self) -> bool:
        return self.select_highlight != 0

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        msg = (
            f"--- MENU STATE ---\n"
            f"Cursor position (top item): X={self.cursor_x_top}, Y={self.cursor_y_top}\n"
            f"Selected item ID: {self.selected_item_id}\n"
            f"Hidden tile under cursor: {self.hidden_tile_under_cursor}\n"
            f"Last item ID: {self.last_item_id}\n"
            f"Key bitmask: 0x{self.key_bitmask:02X}\n"
            f"Previous item ID: {self.previous_item_id}\n"
            f"Last party cursor position: {self.last_party_cursor_pos}\n"
            f"Last item cursor position: {self.last_item_cursor_pos}\n"
            f"Last battle cursor position: {self.last_battle_cursor_pos}\n"
            f"Current party index: {self.current_party_index}\n"
            f"Cursor tile pointer: 0x{self.cursor_tile_ptr:04X}\n"
            f"First displayed item ID: {self.first_displayed_item_id}\n"
            f"Select highlight: {self.select_highlight} ({'active' if self.has_select_highlight else 'none'})\n"
        )
        return msg


def get_menu_state() -> MenuState:
    y = read_u8_mem(MainPokemonData.MenuCursorYPos)
    x = read_u8_mem(MainPokemonData.MenuCursorXPos)

    selected = read_u8_mem(MainPokemonData.MenuSelectedItem)
    hidden = read_u8_mem(MainPokemonData.MenuHiddenTile)
    last_id = read_u8_mem(MainPokemonData.MenuLastItemID)
    keymask = read_u8_mem(MainPokemonData.MenuKeyBitmask)
    prev_id = read_u8_mem(MainPokemonData.MenuPrevItemID)

    last_party = read_u8_mem(MainPokemonData.MenuLastPartyPos)
    last_item = read_u8_mem(MainPokemonData.MenuLastItemPos)
    last_battle = read_u8_mem(MainPokemonData.MenuLastBattlePos)

    party_index = read_u8_mem(MainPokemonData.MenuCurrentPartyIndex)

    cursor_ptr = read_u16_mem(MainPokemonData.MenuCursorTilePtr)

    first_item_id = read_u8_mem(MainPokemonData.MenuFirstItemID)
    select_high = read_u8_mem(MainPokemonData.MenuSelectHighlight)

    return MenuState(
        cursor_y_top=y,
        cursor_x_top=x,
        selected_item_id=selected,
        hidden_tile_under_cursor=hidden,
        last_item_id=last_id,
        key_bitmask=keymask,
        previous_item_id=prev_id,
        last_party_cursor_pos=last_party,
        last_item_cursor_pos=last_item,
        last_battle_cursor_pos=last_battle,
        current_party_index=party_index,
        cursor_tile_ptr=cursor_ptr,
        first_displayed_item_id=first_item_id,
        select_highlight=select_high,
    )


def get_menu_pos() -> Tuple[int, int]:
    return (
        read_u8_mem(MainPokemonData.MenuCursorXPos),
        read_u8_mem(MainPokemonData.MenuCursorYPos),
    )


def get_selected_menu_item_id() -> int:
    return read_u8_mem(MainPokemonData.MenuSelectedItem)


def get_first_displayed_item_id() -> int:
    return read_u8_mem(MainPokemonData.MenuFirstItemID)


def get_select_highlight() -> int:
    return read_u8_mem(MainPokemonData.MenuSelectHighlight)


def get_cursor_tile_ptr() -> int:
    return read_u16_mem(MainPokemonData.MenuCursorTilePtr)


__all__ = [
    "MenuState",
    "get_menu_state",
    "get_menu_pos",
    "get_selected_menu_item_id",
    "get_first_displayed_item_id",
    "get_select_highlight",
    "get_cursor_tile_ptr",
]
