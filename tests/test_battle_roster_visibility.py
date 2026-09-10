"""Confirms BattleScene.to_dict() sees the real party + full opponent roster
(trainer battle) -- no button-driving needed, just a snapshot read compared
against the fixture's recorded ground truth.
"""
import json
from pathlib import Path

from game.scenes.battle_scene import create_battle_scene

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_party_and_enemy_roster_match_fixture(load_fixture):
    state_name = "battle_vs_blue_player_1pkm.state"
    fixture = json.loads((FIXTURES_DIR / "battle_vs_blue_player_1pkm.json").read_text(encoding="utf-8"))
    expected = fixture["expected"]

    session = load_fixture(state_name)
    scene = create_battle_scene(session, 0)
    d = scene.to_dict()

    assert [p["name"] for p in d["party"]] == [p["name"] for p in expected["party"]]
    assert [p["name"] for p in d["party"]] == ["Charmander"]

    assert [p["name"] for p in d["enemy_party"]] == [p["name"] for p in expected["enemy_party"]]
    assert [p["name"] for p in d["enemy_party"]] == ["Pidgey", "Squirtle"]

    assert d["battle_type"] == fixture["battle_type"]  # "battle_type" is a top-level key, sibling of "expected"
