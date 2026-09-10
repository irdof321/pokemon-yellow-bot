"""Tests for the new 'switch' command path -- pure logic, no PyBoy/fixtures.
"""
from dataclasses import dataclass

from game.scenes.battle_scene import filter_eligible_switch_slots
from game.scenes.common import BATTLE_ACTION
from game.services.battle_service import BattleService


class NullLogger:
    def warning(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass


@dataclass
class FakePartyMember:
    slot: int
    current_hp: int


def _service() -> BattleService:
    return BattleService(mqtt_client=None, logger=NullLogger(), scene_provider=None)


# --- filter_eligible_switch_slots -------------------------------------------------

def test_excludes_fainted_and_active_slot():
    party = [
        FakePartyMember(slot=1, current_hp=20),  # active
        FakePartyMember(slot=2, current_hp=0),   # fainted
        FakePartyMember(slot=3, current_hp=15),  # eligible
    ]
    assert filter_eligible_switch_slots(party, active_slot=1) == [3]


def test_all_alive_and_none_active_are_eligible():
    party = [FakePartyMember(slot=i, current_hp=10) for i in range(1, 4)]
    assert filter_eligible_switch_slots(party, active_slot=None) == [1, 2, 3]


def test_no_eligible_slots_when_only_active_is_alive():
    party = [
        FakePartyMember(slot=1, current_hp=20),  # active
        FakePartyMember(slot=2, current_hp=0),
    ]
    assert filter_eligible_switch_slots(party, active_slot=1) == []


# --- BattleService._build_command('pkm') ------------------------------------------

def test_build_command_pkm_valid_choice():
    cmd = _service()._build_command(BATTLE_ACTION.PKM, {"action": "pkm", "choice": 3})
    assert cmd is not None
    assert cmd.kind == "switch"
    assert cmd.party_slot == 3
    assert cmd.move_index is None


def test_build_command_pkm_missing_choice():
    assert _service()._build_command(BATTLE_ACTION.PKM, {"action": "pkm"}) is None


def test_build_command_pkm_non_int_choice():
    assert _service()._build_command(BATTLE_ACTION.PKM, {"action": "pkm", "choice": "abc"}) is None


def test_build_command_pkm_out_of_range_choice():
    assert _service()._build_command(BATTLE_ACTION.PKM, {"action": "pkm", "choice": 7}) is None
    assert _service()._build_command(BATTLE_ACTION.PKM, {"action": "pkm", "choice": 0}) is None
