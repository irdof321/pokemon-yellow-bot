"""Battle scene helpers (state-driven, command-queue based)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from game.core.emulator import EmulatorSession
from game.core.queue import ThreadSafeQueue
from game.data.data import GBAButton
from game.data.helpers import read_u8
from game.data.menu import MenuState as MenuDumpState, get_menu_state
from game.data.pokemon import EnemyPokemon, PartyPokemon, PlayerPokemonBattle, OpponentPartyPokemon
from game.data.ram_reader import MainPokemonData, MemoryData
from game.scenes.commands import BattleCommand
from game.scenes.scene import Scene


class BattleType(Enum):
    """MainPokemonData.BattleTypeID (0xD057) -- empirically confirmed values only.
    A gym leader battle (Brock) reads TRAINER (2), same as any other trainer --
    there is no separate value for it at this byte. Don't add members here on
    a guess; confirm against a real fixture first (see test_battle_type_byte.py)."""
    NONE = 0
    WILD = 1
    TRAINER = 2


class BattleSubType(Enum):
    """MainPokemonData.BattleSubType (0xD05A) -- "Normal, Safari Zone, Old Man
    battle...". Only NORMAL (0) is empirically confirmed so far (wild/trainer/
    gym leader fixtures all read 0). Add SAFARI_ZONE/OLD_MAN_BATTLE here only
    once captured and verified against a real fixture -- see
    test_battle_type_byte.py, same discipline as BattleType."""
    NORMAL = 0


@dataclass
class BattleContext:
    """Resolved once, at battle-scene creation time, from three RAM bytes that
    don't change mid-battle. See read_battle_context()."""
    battle_type: BattleType
    battle_sub_type: BattleSubType
    trainer_class: Optional[int]  # MainPokemonData.EngagedTrainerClass (0xCD2D) -- only meaningful when battle_type is TRAINER


def read_battle_context(session: EmulatorSession) -> BattleContext:
    raw_type = session.read_memory(MainPokemonData.BattleTypeID)
    raw_value = raw_type[0] if raw_type else 0
    try:
        battle_type = BattleType(raw_value)
    except ValueError:
        session.logger.warning("Unknown BattleTypeID value: {}", raw_value)
        battle_type = BattleType.NONE

    raw_sub_type = session.read_memory(MainPokemonData.BattleSubType)
    raw_sub_value = raw_sub_type[0] if raw_sub_type else 0
    try:
        battle_sub_type = BattleSubType(raw_sub_value)
    except ValueError:
        session.logger.warning(
            "Unknown BattleSubType value: {} -- not yet a confirmed member (only NORMAL=0 is), "
            "defaulting to NORMAL. Capture this as a fixture and add it to the enum.",
            raw_sub_value,
        )
        battle_sub_type = BattleSubType.NORMAL

    trainer_class: Optional[int] = None
    if battle_type == BattleType.TRAINER:
        raw_trainer_class = session.read_memory(MainPokemonData.EngagedTrainerClass)
        trainer_class = raw_trainer_class[0] if raw_trainer_class else None

    return BattleContext(battle_type=battle_type, battle_sub_type=battle_sub_type, trainer_class=trainer_class)


# ----------------------------------------------------------------------
# Menu constants (your PPT)
# ----------------------------------------------------------------------
class MenuLocation(Enum):
    MAIN_MENU_LEFT = (9, 14)
    MAIN_MENU_RIGHT = (15, 14)
    MOVES_OR_TEXT = (5, 12)  # move selection AND post-move message UI share this top-left


