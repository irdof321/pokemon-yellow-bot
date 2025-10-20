import os
import threading
import time
from enum import Enum, auto
from collections import deque

from pyboy import PyBoy
from loguru import logger

from data.ram_reader import MemoryData, SavedPokemonData, MainPokemonData
from scenes.battles import get_battle_scene
# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/pokemon_{time}.log",
    rotation="1 week",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_AUTOSAVE_INTERVAL_SEC = 10
_SCENE_POLL_SEC = 0.10      # Check the scene only 10 times per second
_LOG_THROTTLE_SEC = 1.0     # Avoid spamming exception logs

class GBAButton(str, Enum):
    A = "a"
    B = "b"
    START = "start"
    SELECT = "select"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    L = "l"
    R = "r"

class GameVersion(Enum):
    """Supported Pokémon game versions."""

    RED = auto()
    BLUE = auto()
    YELLOW = auto()

    @property
    def is_yellow(self) -> bool:
        """Convenience flag for logic that depends on Yellow-specific RAM layout."""
        return self is GameVersion.YELLOW


class PokemonGame(PyBoy):
    """
    Thin wrapper around PyBoy with helpers specific to Pokémon Red/Blue/Yellow.

    Notes on RAM layout:
      - According to the Yellow shift rule, the variable at WRAM 0xCF1A is moved to HRAM.
        Therefore, in Yellow, all WRAM variables after 0xCF1A are shifted by -1 byte.
      - We honor an additional project-wide MemoryData.shift (bank/offset usage) and
        combine both corrections inside get_data().
    """

    # WRAM boundary for the Yellow version shift rule
    CF1A = 0xCF1A

    # Allowed user choices for interactive selection
    CHOICES = ["red", "blue", "yellow"]

    @property
    def game_version(self) -> GameVersion:
        """
        Detect the game version from the ROM file path.
        """
        if self.rom_name == "games/PokemonRed.gb":
            return GameVersion.RED
        elif self.rom_name == "games/PokemonBleu.gb":
            return GameVersion.BLUE
        elif self.rom_name == "games/PokemonJaune.gb":
            return GameVersion.YELLOW
        raise ValueError("Unknown game version")

    @staticmethod
    def get_game(input_choice: str = "") -> "PokemonGame":
        """
        Create a PokemonGame instance from a user choice (interactive if empty).

        The function also sets the MemoryData global shift expected by the project.
        """
        path = ""
        while input_choice.lower() not in PokemonGame.CHOICES:
            input_choice = input("Choose your game Pokémon Red (r), Blue (b) or Yellow (y): ").strip()
            if input_choice.lower() in ["r", "red"]:
                input_choice = "red"
                MemoryData.set_shift(0x0)
                path = "games/PokemonRed.gb"
            elif input_choice.lower() in ["b", "blue"]:
                input_choice = "blue"
                MemoryData.set_shift(0x5)
                path = "games/PokemonBleu.gb"
            elif input_choice.lower() in ["y", "yellow"]:
                input_choice = "yellow"
                MemoryData.set_shift(0x4)
                path = "games/PokemonJaune.gb"
            else:
                print("Invalid choice. Please try again.")

        return PokemonGame(path, window="SDL2", log_level="INFO")

    def __init__(self, rom_path: str, *args, **kwargs):
        """
        Initialize the PyBoy emulator with the selected ROM and keep some flags.
        """
        super().__init__(rom_path, *args, **kwargs)
        MemoryData.set_game(self)
        self.rom_name = rom_path
        self.is_running = False
        self.btn_event_list = deque([])

    def button(self,btn : GBAButton):
        self.btn_event_list.append(btn)

    def start(self, file_save_state: str = "") -> None:
        """
        Start the emulator loop.
        - Loads an existing save state (if found)
        - Periodically autosaves and polls the battle scene
        - Runs everything in a single thread for performance
        """
        # --- Load save state (same as your code) ---
        if file_save_state != "":
            self.save_state_path = file_save_state
        else:
            self.save_state_path = f"{self.rom_name}.state"

        if self.save_state_path and os.path.exists(self.save_state_path):
            try:
                with open(self.save_state_path, "rb") as f:
                    self.load_state(f)
                logger.info("Save state loaded.")
            except Exception:
                logger.exception("Failed to load the save state.")
        else:
            try:
                choice = input("Load save state? (y/n): ").strip().lower()
                if choice == "y":
                    default_state = f"{self.rom_name}.state"
                    if os.path.exists(default_state):
                        with open(default_state, "rb") as f:
                            self.load_state(f)
                        logger.info("Save state loaded.")
                    else:
                        logger.warning("No save state found.")
            except Exception:
                logger.exception("Failed during save-state prompt or load.")

        # --- Timing setup ---
        now = time.monotonic()
        next_save_at = now + _AUTOSAVE_INTERVAL_SEC
        next_scene_at = now + _SCENE_POLL_SEC
        next_log_ok = now + _LOG_THROTTLE_SEC

        # --- Main emulator loop ---
        while True:
            # 1) Advance the emulator (no background PyBoy access)
            self.is_running = self.tick()
            if len(self.btn_event_list) > 0:
                logger.debug(f"BTN list : {self.btn_event_list}")
                super().button(self.btn_event_list.popleft())
            if not self.is_running:
                logger.info("Emulator stopped running.")
                break

            now = time.monotonic()

            # 2) Periodic autosave
            if now >= next_save_at:
                try:
                    logger.debug("Saving game state ...")
                    with open(self.save_state_path, "wb") as f:
                        self.save_state(f)
                    logger.info("Game state saved.")
                except Exception:
                    logger.exception("Failed to autosave the game state.")
                finally:
                    next_save_at = now + _AUTOSAVE_INTERVAL_SEC

            # 3) Periodic scene check (no need to do it every frame)
            if now >= next_scene_at:
                try:
                    self._poll_scene_once()
                except Exception:
                    if now >= next_log_ok:
                        logger.exception("Error while polling scene.")
                        next_log_ok = now + _LOG_THROTTLE_SEC
                finally:
                    next_scene_at = now + _SCENE_POLL_SEC

            # Optional: tiny sleep if CPU load is too high
            # time.sleep(0.001)


    def _poll_scene_once(self) -> None:
        """Read battle state occasionally. Must only run in the main thread."""
        battle_id_bytes = self.get_data(MainPokemonData.BattleTypeID)
        if not battle_id_bytes:
            return
        battle_id = battle_id_bytes[0]

        if battle_id > 0:
            if not hasattr(self, "_in_battle") or not self._in_battle:
                logger.info(f"Battle started with ID {battle_id}")
                self._in_battle = True
                self._pressed_btn = False

            if not hasattr(self, "scene") or self.scene is None:
                self.scene = get_battle_scene(self, battle_id)

            if not getattr(self, "_pressed_btn", False):
                self.scene.use_move_4()
                logger.debug("Move 4 selected.")
                self._pressed_btn = True

        else:
            if getattr(self, "_in_battle", False):
                logger.info("Battle ended.")
            self._in_battle = False
            self._pressed_btn = False
            self.scene = None
                

    def get_data(self, elem: MemoryData) -> bytes:
        """
        Read a slice of emulator memory, compensating for both:
          - the global MemoryData.shift used in this project,
          - and the Yellow-specific -1 byte shift for WRAM addresses >= 0xCF1A.
        """
        elem = MemoryData.get_pkm_yellow_addresses(elem)
        return SavedPokemonData.get_data(self, elem)

    def get_scene(self) -> str:
        """
        Return the current battle type ID as a string (for quick logging/printing).
        0 --> no battle
        1 --> wild Pokemon
        2 --> rival/ normal battle
        """
        if not hasattr(self,"pressed_btn"):
            self.pressed_btn = False

        battle_id = self.get_data(MainPokemonData.BattleTypeID)
        logger.debug(f"DEBUG ----- battle_id : {battle_id}")
        battle_id = battle_id[0]
        if battle_id > 0:
            logger.info(f"It is a battle with id {battle_id}")

            self.scene = get_battle_scene(self,battle_id)
            logger.debug(f"SCENE\n {self.scene}")

            if not self.pressed_btn:
                self.scene.use_move_4()
                logger.debug("Move 1 selected")
                self.pressed_btn = True

        return None


if __name__ == "__main__":
    game = PokemonGame.get_game()
    game.start()
    # game.start(file_save_state="games/Rouge/PokemonRouge.Carabaffe.gb.state")
