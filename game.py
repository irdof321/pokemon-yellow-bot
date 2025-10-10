import os
import threading
import time
from pyboy import PyBoy

from data.ram_reader import MemoryData, SavedPokemonData, SavedPokemonData,MainPokemonData
from enum import Enum, auto
from loguru import logger

os.makedirs("logs", exist_ok=True)
logger.add("logs/pokemon_{time}.log", rotation="1 week", enqueue=True, backtrace=True, diagnose=True)


class GameVersion(Enum):
    RED = auto()
    BLUE = auto()
    YELLOW = auto()

    @property
    def is_yellow(self) -> bool:
        return self is GameVersion.YELLOW


class PokemonGame(PyBoy):
    CF1A = 0xCF1A  # WRAM boundary for Yellow version shift rule
    CHOICES = ['red', 'blue', 'yellow']


    @property
    def game_version(self) -> GameVersion:
        if self.rom_name == 'games/PokemonRed.gb':
            return GameVersion.RED
        elif self.rom_name == 'games/PokemonBleu.gb':
            return GameVersion.BLUE
        elif self.rom_name == 'games/PokemonJaune.gb':
            return GameVersion.YELLOW
        raise ValueError("Unknown game version")

    @staticmethod
    def get_game(input_choice: str = "") -> "PokemonGame":
        while input_choice.lower() not in PokemonGame.CHOICES:
            input_choice = input("Choose your game pokemon red (r), blue (b) or yellow (y): ")
            if input_choice.lower() in ['r', 'red']:
                input_choice = 'red'
                MemoryData.set_shift(0x0)
                path = 'games/PokemonRed.gb'
            elif input_choice.lower() in ['b', 'blue']:
                input_choice = 'blue'
                MemoryData.set_shift(0x5)
                path = 'games/PokemonBleu.gb'
            elif input_choice.lower() in ['y', 'yellow']:
                input_choice = 'yellow'
                MemoryData.set_shift(0x4)
                path = 'games/PokemonJaune.gb'
            else:
                print("Invalid choice. Please try again.")
        return PokemonGame(path, window="SDL2", log_level="INFO")

    def __init__(self, rom_path: str, *args, **kwargs):
        super().__init__(rom_path, *args, **kwargs)
        self.rom_name = rom_path
        self.is_running = False

    


    def start(self, file_save_state: str = ""):
        if not file_save_state == "":
            self.save_state_path = file_save_state
        else:
            self.save_state_path = f"{self.rom_name}.state"

        if  self.save_state_path and os.path.exists(self.save_state_path):
            with open(self.save_state_path, "rb") as f:
                self.load_state(f)
            print("Save state loaded.")
        else:
            load_data = input("Load save state? (y/n): ")
            if load_data.lower() == 'y':
                if os.path.exists(f"{self.rom_name}.state"):
                    with open(f"{self.rom_name}.state", "rb") as f:
                        self.load_state(f)
                    print("Save state loaded.")
                else:
                    print("No save state found.")



        #thread of saving the game every x seconds
        # threading.Thread(target=self.auto_save, daemon=True).start()

        start_time = time.time()

        # === DÉMARRER LE LOGGER POKÉMON TOUTES LES 60s ===
        try:
            # Choisis le bon MemoryData (exemples, adapte le nom à ton ram_reader)
            # md = SavedPokemonData.Pokemon1SlotBattle
            # ou si tu as un nom différent :
            md = getattr(SavedPokemonData, "Pokemon1SlotBattle", None) \
                 or getattr(SavedPokemonData, "Pokemon1", None)

            if md is None:
                logger.warning("No MemoryData for first Pokémon found in SavedPokemonData. Skipping Pokémon logger.")
            else:
                SavedPokemonData.start_pokemon_logger(self, md, interval_sec=60)
                logger.info("Started periodic Pokémon logger (every 60s).")
        except Exception as e:
            logger.exception(f"Failed to start Pokémon logger: {e}")
        while True:
            self.is_running = self.tick()
            if not self.is_running:
                break
            #auto save every 60 seconds
            if time.time() - start_time > 60:  # Run for 60 seconds
                with open(self.save_state_path, "wb") as f:
                    self.save_state(f)
                print("Game state saved.")
                print(f"Battle counter : {self.get_scene()}")
                start_time = time.time()



    def get_data(self, elem: MemoryData) -> bytes:
        threshold = self.CF1A + MemoryData.shift

        if self.game_version.is_yellow:
            shift_start = -1 if elem.start_address >= threshold else 0
            shift_end   = -1 if elem.end_address   >= threshold else 0
            elem = MemoryData(
                elem.start_address + shift_start - MemoryData.shift,
                elem.end_address   + shift_end   - MemoryData.shift,
                elem.description
            )
        return SavedPokemonData.get_data(self, elem)
    
    def get_scene(self) -> str:
        battle_id = MainPokemonData.BattleTypeID
        return str(self.get_data(battle_id))


if __name__ == "__main__":
    game = PokemonGame.get_game()
    game.start()
    #game.start(file_save_state="games/Rouge/PokemonRouge.Battle-test.state")