@dataclass
class BattleScene(Scene):
    """
    BattleScene NEVER presses buttons directly via PyBoy.button().
    It only enqueues buttons into session.buttons, and EmulatorLoop consumes them 1-by-1.
    """

    # Internal phases for robust disambiguation between "move menu" and "dialogue"
    # when both share the same menu top-left (5,12).
    _PHASE_IDLE = "idle"
    _PHASE_SELECT_MOVE = "select_move"
    _PHASE_POST_DIALOG = "post_dialog"
    
    
    battle_id: int
    battle_context: Optional[BattleContext] = None

    def __post_init__(self) -> None:
        super().__post_init__()

        # last menu dump from RAM
        self._menu_state: Optional[MenuDumpState] = None

        # high-level commands coming from BattleService (thread-safe)
        self._commands: ThreadSafeQueue[BattleCommand] = ThreadSafeQueue()
        self._active_cmd: Optional[BattleCommand] = None

        # input throttling (avoid spamming A)
        self._next_input_allowed_at: float = 0.0
        self._input_cooldown: float = 0.20  # seconds

        # state machine phase
        self._phase: str = self._PHASE_IDLE
        
        party_count = self._read_party_count(MainPokemonData.PartyCount)
        self.player_party: List[PartyPokemon] = [
            PartyPokemon(self.session, slot, self.session.version.is_yellow) for slot in range(1, party_count + 1)
        ]
        self.player_active = PlayerPokemonBattle(self.session, self.session.version.is_yellow)
        self.enemy = EnemyPokemon(self.session, self.session.version.is_yellow)
        self.enemy_party: List[OpponentPartyPokemon] = []
        if self.battle_context is not None and self.battle_context.battle_type == BattleType.TRAINER:
            enemy_count = self._read_party_count(MainPokemonData.OpponentPartyCount)
            self.enemy_party = [
                OpponentPartyPokemon(self.session, slot, self.session.version.is_yellow) for slot in range(1, enemy_count + 1)
            ]
        else:
            self.enemy_party = [self.enemy]

    def _read_party_count(self, field: MemoryData, max_count: int = 6) -> int:
        """Reads a *PartyCount-style byte, clamped to [0, max_count]. Fails safe:
        if it can't be read, returns 0 rather than assuming the max -- better to
        under-report than to expose a slot that might not actually exist."""
        raw = self.session.read_memory(field)
        if not raw:
            self.logger.warning("Could not read party count from {}", field)
            return 0
        return max(0, min(raw[0], max_count))



    # ------------------------------------------------------------------
    # API used by BattleService
    # ------------------------------------------------------------------
    def enqueue_command(self, cmd: BattleCommand) -> None:
        self._commands.append(cmd)

    # ------------------------------------------------------------------
    # Main loop hook (SceneManagerService calls update(); we accept now optionally)
    # ------------------------------------------------------------------
    def update(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.monotonic()

        # 1) Refresh RAM-derived state
        self._menu_state = get_menu_state()
        self._refresh()  # subclass-only data refresh (pokemon stats etc.)

        # 2) If no active command, keep the UI stable at "ready main menu"
        if self._active_cmd is None:
            self._ensure_ready_main_menu(now)

        # 3) Execute commands progressively (state-driven)
        self._drive_commands(now)

    # ------------------------------------------------------------------
    # Menu helpers
    # ------------------------------------------------------------------
    @property
    def menu_top(self) -> Optional[Tuple[int, int]]:
        if self._menu_state is None:
            return None
        return tuple(self._menu_state.cursor_pos_top)

    @property
    def menu_id(self) -> Optional[int]:
        if self._menu_state is None:
            return None
        # your dumps use "Selected item ID"
        return int(self._menu_state.selected_item_id)

    @property
    def is_ready_main_menu(self) -> bool:
        # Strict definition you wanted: left column + first item
        return self.menu_top == MenuLocation.MAIN_MENU_LEFT.value and self.menu_id == 0

    @property
    def is_in_any_main_menu_column(self) -> bool:
        return self.menu_top in {
            MenuLocation.MAIN_MENU_LEFT.value,
            MenuLocation.MAIN_MENU_RIGHT.value,
        }

    @property
    def is_in_moves_or_text_menu(self) -> bool:
        # This is the ambiguous area: move list OR post-move messages
        return self.menu_top == MenuLocation.MOVES_OR_TEXT.value

    # ------------------------------------------------------------------
    # Input gating: enqueue at most 1 button when allowed
    # ------------------------------------------------------------------
    def _can_enqueue_input(self, now: float) -> bool:
        if now < self._next_input_allowed_at:
            return False
        try:
            # Don't enqueue if we still have pending buttons.
            return len(self.session.buttons) == 0
        except Exception:
            # If ThreadSafeQueue doesn't implement __len__ reliably, be conservative
            return False

    def _enqueue_input(self, now: float, btn: GBAButton) -> None:
        self.session.enqueue_button(btn)
        self._next_input_allowed_at = now + self._input_cooldown

    # ------------------------------------------------------------------
    # Idle behavior: return to a stable main menu position
    # ------------------------------------------------------------------
    def _ensure_ready_main_menu(self, now: float) -> None:
        if self._menu_state is None:
            return

        if self.is_ready_main_menu:
            return

        # If we are in the ambiguous moves/text menu while idle, do NOT spam A here.
        # (The command executor will handle it when needed.)
        # if self.is_in_moves_or_text_menu:
        #     return

        # If we're not in recognized main menu columns, advance with A slowly.
        if not self.is_in_any_main_menu_column:
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.B) # Press B to avoid going deeper into menus
            return

        # Right column -> go left
        if self.menu_top == MenuLocation.MAIN_MENU_RIGHT.value:
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.LEFT)
            return

        # Left column -> move up until ID=0
        if self.menu_top == MenuLocation.MAIN_MENU_LEFT.value:
            mid = self.menu_id
            if mid is None:
                return
            if mid > 0 and self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.UP)
            return

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------
    def _drive_commands(self, now: float) -> None:
        # pick a command if none active
        if self._active_cmd is None:
            self._active_cmd = self._commands.pop()
            if self._active_cmd is not None:
                # reset phase for new command
                self._phase = self._PHASE_IDLE

        if self._active_cmd is None:
            return

        cmd = self._active_cmd

        if cmd.kind == "move":
            done = self._execute_move(now, cmd.move_index)
            if done:
                self._active_cmd = None
                self._phase = self._PHASE_IDLE
                cmd.done_event.set()
            return

        self.logger.warning("Unsupported command kind: {}", cmd.kind)
        self._active_cmd = None
        self._phase = self._PHASE_IDLE
        cmd.done_event.set()

    def _execute_move(self, now: float, move_index: int) -> bool:
        """
        move_index (MQTT) is 1..4.
        Menu internal IDs (RAM) are 0..3 (as shown by Last item ID: 3).
        """
        if move_index < 1 or move_index > 4:
            self.logger.warning("Invalid move_index (expected 1..4): {}", move_index)
            return True

        target_id = move_index  # 1..4 

        # --------------------------------------------------------------
        # Phase 1: select the move (we interpret menu_id as cursor on moves)
        # --------------------------------------------------------------
        if self._phase in (self._PHASE_IDLE, self._PHASE_SELECT_MOVE):
            self._phase = self._PHASE_SELECT_MOVE

            # If we aren't in the moves/text menu, open it from the ready main menu
            if not self.is_in_moves_or_text_menu:
                if not self.is_ready_main_menu:
                    # wait for _ensure_ready_main_menu() to position us
                    return False
                if self._can_enqueue_input(now):
                    self._enqueue_input(now, GBAButton.A)  # open move list
                return False

            # We are in moves/text menu.
            # In THIS phase, we treat menu_id as move cursor (0..3).
            cur = self.menu_id
            if cur is None:
                return False

            if cur < target_id:
                if self._can_enqueue_input(now):
                    self._enqueue_input(now, GBAButton.DOWN)
                return False

            if cur > target_id:
                if self._can_enqueue_input(now):
                    self._enqueue_input(now, GBAButton.UP)
                return False

            # Correct move selected -> confirm
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.A)

            # After confirming, we must advance dialogues until we're back to ready main menu.
            self._phase = self._PHASE_POST_DIALOG
            return False

        # --------------------------------------------------------------
        # Phase 2: post-move dialogues / message boxes (ambiguous UI)
        # --------------------------------------------------------------
        if self._phase == self._PHASE_POST_DIALOG:
            # We consider the move command completed only when we return to ready main menu.
            if self.is_ready_main_menu:
                return True

            # While not back to main menu, press A to advance text/animations.
            # This covers your case where (5,12) persists during dialogue.
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.B) # To avoid entering sub-menus, use B here.    
            return False

        # fallback
        self._phase = self._PHASE_IDLE
        return True

    # ------------------------------------------------------------------
    # Scene API
    # ------------------------------------------------------------------
    def is_ready(self) -> bool:
        # readiness for publishing: strict "ready main menu"
        return self.is_ready_main_menu


    def _refresh(self) -> None:
        for pokemon in self.player_party + self.enemy_party:
            pokemon.refresh()
        self.player_active.refresh()
        self.enemy.refresh()


    @property
    def turn_counter(self) -> int:
        raw = self.session.read_memory(MainPokemonData.BattleTurnCounter)
        data = list(raw) if raw else []
        return read_u8(data, (0, 1)) if data else 0

    def to_dict(self) -> dict:
        return {
            "battle_type": self.battle_context.battle_type.name.lower() if self.battle_context else None,
            "enemy": self.enemy.to_dict(),
            "enemy_party": [p.to_dict() for p in self.enemy_party],
            "on_battle": self.player_active.to_dict(),
            "party": [p.to_dict() for p in self.player_party],
        }
        






def create_battle_scene(session: EmulatorSession, battle_id: int) -> BattleScene:
    context = read_battle_context(session)
    return BattleScene(session, battle_id, context)


__all__ = ["BattleScene", "BattleType", "BattleSubType", "BattleContext", "read_battle_context", "create_battle_scene", "MenuLocation"]
