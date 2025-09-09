import pyboy
from dataclasses import dataclass
from typing import List, Dict
from data.decoder import decode_pkm_text
from data.ram_reader import MainPokemonData, MemoryData, SavedPokemonData

# Helper for 3-byte EXP (big-ish, hi..lo in memory order)
def read_u24(raw: List[int], sl: tuple[int, int]) -> int:
    b0, b1, b2 = raw[sl[0]:sl[1]]  # [hi, mid, lo]
    return (b0 << 16) | (b1 << 8) | b2
from dataclasses import dataclass
from typing import List, Dict

# Helper for 3-byte EXP (big-ish, hi..lo in memory order)
def read_u24(raw: List[int], sl: tuple[int, int]) -> int:
    b0, b1, b2 = raw[sl[0]:sl[1]]  # [hi, mid, lo]
    return (b0 << 16) | (b1 << 8) | b2


# Gen 1 (RBY) ROM species index  -> National Pokédex number
POKEMON_ROM_ID_TO_PKDX_ID = {
    0x01: 112, # Rhydon
    0x02: 115, # Kangaskhan
    0x03: 32, # Nidoran♂
    0x04: 35, # Clefairy
    0x05: 21, # Spearow
    0x06: 100, # Voltorb
    0x07: 34, # Nidoking
    0x08: 80, # Slowbro
    0x09: 2, # Ivysaur
    0x0A: 103, # Exeggutor
    0x0B: 108, # Lickitung
    0x0C: 102, # Exeggcute
    0x0D: 88, # Grimer
    0x0E: 94, # Gengar
    0x0F: 29, # Nidoran♀
    0x10: 31, # Nidoqueen
    0x11: 104, # Cubone
    0x12: 111, # Rhyhorn
    0x13: 131, # Lapras
    0x14: 59, # Arcanine
    0x15: 151, # Mew
    0x16: 130, # Gyarados
    0x17: 90, # Shellder
    0x18: 72, # Tentacool
    0x19: 92, # Gastly
    0x1A: 123, # Scyther
    0x1B: 120, # Staryu
    0x1C: 9, # Blastoise
    0x1D: 127, # Pinsir
    0x1E: 114, # Tangela
    # 0x1F, 0x20 = MissingNo (omits)
    0x21: 58, # Growlithe
    0x22: 95, # Onix
    0x23: 22, # Fearow
    0x24: 16, # Pidgey
    0x25: 79, # Slowpoke
    0x26: 64, # Kadabra
    0x27: 75, # Graveler
    0x28: 113, # Chansey
    0x29: 67, # Machoke
    0x2A: 122, # Mr. Mime
    0x2B: 106, # Hitmonlee
    0x2C: 107, # Hitmonchan
    0x2D: 24, # Arbok
    0x2E: 47, # Parasect
    0x2F: 54, # Psyduck
    0x30: 96, # Drowzee
    0x31: 76, # Golem
    # 0x32 = MissingNo
    0x33: 126, # Magmar
    # 0x34 = MissingNo
    0x35: 125, # Electabuzz
    0x36: 82, # Magneton
    0x37: 109, # Koffing
    # 0x38 = MissingNo
    0x39: 56, # Mankey
    0x3A: 86, # Seel
    0x3B: 50, # Diglett
    0x3C: 128, # Tauros
    # 0x3D..0x3F = MissingNo
    0x40: 83, # Farfetch'd
    0x41: 48, # Venonat
    0x42: 149, # Dragonite
    # 0x43..0x45 = MissingNo
    0x46: 84, # Doduo
    0x47: 60, # Poliwag
    0x48: 124, # Jynx
    0x49: 146, # Moltres
    0x4A: 144, # Articuno
    0x4B: 145, # Zapdos
    0x4C: 132, # Ditto
    0x4D: 52, # Meowth
    0x4E: 98, # Krabby
    # 0x4F..0x51 = MissingNo
    0x52: 37, # Vulpix
    0x53: 38, # Ninetales
    0x54: 25, # Pikachu
    0x55: 26, # Raichu
    # 0x56..0x57 = MissingNo
    0x58: 147, # Dratini
    0x59: 148, # Dragonair
    0x5A: 140, # Kabuto
    0x5B: 141, # Kabutops
    0x5C: 116, # Horsea
    0x5D: 117, # Seadra
    # 0x5E..0x5F = MissingNo
    0x60: 27, # Sandshrew
    0x61: 28, # Sandslash
    0x62: 138, # Omanyte
    0x63: 139, # Omastar
    0x64: 39, # Jigglypuff
    0x65: 40, # Wigglytuff
    0x66: 133, # Eevee
    0x67: 136, # Flareon
    0x68: 135, # Jolteon
    0x69: 134, # Vaporeon
    0x6A: 66, # Machop
    0x6B: 41, # Zubat
    0x6C: 23, # Ekans
    0x6D: 46, # Paras
    0x6E: 61, # Poliwhirl
    0x6F: 62, # Poliwrath
    0x70: 13, # Weedle
    0x71: 14, # Kakuna
    0x72: 15, # Beedrill
    # 0x73 = MissingNo
    0x74: 85, # Dodrio
    0x75: 57, # Primeape
    0x76: 51, # Dugtrio
    0x77: 49, # Venomoth
    0x78: 87, # Dewgong
    # 0x79 = MissingNo
    # 0x7A = MissingNo
    0x7B: 10, # Caterpie
    0x7C: 11, # Metapod
    0x7D: 12, # Butterfree
    0x7E: 68, # Machamp
    # 0x7F = MissingNo
    0x80: 55, # Golduck
    0x81: 97, # Hypno
    0x82: 42, # Golbat
    0x83: 150, # Mewtwo
    0x84: 143, # Snorlax
    0x85: 129, # Magikarp
    # 0x86..0x87 = MissingNo
    0x88: 89, # Muk
    # 0x89 = MissingNo
    0x8A: 99, # Kingler
    0x8B: 91, # Cloyster
    # 0x8C = MissingNo
    0x8D: 101, # Electrode
    0x8E: 36, # Clefable
    0x8F: 110, # Weezing
    0x90: 53, # Persian
    0x91: 105, # Marowak
    # 0x92 = MissingNo
    0x93: 93, # Haunter
    0x94: 63, # Abra
    0x95: 65, # Alakazam
    0x96: 17, # Pidgeotto
    0x97: 18, # Pidgeot
    0x98: 121, # Starmie
    0x99: 1, # Bulbasaur
    0x9A: 3, # Venusaur
    0x9B: 73, # Tentacruel
    # 0x9C = MissingNo
    0x9D: 118, # Goldeen
    0x9E: 119, # Seaking
    # 0x9F = MissingNo
    # 0xA0..0xA2 = MissingNo
    0xA3: 77, # Ponyta
    0xA4: 78, # Rapidash
    0xA5: 19, # Rattata
    0xA6: 20, # Raticate
    0xA7: 33, # Nidorino
    0xA8: 30, # Nidorina
    0xA9: 74, # Geodude
    0xAA: 137, # Porygon
    0xAB: 142, # Aerodactyl
    # 0xAC = MissingNo
    0xAD: 81, # Magnemite
    # 0xAE = MissingNo
    # 0xAF = MissingNo
    0xB0: 4, # Charmander
    0xB1: 7, # Squirtle
    0xB2: 5, # Charmeleon
    0xB3: 8, # Wartortle  (Carabaffe)  ← ton exemple
    0xB4: 6, # Charizard
    # 0xB5..0xB8 = MissingNo
    0xB9: 43, # Oddish
    0xBA: 44, # Gloom
    0xBB: 45, # Vileplume
    0xBC: 69, # Bellsprout
    0xBD: 70, # Weepinbell
    0xBE: 71, # Victreebel
}

