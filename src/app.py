"""Application entry-point."""
from __future__ import annotations

from game.core.emulator import EmulatorSession
from game.core.loop import EmulatorLoop
from game.mqtt.client import MQTTClient
from game.mqtt.topics import BASE_TOPIC
from game.services.autosave_service import AutosaveService
from game.services.battle_service import BattleService
from game.services.scene_manger_service import SceneManagerService
from game.utils.logging_config import setup_logging

SAVE_STATE_PATH = "games/red_test.gb.state"

def main() -> None:
    logger = setup_logging()

    game = EmulatorSession.from_choice("red", logger=logger, save_state_path = SAVE_STATE_PATH)

    mqtt_client = MQTTClient(
        host="test.mosquitto.org",
        port=1883,
        base_topic=BASE_TOPIC,
        logger=logger,
    )

    autosave = AutosaveService(game, logger,100)
    scene_service = SceneManagerService(game, mqtt_client, logger)
    move_service = BattleService(mqtt_client, logger, scene_service)


    loop = EmulatorLoop(game, services=[
                                autosave,
                                scene_service,
                                move_service
                            ])

    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Game stopped manually.")
    finally:
        mqtt_client.disconnect()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
