
import threading
import time
from loguru import logger
import pyboy



class MemoryData:

    shift = 0x5  # Offset to apply when reading from WRAM in PyBoy

    def __init__(self, start_address, end_address, description=""):
        self.start_address = start_address + self.shift
        self.end_address = end_address + self.shift
        self.description = description
        
    def size(self) -> int:
        return self.end_address - self.start_address + 1

    def __repr__(self):
        return f"MemoryData({self.start_address:#06X}, {self.end_address:#06X}, {self.description})"
    
    @staticmethod
    def set_shift(shift: int):
        MemoryData.shift = shift


class DataType:
    def data_size(self, elem: MemoryData):
        return elem.size()
    

    @classmethod
    def get_data(cls, pyboy: 'pyboy.PyBoy', elem: MemoryData) -> bytes:
        """Lit les données mémoire spécifiées par `elem` depuis l'instance PyBoy."""
        return pyboy.memory[elem.start_address : elem.end_address + 1]

class SavedPokemonData(DataType):
    #SRAM
    
    #Bank 0
    SpriteBuffer0              = MemoryData(0xa000,0xa187) # 0xa000 - 0xa187
    SpriteBuffer1              = MemoryData(0xa188,0xa30f) # 0xa188 - 0xa30f
    SpriteBuffer2              = MemoryData(0xa310,0xa497) # 0xa310 - 0xa497
    HallOfFame                 = MemoryData(0xa598,0xb857) # 0xa598 - 0xb857

    # Bank 1
    PlayerName                 = MemoryData(0xa598,0xa5a2) # 0xa598 - 0xa5a2
    MainData                   = MemoryData(0xa5a3,0xad2b) # 0xa5a3 - 0xad2b
    SpriteData                 = MemoryData(0xad2c,0xaf2b) # 0xad2c - 0xaf2b
    PartyData                  = MemoryData(0xaf2c,0xb0bf) # 0xaf2c - 0xb0bf
    CurrentBoxData             = MemoryData(0xb0c0,0xbc521) # 0xb0c0 - 0xbc521
    TilesetType                = MemoryData(0xbc522,0xbc522) # 0xbc522
    MainDataChecksum           = MemoryData(0xbc523,0xbc523) # 0xbc523
    SpriteDataChecksum         = MemoryData(0xbc524,0xbc524) # 0xbc524
    #Bank 2
    
    Box1                       = MemoryData(0xA000, 0xA461)  # 0x462 bytes
    Box2                       = MemoryData(0xA462, 0xA8C3)  # 0x462 bytes
    Box3                       = MemoryData(0xA8C4, 0xAD25)  # 0x462 bytes
    Box4                       = MemoryData(0xAD26, 0xB187)  # 0x462 bytes
    Box5                       = MemoryData(0xB188, 0xB5E9)  # 0x462 bytes
    Box6                       = MemoryData(0xB5EA, 0xBA4B)  # 0x462 bytes
    GlobalChecksum_2           = MemoryData(0xBA4C, 0xBA4C)  # 0x1 byte
    IndividualChecksums_2      = MemoryData(0xBA4D, 0xBA52)  # 0x6 bytes

    # Bank 3
    Box7                       = MemoryData(0xA000, 0xA461)  # 0x462 bytes
    Box8                       = MemoryData(0xA462, 0xA8C3)  # 0x462 bytes
    Box9                       = MemoryData(0xA8C4, 0xAD25)  # 0x462 bytes
    Box10                      = MemoryData(0xAD26, 0xB187)  # 0x462 bytes
    Box11                      = MemoryData(0xB188, 0xB5E9)  # 0x462 bytes
    Box12                      = MemoryData(0xB5EA, 0xBA4B)  # 0x462 bytes
    GlobalChecksum_3           = MemoryData(0xBA4C, 0xBA4C)  # 0x1 byte
    IndividualChecksums_3      = MemoryData(0xBA4D, 0xBA52)  # 0x6 bytes

