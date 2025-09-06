import random
import time
from pyboy import PyBoy
from data.ram_reader import *
from data.decoder import decode_pkm_text
import os; print(os.getcwd())
from data.pokemon import Pokemon

start_time = time.time()

# RomName = 'PokemonBleu.gb'
RomName = 'PokemonRouge.gb'
# RomName = 'PokemonJaune.gb'

pyboy = PyBoy(RomName,
              window="SDL2",
              log_level="INFO")


#check first if a save state exists

#ask if you want to load it
load = input("Load save state? (y/n): ")
if load.lower() == 'y':
    if os.path.exists(f"{RomName}.state"):
        with open(f"{RomName}.state", "rb") as f:
            pyboy.load_state(f)


def get_data(elem: 'MemoryData'):
    initial_shift = 0x5
    return pyboy.memory[elem.start_address + initial_shift:elem.end_address + 1 + initial_shift]

while True:
    pyboy.tick()
    if time.time() - start_time > 2:  # Run for 10 seconds
        data = get_data(SavedData.get_pkm_yellow_addresses(MainData.PlayerPokemonName))
        name = decode_pkm_text(data)
        print(f"Pokemon name: {name}")

        data2 = get_data(SavedData.get_pkm_yellow_addresses(MainData.PlayerNameString))
        player_name = decode_pkm_text(data2)
        print(f"Player name: {player_name}")

        pokemon = Pokemon.from_memory(pyboy, MainData.Pokemon1SlotBattle,False)
        # pokemon.set_level(random.randint(5,100))
        print(pokemon)

        # print(f"Pokemon 1 name: {pokemon.name}")
        # print(f"Pokemon 1 level: {pokemon.level}")

        start_time = time.time()
        with open(f"{RomName}.state", "wb") as f:
            pyboy.save_state(f)
    pass
pyboy.stop()
