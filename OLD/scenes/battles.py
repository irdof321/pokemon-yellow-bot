from dataclasses import dataclass
from enum import Enum
from threading import Thread
import threading
from time import sleep
from data.data import GBAButton
from data.helpers import read_u8_mem
from data.menu import get_menu_state
from data.pokemon import PartyPokemon, EnemyPokemon, PlayerPokemonBattle, read_u8
from data.ram_reader import MainPokemonData, SavedPokemonData


BATTLE_STATUS_LAYOUT = {
    # ===============================
    # PLAYER STATUS FLAGS
    # ===============================

    "player_status_1": {
        "address": (0xD062, 0xD063),
        "bits": {
            0: "Bide",
            1: "Thrash / Petal Dance",
            2: "Attacking multiple times (e.g. Double Kick)",
            3: "Flinch",
            4: "Charging up for attack",
            5: "Using multi-turn move (e.g. Wrap)",
            6: "Invulnerable to normal attack (Fly/Dig)",
            7: "Confused",
        },
    },

    "player_status_2": {
        "address": (0xD063, 0xD064),
        "bits": {
            0: "X Accuracy effect active",
            1: "Protected by Mist",
            2: "Focus Energy active",
            3: None,  # unused
            4: "Has Substitute",
            5: "Needs to recharge (after Hyper Beam etc.)",
            6: "Rage active",
            7: "Leech Seeded",
        },
    },

    "player_status_3": {
        "address": (0xD064, 0xD065),
        "bits": {
            0: "Toxic active",
            1: "Light Screen active",
            2: "Reflect active",
            3: "Transformed (Ditto)",
        },
    },

    # ===============================
    # CPU STATUS FLAGS
    # ===============================

    "cpu_status_1": {
        "address": (0xD067, 0xD068),
        "bits": {
            0: "Bide",
            1: "Thrash / Petal Dance",
            2: "Attacking multiple times",
            3: "Flinch",
            4: "Charging up for attack",
            5: "Using multi-turn move",
            6: "Invulnerable (Fly/Dig)",
            7: "Confused",
        },
    },

    "cpu_status_2": {
        "address": (0xD068, 0xD069),
        "bits": {
            0: "X Accuracy effect active",
            1: "Protected by Mist",
            2: "Focus Energy active",
            3: None,
            4: "Has Substitute",
            5: "Needs to recharge",
            6: "Rage active",
            7: "Leech Seeded",
        },
    },

    "cpu_status_3": {
        "address": (0xD069, 0xD06A),
        "bits": {
            0: "Toxic active",
            1: "Light Screen active",
            2: "Reflect active",
            3: "Transformed (Ditto)",
        },
    },

    # ===============================
    # PLAYER COUNTERS
    # ===============================

    "player_multi_hit_counter": {
        "address": (0xD06A, 0xD06B),
        "description": "Counts hits for multi-hit moves (Double Kick, etc.)",
    },
    "player_confusion_counter": {
        "address": (0xD06B, 0xD06C),
        "description": "Counts remaining turns of confusion",
    },
    "player_toxic_counter": {
        "address": (0xD06C, 0xD06D),
        "description": "Counts Toxic damage accumulation",
    },
    "player_disable_counter": {
        "address": (0xD06D, 0xD06F),
        "description": "Duration of Disable effect",
    },

    # ===============================
    # CPU COUNTERS
    # ===============================

    "cpu_multi_hit_counter": {
        "address": (0xD06F, 0xD070),
        "description": "Counts hits for multi-hit moves (CPU)",
    },
    "cpu_confusion_counter": {
        "address": (0xD070, 0xD071),
        "description": "Counts remaining turns of confusion (CPU)",
    },
    "cpu_toxic_counter": {
        "address": (0xD071, 0xD072),
        "description": "Counts Toxic damage accumulation (CPU)",
    },
    "cpu_disable_counter": {
        "address": (0xD072, 0xD073),
        "description": "Duration of Disable effect (CPU)",
    },

    # ===============================
    # CPU STAT MODIFIERS
    # ===============================

    "cpu_double_stat": {
        "address": (0xD065, 0xD066),
        "description": "Stat to double for CPU",
    },
    "cpu_half_stat": {
        "address": (0xD066, 0xD067),
        "description": "Stat to halve for CPU",
    },
}