class MainPokemonData(DataType):
    #WRAM
    # Audio
    AudioMuteFlag                = MemoryData(0xC002, 0xC002, "Bit 7: 1 if audio is muted. Other bits: pause music, continue SFX")
    MusicVolumes                 = MemoryData(0xC0DE, 0xC0DE, "Volumes for all music channels (with fade if supported)")
    CurrentSoundBank             = MemoryData(0xC0EF, 0xC0EF, "Current sound bank")
    SavedSoundBank               = MemoryData(0xC0F0, 0xC0F0, "Saved sound bank")
    
    # Sprite Data blocks
    SpriteData_Block             = MemoryData(0xC100, 0xC2FF, "Data for all sprites on the current map (16 sprites × 0x10 bytes, player=sprite 0)") # TODO create a func to get sprite data by index

    TileBuffer                    = MemoryData(0xC3A0, 0xC507, "Buffer of all tiles onscreen")
    TileBufferPrev                = MemoryData(0xC508, 0xC5CF, "Copy of previous buffer (used to restore tiles after closing a menu)")

    # Menu Data
    MenuCursorYPos                = MemoryData(0xCC24, 0xCC24, "Y position of the cursor for the top menu item (id 0)")
    MenuCursorXPos                = MemoryData(0xCC25, 0xCC25, "X position of the cursor for the top menu item (id 0)")
    MenuSelectedItem              = MemoryData(0xCC26, 0xCC26, "Currently selected menu item (topmost is 0)")
    MenuHiddenTile                = MemoryData(0xCC27, 0xCC27, "Tile hidden by the menu cursor")
    MenuLastItemID                = MemoryData(0xCC28, 0xCC28, "ID of the last menu item")
    MenuKeyBitmask                = MemoryData(0xCC29, 0xCC29, "Bitmask applied to the key port for the current menu")
    MenuPrevItemID                = MemoryData(0xCC2A, 0xCC2A, "ID of the previously selected menu item")
    MenuLastPartyPos              = MemoryData(0xCC2B, 0xCC2B, "Last cursor position on the party / Bill's PC screen")
    MenuLastItemPos               = MemoryData(0xCC2C, 0xCC2C, "Last cursor position on the item screen")
    MenuLastBattlePos             = MemoryData(0xCC2D, 0xCC2D, "Last cursor position on the START / battle menu")
    MenuCurrentPartyIndex         = MemoryData(0xCC2F, 0xCC2F, "Index (in party) of the Pokémon currently sent out")
    MenuCursorTilePtr             = MemoryData(0xCC30, 0xCC31, "Pointer to cursor tile in C3A0 buffer")
    MenuFirstItemID               = MemoryData(0xCC36, 0xCC36, "ID of the first displayed menu item")
    MenuSelectHighlight           = MemoryData(0xCC35, 0xCC35, "Item highlighted with Select (01 = first item, 00 = no item, etc.)")
    
    # Link Data
    LinkDataRange        = MemoryData(0xCC3C, 0xCC49, "Cable Club link-related data block")
    LinkTimeoutCounter   = MemoryData(0xCC47, 0xCC47, "Link timeout counter (context-dependent)")
    LinkEnteringCableClub= MemoryData(0xCC47, 0xCC47, "Flag: player entering Cable Club? (context-dependent)")
    
    # Misc
    PartySwapBuffer = MemoryData(0xCC97, 0xCCA0, "Buffer used when swapping party Pokémon")
    
    # Battle
    BattleTurnCounter     = MemoryData(0xCCD5, 0xCCD5, "Number of turns in current battle")
    BattleUnknown_CCD6    = MemoryData(0xCCD6, 0xCCD6, "Undocumented (if used)")
    PlayerSubstituteHP    = MemoryData(0xCCD7, 0xCCD7, "Player's Substitute HP")
    EnemySubstituteHP     = MemoryData(0xCCD8, 0xCCD8, "Enemy Substitute HP")
    BattleMoveMenuType    = MemoryData(0xCCDB, 0xCCDB, "Move menu type (0=regular, 1=mimic, others=text boxes like learn/PP-refill)")
    BattlePlayerMove      = MemoryData(0xCCDC, 0xCCDC, "Player-selected move")
    BattleEnemyMove       = MemoryData(0xCCDD, 0xCCDD, "Enemy-selected move")
    PayDayMoney           = MemoryData(0xCCE5, 0xCCE7, "Money earned by Pay Day (3-byte value)")
    
    # Safari Zone Data
    OpponentEscapeFactor     = MemoryData(0xCCE8, 0xCCE8, "Opponent escaping factor")
    OpponentBaitFactor       = MemoryData(0xCCE9, 0xCCE9, "Opponent baiting factor")
    BattleDisobedienceFlag   = MemoryData(0xCCED, 0xCCED, "Is current Pokémon disobedient?")
    BattleEnemyDisabledMove  = MemoryData(0xCCEE, 0xCCEE, "Player move that the enemy disabled")
    BattlePlayerDisabledMove = MemoryData(0xCCEF, 0xCCEF, "Enemy move that the player disabled")
    LowHealthAlarmDisabled   = MemoryData(0xCCF6, 0xCCF6, "Is low-health alarm disabled?")
    BideAccumulatedDamage    = MemoryData(0xCD05, 0xCD06, "Damage accumulated by enemy while Biding (2-byte value)")

    PlayerAtkModifier        = MemoryData(0xCD1A, 0xCD1A, "Player's Pokémon Attack modifier (7=no modifier)")
    PlayerDefModifier        = MemoryData(0xCD1B, 0xCD1B, "Player's Pokémon Defense modifier")
    PlayerSpdModifier        = MemoryData(0xCD1C, 0xCD1C, "Player's Pokémon Speed modifier")
    PlayerSpcModifier        = MemoryData(0xCD1D, 0xCD1D, "Player's Pokémon Special modifier")
    PlayerAccModifier        = MemoryData(0xCD1E, 0xCD1E, "Player's Pokémon Accuracy modifier")
    PlayerEvaModifier        = MemoryData(0xCD1F, 0xCD1F, "Player's Pokémon Evasion modifier")

    EngagedTrainerClass      = MemoryData(0xCD2D, 0xCD2D, "Engaged Trainer class / legendary Pokémon ID")
    EngagedTrainerRosterID   = MemoryData(0xCD2E, 0xCD2E, "Engaged Trainer roster ID / Enemy's Pokémon Attack modifier (7=no modifier)")
    EnemyDefModifier         = MemoryData(0xCD2F, 0xCD2F, "Enemy's Pokémon Defense modifier")
    EnemySpdModifier         = MemoryData(0xCD30, 0xCD30, "Enemy's Pokémon Speed modifier")
    EnemySpcModifier         = MemoryData(0xCD31, 0xCD31, "Enemy's Pokémon Special modifier")
    EnemyAccModifier         = MemoryData(0xCD32, 0xCD32, "Enemy's Pokémon Accuracy modifier")
    EnemyEvaModifier         = MemoryData(0xCD33, 0xCD33, "Enemy's Pokémon Evasion modifier")
    
    # Jpypad simulation
    JoypadInputSimulation = MemoryData(0xCD38, 0xCD38, "Index for joypad input simulation (if non-zero, disables collision but does not lock player)")
    
    # Pokemon MArt
    MartTotalItems = MemoryData(0xCF7B, 0xCF7B, "Pokémon Mart - total number of items")
    MartItem1      = MemoryData(0xCF7C, 0xCF7C, "Pokémon Mart - Item 1")
    MartItem2      = MemoryData(0xCF7D, 0xCF7D, "Pokémon Mart - Item 2")
    MartItem3      = MemoryData(0xCF7E, 0xCF7E, "Pokémon Mart - Item 3")
    MartItem4      = MemoryData(0xCF7F, 0xCF7F, "Pokémon Mart - Item 4")
    MartItem5      = MemoryData(0xCF80, 0xCF80, "Pokémon Mart - Item 5")
    MartItem6      = MemoryData(0xCF81, 0xCF81, "Pokémon Mart - Item 6")
    MartItem7      = MemoryData(0xCF82, 0xCF82, "Pokémon Mart - Item 7")
    MartItem8      = MemoryData(0xCF83, 0xCF83, "Pokémon Mart - Item 8")
    MartItem9      = MemoryData(0xCF84, 0xCF84, "Pokémon Mart - Item 9")
    MartItem10     = MemoryData(0xCF85, 0xCF85, "Pokémon Mart - Item 10")
    
    # Name rater
    NameRaterTarget = MemoryData(0xCF92, 0xCF92, "Which Pokémon does Name Rater change?")
    
    # Battle

    # Player move info
    PlayerMoveEffect   = MemoryData(0xCFD3, 0xCFD3, "Your Move Effect (e.g. 0x10 = coins scatter everywhere)")
    PlayerMoveType     = MemoryData(0xCFD5, 0xCFD5, "Your Move Type")
    PlayerMoveUsed     = MemoryData(0xCCDC, 0xCCDC, "Your Move Used")

    # Enemy move info
    EnemyMoveID        = MemoryData(0xCFCC, 0xCFCC, "Enemy's Move ID")
    EnemyMoveEffect    = MemoryData(0xCFCD, 0xCFCD, "Enemy's Move Effect")
    EnemyMovePower     = MemoryData(0xCFCE, 0xCFCE, "Enemy's Move Power")
    EnemyMoveType      = MemoryData(0xCFCF, 0xCFCF, "Enemy's Move Type")
    EnemyMoveAccuracy  = MemoryData(0xCFD0, 0xCFD0, "Enemy's Move Accuracy")
    EnemyMoveMaxPP     = MemoryData(0xCFD1, 0xCFD1, "Enemy's Move Max PP")

    # Player move details (redundant structure)
    PlayerMoveID       = MemoryData(0xCFD2, 0xCFD2, "Player's Move ID")
    PlayerMoveEffect2  = MemoryData(0xCFD3, 0xCFD3, "Player's Move Effect")
    PlayerMovePower    = MemoryData(0xCFD4, 0xCFD4, "Player's Move Power")
    PlayerMoveType2    = MemoryData(0xCFD5, 0xCFD5, "Player's Move Type")
    PlayerMoveAccuracy = MemoryData(0xCFD6, 0xCFD6, "Player's Move Accuracy")
    PlayerMoveMaxPP    = MemoryData(0xCFD7, 0xCFD7, "Player's Move Max PP")

    # Pokémon IDs
    EnemyPokemonID     = MemoryData(0xCFD8, 0xCFD8, "Enemy's Pokémon internal ID")
    PlayerPokemonID    = MemoryData(0xCFD9, 0xCFD9, "Player's Pokémon internal ID")

    # Enemy name
    EnemyName          = MemoryData(0xCFDA, 0xCFE4, "Enemy's Name")

    # Enemy Pokémon data
    EnemyPokemonID2    = MemoryData(0xCFE5, 0xCFE5, "Enemy's Pokémon internal ID (duplicate)")
    EnemyHP            = MemoryData(0xCFE6, 0xCFE7, "Enemy's HP (2 bytes)")
    EnemyLevel         = MemoryData(0xCFE8, 0xCFE8, "Enemy's Level")
    EnemyStatus        = MemoryData(0xCFE9, 0xCFE9, "Enemy's Status (bitfield: 6=Paralyzed,5=Frozen,4=Burned,3=Poisoned,0-2=Sleep counter)")
    EnemyType1         = MemoryData(0xCFEA, 0xCFEA, "Enemy's Type 1")
    EnemyType2         = MemoryData(0xCFEB, 0xCFEB, "Enemy's Type 2")
    EnemyCatchRateTmp  = MemoryData(0xCFEC, 0xCFEC, "Enemy's Catch Rate (unused; overwritten by Transform script)")

    # Enemy moves
    EnemyMove1         = MemoryData(0xCFED, 0xCFED, "Enemy's Move 1")
    EnemyMove2         = MemoryData(0xCFEE, 0xCFEE, "Enemy's Move 2")
    EnemyMove3         = MemoryData(0xCFEF, 0xCFEF, "Enemy's Move 3")
    EnemyMove4         = MemoryData(0xCFF0, 0xCFF0, "Enemy's Move 4")

    # Enemy IVs
    EnemyIVsAtkDef     = MemoryData(0xCFF1, 0xCFF1, "Enemy's Attack and Defense IVs")
    EnemyIVsSpdSpc     = MemoryData(0xCFF2, 0xCFF2, "Enemy's Speed and Special IVs")

    # Enemy stats
    EnemyLevel2        = MemoryData(0xCFF3, 0xCFF3, "Enemy's Level (duplicate)")
    EnemyMaxHP         = MemoryData(0xCFF4, 0xCFF5, "Enemy's Max HP (2 bytes)")
    EnemyAttack        = MemoryData(0xCFF6, 0xCFF7, "Enemy's Attack (2 bytes)")
    EnemyDefense       = MemoryData(0xCFF8, 0xCFF9, "Enemy's Defense (2 bytes)")
    EnemySpeed         = MemoryData(0xCFFA, 0xCFFB, "Enemy's Speed (2 bytes)")
    EnemySpecial       = MemoryData(0xCFFC, 0xCFFD, "Enemy's Special (2 bytes)")

    # Enemy PP slots
    EnemyPP1           = MemoryData(0xCFFE, 0xCFFE, "Enemy's PP (Move 1)")
    EnemyPP2           = MemoryData(0xCFFF, 0xCFFF, "Enemy's PP (Move 2)")
    EnemyPP3           = MemoryData(0xD000, 0xD000, "Enemy's PP (Move 3)")
    EnemyPP4           = MemoryData(0xD001, 0xD001, "Enemy's PP (Move 4)")

    # Enemy base stats block
    EnemyBaseStats     = MemoryData(0xD002, 0xD006, "Enemy's Base Stats (5 bytes)")
    EnemyCatchRate     = MemoryData(0xD007, 0xD007, "Enemy's Catch Rate (final)")
    EnemyBaseExp       = MemoryData(0xD008, 0xD008, "Enemy's Base Experience yield")
    
    # Pokémon 1st Slot (In-Battle)
    Pokemon1SlotBattle      = MemoryData(0xD009, 0xD030, "Player's 1st Pokémon in battle data block (48 bytes)")
    PlayerPokemonName       = MemoryData(0xD009, 0xD013, "Player's Pokémon Name")
    PlayerPokemonNumber     = MemoryData(0xD014, 0xD014, "Player's Pokémon Number")
    PlayerCurrentHP         = MemoryData(0xD015, 0xD016, "Player's Current HP (2 bytes)")
    PlayerStatus            = MemoryData(0xD018, 0xD018, "Player's Status (bit 6=Paralyzed, 5=Frozen, 4=Burned, 3=Poisoned, 0–2=Sleep counter)")
    PlayerType1             = MemoryData(0xD019, 0xD019, "Player's Type 1")
    PlayerType2             = MemoryData(0xD01A, 0xD01A, "Player's Type 2")
    PlayerMove1             = MemoryData(0xD01C, 0xD01C, "Player's Move #1 (First Slot)")
    PlayerMove2             = MemoryData(0xD01D, 0xD01D, "Player's Move #2 (Second Slot)")
    PlayerMove3             = MemoryData(0xD01E, 0xD01E, "Player's Move #3 (Third Slot)")
    PlayerMove4             = MemoryData(0xD01F, 0xD01F, "Player's Move #4 (Fourth Slot)")
    PlayerDVsAtkDef         = MemoryData(0xD020, 0xD020, "Player's Attack and Defense DVs")
    PlayerDVsSpdSpc         = MemoryData(0xD021, 0xD021, "Player's Speed and Special DVs")
    PlayerLevel             = MemoryData(0xD022, 0xD022, "Player's Level")
    PlayerMaxHP             = MemoryData(0xD023, 0xD024, "Player's Max HP (2 bytes)")
    PlayerAttack            = MemoryData(0xD025, 0xD026, "Player's Attack (2 bytes)")
    PlayerDefense           = MemoryData(0xD027, 0xD028, "Player's Defense (2 bytes)")
    PlayerSpeed             = MemoryData(0xD029, 0xD02A, "Player's Speed (2 bytes)")
    PlayerSpecial           = MemoryData(0xD02B, 0xD02C, "Player's Special (2 bytes)")
    PlayerPP1               = MemoryData(0xD02D, 0xD02D, "Player's PP (Move 1)")
    PlayerPP2               = MemoryData(0xD02E, 0xD02E, "Player's PP (Move 2)")
    PlayerPP3               = MemoryData(0xD02F, 0xD02F, "Player's PP (Move 3)")
    PlayerPP4               = MemoryData(0xD030, 0xD030, "Player's PP (Move 4)")
    
    # Type of battle
    BattleTypeID          = MemoryData(0xD057, 0xD057, "Type of battle")
    BattleSubType         = MemoryData(0xD05A, 0xD05A, "Battle Type (Normal, Safari Zone, Old Man battle...)")
    GymLeaderMusicFlag    = MemoryData(0xD05C, 0xD05C, "Is Gym Leader battle music playing?")
    BattleUnknown_D05D    = MemoryData(0xD05D, 0xD05D, "Undocumented / unknown")
    BattleCritOHKOFlag    = MemoryData(0xD05E, 0xD05E, "Critical Hit / OHKO flag (01=Critical, 02=One-hit KO)")
    HookedPokemonFlag     = MemoryData(0xD05F, 0xD05F, "Hooked Pokémon flag")
    
    # Battle status
    BattleStatusPlayer    = MemoryData(0xD062, 0xD064, "Battle Status (Player). "
        "D062 bits: 0=Bide, 1=Thrash/Petal Dance, 2=Multi-hit attack, 3=Flinch, 4=Charging, "
        "5=Multi-turn move (Wrap), 6=Invulnerable (Fly/Dig), 7=Confusion. "
        "D063 bits: 0=X Accuracy, 1=Mist, 2=Focus Energy, 4=Substitute, 5=Recharge, "
        "6=Rage, 7=Leech Seeded. "
        "D064 bits: 0=Toxic, 1=Light Screen, 2=Reflect, 3=Transformed.")

    BattleStatDoubleCPU   = MemoryData(0xD065, 0xD065, "Stat to double (CPU)")
    BattleStatHalveCPU    = MemoryData(0xD066, 0xD066, "Stat to halve (CPU)")

    BattleStatusCPU       = MemoryData(0xD067, 0xD069, "Battle Status (CPU). Includes Transformed flag at D069 (opponent treated as Ditto).")

    PlayerMultiHitCounter = MemoryData(0xD06A, 0xD06A, "Multi-Hit Move counter (Player)")
    PlayerConfusionCount  = MemoryData(0xD06B, 0xD06B, "Confusion counter (Player)")
    PlayerToxicCount      = MemoryData(0xD06C, 0xD06C, "Toxic counter (Player)")
    PlayerDisableCounter  = MemoryData(0xD06D, 0xD06E, "Disable counter (Player, 2 bytes)")

    CPUMultiHitCounter    = MemoryData(0xD06F, 0xD06F, "Multi-Hit Move counter (CPU)")
    CPUConfusionCount     = MemoryData(0xD070, 0xD070, "Confusion counter (CPU)")
    CPUToxicCount         = MemoryData(0xD071, 0xD071, "Toxic counter (CPU)")
    CPUDisableCounter     = MemoryData(0xD072, 0xD072, "Disable counter (CPU)")
    BattlePendingDamage   = MemoryData(0xD0D8, 0xD0D8, "Amount of damage the current attack is about to do (may show max possible damage one frame before actual damage)")
    
    # Game Corner
    GameCornerPrize1 = MemoryData(0xD13D, 0xD13D, "Game Corner - 1st prize")
    GameCornerPrize2 = MemoryData(0xD13E, 0xD13E, "Game Corner - 2nd prize")
    GameCornerPrize3 = MemoryData(0xD13F, 0xD13F, "Game Corner - 3rd prize")
    
    # Link Battle PRNG
    LinkBattleRNG = MemoryData(0xD148, 0xD150, "9 pseudo-random numbers used during Link Battles (regenerated as n × 5 + 1 when exhausted)")
    
    # Player
    PlayerNameString   = MemoryData(0xD158, 0xD162, "Player's Name (up to 11 characters)")
    PartyCount         = MemoryData(0xD163, 0xD163, "Number of Pokémon in party")
    PartyPokemon1      = MemoryData(0xD164, 0xD164, "Party Pokémon 1 ID")
    PartyPokemon2      = MemoryData(0xD165, 0xD165, "Party Pokémon 2 ID")
    PartyPokemon3      = MemoryData(0xD166, 0xD166, "Party Pokémon 3 ID")
    PartyPokemon4      = MemoryData(0xD167, 0xD167, "Party Pokémon 4 ID")
    PartyPokemon5      = MemoryData(0xD168, 0xD168, "Party Pokémon 5 ID")
    PartyPokemon6      = MemoryData(0xD169, 0xD169, "Party Pokémon 6 ID")
    PartyListEnd       = MemoryData(0xD16A, 0xD16A, "End of party list marker")
    
    # Pokemon 
    Pokemon1 = MemoryData(0xD16B, 0xD196, "First Pokémon data block (27 bytes)")
    Pokemon2 = MemoryData(0xD197, 0xD1C2, "Second Pokémon data block (27 bytes)")
    Pokemon3 = MemoryData(0xD1C3, 0xD1EE, "Third Pokémon data block (27 bytes)")
    Pokemon4 = MemoryData(0xD1EF, 0xD21A, "Fourth Pokémon data block (27 bytes)")
    Pokemon5 = MemoryData(0xD21B, 0xD246, "Fifth Pokémon data block (27 bytes)")
    Pokemon6 = MemoryData(0xD247, 0xD272, "Sixth Pokémon data block (27 bytes)")
    
    # Trainer name
    TrainerName1 = MemoryData(0xD273, 0xD27D, "Trainer name for 1st")
    TrainerName2 = MemoryData(0xD27E, 0xD288, "Trainer name for 2nd")
    TrainerName3 = MemoryData(0xD289, 0xD293, "Trainer name for 3rd")
    TrainerName4 = MemoryData(0xD294, 0xD29E, "Trainer name for 4th")
    TrainerName5 = MemoryData(0xD29F, 0xD2A9, "Trainer name for 5th")
    TrainerName6 = MemoryData(0xD2AA, 0xD2B4, "Trainer name for 6th")
    
    # NickName
    Nickname1 = MemoryData(0xD2B5, 0xD2BF, "Nickname for 1st Pokémon")
    Nickname2 = MemoryData(0xD2C0, 0xD2CA, "Nickname for 2nd Pokémon")
    Nickname3 = MemoryData(0xD2CB, 0xD2D5, "Nickname for 3rd Pokémon")
    Nickname4 = MemoryData(0xD2D6, 0xD2E0, "Nickname for 4th Pokémon")
    Nickname5 = MemoryData(0xD2E1, 0xD2EB, "Nickname for 5th Pokémon")
    Nickname6 = MemoryData(0xD2EC, 0xD2F6, "Nickname for 6th Pokémon")
    
    #Pokedex
    PokedexOwned = MemoryData(0xd2f7, 0xd309, "Pokédex owned flags (bitfield, 1 bit per Pokémon, 0=not owned, 1=owned)")
    PokedexSeen  = MemoryData(0xd30a, 0xd31c, "Pokédex seen flags (bitfield, 1 bit per Pokémon, 0=not seen, 1=seen)")
    
    #Items
    TotalItems = MemoryData(0xD31d, 0xD31D, "Total number of different items")
    Items = MemoryData(0xD31E, 0xD346, "Items (item ID + quantity, 2 bytes each, up to 50 items)")
    
    # Money
    Money = MemoryData(0xD347, 0xD349, "Money (in cents)")
    
    # Rival
    rival_name = MemoryData(0xD34a, 0xD351, "Rival's name (up to 11 characters)")
    
    # Miscellaneous
    Options              = MemoryData(0xD355, 0xD355, "Game options: bit7=Battle Anim (1=Off,0=On), bit6=Battle Style (1=Set,0=Shift), low nibble=Text Speed (0=fastest, F=slowest)")
    Badges               = MemoryData(0xD356, 0xD356, "Obtained badges (bitfield)")

    TextPrintFlags       = MemoryData(0xD358, 0xD358, "Text printing behavior (bit0=delay 1 frame between letters if 0, bit1=no delay if 0)")

    PlayerID1            = MemoryData(0xD359, 0xD359, "Player ID [1] (multiple of 256)")
    PlayerID2            = MemoryData(0xD35A, 0xD35A, "Player ID [2] (0–255)")

    AudioTrack           = MemoryData(0xD35B, 0xD35B, "Audio track ID (see Audio section)")
    AudioBank            = MemoryData(0xD35C, 0xD35C, "Audio bank (see Audio section)")

    MapPalette           = MemoryData(0xD35D, 0xD35D, "Controls map palette (0=normal, 6=Flash required)")
    CurrentMapNumber     = MemoryData(0xD35E, 0xD35E, "Current map number")

    EventDisplacement    = MemoryData(0xD35F, 0xD360, "Event displacement (see Notes)")

    PlayerYPos           = MemoryData(0xD361, 0xD361, "Current player Y position (pixels)")
    PlayerXPos           = MemoryData(0xD362, 0xD362, "Current player X position (pixels)")
    PlayerYBlock         = MemoryData(0xD363, 0xD363, "Current player Y position (block coordinate)")
    PlayerXBlock         = MemoryData(0xD364, 0xD364, "Current player X position (block coordinate)")
    LastMapLocation      = MemoryData(0xD365, 0xD365, "Last map location (for transitions like Safari Zone gate)")
    
    # Audio
    AudioChannel1        = MemoryData(0xC022, 0xC022, "Audio track channel 1")
    AudioChannel2        = MemoryData(0xC023, 0xC023, "Audio track channel 2")
    AudioChannel3        = MemoryData(0xC024, 0xC024, "Audio track channel 3")
    AudioChannel4        = MemoryData(0xC025, 0xC025, "Audio track channel 4")

    WaveChannelWavetable = MemoryData(0xC0E6, 0xC0E6, "Current wavetable in use by the wave channel (channel 3)")

    MusicTempo           = MemoryData(0xC0E8, 0xC0E9, "Music tempo (lower values in C0E9 = faster, except very low values)")
    SFXTempo             = MemoryData(0xC0EA, 0xC0EB, "Sound effects tempo")
    SFXHeaderPointer     = MemoryData(0xC0EC, 0xC0ED, "Sound effects header pointer")

    NewSoundID           = MemoryData(0xC0EE, 0xC0EE, "New sound ID")
    AudioBank1           = MemoryData(0xC0EF, 0xC0EF, "Audio bank (slot 1)")
    AudioBank2           = MemoryData(0xC0F0, 0xC0F0, "Audio bank (slot 2)")

    MapAudioTrack        = MemoryData(0xD35B, 0xD35B, "Audio track in current map")
    MapAudioBank         = MemoryData(0xD35C, 0xD35C, "Audio bank in current map")
    
    # Map header
    MapTileset          = MemoryData(0xD367, 0xD367, "Map's Tileset (1 byte)")
    MapHeight           = MemoryData(0xD368, 0xD368, "Map's Height in blocks (1 byte)")
    MapWidth            = MemoryData(0xD369, 0xD369, "Map's Width in blocks (1 byte)")
    MapDataPointer      = MemoryData(0xD36A, 0xD36B, "Pointer to Map's data")
    MapTextPtrTable     = MemoryData(0xD36C, 0xD36D, "Pointer to NPC text pointer table")
    MapLevelScriptPtr   = MemoryData(0xD36E, 0xD36F, "Pointer to Map's level script")
    MapConnectionByte   = MemoryData(0xD370, 0xD370, "Map's connection byte")
    MapConnection1      = MemoryData(0xD371, 0xD37B, "Map's 1st connection data")
    MapConnection2      = MemoryData(0xD37C, 0xD386, "Map's 2nd connection data")
    MapConnection3      = MemoryData(0xD387, 0xD391, "Map's 3rd connection data")
    MapConnection4      = MemoryData(0xD392, 0xD39C, "Map's 4th connection data")
    
    # Tileset Header
    TilesetBank        = MemoryData(0xD52B, 0xD52B, "Tileset bank")
    TilesetBlocksPtr   = MemoryData(0xD52C, 0xD52D, "Pointer to tileset blocks")
    TilesetGfxPtr      = MemoryData(0xD52E, 0xD52F, "Pointer to tileset graphics")
    TilesetCollisionPtr= MemoryData(0xD530, 0xD531, "Pointer to tileset collision data")
    TalkingOverTiles   = MemoryData(0xD532, 0xD534, "\"Talking-over\" tiles")
    GrassTile          = MemoryData(0xD535, 0xD535, "Grass tile ID")
    
    # Tiles grpahics
    TileGfx_PlayerTiles  = MemoryData(0x8000, 0x8FFF, "Tile graphics (0x8000–0x9000): 256 tiles (16 bytes each), used for player in all orientations and common elements")
    TileGfx_MapTiles     = MemoryData(0x9000, 0x95FF, "Tile graphics (0x9000–0x9600): Map tiles (16 bytes each, starting at tile 0 = blank)")

    # Example tile mapping explanation
    Tile0_PlayerTopLeft  = MemoryData(0x8000, 0x800F, "Tile 0 (16 bytes) – often the top-left of the player sprite")
    Tile1_PlayerTopRight = MemoryData(0x8010, 0x801F, "Tile 1 (16 bytes) – often the top-right of the player sprite")
    Tile2_PlayerBotLeft  = MemoryData(0x8020, 0x802F, "Tile 2 (16 bytes) – often the bottom-left of the player sprite")

    Tile0_Map            = MemoryData(0x9000, 0x900F, "Map Tile 0 (16 bytes) – often blank")
    Tile1_Map            = MemoryData(0x9010, 0x901F, "Map Tile 1 (16 bytes)")
    Tile2_Map            = MemoryData(0x9020, 0x902F, "Map Tile 2 (16 bytes)")
    
    # Stored Items
    StoredItem = MemoryData(0xD53A, 0xD59F, "Stored items (item ID + quantity, 2 bytes each, up to 50 items)")

    # Game CCoins
    coins = MemoryData(0xD5A4, 0xD5A5, "Game Corner coins (in cents)")
    
    # Events Flags    
    MissableObjectsFlags = MemoryData(0xD5A6, 0xD5C5, "Missable Objects Flags (dis/appearing sprites like guards or Pokéballs)")

    StartersBack         = MemoryData(0xD5AB, 0xD5AB, "Flag: are starters back?")
    MewtwoAppearFlag     = MemoryData(0xD5C0, 0xD5C0, "Bit 1: 0=Mewtwo appears, 1=Doesn't (see also D85F)")

    HaveTownMap          = MemoryData(0xD5F3, 0xD5F3, "Flag: have Town Map?")
    HaveOaksParcel       = MemoryData(0xD60D, 0xD60D, "Flag: have Oak's Parcel?")

    BikeSpeed            = MemoryData(0xD700, 0xD700, "Bike speed")
    FlyAnywhere1         = MemoryData(0xD70B, 0xD70B, "Fly Anywhere flag byte 1")
    FlyAnywhere2         = MemoryData(0xD70C, 0xD70C, "Fly Anywhere flag byte 2")
    SafariTime1          = MemoryData(0xD70D, 0xD70D, "Safari Zone time byte 1")
    SafariTime2          = MemoryData(0xD70E, 0xD70E, "Safari Zone time byte 2")
    FossilizedPokemon    = MemoryData(0xD710, 0xD710, "Which fossilized Pokémon obtained?")
    AirPosition          = MemoryData(0xD714, 0xD714, "Position in air")

    GotLapras            = MemoryData(0xD72E, 0xD72E, "Flag: did you get Lapras?")
    DebugNewGame         = MemoryData(0xD732, 0xD732, "Debug new game flag")

    FoughtGiovanni       = MemoryData(0xD751, 0xD751, "Flag: fought Giovanni yet?")
    FoughtBrock          = MemoryData(0xD755, 0xD755, "Flag: fought Brock yet?")
    FoughtMisty          = MemoryData(0xD75E, 0xD75E, "Flag: fought Misty yet?")
    FoughtLtSurge        = MemoryData(0xD773, 0xD773, "Flag: fought Lt. Surge yet?")
    FoughtErika          = MemoryData(0xD77C, 0xD77C, "Flag: fought Erika yet?")
    FoughtArticuno       = MemoryData(0xD782, 0xD782, "Flag: fought Articuno yet?")
    SafariGameOverFlag   = MemoryData(0xD790, 0xD790, "Flag: Safari Game over (if bit 7 set)")
    FoughtKoga           = MemoryData(0xD792, 0xD792, "Flag: fought Koga yet?")
    FoughtBlaine         = MemoryData(0xD79A, 0xD79A, "Flag: fought Blaine yet?")
    FoughtSabrina        = MemoryData(0xD7B3, 0xD7B3, "Flag: fought Sabrina yet?")
    FoughtZapdos         = MemoryData(0xD7D4, 0xD7D4, "Flag: fought Zapdos yet?")
    FoughtSnorlaxVermilion = MemoryData(0xD7D8, 0xD7D8, "Flag: fought Snorlax yet? (Vermilion)")
    FoughtSnorlaxCeladon   = MemoryData(0xD7E0, 0xD7E0, "Flag: fought Snorlax yet? (Celadon)")
    FoughtMoltres        = MemoryData(0xD7EE, 0xD7EE, "Flag: fought Moltres yet?")
    IsSSAnneHere         = MemoryData(0xD803, 0xD803, "Flag: is SS Anne still present?")

    MewtwoCatchableFlag  = MemoryData(0xD85F, 0xD85F, "Bit 2 clear = Mewtwo can be caught (requires D5C0 bit 1 clear too)")
    
    # Wild Pokemon
    WildEncounterRate    = MemoryData(0xD887, 0xD887, "Wild Pokémon encounter rate")

    # Common battles
    CommonEnc1Level      = MemoryData(0xD888, 0xD888, "Common encounter 1 - Level")
    CommonEnc1Pokemon    = MemoryData(0xD889, 0xD889, "Common encounter 1 - Pokémon ID")
    CommonEnc2Level      = MemoryData(0xD88A, 0xD88A, "Common encounter 2 - Level")
    CommonEnc2Pokemon    = MemoryData(0xD88B, 0xD88B, "Common encounter 2 - Pokémon ID")
    CommonEnc3Level      = MemoryData(0xD88C, 0xD88C, "Common encounter 3 - Level")
    CommonEnc3Pokemon    = MemoryData(0xD88D, 0xD88D, "Common encounter 3 - Pokémon ID")
    CommonEnc4Level      = MemoryData(0xD88E, 0xD88E, "Common encounter 4 - Level")
    CommonEnc4Pokemon    = MemoryData(0xD88F, 0xD88F, "Common encounter 4 - Pokémon ID")

    # Uncommon battles
    UncommonEnc1Level    = MemoryData(0xD890, 0xD890, "Uncommon encounter 1 - Level")
    UncommonEnc1Pokemon  = MemoryData(0xD891, 0xD891, "Uncommon encounter 1 - Pokémon ID")
    UncommonEnc2Level    = MemoryData(0xD892, 0xD892, "Uncommon encounter 2 - Level")
    UncommonEnc2Pokemon  = MemoryData(0xD893, 0xD893, "Uncommon encounter 2 - Pokémon ID")
    UncommonEnc3Level    = MemoryData(0xD894, 0xD894, "Uncommon encounter 3 - Level")
    UncommonEnc3Pokemon  = MemoryData(0xD895, 0xD895, "Uncommon encounter 3 - Pokémon ID")
    UncommonEnc4Level    = MemoryData(0xD896, 0xD896, "Uncommon encounter 4 - Level")
    UncommonEnc4Pokemon  = MemoryData(0xD897, 0xD897, "Uncommon encounter 4 - Pokémon ID")

    # Rare battles
    RareEnc1Level        = MemoryData(0xD898, 0xD898, "Rare encounter 1 - Level")
    RareEnc1Pokemon      = MemoryData(0xD899, 0xD899, "Rare encounter 1 - Pokémon ID")
    RareEnc2Level        = MemoryData(0xD89A, 0xD89A, "Rare encounter 2 - Level")
    RareEnc2Pokemon      = MemoryData(0xD89B, 0xD89B, "Rare encounter 2 - Pokémon ID")
    
    # Opponent Pokemon
    OpponentPartyCount   = MemoryData(0xD89C, 0xD89C, "Total number of opponent's Pokémon")
    OpponentPokemon1     = MemoryData(0xD89D, 0xD89D, "Opponent's Pokémon 1 ID")
    OpponentPokemon2     = MemoryData(0xD89E, 0xD89E, "Opponent's Pokémon 2 ID")
    OpponentPokemon3     = MemoryData(0xD89F, 0xD89F, "Opponent's Pokémon 3 ID")
    OpponentPokemon4     = MemoryData(0xD8A0, 0xD8A0, "Opponent's Pokémon 4 ID")
    OpponentPokemon5     = MemoryData(0xD8A1, 0xD8A1, "Opponent's Pokémon 5 ID")
    OpponentPokemon6     = MemoryData(0xD8A2, 0xD8A2, "Opponent's Pokémon 6 ID")
    OpponentPartyEnd     = MemoryData(0xD8A3, 0xD8A3, "End of opponent's Pokémon list marker")

    OpponentPokemons_Data = MemoryData(0xD8A4, 0xD9AB, "Opponent's Pokémon data blocks (27 bytes each, up to 6 Pokémon)")
    
    # Trainer name
    TrainerName1_Alt = MemoryData(0xD9AC, 0xD9B6, "Trainer name for 1st (alternate block)")
    TrainerName2_Alt = MemoryData(0xD9B7, 0xD9C1, "Trainer name for 2nd (alternate block)")
    TrainerName3_Alt = MemoryData(0xD9C2, 0xD9CC, "Trainer name for 3rd (alternate block)")
    TrainerName4_Alt = MemoryData(0xD9CD, 0xD9D7, "Trainer name for 4th (alternate block)")
    TrainerName5_Alt = MemoryData(0xD9D8, 0xD9E2, "Trainer name for 5th (alternate block)")
    TrainerName6_Alt = MemoryData(0xD9E3, 0xD9ED, "Trainer name for 6th (alternate block)")
    
    # Nickname
    Nickname1_Alt = MemoryData(0xD9EE, 0xD9F8, "Nickname for 1st Pokémon (alternate block)")
    Nickname2_Alt = MemoryData(0xD9F9, 0xDA03, "Nickname for 2nd Pokémon (alternate block)")
    Nickname3_Alt = MemoryData(0xDA04, 0xDA0E, "Nickname for 3rd Pokémon (alternate block)")
    Nickname4_Alt = MemoryData(0xDA0F, 0xDA19, "Nickname for 4th Pokémon (alternate block)")
    Nickname5_Alt = MemoryData(0xDA1A, 0xDA24, "Nickname for 5th Pokémon (alternate block)")
    Nickname6_Alt = MemoryData(0xDA25, 0xDA2F, "Nickname for 6th Pokémon (alternate block)")
    
    # ETC
    GameTimeHours    = MemoryData(0xDA40, 0xDA41, "Game time - Hours (2 bytes)")
    GameTimeMinutes  = MemoryData(0xDA42, 0xDA43, "Game time - Minutes (2 bytes)")
    GameTimeSeconds  = MemoryData(0xDA44, 0xDA44, "Game time - Seconds (1 byte)")
    GameTimeFrames   = MemoryData(0xDA45, 0xDA45, "Game time - Frames (1 byte)")
    SafariBalls      = MemoryData(0xDA47, 0xDA47, "Safari Balls remaining")
    
    # Stored Pokemon
    CurrentBoxCount   = MemoryData(0xDA80, 0xDA80, "Number of Pokémon in current box")
    CurrentBoxMons    = MemoryData(0xDA81, 0xDA94, "Pokémon in current box (slots 1–20)")
    CurrentBoxEnd     = MemoryData(0xDA95, 0xDA95, "End of current box list marker")

    Pokemons_in_box = MemoryData(0xDA96, 0xDD29, "All boxes' Pokémon (14 boxes of 20 Pokémon each = 280 total)")
    Trainer_names_boxes = MemoryData(0xDD2A, 0xDE05, "All boxes' trainer names (11 bytes each, 14 boxes of 20 Pokémon each = 280 total)")
    Nickname_boxes = MemoryData(0xDE06, 0xDEE1, "All boxes' nicknames (11 bytes each, 14 boxes of 20 Pokémon each = 280 total)")

