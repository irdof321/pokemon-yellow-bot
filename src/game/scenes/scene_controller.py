"""Synchronous facade over a tick-driven Scene."""
from __future__ import annotations

from typing import  Optional, Protocol, Tuple

from game.scenes.battle_scene import BattleScene
from game.scenes.commands import BattleCommand


class SceneProvider(Protocol):
    @property
    def current_scene(self) -> Optional[BattleScene]: ...


class SceneController:
    def __init__(self, scene_provider: SceneProvider, logger, *, default_timeout: float = 10.0):
        # TODO 1 : stocke scene_provider, logger et default_timeout sur self
        # (exactement comme le fait BattleService.__init__, regarde battle_service.py:27-30)
        self._logger = logger
        self._scene_provider = scene_provider
        self._default_timeout = default_timeout
        

    def step(self, cmd: BattleCommand, *, timeout: Optional[float] = None) -> Tuple[dict, float, bool, dict]:
        # Ceci correspond à TOUTE la colonne verte de droite dans le 2e schéma,
        # dans l'ordre :

        # retrieve active scen
        scene = self._scene_provider.current_scene

        # Check if a scene is available
        if scene is None :
            return ({}, 0.0, False, {"error": "no_active_scene"})

        # put the command
        scene.enqueue_command(cmd)

        # wait that the command is executed, if not after wait_for seconds, completed is False and continue
        wait_for = self._default_timeout if timeout is None else timeout
        completed = cmd.done_event.wait(wait_for)

        # inform if not completed
        info = {}
        if not completed:
            info["timeout"] = True 
            self._logger.warning("TIMEOUT waiting event on battle")

      
        return scene.to_dict(), 0.0, False, info
        
    @property
    def observation(self) -> dict:
        scene = self._scene_provider.current_scene
        if scene is None:
            return {}
        return scene.to_dict()


__all__ = ["SceneController", "SceneProvider"]