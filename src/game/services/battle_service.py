"""Service listening to battle commands over MQTT and enqueueing them to the active battle scene."""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from game.mqtt.client import MQTTClient
from game.mqtt.topics import BATTLE_MOVE_TOPIC
from game.scenes.common import BATTLE_ACTION, str_to_battle_action
from game.scenes.commands import BattleCommand
from game.services.service import Service


class BattleService(Service):
    """
    Receives battle commands over MQTT, validates/parses them, and forwards them to the
    currently active battle scene via enqueue_command().

    Expected payload (example):
    {
      "action": "move",
      "choice": 2
    }
    """

    def __init__(self, mqtt_client: MQTTClient, logger, scene_provider):
        self.mqtt = mqtt_client
        self.logger = logger
        self.scene_provider = scene_provider  # must expose .current_scene

    def start(self) -> None:
        self.logger.debug("BattleService starting - subscribing to {}", BATTLE_MOVE_TOPIC)
        self.mqtt.subscribe(BATTLE_MOVE_TOPIC, handler=self._on_battle_message)

    def tick(self, now: float) -> None:
        # Event-driven (MQTT callback); nothing to do per tick.
        return

    # ------------------------------------------------------------------
    def _on_battle_message(self, topic: str, payload: str) -> None:
        self.logger.info("Received battle command: {}", payload)

        msg = self._parse_json(payload)
        if msg is None:
            return

        battle_action = self._parse_action(msg)
        if battle_action is None:
            return

        cmd = self._build_command(battle_action, msg)
        if cmd is None:
            return

        scene = self._get_current_scene()
        if scene is None:
            self.logger.warning("No active battle scene. Command ignored.")
            return

        if not hasattr(scene, "enqueue_command"):
            self.logger.warning("Current scene does not support enqueue_command (type={})", type(scene))
            return

        try:
            scene.enqueue_command(cmd)
            self.logger.info("Enqueued battle command: {}", cmd)
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Failed to enqueue battle command: {}", exc)

    # ------------------------------------------------------------------
    def _parse_json(self, payload: str) -> Optional[dict]:
        try:
            msg = json.loads(payload)
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON payload")
            return None

        if not isinstance(msg, dict):
            self.logger.warning("Battle command payload must be a JSON object")
            return None

        return msg

    def _parse_action(self, msg: dict) -> Optional[Any]:
        action = msg.get("action")
        if not action:
            self.logger.warning("Battle command missing 'action'")
            return None

        battle_action = str_to_battle_action(action)
        if battle_action is None:
            self.logger.warning("Unknown battle action: {}", action)
            return None

        return battle_action

    def _build_command(self, battle_action: BATTLE_ACTION, msg: dict) -> Optional[BattleCommand]:
        """
        Converts parsed payload into a BattleCommand.

        Currently supports only 'move' -> BattleCommand(kind="move", move_index=..., created_at=...).
        """
        action_name = getattr(battle_action, "name", str(battle_action)).lower()

        if action_name != "move":
            self.logger.warning("Action '{}' not supported yet (only 'move' is supported).", action_name)
            return None

        choice = msg.get("choice", None)
        if choice is None:
            self.logger.warning("Move command missing 'choice'")
            return None

        try:
            move_index = int(choice)
        except (TypeError, ValueError):
            self.logger.warning("Invalid move 'choice': {}", choice)
            return None

        if move_index < 1:
            self.logger.warning("Invalid move_index (<1): {}", move_index)
            return None

        # Your BattleScene converts 1-based to 0-based internally.
        return BattleCommand(kind="move", move_index=move_index, created_at=time.time())

    def _get_current_scene(self):
        provider = self.scene_provider
        if provider is None or not hasattr(provider, "current_scene"):
            self.logger.warning("scene_provider is missing or does not expose current_scene")
            return None
        return provider.current_scene


__all__ = ["BattleService"]
