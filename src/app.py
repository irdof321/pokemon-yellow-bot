"""Application entry-point."""
from __future__ import annotations

from game.core.emulator import EmulatorSession
from game.core.loop import EmulatorLoop
from game.mqtt.client import MQTTClient
from game.mqtt.topics import BASE_TOPIC
from game.services.autosave_service import AutosaveService
from game.services.move_service import MoveService
from game.services.scene_service import SceneService
from game.utils.logging_config import setup_logging


def main() -> None:
    logger = setup_logging()

    game = EmulatorSession.from_choice("red", logger=logger)

    mqtt_client = MQTTClient(
        host="test.mosquitto.org",
        port=1883,
        base_topic=BASE_TOPIC,
        logger=logger,
    )

    autosave = AutosaveService(game, logger)
    scene_service = SceneService(game, mqtt_client, logger)
    move_service = MoveService(scene_service, mqtt_client, logger)

    loop = EmulatorLoop(game, [autosave, scene_service, move_service])

    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Game stopped manually.")
    finally:
        mqtt_client.disconnect()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