BATTLE_INFO = {
    #=============================
    #           PLAYER
    #=============================

    "player":
    {
        "pv" : 00,
        
    }
}

class MENU_STATE(Enum) :
    MAIN_MENU_LEFT = (9,14)
    MAIN_MENU_RIGHT = (15,14)
    MOVES_SELECTION = (5,12)
    POKEMON_SELECTION = (0,1)
    POKEMON_SUB_MENU = (12,12)


class BattleScene:
    game = None
    

    def __init__(self,pyboy):
        BattleScene.game = pyboy
        self.counter_main_menu = 0
        
    def get_slected_move(self) -> int:
        return get_menu_state().selected_item_id
        

    def _add_down_button(self,n):
        for i in range(n):
            BattleScene.game.button(GBAButton.DOWN)

    def _add_up_button(self,n):
        for i in range(n):
            BattleScene.game.button(GBAButton.UP)


    def go_to_main_menu(self):
        if not self.is_in_battle_main_menu():
            self.counter_main_menu += 1
            if self.game.btn_event_list.size() == 0:
                BattleScene.game.button(GBAButton.A)
            threading.Timer(1, self.go_to_main_menu, args=()).start()
        else:
            self.counter_main_menu = 0
        if self.counter_main_menu > 10:
            return

    def use_move(self,n):
            threading.Timer(1, self._use_move, args=(n,)).start()

    def _use_move(self,n):
        if not self.is_in_battle_main_menu():
            threading.Timer(1, self._use_move, args=(n,)).start()
        BattleScene.game.button(GBAButton.A)
        n_to_move = self.get_slected_move() - n 
        if n_to_move > 0 :
            self._add_up_button(n_to_move-1)
        elif n_to_move < 0:
            self._add_down_button(abs(n_to_move+1))
        BattleScene.game.button(GBAButton.A)


    def get_menu_pos(self):
        x = read_u8_mem(MainPokemonData.MenuCursorXPos)
        y = read_u8_mem(MainPokemonData.MenuCursorYPos)
        return (x,y)
    
    def is_in_battle_main_menu(self):
        return get_menu_state().cursor_pos_top in [MENU_STATE.MAIN_MENU_LEFT.value, MENU_STATE.MAIN_MENU_RIGHT.value]
            


        

@dataclass
class NormalBattle(BattleScene):
    def __init__(self, pyboy):
        super().__init__(pyboy) 
        md = MainPokemonData.get_main_pkm_for_party_slot(1)
        self.pokemon_player_parties = []
        for i in range(1,7):
            self.pokemon_player_parties.append(PartyPokemon(pyboy,i,False))
        self.player_pokemon_battle = PlayerPokemonBattle(pyboy, False)
        self.opponent_pokemon_party = EnemyPokemon(pyboy)
        super().__init__(pyboy)

    @property
    def battle_turn(self):
        return read_u8(SavedPokemonData.get_data(self.game,MainPokemonData.BattleTurnCounter))


    def str_print_enemy_PKM(self) -> str:
        return str(self.opponent_pokemon_party)
    
    def __str__(self) -> str:
        msg = f"\nBattle turn : {self.battle_turn}\n"
        msg += "=============================\n"
        msg += f"Player Pokemon in Party : \n"
        for p in self.pokemon_player_parties:
            msg += f"----------------\n"
            msg += f"\t {p} \n"

        msg += "=============================\n"
        msg += f"Enemy Pokemon in Party : \n{self.opponent_pokemon_party}"
        return msg
    
    def to_dict(self):
        # Choose the correct bank
        return {
            "ennemyPKM" : self.opponent_pokemon_party.to_dict(),
            "playerPKM" : self.player_pokemon_battle.to_dict(),
            "battle_turn" : self.battle_turn 
        }
    
        
    

class SafariBattle(BattleScene):
    pass

class WildBatlleScene(BattleScene):
    pass


active_scene = None

def get_battle_scene(pyboy,battle_id) -> BattleScene:
    
    if battle_id in [1,2]:
        if active_scene is None:
            return NormalBattle(pyboy)
        else:
            return active_scene



