"""Application entry-point."""
from __future__ import annotations
import os

from dotenv import load_dotenv

# Must run before any game.* import below  several modules (version.py,
# mqtt/topics.py, mqtt/client.py's MQTTConfig) read os.getenv(...) as class/module
# level defaults at import time, so loading .env any later would be too late for them.
load_dotenv()

from game.core.emulator import EmulatorSession
from game.core.loop import EmulatorLoop
from game.mqtt.client import MQTTClient
from game.mqtt.topics import BASE_TOPIC
from game.scenes.scene_controller import SceneController
from game.services.autosave_service import AutosaveService
from game.services.battle_service import BattleService
from game.services.scene_manger_service import SceneManagerService
from game.utils.logging_config import setup_logging

SAVE_STATE_PATH = os.getenv("SAVE_STATE_PATH", "games/red_test.gb.state")
print(f"SAVE_STATE_PATH {SAVE_STATE_PATH}")

def main() -> None:
    logger = setup_logging()

    game = EmulatorSession.from_choice("red", logger=logger, save_state_path = SAVE_STATE_PATH)

    mqtt_client = MQTTClient(
        host="test.mosquitto.org",
        port=1883,
        base_topic=BASE_TOPIC,
        logger=logger,
    )
    services = []
    if os.getenv("AUTOLOAD_STATE", "true").lower() == "true":
        services.append(AutosaveService(game, logger,int(os.getenv("AUTOSAVE_INTERVAL_SECONDS","30"))))
    # scene_manager = SceneManagerService(game, mqtt_client, logger)
    # services.append(scene_manager)
    # services.append(BattleService(mqtt_client, logger, scene_manager))

    # Not yet consumed by anything (no FastAPI/direct caller wired in yet) —
    # available for future synchronous callers via controller.step()/.observation.
    #controller = SceneController(scene_manager, logger)

    loop = EmulatorLoop(game, services=services)

    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Game stopped manually.")
    finally:
        mqtt_client.disconnect()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