# National Pokédex number -> ROM species index (Gen 1 internal ID)
POKDX_ID_TO_ROM_ID = {
    1:  0x99, # Bulbasaur
    2:  0x09, # Ivysaur
    3:  0x9A, # Venusaur
    4:  0xB0, # Charmander
    5:  0xB2, # Charmeleon
    6:  0xB4, # Charizard
    7:  0xB1, # Squirtle
    8:  0xB3, # Wartortle
    9:  0x1C, # Blastoise
    10: 0x7B, # Caterpie
    11: 0x7C, # Metapod
    12: 0x7D, # Butterfree
    13: 0x70, # Weedle
    14: 0x71, # Kakuna
    15: 0x72, # Beedrill
    16: 0x24, # Pidgey
    17: 0x96, # Pidgeotto
    18: 0x97, # Pidgeot
    19: 0xA5, # Rattata
    20: 0xA6, # Raticate
    21: 0x05, # Spearow
    22: 0x23, # Fearow
    23: 0x6C, # Ekans
    24: 0x2D, # Arbok
    25: 0x54, # Pikachu
    26: 0x55, # Raichu
    27: 0x60, # Sandshrew
    28: 0x61, # Sandslash
    29: 0x0F, # Nidoran♀
    30: 0xA8, # Nidorina
    31: 0x10, # Nidoqueen
    32: 0x03, # Nidoran♂
    33: 0xA7, # Nidorino
    34: 0x07, # Nidoking
    35: 0x04, # Clefairy
    36: 0x8E, # Clefable
    37: 0x52, # Vulpix
    38: 0x53, # Ninetales
    39: 0x64, # Jigglypuff
    40: 0x65, # Wigglytuff
    41: 0x6B, # Zubat
    42: 0x82, # Golbat
    43: 0xB9, # Oddish
    44: 0xBA, # Gloom
    45: 0xBB, # Vileplume
    46: 0x6D, # Paras
    47: 0x2E, # Parasect
    48: 0x41, # Venonat
    49: 0x77, # Venomoth
    50: 0x3B, # Diglett
    51: 0x76, # Dugtrio
    52: 0x4D, # Meowth
    53: 0x90, # Persian
    54: 0x2F, # Psyduck
    55: 0x80, # Golduck
    56: 0x39, # Mankey
    57: 0x75, # Primeape
    58: 0x21, # Growlithe
    59: 0x14, # Arcanine
    60: 0x47, # Poliwag
    61: 0x6E, # Poliwhirl
    62: 0x6F, # Poliwrath
    63: 0x94, # Abra
    64: 0x26, # Kadabra
    65: 0x95, # Alakazam
    66: 0x6A, # Machop
    67: 0x29, # Machoke
    68: 0x7E, # Machamp
    69: 0xBC, # Bellsprout
    70: 0xBD, # Weepinbell
    71: 0xBE, # Victreebel
    72: 0x18, # Tentacool
    73: 0x9B, # Tentacruel
    74: 0xA9, # Geodude
    75: 0x27, # Graveler
    76: 0x31, # Golem
    77: 0xA3, # Ponyta
    78: 0xA4, # Rapidash
    79: 0x25, # Slowpoke
    80: 0x08, # Slowbro
    81: 0xAD, # Magnemite
    82: 0x36, # Magneton
    83: 0x40, # Farfetch’d
    84: 0x46, # Doduo
    85: 0x74, # Dodrio
    86: 0x3A, # Seel
    87: 0x78, # Dewgong
    88: 0x0D, # Grimer
    89: 0x88, # Muk
    90: 0x17, # Shellder
    91: 0x8B, # Cloyster
    92: 0x19, # Gastly
    93: 0x93, # Haunter
    94: 0x0E, # Gengar
    95: 0x22, # Onix
    96: 0x30, # Drowzee
    97: 0x81, # Hypno
    98: 0x4E, # Krabby
    99: 0x8A, # Kingler
    100: 0x06, # Voltorb
    101: 0x8D, # Electrode
    102: 0x0C, # Exeggcute
    103: 0x0A, # Exeggutor
    104: 0x11, # Cubone
    105: 0x91, # Marowak
    106: 0x2B, # Hitmonlee
    107: 0x2C, # Hitmonchan
    108: 0x0B, # Lickitung
    109: 0x37, # Koffing
    110: 0x8F, # Weezing
    111: 0x12, # Rhyhorn
    112: 0x01, # Rhydon
    113: 0x28, # Chansey
    114: 0x1E, # Tangela
    115: 0x02, # Kangaskhan
    116: 0x5C, # Horsea
    117: 0x5D, # Seadra
    118: 0x9D, # Goldeen
    119: 0x9E, # Seaking
    120: 0x1B, # Staryu
    121: 0x98, # Starmie
    122: 0x2A, # Mr. Mime
    123: 0x1A, # Scyther
    124: 0x48, # Jynx
    125: 0x35, # Electabuzz
    126: 0x33, # Magmar
    127: 0x1D, # Pinsir
    128: 0x3C, # Tauros
    129: 0x85, # Magikarp
    130: 0x16, # Gyarados
    131: 0x13, # Lapras
    132: 0x4C, # Ditto
    133: 0x66, # Eevee
    134: 0x69, # Vaporeon
    135: 0x68, # Jolteon
    136: 0x67, # Flareon
    137: 0xAA, # Porygon
    138: 0x62, # Omanyte
    139: 0x63, # Omastar
    140: 0x5A, # Kabuto
    141: 0x5B, # Kabutops
    142: 0xAB, # Aerodactyl
    143: 0x84, # Snorlax
    144: 0x4A, # Articuno
    145: 0x4B, # Zapdos
    146: 0x49, # Moltres
    147: 0x58, # Dratini
    148: 0x59, # Dragonair
    149: 0x42, # Dragonite
    150: 0x83, # Mewtwo
    151: 0x15, # Mew
}


