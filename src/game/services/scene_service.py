"""Service responsible for publishing scene updates over MQTT."""
from __future__ import annotations

import time
from typing import Optional

from game.core.emulator import EmulatorSession
from game.data.ram_reader import MainPokemonData
from game.mqtt.client import MQTTClient
from game.mqtt.topics import BATTLE_INFO_TOPIC, START_TOPIC
from game.scenes.battle_scene import create_battle_scene, BattleScene
from game.utils.json_utils import to_json
from game.utils.time_utils import has_expired, seconds_from_now


class SceneService:
    def __init__(self, session: EmulatorSession, mqtt_client: MQTTClient, logger, poll_interval: float = 2.0):
        self.session = session
        self.mqtt = mqtt_client
        self.logger = logger
        self.poll_interval = poll_interval
        self._next_poll_at = seconds_from_now(self.poll_interval)
        self._scene: Optional[BattleScene] = None
        self._last_turn = -1

    def start(self) -> None:
        self.logger.debug("Scene service starting")
        payload = to_json({"msg": "hello from PKM", "timestamp": time.time()})
        self.mqtt.publish(START_TOPIC, payload, retain=False)
        self._next_poll_at = seconds_from_now(self.poll_interval)

    def tick(self, now: float) -> None:
        if not has_expired(self._next_poll_at, clock=lambda: now):
            return
        try:
            self._poll_scene(now)
        except Exception as exc:  # pragma: no cover - safety net
            self.logger.exception("Error while polling scene: {}", exc)
        finally:
            self._next_poll_at = seconds_from_now(self.poll_interval, clock=lambda: now)

    # ------------------------------------------------------------------
    def _poll_scene(self, now: float) -> None:
        data = self.session.read_memory(MainPokemonData.BattleTypeID)
        if not data:
            return
        battle_id = data[0]

        if battle_id > 0:
            if self._scene is None or self._scene.battle_id != battle_id:
                self.logger.info("Battle started with ID {}", battle_id)
                self._scene = create_battle_scene(self.session, battle_id)
                self._last_turn = -1

            self._scene.update()
            turn = self._scene.turn_counter
            if turn == self._last_turn:
                return
            self._last_turn = turn

            payload = {
                "battle_id": battle_id,
                "turn": turn,
                "timestamp": time.time(),
                "scene": self._scene.to_dict(),
            }
            self.mqtt.publish(BATTLE_INFO_TOPIC, to_json(payload), retain=True)
            self.logger.info("Published battle update for turn {}", turn)
        else:
            if self._scene is not None:
                self.logger.info("Battle ended")
            self._scene = None
            self._last_turn = -1

    @property
    def current_scene(self) -> Optional[BattleScene]:
        return self._scene


__all__ = ["SceneService"]
