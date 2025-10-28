# menu_state.py
from dataclasses import dataclass
from typing import Tuple

from data.helpers import read_u16_mem, read_u8_mem
from data.ram_reader import MainPokemonData





# ---------------------------------------------------------------------
# Dataclass representing the full menu state
# ---------------------------------------------------------------------
@dataclass
class MenuState:
    # Cursor coordinates for the topmost menu item (id 0)
    cursor_y_top: int                 # CC24
    cursor_x_top: int                 # CC25

    # Selection and item IDs
    selected_item_id: int             # CC26 - currently selected item (topmost = 0)
    hidden_tile_under_cursor: int     # CC27 - tile hidden by the cursor
    last_item_id: int                 # CC28 - ID of the last item
    key_bitmask: int                  # CC29 - bitmask applied to key port for the current menu
    previous_item_id: int             # CC2A - ID of the previously selected item

    # Last cursor positions by screen
    last_party_cursor_pos: int        # CC2B - last cursor position on the party / Bill’s PC screen
    last_item_cursor_pos: int         # CC2C - last cursor position on the item screen
    last_battle_cursor_pos: int       # CC2D - last cursor position on the START / battle menu

    # Battle info
    current_party_index: int          # CC2F - index (in party) of the currently sent-out Pokémon

    # Pointer to cursor tile in buffer C3A0
    cursor_tile_ptr: int              # CC30~CC31 - 16-bit pointer (little-endian)

    # Displayed items
    first_displayed_item_id: int      # CC36 - ID of the first displayed menu item
    select_highlight: int             # CC35 - item highlighted with Select (01 = first item, 00 = none, etc.)

    # -----------------------------------------------------------------
    # Derived / convenience properties
    # -----------------------------------------------------------------
    @property
    def cursor_pos_top(self) -> Tuple[int, int]:
        """Returns (x, y) of the cursor for the topmost menu item."""
        return (self.cursor_x_top, self.cursor_y_top)

    @property
    def has_select_highlight(self) -> bool:
        """True if any item is highlighted using the Select button."""
        return self.select_highlight != 0

    # -----------------------------------------------------------------
    # Pretty print
    # -----------------------------------------------------------------
    def __str__(self) -> str:
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


# ---------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------
def get_menu_state() -> MenuState:
    """
    Reads all menu-related variables via MainPokemonData and returns a MenuState instance.
    """
    y = read_u8_mem(MainPokemonData.MenuCursorYPos)           # CC24
    x = read_u8_mem(MainPokemonData.MenuCursorXPos)           # CC25

    selected = read_u8_mem(MainPokemonData.MenuSelectedItem)  # CC26
    hidden   = read_u8_mem(MainPokemonData.MenuHiddenTile)    # CC27
    last_id  = read_u8_mem(MainPokemonData.MenuLastItemID)    # CC28
    keymask  = read_u8_mem(MainPokemonData.MenuKeyBitmask)    # CC29
    prev_id  = read_u8_mem(MainPokemonData.MenuPrevItemID)    # CC2A

    last_party  = read_u8_mem(MainPokemonData.MenuLastPartyPos)   # CC2B
    last_item   = read_u8_mem(MainPokemonData.MenuLastItemPos)    # CC2C
    last_battle = read_u8_mem(MainPokemonData.MenuLastBattlePos)  # CC2D

    party_index = read_u8_mem(MainPokemonData.MenuCurrentPartyIndex)  # CC2F

    cursor_ptr = read_u16_mem(MainPokemonData.MenuCursorTilePtr)   # CC31 (hi)
    # NOTE: if your MemoryData class represents ranges (0xCC30–0xCC31) as a single object,
    # you may need to adapt this call accordingly.

    first_item_id = read_u8_mem(MainPokemonData.MenuFirstItemID)       # CC36
    select_high   = read_u8_mem(MainPokemonData.MenuSelectHighlight)   # CC35

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
        select_highlight=select_high
    )


# ---------------------------------------------------------------------
# Convenience single-value getters
# ---------------------------------------------------------------------
def get_menu_pos() -> Tuple[int, int]:
    """Returns (x, y) for the topmost menu item cursor position."""
    x = read_u8_mem(MainPokemonData.MenuCursorXPos)
    y = read_u8_mem(MainPokemonData.MenuCursorYPos)
    return (x, y)


def get_selected_menu_item_id() -> int:
    return read_u8_mem(MainPokemonData.MenuSelectedItem)


def get_first_displayed_item_id() -> int:
    return read_u8_mem(MainPokemonData.MenuFirstItemID)


def get_select_highlight() -> int:
    return read_u8_mem(MainPokemonData.MenuSelectHighlight)


def get_cursor_tile_ptr() -> int:
    """
    Returns the 16-bit pointer to the cursor tile (in buffer C3A0).
    """
    return read_u16_mem(MainPokemonData.MenuCursorTilePtr)
