
from data.pokemon import  POKEMON_TYPES
from dataclasses import dataclass
from data.helpers import select_rom_bank
from data.decoder import decode_pkm_text


def find_index(li : list, number,max_occ=999999):
    try:
        if max_occ == 0:
            return 0
        idx = li.index(number)
        max_occ -=1
        return idx + 1 + find_index(li[idx+1:],number,max_occ)
    except ValueError:
        return 0

# --- Find start of the Nth (1-based) 0x50-terminated string in the *current* bank
def _move_name_ptr_current_bank(pyboy, move_id: int, table_base: int = 0x4000) -> int:
    """
    Return a pointer (address) to the start of the Nth move name in the
    *currently selected* ROM bank. No bank selection here.
    - move_id: 1-based (0 => empty slot).
    - table_base: where the concatenated names start (0x4000 in this bank).
    """
    if move_id <= 0:
        return -1  # empty / NA
    idx = find_index(pyboy.memory[0x4000:0x460F],0x50,move_id-1)
    
    return  idx   # now at the first byte of the requested name

# --- Read+decode one move name from the *current* bank (no constants, no bank switch)
def _read_move_name_current_bank(pyboy, move_id: int, table_base: int = 0x4000, cap: int = 24) -> str:
    """
    Decode the move name at the current bank using only the ID:
    - Walk to the Nth string via terminators, then read a small window.
    - Your decode_pkm_text() stops at 0x50, so 'cap' is just a safe upper bound.
    """
    if move_id == 0:
        return "NA"
    start = _move_name_ptr_current_bank(pyboy, move_id, table_base=table_base)
    if start < 0:
        return "NA"
    raw = pyboy.memory[0x4000+start:0xB060F]
    return decode_pkm_text(raw, stop_at_terminator=True)


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

@dataclass
class Move:
    def __init__(self):
        self.name = "Unknown"
        self.id = -1
        self._effect = -1
        self.power = -1
        self._type = -1
        self._accuracy = -1
        self.pp = -1
        return
    
    @staticmethod
    def load_from_id(pyboy, id : int):
        if id > 0x56:
            raise ValueError("id must be contained in [0x0:0x56]")
        
        select_rom_bank(pyboy,0xE)
        new_move = Move.load_from_bytes(pyboy.memory[0x4000+(id-1)*6:0x4000+id*6])

        select_rom_bank(pyboy,0x2C)
        new_move.name = _read_move_name_current_bank(pyboy, new_move.id)

        return new_move


    @staticmethod
    def load_from_bytes(li : list) :
        new_move = Move()
        new_move.id = li[0]
        new_move._effect = li[1]
        new_move.power = li[2]
        new_move._type = li[3]
        new_move._accuracy = li[4]
        new_move.pp = li[5]
        return new_move


    @property
    def effect(self):
        return FUNCTION_CODE_EFFECT.get(self._effect, "(undefined effect – game crash)")
    
    @property
    def type(self):
        return POKEMON_TYPES.get(self._type, "Unknown")

    @property
    def accuracy(self):
        return self._accuracy/255*100
    
    def __str__(self):
        return """
    "name": {},
    "id" : {},
    "effect" : {},
    "power" : {},
    "type": {},
    "accuracy" : {},
    "pp" : {}

        """.format(self.name,self.id,self.effect,self.power,self.type,self.accuracy,self.pp)