class InternalPokemonData(DataType):
    OamDmaRoutine = MemoryData(0xFF80, 0xFF89, "OAM DMA routine")
    
    # Misc
    SoftResetCounter = MemoryData(0xFF8A, 0xFF8A, "Soft reset frame counter (init 16, decremented each frame START+SELECT+A+B held; reset when 0)")
    MoneyCoins       = MemoryData(0xFF9F, 0xFFA1, "Money/Coins amount (big-endian; FF9F=0 when holding coins amount)")
    
    # Serial
    SerialStatusData = MemoryData(0xFFA9, 0xFFAD, "Serial status data (sync method, etc.)")
    
    # Graphics scroll values
    VBlankSCX = MemoryData(0xFFAE, 0xFFAE, "Value copied to SCX at VBlank")
    VBlankSCY = MemoryData(0xFFAF, 0xFFAF, "Value copied to SCY at VBlank")
    VBlankWY  = MemoryData(0xFFB0, 0xFFB0, "Value copied to WY at VBlank")
    
    # Joypad
    JoypadPrevInput   = MemoryData(0xFFB1, 0xFFB1, "Joypad input during previous frame")
    JoypadReleased    = MemoryData(0xFFB2, 0xFFB2, "Released buttons on this frame")
    JoypadPressed     = MemoryData(0xFFB3, 0xFFB3, "Pressed buttons on this frame")
    JoypadHeld        = MemoryData(0xFFB4, 0xFFB4, "Held buttons on this frame")
    JoypadLowSensitivity   = MemoryData(0xFFB5, 0xFFB5, "Low-sensitivity joypad output (controlled by FFB6 and FFB7)")
    JoypadConfigFFB6       = MemoryData(0xFFB6, 0xFFB6, "Joypad config: if 0 and A/B held, outputs nothing; else long presses counted as 12/s. Ignored if FFB7=0")
    JoypadConfigFFB7       = MemoryData(0xFFB7, 0xFFB7, "Joypad config: if 0, FFB5 contains newly-pressed buttons only")
    
    # ROM Banking
    LoadedROMBank = MemoryData(0xFFB8, 0xFFB8, "Currently loaded ROM bank")
    SavedROMBank  = MemoryData(0xFFB9, 0xFFB9, "Saved ROM bank")
    
    # VBlank data transfer
    BgTransferEnable      = MemoryData(0xFFBA, 0xFFBA, "Transfer background to VRAM during VBlank?")
    BgTransferPortion     = MemoryData(0xFFBB, 0xFFBB, "Which portion of the screen to transfer? (0=top, 1=middle, 2=bottom)")
    BgCopyDest1           = MemoryData(0xFFBC, 0xFFBD, "Background copy destination (low-endian address, not including FFBB offset)")
    StackPointerSave      = MemoryData(0xFFBF, 0xFFC0, "Saved stack pointer")
    BgCopySource1         = MemoryData(0xFFC1, 0xFFC2, "Background copy source (low-endian address, FFBA copied to LSB)")
    BgCopyDest2           = MemoryData(0xFFC3, 0xFFC4, "Background copy destination (low-endian address)")
    BgCopyNumRows         = MemoryData(0xFFC5, 0xFFC5, "Number of rows to copy")
    BgCopyUnits16         = MemoryData(0xFFC6, 0xFFC6, "Number of 16-byte units to copy during VBlank")
    BgCopySource2         = MemoryData(0xFFC7, 0xFFC8, "Background copy source (low-endian address)")
    BgCopyDest3           = MemoryData(0xFFC9, 0xFFCA, "Background copy destination (low-endian address)")
    BgCopyUnits8          = MemoryData(0xFFCB, 0xFFCB, "Number of 8-byte units to copy during VBlank")
    BgCopySource3         = MemoryData(0xFFCC, 0xFFCD, "Background copy source (low-endian address)")
    BgCopyDest4           = MemoryData(0xFFCE, 0xFFCF, "Background copy destination (low-endian address)")
    
    # VBlank 2x2 tile block redraw
    RedrawMode       = MemoryData(0xFFD0, 0xFFD0, "What to redraw (0=Nothing, 1=Column, 2=Row)")
    RedrawDest       = MemoryData(0xFFD1, 0xFFD2, "Redraw destination address (low-endian)")
    
    # RNG
    RandomAdd = MemoryData(0xFFD3, 0xFFD3, "Random number generator - Add value")
    RandomSub = MemoryData(0xFFD4, 0xFFD4, "Random number generator - Sub value")
            
    # VBlank interface
    VBlankFrameCounter = MemoryData(0xFFD5, 0xFFD5, "Frame counter (decremented each VBlank)")
    VBlankFlag         = MemoryData(0xFFD6, 0xFFD6, "Set to 0 when a VBlank occurs")
    
    # MISC 2
    TilesetType        = MemoryData(0xFFD7, 0xFFD7, "Tileset type (0=indoors, 1=cave, 2=outside). Nonzero=water anim, 2=flower anim")
    BattleTurn         = MemoryData(0xFFF3, 0xFFF3, "Battle turn (0=player, 1=opponent)")
    JoypadInput        = MemoryData(0xFFF8, 0xFFF8, "Joypad input")
    JoypadPollingFlag  = MemoryData(0xFFF9, 0xFFF9, "Disable joypad polling flag")


        


