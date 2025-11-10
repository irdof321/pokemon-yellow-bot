"""Battle scene helpers."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from game.core.emulator import EmulatorSession
from game.data.data import GBAButton
from game.data.helpers import read_u8
from game.data.menu import MenuState, get_menu_state
from game.data.pokemon import EnemyPokemon, PartyPokemon, PlayerPokemonBattle
from game.data.ram_reader import MainPokemonData
from game.scenes.common import BATTLE_ACTION


class MenuLocation(Enum):
    MAIN_MENU_LEFT      = (9, 14)
    MAIN_MENU_RIGHT     = (15, 14)
    MOVES_SELECTION     = (5, 12)
    POKEMON_SELECTION   = (0, 1)
    POKEMON_SUB_MENU    = (12, 12)


@dataclass
class BattleScene:
    session: EmulatorSession
    battle_id: int

    def __post_init__(self) -> None:
        self.logger = self.session.logger
        self._menu_state: MenuState | None = None
        self._main_menu_attempts = 0

    def update(self) -> None:
        self._menu_state = get_menu_state()
        self._ensure_main_menu()
        self._refresh()

    # ------------------------------------------------------------------
    def _ensure_main_menu(self) -> None:
        if self._menu_state is None:
            return
        if self.is_in_battle_main_menu:
            self._main_menu_attempts = 0
            return
        self._main_menu_attempts += 1
        if self._main_menu_attempts <= 5:
            self.session.enqueue_button(GBAButton.A)

    @property
    def is_in_battle_main_menu(self) -> bool:
        if self._menu_state is None:
            return False
        return self._menu_state.cursor_pos_top in {
            MenuLocation.MAIN_MENU_LEFT.value,
            MenuLocation.MAIN_MENU_RIGHT.value,
        }

    @property
    def is_in_move_menu(self) -> bool:
        if self._menu_state is None:
            return False
        return self._menu_state.cursor_pos_top == MenuLocation.MOVES_SELECTION

    @property
    def selected_move_index(self) -> int:
        if self._menu_state is None:
            return 0
        return self._menu_state.selected_item_id

    def use_action(action: BATTLE_ACTION, actions_list: dict | None = None):
        if action == BATTLE_ACTION.MOVES:
            return
        elif action == BATTLE_ACTION.ITEM:
            return
        elif action == BATTLE_ACTION.PKM:
            return
        elif action == BATTLE_ACTION.RUN:
            return
        else:
            raise ValueError(f"action must be of type BATTLE_ACTION but got {action}")
        pass    

# Actions -----------------------------------------------------------------------
    def use_move(self, move_index: int) -> None:
        """Queue button presses to select a move."""
        self.session.enqueue_button(GBAButton.A)
        diff = self.selected_move_index - move_index
        if diff > 0:
            for _ in range(diff):
                self.session.enqueue_button(GBAButton.UP)
        elif diff < 0:
            for _ in range(-diff):
                self.session.enqueue_button(GBAButton.DOWN)
        self.session.enqueue_button(GBAButton.A)

    def _refresh(self) -> None:
        """Hook for subclasses to refresh cached data."""


# --------------------------------------------------------------------------------
    @property
    def turn_counter(self) -> int:
        raw = self.session.read_memory(MainPokemonData.BattleTurnCounter)
        data = list(raw) if raw else []
        return read_u8(data, (0, 1)) if data else 0

    def to_dict(self) -> dict:
        raise NotImplementedError


class NormalBattle(BattleScene):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.player_party: List[PartyPokemon] = [
            PartyPokemon(self.session, slot, self.session.version.is_yellow)
            for slot in range(1, 7)
        ]
        self.player_active = PlayerPokemonBattle(self.session, self.session.version.is_yellow)
        self.enemy = EnemyPokemon(self.session, self.session.version.is_yellow)

    def _refresh(self) -> None:
        for pokemon in self.player_party:
            pokemon.refresh()
        self.player_active.refresh()
        self.enemy.refresh()

    def to_dict(self) -> dict:
        return {
            "enemy": self.enemy.to_dict(),
            "player": self.player_active.to_dict(),
            "party": [p.to_dict() for p in self.player_party],
        }


def create_battle_scene(session: EmulatorSession, battle_id: int) -> BattleScene:
    return NormalBattle(session, battle_id)


__all__ = ["BattleScene", "NormalBattle", "create_battle_scene"]
