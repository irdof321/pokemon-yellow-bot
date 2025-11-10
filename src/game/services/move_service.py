"""Service listening to move commands over MQTT."""
from __future__ import annotations

import json

from game.mqtt.client import MQTTClient
from game.mqtt.topics import BATTLE_MOVE_TOPIC
from game.services.scene_service import SceneService
from game.services.service import Service


class MoveService(Service):
    def __init__(self, scene_service: SceneService, mqtt_client: MQTTClient, logger):
        self.scene_service = scene_service
        self.mqtt = mqtt_client
        self.logger = logger

    def start(self) -> None:
        self.logger.debug("Subscribing to move commands")
        self.mqtt.subscribe(BATTLE_MOVE_TOPIC, handler=self._on_move_message)

    def tick(self, now: float) -> None:
        # Move service is event-driven; nothing to do per tick.
        return

    # ------------------------------------------------------------------
    def _on_move_message(self, topic: str, payload: str) -> None:
        self.logger.info("Received move command: {}", payload)
        try:
            message = json.loads(payload)
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON payload for move command")
            return

        move_index = message.get("move_nb")
        if move_index is None:
            self.logger.warning("Move command missing 'move_nb'")
            return

        scene = self.scene_service.current_scene
        if scene is None:
            self.logger.warning("Received move command but no battle is active")
            return

        try:
            scene.use_move(int(move_index))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to queue move: {}", exc)


__all__ = ["MoveService"]
