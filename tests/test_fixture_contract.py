"""Validates that every tests/fixtures/*.json file honors the unified
BattleScene.to_dict() contract: enemy_party is always a list (or null when
no Pokemon is on screen yet), sized 1 for wild battles and 1-6 for trainer
battles. Pure data validation -- no PyBoy/ROM involved.
"""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_files():
    return sorted(p for p in FIXTURES_DIR.glob("*.json") if not p.name.startswith("_"))


@pytest.mark.parametrize("path", _fixture_files(), ids=lambda p: p.stem)
def test_battle_type_is_known(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    battle_type = data.get("battle_type")
    assert battle_type in ("wild", "trainer"), (
        f"{path.name}: battle_type must be 'wild' or 'trainer', got {battle_type!r}"
    )


@pytest.mark.parametrize("path", _fixture_files(), ids=lambda p: p.stem)
def test_enemy_party_shape_matches_battle_type(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = data["expected"]
    enemy_party = expected.get("enemy_party")

    if expected.get("enemy") is None:
        # Battle hasn't progressed far enough to show any Pokemon yet
        # (e.g. battle_start_must_go_to_menu.json) -- enemy_party must
        # stay null too, not an empty/guessed list.
        assert enemy_party is None, (
            f"{path.name}: enemy is null but enemy_party is not -- "
            "don't guess a roster before any Pokemon has been shown"
        )
        return

    assert isinstance(enemy_party, list), f"{path.name}: enemy_party must be a list"
    assert len(enemy_party) >= 1, f"{path.name}: enemy_party must not be empty"

    if data["battle_type"] == "wild":
        assert len(enemy_party) == 1, (
            f"{path.name}: wild battles must have exactly 1 enemy_party entry, "
            f"got {len(enemy_party)}"
        )
        assert enemy_party[0] == expected["enemy"], (
            f"{path.name}: for a wild battle, enemy_party[0] must mirror 'enemy' exactly"
        )
    else:  # trainer
        assert 1 <= len(enemy_party) <= 6, (
            f"{path.name}: trainer battles must have 1-6 enemy_party entries, "
            f"got {len(enemy_party)}"
        )
