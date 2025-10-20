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


FUNCTION_CODE_EFFECT = {
    0x00: "Just damage.",
    0x01: "Target falls asleep.",
    0x02: "The target may be poisoned. 52/256 chance (20.31%).",
    0x03: "The user regains HP equal to 50% of the damage dealt, minimum 1 HP.",
    0x04: "The target may be burned. 26/256 chance (10.16%).",
    0x05: "The target may be frozen. 26/256 chance (10.16%).",
    0x06: "The target may be paralyzed. 26/256 chance (10.16%). Pokémon that are the same type as the move cannot be paralyzed.",
    0x07: "The user faints. Damage calculation uses target's Defense as halved.",
    0x08: "Works only if the target is asleep. If so, user regains HP equal to half the damage dealt (min 1 HP).",
    0x09: "Uses the last move the target used, replacing this move.",
    0x0A: "Raises the user's Attack by 1 stage.",
    0x0B: "Raises the user's Defense by 1 stage.",
    0x0C: "Raises the user's Speed by 1 stage.",
    0x0D: "Raises the user's Special by 1 stage.",
    0x0E: "Raises the user's Accuracy by 1 stage.",
    0x0F: "Raises the user's Evasion by 1 stage.",
    0x10: "Pay Day effect: if attack works and EXP can be gained, adds 2 × user's Level to money earned after battle.",
    0x11: "The attack will hit without fail.",
    0x12: "Lowers the target's Attack by 1 stage.",
    0x13: "Lowers the target's Defense by 1 stage.",
    0x14: "Lowers the target's Speed by 1 stage.",
    0x15: "Lowers the target's Special by 1 stage.",
    0x16: "Lowers the target's Accuracy by 1 stage.",
    0x17: "Lowers the target's Evasion by 1 stage.",
    0x18: "Changes the user's type to the target's until switching or battle end.",
    0x19: "Nullifies all stat mods and cures foe of status/confusion; also negates barriers, Leech Seed, and Mist.",
    0x1A: "Bide: deal 2× the damage taken during Bide (flat, typeless).",
    0x1B: "Locked for 3–4 turns; after series ends, user becomes confused.",
    0x1C: "Immediately ends a wild battle (fails in Trainer battles).",
    0x1D: "Hits 2–5 times (37.5% for 2 or 3 hits; 12.5% for 4 or 5).",
    0x1E: "Seemingly the same as $1D?",
    0x1F: "May cause flinch. 26/256 chance (10.16%).",
    0x20: "Puts the target to sleep.",
    0x21: "High chance to poison: 103/256 (40.23%).",
    0x22: "High chance to burn: 77/256 (30.07%).",
    0x23: "High chance to freeze: 77/256 (30.07%).",
    0x24: "High chance to paralyze: 77/256 (30.07%). Does not paralyze if target shares the move's type.",
    0x25: "High chance to flinch: 77/256 (30.07%).",
    0x26: "OHKO; fails if user's Speed < target's. Affected by type immunities. Technically deals 65,535 damage.",
    0x27: "Two-turn move: charge (glow) then attack.",
    0x28: "Deals damage equal to half the target's current HP (rounded up). Ignores type immunities.",
    0x29: "Ignores type immunities to deal flat damage per move (e.g., Sonic Boom 20, Seismic Toss/Night Shade = Level, Dragon Rage 40, Psywave variable).",
    0x2A: "Binding move (Wrap-like) for 2–5 turns; cancels if first turn misses; target can switch; user locked into it.",
    0x2B: "Fly effect: invulnerable first turn (except Bide/Swift), strike second turn.",
    0x2C: "Two-hit attack this turn; each hit deals equal damage.",
    0x2D: "If the attack misses, the user loses 50% of their max HP.",
    0x2E: "Mist effect: prevents the opponent from lowering the user's stats until switching.",
    0x2F: "Focus Energy (bugged in RB/GY): reduces crit rate to 25% of original instead of 4×.",
    0x30: "Recoil: user takes 1/4 of damage dealt (min 1 HP).",
    0x31: "Confuses the target (100% if it hits).",
    0x32: "Raises the user's Attack by 2 stages.",
    0x33: "Raises the user's Defense by 2 stages.",
    0x34: "Raises the user's Speed by 2 stages.",
    0x35: "Raises the user's Special by 2 stages.",
    0x36: "Raises the user's Accuracy by 2 stages.",
    0x37: "Raises the user's Evasion by 2 stages.",
    0x38: "Recover/Softboiled: heal 1/2 max HP; fails at full HP and on certain 256-boundary HP deficits (RB/Y bug).",
    0x39: "Transform: copy target's species, type, stats (except Level/HP), stat mods, and moves (each set to 5 PP). Ditto is immune.",
    0x3A: "Lowers the target's Attack by 2 stages.",
    0x3B: "Lowers the target's Defense by 2 stages.",
    0x3C: "Lowers the target's Speed by 2 stages.",
    0x3D: "Lowers the target's Special by 2 stages.",
    0x3E: "Lowers the target's Accuracy by 2 stages.",
    0x3F: "Lowers the target's Evasion by 2 stages.",
    0x40: "Light Screen: halves Special damage received; ignores crits; ends on switching.",
    0x41: "Reflect: halves Physical damage received; ignores crits; ends on switching.",
    0x42: "Guaranteed poison on hit (Toxic = badly poison).",
    0x43: "Guaranteed paralysis on hit; ignores type immunities.",
    0x44: "May lower Attack by 1 stage (85/256 ≈ 33.20%).",
    0x45: "May lower Defense by 1 stage (85/256 ≈ 33.20%).",
    0x46: "May lower Speed by 1 stage (85/256 ≈ 33.20%).",
    0x47: "May lower Special by 1 stage (85/256 ≈ 33.20%).",
    0x48: "May lower Accuracy by 1 stage (85/256 ≈ 33.20%).",
    0x49: "May lower Evasion by 1 stage (85/256 ≈ 33.20%).",
    0x4A: "(glitched stat lowering thing).",
    0x4B: "(glitched stat lowering thing).",
    0x4C: "May confuse the target on hit (26/256 ≈ 10.16%).",
    0x4D: "May poison on hit (52/256 ≈ 20.31%); hits twice, combined poison chance ≈ 36.50%.",
    0x4E: "(undefined effect – game crash).",
    0x4F: "Substitute: create a decoy at cost of 25% max HP (needs ≥ 25%+1 HP). Decoy has 25% max HP; disappears when broken or on switching.",
    0x50: "Recharge next turn unless it missed, dealt 0 damage, or KOed the target/Substitute.",
    0x51: "Rage: locks user; each time user (or its Substitute) loses HP from an opponent attack, Attack rises by 1 stage. If this misses, its accuracy becomes ~1.",
    0x52: "Mimic: copy one selected opposing move, replacing this move until switching/battle end.",
    0x53: "Metronome: calls a random valid move (except Metronome/Struggle); ignores Disable.",
    0x54: "Leech Seed: fails on Grass; target loses 1/16 max HP each turn; user's current Pokémon heals that amount (multiplies with Toxic counter).",
    0x55: "Splash: does nothing.",
    0x56: "Disable: prevents the target from using a random move.",
    # 0x57–0xFF are undefined and generally crash:
}