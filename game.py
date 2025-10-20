import os
import time
from enum import Enum, auto

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
_AUTOSAVE_INTERVAL_SEC = 10  # Interval for autosaving the emulator state (seconds)


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

    def start(self, file_save_state: str = "") -> None:
        """
        Start the emulator loop.

        - Loads a save state if provided or if a default .state file is present.
        - Optionally asks the user whether to load the default save state.
        - Periodically logs Pokémon info every 60s (if MemoryData is configured).
        - Autosaves the game state every 60s.
        """
        # Resolve save-state path
        if file_save_state != "":
            self.save_state_path = file_save_state
        else:
            self.save_state_path = f"{self.rom_name}.state"

        # Load an existing save state, or ask the user if one isn't found
        if self.save_state_path and os.path.exists(self.save_state_path):
            try:
                with open(self.save_state_path, "rb") as f:
                    self.load_state(f)
                logger.info("Save state loaded.")
            except Exception:
                logger.exception("Failed to load the save state.")
        else:
            try:
                load_data = input("Load save state? (y/n): ").strip().lower()
                if load_data == "y":
                    default_state = f"{self.rom_name}.state"
                    if os.path.exists(default_state):
                        with open(default_state, "rb") as f:
                            self.load_state(f)
                        logger.info("Save state loaded.")
                    else:
                        logger.warning("No save state found.")
            except Exception:
                logger.exception("Failed during save-state prompt or load.")

        # Optionally start a background thread to autosave (kept commented as in original)
        # threading.Thread(target=self.auto_save, daemon=True).start()

        start_time = time.time()

        # --- Start periodic Pokémon logger every 60s ---
        try:
            # Choose a MemoryData entry for the first Pokémon in battle/saved context.
            # Falls back if a specific name does not exist in your ram_reader.
            md = getattr(SavedPokemonData, "Pokemon1SlotBattle", None) or getattr(
                SavedPokemonData, "Pokemon1", None
            )

            if md is None:
                logger.warning(
                    "No MemoryData for first Pokémon found in SavedPokemonData. Skipping periodic Pokémon logger."
                )
            else:
                SavedPokemonData.start_pokemon_logger(self, md, interval_sec=60)
                logger.info("Started periodic Pokémon logger (every 60s).")
        except Exception as e:
            logger.exception(f"Failed to start periodic Pokémon logger: {e}")

        # --- Main emulator loop ---
        try:
            while True:
                self.is_running = self.tick()
                if not self.is_running:
                    logger.info("Emulator stopped running.")
                    break

                

                # Autosave at fixed interval
                if time.time() - start_time > _AUTOSAVE_INTERVAL_SEC:
                    try:
                        with open(self.save_state_path, "wb") as f:
                            self.save_state(f)
                        logger.info("Game state saved")
                        self.get_scene()
                    except Exception:
                        logger.exception("Failed to autosave the game state.")
                    finally:
                        start_time = time.time()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, exiting main loop.")
        except Exception:
            logger.exception("Unexpected error in the main loop.")

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
        
        battle_id = self.get_data(MainPokemonData.BattleTypeID)
        logger.debug(f"DEBUG ----- battle_id : {battle_id}")
        battle_id = battle_id[0]
        if battle_id > 0:
            logger.info(f"It is a battle with id {battle_id}")

            self.scene = get_battle_scene(self,battle_id)
            logger.debug(f"SCENE\n {self.scene}")

        return None


if __name__ == "__main__":
    game = PokemonGame.get_game()
    #game.start()
    game.start(file_save_state="games/Rouge/PokemonRed.TestMove.gb.state")