POKDX_ID_TO_NAME = {
    1: {"en": "Bulbasaur",   "fr": "Bulbizarre"},
    2: {"en": "Ivysaur",     "fr": "Herbizarre"},
    3: {"en": "Venusaur",    "fr": "Florizarre"},
    4: {"en": "Charmander",  "fr": "Salamèche"},
    5:  {"en": "Charmeleon",  "fr": "Reptincel"},
    6:  {"en": "Charizard",   "fr": "Dracaufeu"},
    7:  {"en": "Squirtle",    "fr": "Carapuce"},
    8:  {"en": "Wartortle",   "fr": "Carabaffe"},
    9:  {"en": "Blastoise",   "fr": "Tortank"},
    10: {"en": "Caterpie",    "fr": "Chenipan"},
    11: {"en": "Metapod",     "fr": "Chrysacier"},
    12: {"en": "Butterfree",  "fr": "Papilusion"},
    13: {"en": "Weedle",      "fr": "Aspicot"},
    14: {"en": "Kakuna",      "fr": "Coconfort"},
    15: {"en": "Beedrill",    "fr": "Dardargnan"},
    16: {"en": "Pidgey",      "fr": "Roucool"},
    17: {"en": "Pidgeotto",   "fr": "Roucoups"},
    18: {"en": "Pidgeot",     "fr": "Roucarnage"},
    19: {"en": "Rattata",     "fr": "Rattata"},
    20: {"en": "Raticate",    "fr": "Rattatac"},
    21: {"en": "Spearow",     "fr": "Piafabec"},
    22: {"en": "Fearow",      "fr": "Rapasdepic"},
    23: {"en": "Ekans",       "fr": "Abo"},
    24: {"en": "Arbok",       "fr": "Arbok"},
    25: {"en": "Pikachu",     "fr": "Pikachu"},
    26: {"en": "Raichu",      "fr": "Raichu"},
    27: {"en": "Sandshrew",   "fr": "Sabelette"},
    28: {"en": "Sandslash",   "fr": "Sablaireau"},
    29: {"en": "Nidoran♀",    "fr": "Nidoran♀"},
    30: {"en": "Nidorina",    "fr": "Nidorina"},
    31: {"en": "Nidoqueen",   "fr": "Nidoqueen"},
    32: {"en": "Nidoran♂",    "fr": "Nidoran♂"},
    33: {"en": "Nidorino",    "fr": "Nidorino"},
    34: {"en": "Nidoking",    "fr": "Nidoking"},
    35: {"en": "Clefairy",    "fr": "Mélofée"},
    36: {"en": "Clefable",    "fr": "Mélodelfe"},
    37: {"en": "Vulpix",      "fr": "Goupix"},
    38: {"en": "Ninetales",   "fr": "Feunard"},
    39: {"en": "Jigglypuff",  "fr": "Rondoudou"},
    40: {"en": "Wigglytuff",  "fr": "Grodoudou"},
    41: {"en": "Zubat",       "fr": "Nosferapti"},
    42: {"en": "Golbat",      "fr": "Nosferalto"},
    43: {"en": "Oddish",      "fr": "Mystherbe"},
    44: {"en": "Gloom",       "fr": "Ortide"},
    45: {"en": "Vileplume",   "fr": "Rafflesia"},
    46: {"en": "Paras",       "fr": "Paras"},
    47: {"en": "Parasect",    "fr": "Parasect"},
    48: {"en": "Venonat",     "fr": "Mimitoss"},
    49: {"en": "Venomoth",    "fr": "Aéromite"},
    50: {"en": "Diglett",     "fr": "Taupiqueur"},
    51: {"en": "Dugtrio",     "fr": "Triopikeur"},
    52: {"en": "Meowth",      "fr": "Miaouss"},
    53: {"en": "Persian",     "fr": "Persian"},
    54: {"en": "Psyduck",     "fr": "Psykokwak"},
    55: {"en": "Golduck",     "fr": "Akwakwak"},
    56: {"en": "Mankey",      "fr": "Férosinge"},
    57: {"en": "Primeape",    "fr": "Colossinge"},
    58: {"en": "Growlithe",   "fr": "Caninos"},
    59: {"en": "Arcanine",    "fr": "Arcanin"},
    60: {"en": "Poliwag",     "fr": "Ptitard"},
    61: {"en": "Poliwhirl",   "fr": "Têtarte"},
    62: {"en": "Poliwrath",   "fr": "Tartard"},
    63: {"en": "Abra",        "fr": "Abra"},
    64: {"en": "Kadabra",     "fr": "Kadabra"},
    65: {"en": "Alakazam",    "fr": "Alakazam"},
    66: {"en": "Machop",      "fr": "Machoc"},
    67: {"en": "Machoke",     "fr": "Machopeur"},
    68: {"en": "Machamp",     "fr": "Mackogneur"},
    69: {"en": "Bellsprout",  "fr": "Chétiflor"},
    70: {"en": "Weepinbell",  "fr": "Boustiflor"},
    71: {"en": "Victreebel",  "fr": "Empiflor"},
    72: {"en": "Tentacool",   "fr": "Tentacool"},
    73: {"en": "Tentacruel",  "fr": "Tentacruel"},
    74: {"en": "Geodude",     "fr": "Racaillou"},
    75: {"en": "Graveler",    "fr": "Gravalanch"},
    76: {"en": "Golem",       "fr": "Grolem"},
    77: {"en": "Ponyta",      "fr": "Ponyta"},
    78: {"en": "Rapidash",    "fr": "Galopa"},
    79: {"en": "Slowpoke",    "fr": "Ramoloss"},
    80: {"en": "Slowbro",     "fr": "Flagadoss"},
    81: {"en": "Magnemite",   "fr": "Magnéti"},
    82: {"en": "Magneton",    "fr": "Magnéton"},
    83: {"en": "Farfetch'd",  "fr": "Canarticho"},
    84: {"en": "Doduo",       "fr": "Doduo"},
    85: {"en": "Dodrio",      "fr": "Dodrio"},
    86: {"en": "Seel",        "fr": "Otaria"},
    87: {"en": "Dewgong",     "fr": "Lamantine"},
    88: {"en": "Grimer",      "fr": "Tadmorv"},
    89: {"en": "Muk",         "fr": "Grotadmorv"},
    90: {"en": "Shellder",    "fr": "Kokiyas"},
    91: {"en": "Cloyster",    "fr": "Crustabri"},
    92: {"en": "Gastly",      "fr": "Fantominus"},
    93: {"en": "Haunter",     "fr": "Spectrum"},
    94: {"en": "Gengar",      "fr": "Ectoplasma"},
    95: {"en": "Onix",        "fr": "Onix"},
    96: {"en": "Drowzee",     "fr": "Soporifik"},
    97: {"en": "Hypno",       "fr": "Hypnomade"},
    98: {"en": "Krabby",      "fr": "Krabby"},
    99: {"en": "Kingler",     "fr": "Krabboss"},
    100: {"en": "Voltorb",    "fr": "Voltorbe"},
    101: {"en": "Electrode",  "fr": "Électrode"},
    102: {"en": "Exeggcute",  "fr": "Noeunoeuf"},
    103: {"en": "Exeggutor",  "fr": "Noadkoko"},
    104: {"en": "Cubone",     "fr": "Osselait"},
    105: {"en": "Marowak",    "fr": "Ossatueur"},
    106: {"en": "Hitmonlee",  "fr": "Kicklee"},
    107: {"en": "Hitmonchan", "fr": "Tygnon"},
    108: {"en": "Lickitung",  "fr": "Excelangue"},
    109: {"en": "Koffing",    "fr": "Smogo"},
    110: {"en": "Weezing",    "fr": "Smogogo"},
    111: {"en": "Rhyhorn",    "fr": "Rhinocorne"},
    112: {"en": "Rhydon",     "fr": "Rhinoféros"},
    113: {"en": "Chansey",    "fr": "Leveinard"},
    114: {"en": "Tangela",    "fr": "Saquedeneu"},
    115: {"en": "Kangaskhan", "fr": "Kangourex"},
    116: {"en": "Horsea",     "fr": "Hypotrempe"},
    117: {"en": "Seadra",     "fr": "Hypocéan"},
    118: {"en": "Goldeen",    "fr": "Poissirène"},
    119: {"en": "Seaking",    "fr": "Poissoroy"},
    120: {"en": "Staryu",     "fr": "Stari"},
    121: {"en": "Starmie",    "fr": "Staross"},
    122: {"en": "Mr. Mime",   "fr": "M. Mime"},
    123: {"en": "Scyther",    "fr": "Insécateur"},
    124: {"en": "Jynx",       "fr": "Lippoutou"},
    125: {"en": "Electabuzz", "fr": "Élektek"},
    126: {"en": "Magmar",     "fr": "Magmar"},
    127: {"en": "Pinsir",     "fr": "Scarabrute"},
    128: {"en": "Tauros",     "fr": "Tauros"},
    129: {"en": "Magikarp",   "fr": "Magicarpe"},
    130: {"en": "Gyarados",   "fr": "Léviator"},
    131: {"en": "Lapras",     "fr": "Lokhlass"},
    132: {"en": "Ditto",      "fr": "Métamorph"},
    133: {"en": "Eevee",      "fr": "Évoli"},
    134: {"en": "Vaporeon",   "fr": "Aquali"},
    135: {"en": "Jolteon",    "fr": "Voltali"},
    136: {"en": "Flareon",    "fr": "Pyroli"},
    137: {"en": "Porygon",    "fr": "Porygon"},
    138: {"en": "Omanyte",    "fr": "Amonita"},
    139: {"en": "Omastar",    "fr": "Amonistar"},
    140: {"en": "Kabuto",     "fr": "Kabuto"},
    141: {"en": "Kabutops",   "fr": "Kabutops"},
    142: {"en": "Aerodactyl", "fr": "Ptéra"},
    143: {"en": "Snorlax",    "fr": "Ronflex"},
    144: {"en": "Articuno",   "fr": "Artikodin"},
    145: {"en": "Zapdos",     "fr": "Électhor"},
    146: {"en": "Moltres",    "fr": "Sulfura"},
    147: {"en": "Dratini",    "fr": "Minidraco"},
    148: {"en": "Dragonair",  "fr": "Draco"},
    149: {"en": "Dragonite",  "fr": "Dracolosse"},
    150: {"en": "Mewtwo",     "fr": "Mewtwo"},
    151: {"en": "Mew",        "fr": "Mew"},
}

