"""Constants describing the MQTT topics used by the application."""
from __future__ import annotations

BASE_TOPIC = "/dforirdod/PKM/"
BATTLE_INFO_TOPIC = f"{BASE_TOPIC}battle/info"
BATTLE_MOVE_TOPIC = f"{BASE_TOPIC}battle/move"
START_TOPIC = f"{BASE_TOPIC}start"
STATUS_TOPIC = f"{BASE_TOPIC}status"

__all__ = [
    "BASE_TOPIC",
    "BATTLE_INFO_TOPIC",
    "BATTLE_MOVE_TOPIC",
    "START_TOPIC",
    "STATUS_TOPIC",
]
