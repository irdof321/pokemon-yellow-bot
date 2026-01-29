"""High level MQTT client used by the services."""
from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

import paho.mqtt.client as mqtt


@dataclass(slots=True)
class MQTTConfig:
    host: str = os.getenv("MQTT_BROKER", "test.mosquitto.org")
    port: int = int(os.getenv("MQTT_PORT", "1883"))
    keepalive: int = 30
    client_id: Optional[str] = os.getenv("MQTT_CLIENT_ID", None)
    use_tls: bool = False
    username: Optional[str] = os.getenv("MQTT_USERNAME", None)
    password: Optional[str] = os.getenv("MQTT_PASSWORD", None)


class MQTTClient:
    """Thin wrapper around :mod:`paho.mqtt.client` with sensible defaults."""

    def __init__(self, *, host: str, port: int, base_topic: str, logger) -> None:
        self.config = MQTTConfig(host=host, port=port)
        self.base_topic = base_topic.rstrip("/") + "/"
        self.logger = logger
        self._client = self._create_client()
        self._connected = threading.Event()
        self._client.user_data_set({"logger": logger})
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_subscribe = self._on_subscribe
        self._client.on_unsubscribe = self._on_unsubscribe
        self._message_handlers: dict[str, Callable[[str, str], None]] = {}
        self.connect()

    # ------------------------------------------------------------------
    # Life-cycle
    # ------------------------------------------------------------------
    def _create_client(self) -> mqtt.Client:
        client_id = self.config.client_id or f"pyboy-{uuid.uuid4().hex[:10]}"
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)

    def connect(self) -> None:
        if self._client.is_connected():
            return
        self.logger.info(
            "Connecting to MQTT broker {}:{}", self.config.host, self.config.port
        )
        self._connected.clear()
        self._client.connect(self.config.host, self.config.port, self.config.keepalive)
        self._client.loop_start()
        if not self._connected.wait(timeout=5.0):
            self.logger.warning("MQTT connection timeout")

    def disconnect(self) -> None:
        return
        try:
            self._client.loop_stop()
            if self._client.is_connected():
                self._client.disconnect()
        finally:
            self._connected.clear()

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    # paho expects call-signature with userdata first
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags, reason_code, properties=None):
        if reason_code.is_failure:
            self.logger.error("MQTT connection failed: {}", reason_code)
            return
        self.logger.info("MQTT connected (rc={})", reason_code.value)
        self._connected.set()

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags,
        reason_code,
        properties=None,
    ):
        self.logger.warning("MQTT disconnected: {} (flags={})", reason_code, disconnect_flags)
        self._connected.clear()

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        payload = message.payload.decode(errors="ignore")
        handler = self._message_handlers.get(message.topic)
        if handler:
            handler(message.topic, payload)
        else:
            self.logger.debug("MQTT message on {}: {}", message.topic, payload)

    def _on_subscribe(self, client: mqtt.Client, userdata: Any, mid: int, reason_codes, properties=None):
        self.logger.info("Subscribed to topic (mid={})", mid)

    def _on_unsubscribe(self, client: mqtt.Client, userdata: Any, mid: int, reason_codes, properties=None):
        self.logger.info("Unsubscribed from topic (mid={})", mid)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def publish(self, topic: str, payload: str | bytes, qos: int = 0, retain: bool = False) -> None:
        self.logger.debug("Publishing MQTT message to {}", topic)
        self._client.publish(topic, payload=payload, qos=qos, retain=retain)

    def subscribe(self, topic: str, *, handler: Callable[[str, str], None]) -> None:
        self.logger.debug("Subscribing to topic {}", topic)
        self._message_handlers[topic] = handler
        self._client.subscribe(topic)

    def unsubscribe(self, topic: str) -> None:
        self.logger.debug("Unsubscribing from topic {}", topic)
        self._message_handlers.pop(topic, None)
        self._client.unsubscribe(topic)


__all__ = ["MQTTClient", "MQTTConfig"]
