from enum import Enum


class BATTLE_ACTION(Enum):
    MOVE  = 0
    ITEM    = 1
    PKM     = 2
    RUN     = 3

def str_to_battle_action(value: str) -> BATTLE_ACTION | None:
    value = value.replace("BATTLE_ACTION.", "").upper()
    return next((a for a in BATTLE_ACTION if a.name == value), None)