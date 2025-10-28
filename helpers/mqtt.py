"""
mqtt_client.py — Simple MQTT Client for testing or prototyping
Compatible with public broker test.mosquitto.org

⚠️ SECURITY NOTE:
- This broker is public and insecure. Do NOT send secrets or sensitive data.
- Use a private broker (Mosquitto, EMQX, HiveMQ) for production.
- Always prefer TLS (port 8883) if possible.

Features:
- Auto reconnect (with backoff)
- TLS / WebSocket support
- Last Will & Testament (LWT)
- Subscribe / Unsubscribe / Publish helpers
- Graceful stop
"""

import json
import threading
import uuid
import logging
from typing import Any, Iterable

import paho.mqtt.client as mqtt


# -------------------------------------------------------------------------
# Default configuration
# -------------------------------------------------------------------------
DEFAULT_HOST = "test.mosquitto.org"
DEFAULT_PORT = 1883           # 8883 for TLS, 8080 for WS, 8081 for WSS
DEFAULT_KEEPALIVE = 30
DEFAULT_QOS = 0
RECONNECT_MIN_S = 1
RECONNECT_MAX_S = 30

DEFAULT_LWT = {
    "topic": "dforgione/myapp/status",
    "payload": "offline",
    "qos": 0,
    "retain": True,
}

# Connection event
_connected_event = threading.Event()

# Optional global client
_mqttc: mqtt.Client | None = None


# -------------------------------------------------------------------------
# MQTT Callbacks
# -------------------------------------------------------------------------
def _on_connect(client: mqtt.Client, userdata: Any, flags: mqtt.ConnectFlags, reason_code: mqtt.ReasonCodes, properties: mqtt.Properties | None) -> None:
    if reason_code.is_failure:
        client.logger.error(f"[MQTT] Connection failed: {reason_code}")
    else:
        client.logger.info(f"[MQTT] Connected (rc={reason_code.value})")
        _connected_event.set()


def _on_disconnect(client: mqtt.Client, userdata: Any, reason_code: mqtt.ReasonCodes, properties: mqtt.Properties | None) -> None:
    client.logger.warning(f"[MQTT] Disconnected: {reason_code}. Auto-reconnect active if loop is running.")


def _on_message(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
    topic = message.topic
    payload = message.payload.decode(errors="ignore")
    client.logger.debug(f"[MQTT] Message on {topic}: {payload}")

    # Example: append messages to a shared list if userdata is a list
    if isinstance(userdata, list):
        userdata.append({"topic": topic, "payload": payload})


def _on_subscribe(client: mqtt.Client, userdata: Any, mid: int, reason_code_list: list[mqtt.ReasonCodes], properties: mqtt.Properties | None) -> None:
    if reason_code_list and not reason_code_list[0].is_failure:
        client.logger.info(f"[MQTT] Subscribed (QoS={reason_code_list[0].value})")
    else:
        client.logger.error("[MQTT] Subscription failed.")


def _on_unsubscribe(client: mqtt.Client, userdata: Any, mid: int, reason_code_list: list[mqtt.ReasonCodes], properties: mqtt.Properties | None) -> None:
    if not reason_code_list or not reason_code_list[0].is_failure:
        client.logger.info("[MQTT] Unsubscribed successfully.")
    else:
        client.logger.error(f"[MQTT] Unsubscribe failed: {reason_code_list[0]}")

def subscribe_with_callback(client, topic, callback):
    """Subscribe to a topic and call `callback(topic, payload)` for each message."""
    def on_message_wrapper(_client, _userdata, msg):
        payload = msg.payload.decode(errors="ignore")
        callback(msg.topic, payload)

    # Temporarily override the client's message handler
    client.message_callback_add(topic, on_message_wrapper)
    client.subscribe(topic)
# -------------------------------------------------------------------------
# Client creation / start / stop
# -------------------------------------------------------------------------
def _make_logger(logger: Any | None) -> logging.Logger:
    """Return an existing logger or create a basic one."""
    if logger is not None:
        return logger
    lg = logging.getLogger("mqtt")
    if not lg.handlers:
        h = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        h.setFormatter(fmt)
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
    return lg


def _apply_callbacks(client: mqtt.Client) -> None:
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message
    client.on_subscribe = _on_subscribe
    client.on_unsubscribe = _on_unsubscribe


def create_client(
    logger: Any | None = None,
    client_id: str | None = None,
    use_websocket: bool = False,
) -> mqtt.Client:
    """
    Create an MQTT client with callbacks configured.
    - use_websocket: True for WebSocket transport (ports 8080/8081)
    """
    transport = "websockets" if use_websocket else "tcp"
    cid = client_id or f"pyboy-{uuid.uuid4().hex[:10]}"

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=cid,
        transport=transport
    )
    _apply_callbacks(client)
    client.logger = _make_logger(logger)
    client.user_data_set([])  # Shared message list
    client.reconnect_delay_set(min_delay=RECONNECT_MIN_S, max_delay=RECONNECT_MAX_S)
    return client


