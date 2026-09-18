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
    # DAMAGE_DEALT_WEIGHT/KO_BONUS added 2026-09-11: the reward used to have
    # NO direct signal for dealing damage at all (only a penalty for own-team
    # HP lost, plus the terminal bonus) -- an agent had to learn "attacking
    # well shortens the episode" entirely indirectly. Symmetric to
    # HP_LOSS_WEIGHT so a good, type-effective hit is rewarded the moment it
    # lands instead of only paying off much later at the terminal bonus --
    # this also gives a delayed action like switching a shorter path to
    # credit: a good switch is worth more once the FOLLOWING turn's bigger
    # hit is itself directly rewarded.
    PER_TURN_PENALTY = -1.0
    HP_LOSS_WEIGHT = 1.0  # weight on %-of-team-HP lost this turn (0..100 scale)
    DAMAGE_DEALT_WEIGHT = 1.0  # weight on %-of-enemy-team-HP dealt this turn (0..100 scale)
    KO_BONUS = 20.0  # flat bonus per enemy Pokemon knocked out this turn -- first guess, tune empirically
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

        hp_fraction_before = self.team_hp_fraction(scene)
        enemy_hp_fraction_before = self.enemy_team_hp_fraction(scene)
        enemy_count_before = scene.enemy_remaining_count

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
        reward, done, reward_info = self.compute_reward(
            scene, hp_fraction_before, enemy_hp_fraction_before, enemy_count_before,
        )
        info.update(reward_info)

        return scene.to_dict(), reward, done, info

    @classmethod
    def compute_reward(
        cls, scene: BattleScene, hp_fraction_before: float,
        enemy_hp_fraction_before: float, enemy_count_before: int,
    ) -> Tuple[float, bool, dict]:
        """The reward/done math, factored out of step() so a caller that
        drives the scene itself (e.g. an RL training loop using a fast
        synthetic clock instead of step()'s real-time done_event.wait(),
        for throughput) can reuse the exact same reward logic instead of
        re-deriving it. Call AFTER the command has finished executing.
        enemy_hp_fraction_before/enemy_count_before mirror hp_fraction_before
        but for the OPPONENT's roster (from enemy_team_hp_fraction/
        scene.enemy_remaining_count taken right before the command was
        enqueued) -- see DAMAGE_DEALT_WEIGHT/KO_BONUS above for why.
        Returns (reward, done, info) -- info has "won" set only when done."""
        hp_fraction_after = cls.team_hp_fraction(scene)
        hp_lost_pct = max(0.0, (hp_fraction_before - hp_fraction_after) * 100.0)

        enemy_hp_fraction_after = cls.enemy_team_hp_fraction(scene)
        hp_dealt_pct = max(0.0, (enemy_hp_fraction_before - enemy_hp_fraction_after) * 100.0)
        kos_this_turn = max(0, enemy_count_before - scene.enemy_remaining_count)

        reward = (
            cls.PER_TURN_PENALTY
            - cls.HP_LOSS_WEIGHT * hp_lost_pct
            + cls.DAMAGE_DEALT_WEIGHT * hp_dealt_pct
            + cls.KO_BONUS * kos_this_turn
        )
        done = scene.is_scene_complete()

        info = {}
        if done:
            # scene.can_still_fight is a CACHE of the last "player has an
            # alive/switchable Pokemon" reading taken while still definitely
            # in battle -- NOT re-derived live here. is_scene_complete()
            # only becomes true once BattleTypeID has already returned to 0
            # (game back in the overworld), and a live read of
            # player_active/player_party at that point isn't guaranteed to
            # still mean anything. Confirmed broken in practice (2026-09-11,
            # twice): a live read here reported a win for a battle that was
            # actually a full team wipe -- see can_still_fight's own
            # docstring for the full story, including why an earlier
            # "read player_active instead of player_party" fix wasn't
            # enough (both are equally suspect once the transition has
            # already happened).
            won = scene.can_still_fight
            reward += cls.WIN_BONUS if won else cls.LOSS_BONUS
            info["won"] = won

        return reward, done, info

    @staticmethod
    def team_hp_fraction(scene: BattleScene) -> float:
        """Fraction (0..1) of the player's whole party's max HP still
        remaining right now -- team-wide, not just the active Pokemon, since
        a switch doesn't cost HP but the team's overall health is what we
        actually want to preserve."""
        total_max = sum(p.max_hp for p in scene.player_party)
        if total_max <= 0:
            return 0.0
        total_cur = sum(p.current_hp for p in scene.player_party)
        return total_cur / total_max

    @staticmethod
    def enemy_team_hp_fraction(scene: BattleScene) -> float:
        """Fraction (0..1) of the OPPONENT's whole roster's max HP still
        remaining right now -- symmetric to team_hp_fraction, so damage
        dealt can be rewarded directly instead of only inferred indirectly
        from a shorter episode. scene.enemy_party is [enemy] for a wild
        battle (single opponent) or the full roster for a trainer battle."""
        total_max = sum(p.max_hp for p in scene.enemy_party)
        if total_max <= 0:
            return 0.0
        total_cur = sum(p.current_hp for p in scene.enemy_party)
        return total_cur / total_max

    @property
    def observation(self) -> dict:
        scene = self._scene_provider.current_scene
        if scene is None:
            return {}
        return scene.to_dict()


__all__ = ["SceneController", "SceneProvider"]