# --- Status flags ---
STATUS_BIT_MASKS = {
    0b00000001: "Sleep counter 1",
    0b00000010: "Sleep counter 2",
    0b00000100: "Sleep counter 3",
    0b00001000: "Poisoned",
    0b00010000: "Burned",
    0b00100000: "Frozen",
    0b01000000: "Paralyzed"
}

# --- Pokémon types (Gen I) ---
POKEMON_TYPES = {
    0: "Normal",
    1: "Fighting",
    2: "Flying",
    3: "Poison",
    4: "Ground",
    5: "Rock",
    6: "Bird",   # unused
    7: "Bug",
    8: "Ghost",
    9: "Steel",  # placeholder in some tables
    20: "Fire",
    21: "Water",
    22: "Grass",
    23: "Electric",
    24: "Psychic",
    25: "Ice",
    26: "Dragon"
}

# --- In-battle slot (D009..D030) ---
POKEMON_LAYOUT_BATTLE = {
    "name":       (0, 11),   # 11 bytes, Gen1 text
    "number":     (11, 12),  # species/ROM id
    "current_hp": (12, 14),  # u16 LE
    "status":     (15, 16),
    "type1":      (16, 17),
    "type2":      (17, 18),
    "moves":      (19, 23),  # 4 bytes
    "dvs":        (23, 25),  # [ATK/DEF][SPD/SPC] (2 bytes)
    "level":      (25, 26),
    "max_hp":     (26, 28),  # u16 LE
    "attack":     (28, 30),  # u16 LE
    "defense":    (30, 32),  # u16 LE
    "speed":      (32, 34),  # u16 LE
    "special":    (34, 36),  # u16 LE
    "pp":         (36, 40),  # 4 bytes (PP1..PP4)
}
BATTLE_STRUCT_LEN = 40  # bytes
BATTLE_NAME_LEN   = 11

