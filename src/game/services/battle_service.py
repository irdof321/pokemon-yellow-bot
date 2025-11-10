"""Service listening to move commands over MQTT."""
from __future__ import annotations

import json

from game.mqtt.client import MQTTClient
from game.mqtt.topics import BATTLE_MOVE_TOPIC
from game.scenes.common import str_to_battle_action
from game.services.scene_service import SceneService
from game.services.service import Service


class BattleService(Service):
    def __init__(self, scene_service: SceneService, mqtt_client: MQTTClient, logger):
        self.scene_service = scene_service
        self.mqtt = mqtt_client
        self.logger = logger

    def start(self) -> None:
        self.logger.debug("Subscribing to move commands")
        self.mqtt.subscribe(BATTLE_MOVE_TOPIC, handler=self._on_battle_message)

    def tick(self, now: float) -> None:
        # Move service is event-driven; nothing to do per tick.
        return

    # ------------------------------------------------------------------
    def _on_battle_message(self, topic: str, payload: str) -> None:
        """
        type of message :
        {
            action: <action>,
            choice: <choice>
        }

        for <action> = 
            1. "move" choice must be a number between 1 and 4 included.
            2. "item" choice  must be .... TODO
            3. "pkm" choice must be a number between 1 and 6 included.
            4. "run" choice is not used.
        """
        self.logger.info("Received move command: {}", payload)
        try:
            message = json.loads(payload)
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON payload for move command")
            return

        action = message.get("action")
        if action is None:
            self.logger.warning("Action command missing 'action'")
            return
        
        battle_action = str_to_battle_action(action)

        scene = self.scene_service.current_scene
        if scene is None:
            self.logger.warning("Received battle action command but no battle is active")
            return

        try:
            scene.use_action(battle_action,message.get("choice"),None)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to queue move: {}", exc)


__all__ = ["BattleService"]
