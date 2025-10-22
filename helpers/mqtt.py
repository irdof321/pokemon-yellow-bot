import json
import threading
import paho.mqtt.client as mqtt


# Global event for connection state
_connected = threading.Event()

# -------------------------------------------------------------------------
# MQTT callbacks
# -------------------------------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        client.logger.error(f"Failed to connect to broker: {reason_code}")
    else:
        client.logger.info(f"Connected to broker successfully (reason={reason_code.value})")
        _connected.set()


def on_disconnect(client, userdata, reason_code, properties):
    client.logger.warning(f"Disconnected from broker (reason={reason_code})")


def on_message(client, userdata, message):
    """Callback for subscribed topics (if you subscribe to control topics)."""
    topic = message.topic
    payload = message.payload.decode(errors="ignore")
    client.logger.debug(f"Received message on {topic}: {payload}")

    # Example: append to shared list if needed
    if isinstance(userdata, list):
        userdata.append(payload)


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    if reason_code_list and not reason_code_list[0].is_failure:
        client.logger.info(f"Subscribed with QoS {reason_code_list[0].value}")
    else:
        client.logger.error("Subscription failed.")


def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
    # We *never* disconnect automatically here
    if not reason_code_list or not reason_code_list[0].is_failure:
        client.logger.info("Unsubscribed successfully.")
    else:
        client.logger.error(f"Unsubscribe failed: {reason_code_list[0]}")
# -------------------------------------------------------------------------
# Initialization and helpers
# -------------------------------------------------------------------------


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pyboy-pub")
mqttc.on_connect = on_connect
mqttc.on_disconnect = on_disconnect
mqttc.on_message = on_message
mqttc.on_subscribe = on_subscribe
mqttc.on_unsubscribe = on_unsubscribe


def start_mqttc(logger, host="localhost", port=1883, keepalive=30):
    """
    Initialize and start the MQTT client loop.
    Must be called once at startup before publishing.
    """
    mqttc.logger = logger
    mqttc.user_data_set([])  # optional shared data list
    mqttc.connect(host, port, keepalive)
    mqttc.loop_start()

    if not _connected.wait(timeout=5):
        logger.error("MQTT connection timeout.")
    else:
        logger.info(f"MQTT connected to {host}:{port}")


def publish(topic: str, payload: dict | str, qos: int = 0, retain: bool = False):
    """
    Publish JSON or string payload to the broker.
    Safe to call from the main thread.
    """
    try:
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        info = mqttc.publish(topic, payload, qos=qos, retain=retain)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            mqttc.logger.warning(f"Publish returned rc={info.rc} for topic {topic}")
        else:
            mqttc.logger.debug(f"Published to {topic}: {payload}")
    except Exception as e:
        mqttc.logger.exception(f"Failed to publish to {topic}: {e}")
