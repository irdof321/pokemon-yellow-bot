# src/game/app.py
from game.core.emulator import EmulatorSession
from game.services.scene_service import SceneService
from game.services.autosave_service import AutosaveService
from game.mqtt.client import MQTTClient
from game.utils.logging_config import setup_logging

def main():
    # 1️⃣  Setup logging
    logger = setup_logging()

    # 2️⃣  Create emulator session (choose version)
    game = EmulatorSession.from_choice("red")  # or "yellow", or ask user

    # 3️⃣  Setup MQTT client
    mqtt_client = MQTTClient(
        host="test.mosquitto.org",
        port=1883,
        base_topic="/dforirdod/PKM/",
        logger=logger
    )

    # 4️⃣  Create services
    autosave = AutosaveService(game, logger)
    scene_service = SceneService(game, mqtt_client, logger)

    # 5️⃣  Run the main loop
    try:
        game.run(autosave, scene_service)
    except KeyboardInterrupt:
        logger.info("Game stopped manually.")
    finally:
        mqtt_client.disconnect()
        logger.info("Goodbye!")

if __name__ == "__main__":
    main()