# --- Party/Save struct (D16B..D272) ---
# Offsets relatifs au début du Pokémon (44 octets)
POKEMON_LAYOUT_PARTY = {
    "id":             (0, 1),     # species/ROM id
    "current_hp":     (1, 3),     # u16 LE

    # 'Level' fantôme (D16E) -> pas le vrai niveau utilisé pour les stats
    "level_shadow":   (3, 4),

    "status":         (4, 5),
    "type1":          (5, 6),
    "type2":          (6, 7),
    "catch_rate_g2":  (7, 8),     # catch rate / held item if traded to Gen2

    "moves":          (8, 12),    # 4 bytes (Move1..Move4)

    "trainer_id":     (12, 14),   # u16 LE
    "experience":     (14, 17),   # 3 bytes big-ish integer (hi..lo)

    # EVs (u16 LE each)
    "hp_ev":          (17, 19),
    "attack_ev":      (19, 21),
    "defense_ev":     (21, 23),
    "speed_ev":       (23, 25),
    "special_ev":     (25, 27),

    # IVs/DVs (2 bytes, nibbles)
    # byte1: ATK (hi nibble), DEF (lo nibble)
    # byte2: SPD (hi), SPC (lo)
    "ivs":            (27, 29),

    # PP bytes (PP1..PP4)
    "pp":             (29, 33),

    # VRAI niveau + stats dérivées
    "level":          (33, 34),
    "max_hp":         (34, 36),   # u16 LE
    "attack":         (36, 38),   # u16 LE
    "defense":        (38, 40),   # u16 LE
    "speed":          (40, 42),   # u16 LE
    "special":        (42, 44),   # u16 LE

    "name":           (44, 55),   # 11 bytes, Gen1 text (not in battle struct)
}
PARTY_STRUCT_LEN = 44  # bytes

