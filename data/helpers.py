
def select_rom_bank(pyboy, bank: int) -> None:
    bank &= 0x7F
    pyboy.memory[0x6000] = 0x00
    # pyboy.memory[0x4000] = (bank >> 5) & 0x03
    pyboy.memory[0x2000] = bank 