def start_client(
    client: mqtt.Client,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    keepalive: int = DEFAULT_KEEPALIVE,
    use_tls: bool = False,
    lwt: dict | None = None,
    username: str | None = None,
    password: str | None = None,
    connect_timeout_s: float = 5.0,
) -> None:
    """
    Configure TLS, credentials, and Last Will, then connect and start the loop.
    """
    # Optional authentication (not used on test.mosquitto.org)
    if username is not None or password is not None:
        client.username_pw_set(username=username or "", password=password or "")

    # TLS support
    if use_tls:
        client.tls_set()  # System CA is fine for test.mosquitto.org
        if port == 1883:
            port = 8883

    # LWT setup
    lwt = lwt or DEFAULT_LWT
    client.will_set(lwt["topic"], lwt["payload"], qos=lwt.get("qos", 0), retain=lwt.get("retain", True))

    # Connect and start background thread
    _connected_event.clear()
    client.connect(host, port, keepalive)
    client.loop_start()

    if not _connected_event.wait(timeout=connect_timeout_s):
        client.logger.error(f"[MQTT] Connection timeout to {host}:{port}")
    else:
        client.logger.info(f"[MQTT] Connected to {host}:{port} (TLS={use_tls}, transport={client._transport})")


def stop_client(client: mqtt.Client) -> None:
    """Gracefully stop the client and disconnect."""
    try:
        client.loop_stop()
       # client.disconnect()
    except Exception as e:
        client.logger.exception(f"[MQTT] Stop error: {e}")


# -------------------------------------------------------------------------
# Simple API: publish / subscribe / unsubscribe
# -------------------------------------------------------------------------
def publish(client: mqtt.Client, topic: str, payload: dict | list | str, qos: int = DEFAULT_QOS, retain: bool = False) -> None:
    """Publish JSON or string payload."""
    try:
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        info = client.publish(topic, payload, qos=qos, retain=retain)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            client.logger.warning(f"[MQTT] Publish rc={info.rc} topic={topic}")
        else:
            client.logger.debug(f"[MQTT] Published {topic}: {payload}")
    except Exception as e:
        client.logger.exception(f"[MQTT] Publish error on {topic}: {e}")


def subscribe(client: mqtt.Client, topic_or_topics: str | Iterable[tuple[str, int]], qos: int = DEFAULT_QOS) -> None:
    """Subscribe to one or more topics."""
    try:
        if isinstance(topic_or_topics, str):
            result, _mid = client.subscribe(topic_or_topics, qos=qos)
        else:
            result, _mid = client.subscribe(list(topic_or_topics))
        if result != mqtt.MQTT_ERR_SUCCESS:
            client.logger.error(f"[MQTT] Subscribe failed rc={result}")
    except Exception as e:
        client.logger.exception(f"[MQTT] Subscribe exception: {e}")


def unsubscribe(client: mqtt.Client, topic: str) -> None:
    """Unsubscribe from a topic."""
    try:
        result, _mid = client.unsubscribe(topic)
        if result != mqtt.MQTT_ERR_SUCCESS:
            client.logger.error(f"[MQTT] Unsubscribe failed rc={result}")
    except Exception as e:
        client.logger.exception(f"[MQTT] Unsubscribe exception: {e}")


# -------------------------------------------------------------------------
# Convenience Global Client (optional functional style)
# -------------------------------------------------------------------------
def start_global(
    logger: Any = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    keepalive: int = DEFAULT_KEEPALIVE,
    use_tls: bool = False,
    use_websocket: bool = False,
    lwt: dict | None = None,
    username: str | None = None,
    password: str | None = None,
) -> mqtt.Client:
    """Create and start a global MQTT client instance."""
    global _mqttc
    _mqttc = create_client(logger=logger, use_websocket=use_websocket)
    start_client(
        _mqttc,
        host=host,
        port=port,
        keepalive=keepalive,
        use_tls=use_tls,
        lwt=lwt,
        username=username,
        password=password,
    )
    return _mqttc


def get_global() -> mqtt.Client:
    if _mqttc is None:
        raise RuntimeError("Global MQTT client not started. Call start_global() first.")
    return _mqttc


def stop_global() -> None:
    if _mqttc is not None:
        stop_client(_mqttc)


# -------------------------------------------------------------------------
# Example execution
# -------------------------------------------------------------------------
if __name__ == "__main__":
    lg = _make_logger(None)
    # Non-TLS example. For TLS, set use_tls=True and port=8883.
    c = start_global(
        logger=lg,
        host="test.mosquitto.org",
        port=1883,
        use_tls=False,
        use_websocket=False,
        lwt={"topic": "dforgione/myapp/status", "payload": "offline", "qos": 0, "retain": True},
    )

    topic = f"dforgione/myapp/test/{uuid.uuid4().hex[:6]}"
    subscribe(get_global(), topic)
    publish(get_global(), topic, {"msg": "hello from Dada"}, qos=0, retain=False)

    import time
    time.sleep(2)

    stop_global()