# --- Helpers for decoding ---
def read_u8(raw: List[int], sl: tuple[int, int]) -> int:
    return raw[sl[0]]

def read_u16(raw: List[int], sl: tuple[int, int]) -> int:
    hi, lo = raw[sl[0]:sl[1]]
    return lo | (hi << 8)

def read_str(raw: List[int], sl: tuple[int, int]) -> str:
    return decode_pkm_text(raw[sl[0]:sl[1]], stop_at_terminator=True)

def read_list(raw: List[int], sl: tuple[int, int]) -> List[int]:
    return raw[sl[0]:sl[1]]

def parse_status(b: int) -> List[str]:
    #Only one status can be active at a time in Gen I
    #If it is a sleep status, the 3 first of the mask are used to know what counter it is
    # it can be from 0 to 7 max turns sleep and 0 means not asleep
    if b & 0b00000111:
        return [f"Sleep ({b & 0b00000111} turn asleep)"]
    return [status for bit, status in STATUS_BIT_MASKS.items() if b & bit and bit != 0b00000111]


def parse_dvs(b1: int, b2: int) -> Dict[str, int]:
    return {
        "attack":  (b1 >> 4) & 0xF,
        "defense": b1 & 0xF,
        "speed":   (b2 >> 4) & 0xF,
        "special": b2 & 0xF,
    }

