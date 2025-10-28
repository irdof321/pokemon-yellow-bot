import json
import os
import sys
import threading
import time
from enum import Enum, auto
from collections import deque

from pyboy import PyBoy
from loguru import logger

from data.data import GBAButton
from data.menu import MenuState, get_menu_state
from data.ram_reader import MemoryData, SavedPokemonData, MainPokemonData
from scenes.battles import get_battle_scene

from helpers.mqtt import get_global, start_global, publish, subscribe, subscribe_with_callback
# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------
# Remove default handler (it logs everything to stderr)
logger.remove()
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/pokemon_{time}.log",
    rotation="1 week",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)
logger.add(
    sys.stderr,
    level="WARNING",
    diagnose=True,  # Keep nice traceback and variable inspection for warnings/errors
    backtrace=True
)
# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_AUTOSAVE_INTERVAL_SEC = 1
_SCENE_POLL_SEC = 2      # Check the scene only 10 times per second
_LOG_THROTTLE_SEC = 1.0     # Avoid spamming exception logs
_BTN_POP_COOLDOWN = 1.0  # seconds

BASE_TOPIC = f"/dforirdod/PKM/"
BATTLE_TOPIC = BASE_TOPIC +"battle/info"
BATTLE_MOVE = BASE_TOPIC + "battle/move"

_last_battle_turn = -1

class GameQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = threading.Lock()

    def append(self, item):
        with self.lock:
            self.queue.append(item)

    def pop(self):
        with self.lock:
            if self.queue:
                return self.queue.popleft()
            
    def size(self) -> int :
        return len(self.queue)
    
    def __str__(self) -> str:
        return "[" + ",".join(str(elem) for elem in self.queue) + "]"

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
        while True:
            if input_choice.lower() in ["r", "red"]:
                input_choice = "red"
                MemoryData.set_shift(0x0)
                path = "games/PokemonRed.gb"
            elif input_choice.lower() in ["b", "blue"]:
                input_choice = "blue"
                MemoryData.set_shift(0x0)
                path = "games/PokemonBleu.gb"
            elif input_choice.lower() in ["y", "yellow"]:
                input_choice = "yellow"
                MemoryData.set_shift(0x0)
                path = "games/PokemonJaune.gb"
            else:
                input_choice = input("Choose your game Pokémon Red (r), Blue (b) or Yellow (y): ").strip()
            if input_choice.lower()  in PokemonGame.CHOICES:
                break

        return PokemonGame(path, window="SDL2", log_level="INFO")

    def __init__(self, rom_path: str, *args, **kwargs):
        """
        Initialize the PyBoy emulator with the selected ROM and keep some flags.
        """
        super().__init__(rom_path, *args, **kwargs)
        MemoryData.set_game(self)
        self.rom_name = rom_path
        self.is_running = False
        self.btn_event_list = GameQueue()

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
        next_scene_at = now + 10
        next_log_ok = now + _LOG_THROTTLE_SEC
        last_btn_pop_at = 0.0  # allow immediate first pop


        #MQTT subscription
        start_global(
                logger=logger,
                host="test.mosquitto.org",
                port=1883,
                use_tls=False,
                use_websocket=False,
                lwt={"topic": f"{BASE_TOPIC}/status", "payload": "offline", "qos": 0, "retain": True},
            )
        publish(get_global(), f"{BASE_TOPIC}/start", {"msg": "hello from PKM"}, qos=0, retain=False)
        subscribe_with_callback(get_global(),BATTLE_MOVE,self.callback_move)


        
        # --- Main emulator loop ---
        while True:
            # 1) Advance the emulator
            self.is_running = self.tick()

            # Compute 'now' once per loop; reuse below
            now = time.monotonic()

            # 1b) Pop a game button only if: (a) queue not empty AND (b) >= 0.5s since last pop
            if self.btn_event_list.size() > 0 and (now - last_btn_pop_at) >= _BTN_POP_COOLDOWN:
                logger.debug(f"BTN list : {self.btn_event_list}")
                btn = self.btn_event_list.pop()
                if btn != GBAButton.PASS:
                    super().button(btn.value)
                last_btn_pop_at = now

            if not self.is_running:
                logger.info("Emulator stopped running.")
                break

            # 2) Autosave
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

            # 3) Scene poll
            if now >= next_scene_at:
                try:
                    self._poll_scene_once()
                except Exception:
                    if now >= next_log_ok:
                        logger.exception("Error while polling scene.")
                        next_log_ok = now + _LOG_THROTTLE_SEC
                finally:
                    next_scene_at = now + _SCENE_POLL_SEC


    def get_scene(self):
        if self.scene:
            return self.scene
        else:
            return None

    def _poll_scene_once(self) -> None:
        """Read battle state occasionally. Must only run in the main thread."""
        global _last_battle_turn
        battle_id_bytes = self.get_data(MainPokemonData.BattleTypeID)
        if not battle_id_bytes:
            return
        battle_id = battle_id_bytes[0]

        if battle_id > 0:
            if not hasattr(self, "_in_battle") or not self._in_battle:
                logger.info(f"Battle started with ID {battle_id}")
                self._in_battle = True
            

            if not hasattr(self, "scene") or self.scene is None:
                self.scene = get_battle_scene(self, battle_id)
                
            #Publish only once the scene
            if not hasattr(self,"menu_state"):
                self.menu_state = get_menu_state()
            # logger.warning(f"Main menu : {self.scene.is_in_battle_main_menu()}")
            self.scene.go_to_main_menu()
            if not self.menu_state == get_menu_state():
                self.menu_state = get_menu_state() 
                logger.warning(f"POS : {get_menu_state()}")
            if self.scene.battle_turn == _last_battle_turn:
                return
            _last_battle_turn = self.scene.battle_turn
            
            # Publish battle info as JSON
            try:
                publish(
                    get_global(),
                    BATTLE_TOPIC,
                    {
                        "battle_id": battle_id,
                        "turn": self.scene.battle_turn,
                        "timestamp": time.time(),
                        "scene" : self.scene.to_dict()
                    },
                    qos=0,
                    retain=True
                )
            except Exception as e:
                logger.error(f"Failed to publish MQTT message: {e}")

            # self.simulation_test()
            logger.info(f"Battle turn : {self.scene.battle_turn}")
        else:
            if getattr(self, "_in_battle", False):
                logger.info("Battle ended.")
            self._in_battle = False
            self._pressed_btn = False
            self.scene = None
                
    def simulation_test(self):
        if not getattr(self, "_pressed_btn", False):
            self.scene.use_move_2()
            logger.debug("Move 4 selected.")
            self._pressed_btn = True

    def get_data(self, elem: MemoryData) -> bytes:
        """
        Read a slice of emulator memory, compensating for both:
          - the global MemoryData.shift used in this project,
          - and the Yellow-specific -1 byte shift for WRAM addresses >= 0xCF1A.
        """
        elem = MemoryData.get_pkm_yellow_addresses(elem)
        return SavedPokemonData.get_data(self, elem)



    def callback_move(self,topic,msg):
        if not hasattr(self,"scene"):
            return
        logger.warning(f"The chosen move is {msg}")
        j = json.loads(msg)
        move_nb = j["move_nb"]
        self.scene.use_move(move_nb)


async def get_battle():
    scene = game.get_scene()
    return {"scene": str(scene) if scene else None}

if __name__ == "__main__":
    game = PokemonGame.get_game("red")
    game.start()
    # game.start(file_save_state="games/Rouge/PokemonRed.TestMove.gb.state")
