"""BattleCommand shape regression tests -- no PyBoy/fixtures involved.
Guards against the dataclass-default change made when adding kind="switch"
(move_index becoming Optional) silently breaking the existing move path.
"""
from game.scenes.commands import BattleCommand
from game.scenes.common import str_to_battle_action, BATTLE_ACTION


def test_move_command_still_constructs_with_only_move_index():
    cmd = BattleCommand(kind="move", move_index=1)
    assert cmd.move_index == 1
    assert cmd.party_slot is None


def test_switch_command_constructs_with_only_party_slot():
    cmd = BattleCommand(kind="switch", party_slot=3)
    assert cmd.party_slot == 3
    assert cmd.move_index is None


def test_each_command_gets_its_own_done_event():
    a = BattleCommand(kind="move", move_index=1)
    b = BattleCommand(kind="move", move_index=1)
    assert a.done_event is not b.done_event
    assert not a.done_event.is_set()


def test_str_to_battle_action_resolves_pkm():
    assert str_to_battle_action("pkm") == BATTLE_ACTION.PKM
    assert str_to_battle_action("PKM") == BATTLE_ACTION.PKM