# --- Pokémon wrapper class ---
@dataclass
class PokemonBattleSlot:
    raw: List[int]
    memory_address: int
    pyboy: 'pyboy.PyBoy'

    @classmethod
    def from_memory(cls, pyboy: 'pyboy.PyBoy', data: MemoryData, is_yellow=True) -> 'Pokemon':
        """Load a Pokémon struct directly from PyBoy memory."""
        
        fixed = SavedPokemonData.get_pkm_yellow_addresses(data) if is_yellow else data
        raw_data = list(pyboy.memory[fixed.start_address  : fixed.end_address + 1 ])
        return cls(raw_data, fixed.start_address, pyboy)

    # --- Properties ---
    @property
    def nickname(self) -> str:
        return read_str(self.raw, POKEMON_LAYOUT_BATTLE["name"])

    @property
    def name(self) -> str:
        # pokedex name, not nickname
        return POKDX_ID_TO_NAME.get(self.number, {"en": "Unknown", "fr": "Inconnu"})["en"]
    
    @property
    def number(self) -> int:
        return POKEMON_ROM_ID_TO_PKDX_ID[read_u8(self.raw, POKEMON_LAYOUT_BATTLE["number"])]

    @property
    def current_hp(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_BATTLE["current_hp"])

    @property
    def max_hp(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_BATTLE["max_hp"])

    @property
    def level(self) -> int:
        return read_u8(self.raw, POKEMON_LAYOUT_BATTLE["level"])

    @property
    def status(self) -> List[str]:
        return parse_status(read_u8(self.raw, POKEMON_LAYOUT_BATTLE["status"]))

    @property
    def types(self) -> tuple[str, str]:
        t1 = POKEMON_TYPES.get(read_u8(self.raw, POKEMON_LAYOUT_BATTLE["type1"]), "Unknown")
        t2 = POKEMON_TYPES.get(read_u8(self.raw, POKEMON_LAYOUT_BATTLE["type2"]), "Unknown")
        return (t1, t2)

    @property
    def moves(self) -> List[int]:
        return read_list(self.raw, POKEMON_LAYOUT_BATTLE["moves"])

    @property
    def pp(self) -> List[int]:
        return read_list(self.raw, POKEMON_LAYOUT_BATTLE["pp"])

    @property
    def dvs(self) -> Dict[str, int]:
        b1, b2 = self.raw[23], self.raw[24]
        return parse_dvs(b1, b2)

    @property
    def attack(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_BATTLE["attack"])

    @property
    def defense(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_BATTLE["defense"])

    @property
    def speed(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_BATTLE["speed"])

    @property
    def special(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_BATTLE["special"])

    # --- Setters (write directly to WRAM) ---
    def set_level(self, new_level: int):
        self.pyboy.memory[self.memory_address + 0x5 + 25-1] = new_level
        self._reload_memory()

    def _reload_memory(self):
        shift = 0x5
        self.raw = list(self.pyboy.memory[self.memory_address + shift : self.memory_address + shift + len(self.raw)])

    # --- Pretty-print ---
    def __str__(self):
        return (
            f"Name: {self.name}, "
            f"Level: {self.level}, "
            f"HP: {self.current_hp}/{self.max_hp}, "
            f"Type: {self.types[0]}/{self.types[1]}, "
            f"Status: {', '.join(self.status) if self.status else 'Healthy'}"
        )
    



