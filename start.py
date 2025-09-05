import time
from pyboy import PyBoy
from data.ram_reader import *
from data.decoder import decode_pkm_text
import os; print(os.getcwd())

start_time = time.time()

pyboy = PyBoy('C:\\Users\\irdof\\Documents\\pokemon-yellow-bot\\PokemonJaune.gb',
              window="SDL2",
              log_level="INFO")


def get_data(elem: 'MemoryData'):
    return pyboy.memory[elem.start_address:elem.end_address+1]

while True:
    pyboy.tick()
    if time.time() - start_time > 2:
        data = get_data(SavedData.get_pkm_yellow_addresses(MainData.PlayerPokemonName))
        name = decode_pkm_text(data)
        print(name)
        start_time = time.time()
    pass
pyboy.stop()
