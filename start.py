from pyboy import PyBoy

pyboy = PyBoy('PokemonYellow.gb')
while not pyboy.tick():
    pass
pyboy.stop()