@dataclass
class PokemonParty:
    raw: List[int]
    memory_address: int
    pyboy: 'pyboy.PyBoy'


    @classmethod
    def from_memory(cls, pyboy: 'pyboy.PyBoy', data: MemoryData, is_yellow=True) -> 'PokemonParty':
        """
        Load a Party/Save Pokémon struct directly from PyBoy memory.
        Uses your SavedPokemonData.get_pkm_yellow_addresses() to correct Yellow shift.
        """
        fixed = SavedPokemonData.get_pkm_yellow_addresses(data) if is_yellow else data
        raw_data = list(pyboy.memory[fixed.start_address : fixed.end_address + 1])

        if data == MainPokemonData.Pokemon1:
            list_to_add = pyboy.memory[MemoryData.Nickname1.start_address : MemoryData.Nickname1.end_address + 1]
            raw_data += list(list_to_add)
        elif data == MainPokemonData.Pokemon2:
            list_to_add = pyboy.memory[MainPokemonData.Nickname2.start_address : MainPokemonData.Nickname2.end_address + 1]
            raw_data += list(list_to_add)
        elif data == MainPokemonData.Pokemon3:
            list_to_add = pyboy.memory[MainPokemonData.Nickname3.start_address : MainPokemonData.Nickname3.end_address + 1]
            raw_data += list(list_to_add)
        elif data == MainPokemonData.Pokemon4:
            list_to_add = pyboy.memory[MainPokemonData.Nickname4.start_address : MainPokemonData.Nickname4.end_address + 1]
            raw_data += list(list_to_add)
        elif data == MainPokemonData.Pokemon5:
            list_to_add = pyboy.memory[MainPokemonData.Nickname5.start_address : MainPokemonData.Nickname5.end_address + 1]
            raw_data += list(list_to_add)
        elif data == MainPokemonData.Pokemon6:
            list_to_add = pyboy.memory[MainPokemonData.Nickname6.start_address : MainPokemonData.Nickname6.end_address + 1]
            raw_data += list(list_to_add)

        return cls(raw_data, fixed.start_address, pyboy)
    


    # --- Core fields ---

    @property
    def name(self) -> str:
        # pokedex name, not nickname
        return POKDX_ID_TO_NAME.get(self.number, {"en": "Unknown", "fr": "Inconnu"}).get("en", "Unknown")

    @property
    def nickname(self) -> str:
        return decode_pkm_text(self.raw[POKEMON_LAYOUT_PARTY["name"][0]:POKEMON_LAYOUT_PARTY["name"][1]], stop_at_terminator=True)
    
    @property
    def species_id(self) -> int:
        return read_u8(self.raw, POKEMON_LAYOUT_PARTY["id"])

    @property
    def number(self) -> int:
        """National Pokédex number (via your ROM->Dex map)."""
        return POKEMON_ROM_ID_TO_PKDX_ID[self.species_id]

    @property
    def current_hp(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["current_hp"])

    @property
    def max_hp(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["max_hp"])

    @property
    def level(self) -> int:
        return read_u8(self.raw, POKEMON_LAYOUT_PARTY["level"])

    @property
    def status(self) -> List[str]:
        return parse_status(read_u8(self.raw, POKEMON_LAYOUT_PARTY["status"]))

    @property
    def types(self) -> tuple[str, str]:
        t1 = POKEMON_TYPES.get(read_u8(self.raw, POKEMON_LAYOUT_PARTY["type1"]), "Unknown")
        t2 = POKEMON_TYPES.get(read_u8(self.raw, POKEMON_LAYOUT_PARTY["type2"]), "Unknown")
        return (t1, t2)

    # --- Moves / PP ---
    @property
    def moves(self) -> List[int]:
        return read_list(self.raw, POKEMON_LAYOUT_PARTY["moves"])  # 4 bytes

    @property
    def pp(self) -> List[int]:
        return read_list(self.raw, POKEMON_LAYOUT_PARTY["pp"])     # 4 bytes

    # --- Stats ---
    @property
    def attack(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["attack"])

    @property
    def defense(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["defense"])

    @property
    def speed(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["speed"])

    @property
    def special(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["special"])

    # --- IDs / EXP ---
    @property
    def trainer_id(self) -> int:
        return read_u16(self.raw, POKEMON_LAYOUT_PARTY["trainer_id"])

    @property
    def experience(self) -> int:
        return read_u24(self.raw, POKEMON_LAYOUT_PARTY["experience"])

    # --- EVs / IVs ---
    @property
    def evs(self) -> Dict[str, int]:
        return {
            "hp":      read_u16(self.raw, POKEMON_LAYOUT_PARTY["hp_ev"]),
            "attack":  read_u16(self.raw, POKEMON_LAYOUT_PARTY["attack_ev"]),
            "defense": read_u16(self.raw, POKEMON_LAYOUT_PARTY["defense_ev"]),
            "speed":   read_u16(self.raw, POKEMON_LAYOUT_PARTY["speed_ev"]),
            "special": read_u16(self.raw, POKEMON_LAYOUT_PARTY["special_ev"]),
        }

    @property
    def ivs(self) -> Dict[str, int]:
        iv_b1, iv_b2 = read_list(self.raw, POKEMON_LAYOUT_PARTY["ivs"])
        return parse_dvs(iv_b1, iv_b2)  # same nibble split as DVs

    # --- Misc ---
    @property
    def level_shadow(self) -> int:
        """The non-authoritative level byte (D16E) kept for completeness."""
        return read_u8(self.raw, POKEMON_LAYOUT_PARTY["level_shadow"])

    @property
    def catch_rate_g2(self) -> int:
        """Catch rate (Gen1) / becomes Held Item when traded to Gen2."""
        return read_u8(self.raw, POKEMON_LAYOUT_PARTY["catch_rate_g2"])

    # --- Setters (optional examples) ---
    def set_level(self, new_level: int):
        self.pyboy.memory[self.memory_address + POKEMON_LAYOUT_PARTY["level"][0]] = new_level
        self._reload_memory()

    def set_move(self, slot_idx: int, move_id: int):
        assert 0 <= slot_idx < 4
        start, _ = POKEMON_LAYOUT_PARTY["moves"]
        self.pyboy.memory[self.memory_address + start + slot_idx] = move_id
        self._reload_memory()

    def set_pp(self, slot_idx: int, new_pp: int):
        assert 0 <= slot_idx < 4
        start, _ = POKEMON_LAYOUT_PARTY["pp"]
        self.pyboy.memory[self.memory_address + start + slot_idx] = new_pp & 0xFF
        self._reload_memory()

    # --- Reload from WRAM ---
    def _reload_memory(self):
        length = len(self.raw)
        self.raw = list(self.pyboy.memory[self.memory_address : self.memory_address + length])

    # --- Pretty-print ---
    def __str__(self):
        return (
            f"Dex #{self.number:03d} | L{self.level} | "
            f"HP {self.current_hp}/{self.max_hp} | "
            f"{self.types[0]}/{self.types[1]} | "
            f"Status: {', '.join(self.status) if self.status else 'Healthy'}"
        )

