"""Confirms BattleScene.to_dict() correctly decodes status conditions from
real RAM -- no button-driving needed, just a snapshot read compared against
the fixture's recorded ground truth.
"""
import json
from pathlib import Path

from game.scenes.battle_scene import create_battle_scene

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _expected(state_name: str) -> dict:
    json_path = FIXTURES_DIR / (Path(state_name).stem + ".json")
    return json.loads(json_path.read_text(encoding="utf-8"))["expected"]


def test_player_active_poisoned(load_fixture):
    state_name = "battle_pokemon_1_player_psn.state"
    session = load_fixture(state_name)
    scene = create_battle_scene(session, 0)

    on_battle = scene.to_dict()["on_battle"]
    assert on_battle["status"] == _expected(state_name)["on_battle"]["status"]
    assert on_battle["status"] == ["Poisoned"]


def test_enemy_paralyzed(load_fixture):
    state_name = "wild_ratatta_par.state"
    session = load_fixture(state_name)
    scene = create_battle_scene(session, 0)

    enemy = scene.to_dict()["enemy"]
    assert enemy["status"] == _expected(state_name)["enemy"]["status"]
    assert enemy["status"] == ["Paralyzed"]
