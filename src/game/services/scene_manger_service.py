"""Service responsible for publishing scene updates over MQTT."""
from __future__ import annotations

import time
from typing import Optional

from game.core.emulator import EmulatorSession
from game.data.ram_reader import MainPokemonData
from game.mqtt.client import MQTTClient
from game.mqtt.topics import BATTLE_INFO_TOPIC, START_TOPIC
from game.scenes.battle_scene import create_battle_scene, BattleScene
from game.services.service import Service
from game.utils.json_utils import to_json
from game.utils.time_utils import has_expired, seconds_from_now


class SceneManagerService(Service):
    def __init__(
        self,
        session: EmulatorSession,
        mqtt_client: MQTTClient,
        logger,
        poll_interval: float = 0.5,
    ):
        self.session = session
        self.mqtt = mqtt_client
        self.logger = logger
        self.poll_interval = poll_interval

        self._next_poll_at = seconds_from_now(self.poll_interval)
        self._scene: Optional[BattleScene] = None
        self._last_published_turn: int = -1

    def start(self) -> None:
        self.logger.debug("SceneManagerService starting")
        payload = to_json({"msg": "hello from PKM", "timestamp": time.time()})
        self.mqtt.publish(START_TOPIC, payload, retain=False)
        self._next_poll_at = seconds_from_now(self.poll_interval)

    def tick(self, now: float) -> None:
        if not has_expired(self._next_poll_at, clock=lambda: now):
            return

        try:
            self._poll(now)
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Error while polling scene: {}", exc)
        finally:
            self._next_poll_at = seconds_from_now(self.poll_interval, clock=lambda: now)

    # ------------------------------------------------------------------
    def _poll(self, now: float) -> None:
        battle_id = self._read_battle_id()
        if battle_id is None:
            # Lecture RAM échouée / vide
            self.logger.debug("BattleTypeID read returned no data")
            return

        if battle_id > 0:
            self._ensure_battle_scene(battle_id)
            assert self._scene is not None

            # Update = lecture état + éventuellement progression des actions internes
            self._scene.update(now)

            if not self._scene.is_ready():
                self.logger.debug("Scene not ready yet (battle_id={}), skipping publish", battle_id)
                return

            self._publish_if_needed(battle_id)
        else:
            self._end_battle_if_needed()

    def _read_battle_id(self) -> Optional[int]:
        data = self.session.read_memory(MainPokemonData.BattleTypeID)
        if not data:
            return None
        return int(data[0])

    def _ensure_battle_scene(self, battle_id: int) -> None:
        if self._scene is None or self._scene.battle_id != battle_id:
            self.logger.info("Battle started (ID={})", battle_id)
            self._scene = create_battle_scene(self.session, battle_id)
            self._last_published_turn = -1

    def _publish_if_needed(self, battle_id: int) -> None:
        assert self._scene is not None
        turn = int(self._scene.turn_counter)

        if turn == self._last_published_turn:
            return

        self._last_published_turn = turn
        payload = {
            "battle_id": battle_id,
            "turn": turn,
            "timestamp": time.time(),
            "scene": self._scene.to_dict(),
        }
        self.mqtt.publish(BATTLE_INFO_TOPIC, to_json(payload), retain=True)
        self.logger.info("Published battle update (battle_id={}, turn={})", battle_id, turn)

    def _end_battle_if_needed(self) -> None:
        if self._scene is not None:
            self.logger.info("Battle ended (ID={})", self._scene.battle_id)
        self._scene = None
        self._last_published_turn = -1

    @property
    def current_scene(self) -> Optional[BattleScene]:
        return self._scene


__all__ = ["SceneManagerService"]