# ... (tes imports existants)
# from data.pokemon import Pokemon  # Importé dans la fonction pour éviter les cycles

class SavedPokemonData(DataType):
    # --- tes MemoryData existants ici ---
    # Exemple (remplace par ton vrai champ) :
    # Pokemon1SlotBattle = MemoryData(0xD16B, 0xD192, "First Pokémon battle block")

    @staticmethod
    def start_pokemon_logger(pyboy, pokemon_md: MemoryData, interval_sec: int = 60):
        """
        Lance un thread qui logge les infos du Pokémon défini par 'pokemon_md' toutes les 'interval_sec' secondes.
        Retourne le thread (daemon).
        """
        # Déterminer Yellow dynamiquement si possible
        is_yellow_flag = False
        try:
            gv = getattr(pyboy, "game_version", None)
            is_yellow_flag = bool(getattr(gv, "is_yellow", False))
        except Exception:
            pass

        def _worker():
            # Import tardif pour éviter import-cycles (pokemon -> ram_reader)
            from data.pokemon import Pokemon
            while True:
                try:
                    mon = Pokemon.from_memory(pyboy, pokemon_md, is_yellow=is_yellow_flag)
                    # __str__ de ta classe Pokemon est déjà propre ; on logge la ligne lisible
                    logger.info(str(mon))
                except Exception as e:
                    logger.exception(f"[PokemonLogger] failure: {e}")
                time.sleep(interval_sec)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t