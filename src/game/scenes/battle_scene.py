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
    # TBD sentinels -- (-1, -1) can never be a real observed value (MenuCursorXPos/YPos
    # are unsigned bytes, 0-255). Fill in with real values from
    # tests/test_switch_menu_coords.py once tests/fixtures/battle_party_select_screen.state
    # and battle_party_submenu.state are captured. Do not guess.
    POKEMON_SELECTION = (-1, -1)
    POKEMON_SUB_MENU = (-1, -1)


_SWITCH_COORDS_UNSET = (-1, -1)


def filter_eligible_switch_slots(party: list, active_slot: Optional[int]) -> List[int]:
    """Pure filtering logic behind BattleScene.eligible_switch_slots, split out
    so it's testable against plain fake objects (anything with .slot/.current_hp)
    without needing a real session/PyBoy."""
    return [p.slot for p in party if p.current_hp > 0 and p.slot != active_slot]


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
    _PHASE_SWITCH_OPEN_MENU = "switch_open_menu"      # voluntary only: FIGHT -> PKMN, press A
    _PHASE_SWITCH_SELECT_SLOT = "switch_select_slot"  # party-list cursor -> target party_slot
    _PHASE_SWITCH_SUBMENU = "switch_submenu"          # SWITCH/STATS/CANCEL -> land on SWITCH, confirm
    _PHASE_SWITCH_POST_DIALOG = "switch_post_dialog"  # advance text/animation after confirming

    
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

    @property
    def is_forced_switch_pending(self) -> bool:
        """True once the active Pokemon has fainted and the game has (or is
        about to have) auto-opened the mandatory party-select screen. Falls
        back to the HP-only signal until MenuLocation.POKEMON_SELECTION is
        filled in with a real value (see test_switch_menu_coords.py) -- once
        it is, also checks cursor position to avoid a false positive during
        the faint animation/text (HP is already 0 for several frames before
        the party-select UI actually appears)."""
        if self.player_active.current_hp != 0:
            return False
        if MenuLocation.POKEMON_SELECTION.value == _SWITCH_COORDS_UNSET:
            return True
        return self.menu_top == MenuLocation.POKEMON_SELECTION.value

    @property
    def eligible_switch_slots(self) -> List[int]:
        """1-based party slots that are valid switch targets right now: alive
        (current_hp > 0) and not already the active Pokemon. Active-slot
        exclusion uses MenuCurrentPartyIndex (0xCC2F), confirmed 0-based
        against every existing fixture (all have slot 1 active -> reads 0)."""
        raw = self.session.read_memory(MainPokemonData.MenuCurrentPartyIndex)
        active_slot = (raw[0] + 1) if raw else None
        return filter_eligible_switch_slots(self.player_party, active_slot)

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
    # Main menu navigation (shared by idle stabilization and every command
    # executor -- each executor is responsible for reaching its own target
    # cell in the FIGHT/ITEM/PKMN/RUN grid itself, since only one thing ever
    # drives input at a time (see update(): _ensure_ready_main_menu only runs
    # when _active_cmd is None, so there's no risk of two targets fighting
    # over the cursor).
    # ------------------------------------------------------------------
    def _navigate_main_menu_to(self, now: float, target_top: Tuple[int, int], target_id: int) -> bool:
        """Nudges the cursor toward (target_top, target_id) within the
        FIGHT/ITEM/PKMN/RUN grid, at most one input per call. Returns True
        once positioned there -- the caller then presses A itself to enter
        its own submenu; reaching the target cell is all this does."""
        if not self.is_in_any_main_menu_column:
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.B)  # escape dialogue/other screens
            return False

        if self.menu_top != target_top:
            if self._can_enqueue_input(now):
                btn = GBAButton.LEFT if target_top == MenuLocation.MAIN_MENU_LEFT.value else GBAButton.RIGHT
                self._enqueue_input(now, btn)
            return False

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

        return True

    # ------------------------------------------------------------------
    # Idle behavior: return to a stable main menu position
    # ------------------------------------------------------------------
    def _ensure_ready_main_menu(self, now: float) -> None:
        if self._menu_state is None:
            return

        if self.is_forced_switch_pending:
            # The game itself is forcing the party-select screen open (active
            # Pokemon fainted) -- don't fight it by pressing B to "escape".
            # Only an explicit "switch" command may act here.
            return

        self._navigate_main_menu_to(now, MenuLocation.MAIN_MENU_LEFT.value, 0)

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

        if cmd.kind == "switch":
            done = self._execute_switch(now, cmd.party_slot)
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

        target_id = move_index   # RAM menu_id is 0-based, move_index is 1-based

        # --------------------------------------------------------------
        # Phase 1: select the move (we interpret menu_id as cursor on moves)
        # --------------------------------------------------------------
        if self._phase in (self._PHASE_IDLE, self._PHASE_SELECT_MOVE):
            self._phase = self._PHASE_SELECT_MOVE

            # If we aren't in the moves/text menu, navigate there ourselves --
            # don't rely on _ensure_ready_main_menu(), which stops running the
            # moment this command becomes active (see update()).
            if not self.is_in_moves_or_text_menu:
                if not self._navigate_main_menu_to(now, MenuLocation.MAIN_MENU_LEFT.value, 0):
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

    def _execute_switch(self, now: float, party_slot: Optional[int]) -> bool:
        """
        party_slot is 1..6 (party position to switch in). Handles both the
        voluntary path (chosen from the FIGHT/PKMN/ITEM/RUN main menu on your
        turn) and the forced path (active Pokemon fainted, game auto-opens
        the party-select screen) -- both converge on the same
        _PHASE_SWITCH_SELECT_SLOT once the party list is actually on screen,
        since is_forced_switch_pending's screen is the same list either way.
        """
        if party_slot is None or party_slot < 1 or party_slot > 6:
            self.logger.warning("Invalid party_slot (expected 1..6): {}", party_slot)
            return True

        if MenuLocation.POKEMON_SELECTION.value == _SWITCH_COORDS_UNSET:
            self.logger.error(
                "MenuLocation.POKEMON_SELECTION coordinates not yet filled in "
                "(see tests/test_switch_menu_coords.py) -- switch unsupported."
            )
            return True

        target_index = party_slot - 1  # RAM menu_id is 0-based, party_slot is 1-based

        # --------------------------------------------------------------
        # Phase 1: reach the party-select screen (voluntary: FIGHT -> PKMN -> A;
        # forced: the game already put us here, so this falls through immediately)
        # --------------------------------------------------------------
        if self._phase in (self._PHASE_IDLE, self._PHASE_SWITCH_OPEN_MENU):
            self._phase = self._PHASE_SWITCH_OPEN_MENU

            if self.menu_top == MenuLocation.POKEMON_SELECTION.value:
                self._phase = self._PHASE_SWITCH_SELECT_SLOT
                return False

            # Navigate to PKMN ourselves -- don't rely on _ensure_ready_main_menu(),
            # which stops running the moment this command becomes active (see
            # update()), and which would push toward FIGHT anyway, not PKMN.
            if not self._navigate_main_menu_to(now, MenuLocation.MAIN_MENU_RIGHT.value, 0):
                return False
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.A)  # open the party list
            return False

        # --------------------------------------------------------------
        # Phase 2: navigate the party list to the target slot
        # --------------------------------------------------------------
        if self._phase == self._PHASE_SWITCH_SELECT_SLOT:
            if self.menu_top != MenuLocation.POKEMON_SELECTION.value:
                return False  # transition animation still catching up

            cur = self.menu_id
            if cur is None:
                return False

            if cur < target_index:
                if self._can_enqueue_input(now):
                    self._enqueue_input(now, GBAButton.DOWN)
                return False

            if cur > target_index:
                if self._can_enqueue_input(now):
                    self._enqueue_input(now, GBAButton.UP)
                return False

            # correct party member highlighted -> open SWITCH/STATS/CANCEL
            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.A)
            self._phase = self._PHASE_SWITCH_SUBMENU
            return False

        # --------------------------------------------------------------
        # Phase 3: SWITCH/STATS/CANCEL sub-menu -- confirm SWITCH
        # --------------------------------------------------------------
        if self._phase == self._PHASE_SWITCH_SUBMENU:
            if self.menu_top != MenuLocation.POKEMON_SUB_MENU.value:
                return False  # waiting for the popup to appear

            # Assumes SWITCH is the default cursor position (id 0) -- confirm
            # against tests/fixtures/battle_party_submenu.state once captured.
            if self.menu_id != 0:
                if self._can_enqueue_input(now):
                    self._enqueue_input(now, GBAButton.UP)
                return False

            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.A)  # confirm SWITCH
            self._phase = self._PHASE_SWITCH_POST_DIALOG
            return False

        # --------------------------------------------------------------
        # Phase 4: post-switch dialogue/animation (mirrors _execute_move's
        # phase 2 exactly -- unverified whether the forced path also settles
        # back at is_ready_main_menu the same way; confirm once
        # tests/fixtures/battle_forced_switch_screen.state exists)
        # --------------------------------------------------------------
        if self._phase == self._PHASE_SWITCH_POST_DIALOG:
            if self.is_ready_main_menu:
                return True

            if self._can_enqueue_input(now):
                self._enqueue_input(now, GBAButton.B)
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
            "forced_switch_pending": self.is_forced_switch_pending,
        }
        






def create_battle_scene(session: EmulatorSession, battle_id: int) -> BattleScene:
    context = read_battle_context(session)
    return BattleScene(session, battle_id, context)


__all__ = ["BattleScene", "BattleType", "BattleSubType", "BattleContext", "read_battle_context", "create_battle_scene", "MenuLocation"]
