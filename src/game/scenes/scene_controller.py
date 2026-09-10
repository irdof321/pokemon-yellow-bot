"""Synchronous facade over a tick-driven Scene."""
from __future__ import annotations

from typing import  Optional, Protocol, Tuple

from game.scenes.battle_scene import BattleScene, eligibility_error
from game.scenes.commands import BattleCommand


class SceneProvider(Protocol):
    @property
    def current_scene(self) -> Optional[BattleScene]: ...


class SceneController:
    # Reward shaping constants (POC scope: fastest possible win, least HP
    # lost, no items/fleeing -- see project memory). Tune by hand, not
    # computed: PER_TURN_PENALTY pushes toward fewer turns, HP_LOSS_WEIGHT
    # trades that off against caution, WIN/LOSS_BONUS is the terminal signal.
    PER_TURN_PENALTY = -1.0
    HP_LOSS_WEIGHT = 1.0  # weight on %-of-team-HP lost this turn (0..100 scale)
    WIN_BONUS = 100.0
    LOSS_BONUS = -100.0

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

        # reject an ineligible command before it's even enqueued -- same rule
        # BattleService enforces on the MQTT path, so a direct caller (e.g. an
        # RL agent) gets the same protection instead of waiting on a
        # done_event that would never be set.
        error = eligibility_error(scene, cmd)
        if error:
            self._logger.warning(error)
            return (scene.to_dict(), 0.0, False, {"error": "ineligible_command", "reason": error})

        hp_fraction_before = self._team_hp_fraction(scene)

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

        # scene is the SAME BattleScene instance we grabbed above -- still
        # fully readable (session never gets swapped mid-battle) even if
        # SceneManagerService has already dropped its own current_scene
        # reference by the time we get here (it does exactly that the moment
        # is_scene_complete() becomes true, see _end_battle_if_needed).
        hp_fraction_after = self._team_hp_fraction(scene)
        hp_lost_pct = max(0.0, (hp_fraction_before - hp_fraction_after) * 100.0)

        reward = self.PER_TURN_PENALTY - self.HP_LOSS_WEIGHT * hp_lost_pct
        done = scene.is_scene_complete()

        if done:
            won = any(p.current_hp > 0 for p in scene.player_party)
            reward += self.WIN_BONUS if won else self.LOSS_BONUS
            info["won"] = won

        return scene.to_dict(), reward, done, info

    @staticmethod
    def _team_hp_fraction(scene: BattleScene) -> float:
        """Fraction (0..1) of the player's whole party's max HP still
        remaining right now -- team-wide, not just the active Pokemon, since
        a switch doesn't cost HP but the team's overall health is what we
        actually want to preserve."""
        total_max = sum(p.max_hp for p in scene.player_party)
        if total_max <= 0:
            return 0.0
        total_cur = sum(p.current_hp for p in scene.player_party)
        return total_cur / total_max

    @property
    def observation(self) -> dict:
        scene = self._scene_provider.current_scene
        if scene is None:
            return {}
        return scene.to_dict()


__all__ = ["SceneController", "SceneProvider"]