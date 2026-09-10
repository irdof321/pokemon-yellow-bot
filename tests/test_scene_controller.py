import threading
import time

import pytest

from game.scenes.battle_scene import create_battle_scene
from game.scenes.commands import BattleCommand
from game.scenes.scene_controller import SceneController


class FakePokemon:
    """Minimal stand-in for PartyPokemon: just the two fields
    SceneController's reward math reads."""

    def __init__(self, current_hp: int, max_hp: int):
        self.current_hp = current_hp
        self.max_hp = max_hp


class FakeBattleScene:
    """Minimal stand-in for BattleScene: mimics enqueue_command()/to_dict()
    without needing PyBoy or a ROM. Reports everything as eligible -- these
    tests are about step()'s blocking/timeout behavior, not eligibility
    rejection (that's covered by filter_eligible_move_slots /
    filter_eligible_switch_slots' own tests). player_party/is_battle_over
    default to "full HP, battle still going" so existing tests (about
    blocking/timeout, not reward math) don't need to care about them."""

    eligible_move_slots = [1, 2, 3, 4]
    eligible_switch_slots = [1, 2, 3, 4, 5, 6]

    def __init__(self, player_party=None, is_battle_over: bool = False):
        self._commands = []
        self._lock = threading.Lock()
        self.player_party = player_party if player_party is not None else [FakePokemon(35, 35)]
        self._is_battle_over = is_battle_over

    def enqueue_command(self, cmd):
        with self._lock:
            self._commands.append(cmd)

    def to_dict(self):
        return {"ok": True}

    def is_scene_complete(self) -> bool:
        return self._is_battle_over

    def drive_one(self):
        """Simulate one SceneManagerService tick completing the oldest command,
        the way BattleScene._drive_commands() does via cmd.done_event.set()."""
        with self._lock:
            cmd = self._commands.pop(0) if self._commands else None
        if cmd is not None:
            cmd.done_event.set()


class FakeSceneProvider:
    def __init__(self, scene):
        self._scene = scene

    @property
    def current_scene(self):
        return self._scene


class NullLogger:
    def warning(self, *args, **kwargs):
        pass


def test_step_blocks_until_command_completes_not_until_scene_is_idle():
    scene = FakeBattleScene()
    controller = SceneController(FakeSceneProvider(scene), NullLogger(), default_timeout=2.0)
    cmd = BattleCommand(kind="move", move_index=1)

    results = {}

    def call_step():
        results["obs"], results["reward"], results["done"], results["info"] = controller.step(cmd)

    t = threading.Thread(target=call_step)
    t.start()

    # step() must still be waiting here — it must NOT return just because the
    # scene "looks idle"; only drive_one() (below) may unblock it.
    time.sleep(0.1)
    assert t.is_alive(), "step() returned before the command was driven to completion"

    scene.drive_one()
    t.join(timeout=2.0)

    assert not t.is_alive()
    assert results["obs"] == {"ok": True}
    assert results["info"].get("timeout") is not True


def test_step_reports_timeout_when_command_never_completes():
    scene = FakeBattleScene()
    controller = SceneController(FakeSceneProvider(scene), NullLogger(), default_timeout=0.1)
    cmd = BattleCommand(kind="move", move_index=1)

    # nobody ever calls scene.drive_one(), so the command never completes
    _, _, _, info = controller.step(cmd)

    assert info["timeout"] is True


def test_step_rejects_ineligible_move_without_enqueueing():
    scene = FakeBattleScene()
    scene.eligible_move_slots = [1, 2, 3]  # no slot 4, like a Pokemon with only 3 moves
    controller = SceneController(FakeSceneProvider(scene), NullLogger(), default_timeout=0.2)
    cmd = BattleCommand(kind="move", move_index=4)

    obs, reward, done, info = controller.step(cmd)

    assert info["error"] == "ineligible_command"
    assert info.get("timeout") is not True
    assert scene._commands == [], "an ineligible command must never be enqueued"


def test_step_returns_error_info_when_no_active_scene():
    controller = SceneController(FakeSceneProvider(None), NullLogger())
    cmd = BattleCommand(kind="move", move_index=1)

    obs, reward, done, info = controller.step(cmd)

    assert obs == {}
    assert info["error"] == "no_active_scene"


def test_observation_returns_scene_state_when_active():
    scene = FakeBattleScene()
    controller = SceneController(FakeSceneProvider(scene), NullLogger())

    assert controller.observation == {"ok": True}


def test_observation_returns_empty_dict_when_no_active_scene():
    controller = SceneController(FakeSceneProvider(None), NullLogger())

    assert controller.observation == {}


def _run_step_and_drive(controller, cmd, scene, *, mutate_before_drive=None):
    """Runs controller.step(cmd) on a background thread (it blocks on
    done_event) and completes it from the main thread via scene.drive_one(),
    same pattern as test_step_blocks_until_command_completes_not_until_scene_is_idle.
    mutate_before_drive, if given, runs just before drive_one() -- e.g. to
    drop a Pokemon's HP to simulate damage taken during this turn."""
    results = {}

    def call_step():
        results["obs"], results["reward"], results["done"], results["info"] = controller.step(cmd)

    t = threading.Thread(target=call_step)
    t.start()
    time.sleep(0.05)

    if mutate_before_drive is not None:
        mutate_before_drive()
    scene.drive_one()
    t.join(timeout=2.0)
    assert not t.is_alive()
    return results


def test_step_applies_per_turn_and_hp_loss_penalty_when_battle_continues():
    mon = FakePokemon(35, 35)
    scene = FakeBattleScene(player_party=[mon], is_battle_over=False)
    controller = SceneController(FakeSceneProvider(scene), NullLogger(), default_timeout=2.0)
    cmd = BattleCommand(kind="move", move_index=1)

    # 10 of 35 max HP lost this turn (~28.57% of the team's max HP).
    results = _run_step_and_drive(
        controller, cmd, scene, mutate_before_drive=lambda: setattr(mon, "current_hp", 25)
    )

    expected = SceneController.PER_TURN_PENALTY - SceneController.HP_LOSS_WEIGHT * (10 / 35 * 100)
    assert results["reward"] == pytest.approx(expected)
    assert results["done"] is False
    assert "won" not in results["info"]


def test_step_adds_win_bonus_when_battle_ends_with_a_pokemon_alive():
    scene = FakeBattleScene(player_party=[FakePokemon(20, 35)], is_battle_over=True)
    controller = SceneController(FakeSceneProvider(scene), NullLogger(), default_timeout=2.0)
    cmd = BattleCommand(kind="move", move_index=1)

    results = _run_step_and_drive(controller, cmd, scene)

    expected = SceneController.PER_TURN_PENALTY + SceneController.WIN_BONUS
    assert results["reward"] == pytest.approx(expected)
    assert results["done"] is True
    assert results["info"]["won"] is True


def test_step_adds_loss_bonus_when_battle_ends_with_no_pokemon_alive():
    scene = FakeBattleScene(player_party=[FakePokemon(0, 35)], is_battle_over=True)
    controller = SceneController(FakeSceneProvider(scene), NullLogger(), default_timeout=2.0)
    cmd = BattleCommand(kind="move", move_index=1)

    results = _run_step_and_drive(controller, cmd, scene)

    expected = SceneController.PER_TURN_PENALTY + SceneController.LOSS_BONUS
    assert results["reward"] == pytest.approx(expected)
    assert results["done"] is True
    assert results["info"]["won"] is False


# ----------------------------------------------------------------------
# Real-battle test: everything above uses FakeBattleScene (fast, but only
# proves the reward ARITHMETIC is right). is_scene_complete() reads real RAM
# (BattleTypeID) that we've never actually seen flip to 0 in an automated
# test -- every existing fixture is captured mid-battle. This one drives a
# genuine wild battle to a genuine win and checks SceneController.step()
# reports it correctly, per the project's "verify against real RAM, don't
# just trust the mock" rule.
# ----------------------------------------------------------------------
class _RealSceneProvider:
    """SceneProvider that always returns the same already-created BattleScene
    -- unlike SceneManagerService, it never nulls itself out when the battle
    ends, which is fine here: the test reads `scene` directly afterward."""

    def __init__(self, scene):
        self.current_scene = scene


def test_step_reports_real_win_against_a_live_battle(load_fixture):
    # wild_ratatta_par.state: wild Rattata at 3/18 HP -- our Thundershock
    # (move_index=1, power 40) kills it in a single hit.
    session = load_fixture("wild_ratatta_par.state")
    scene = create_battle_scene(session, battle_id=0)
    scene.update(0.0)
    assert scene.to_dict()["enemy"]["hp"][0] <= 3, "fixture assumption changed -- won't die in one hit"

    controller = SceneController(_RealSceneProvider(scene), session.logger, default_timeout=15.0)
    cmd = BattleCommand(kind="move", move_index=1)

    # Same synthetic-clock driving as conftest.py's _SceneDriver, but on its
    # own thread: step() blocks on cmd.done_event, so something else has to
    # keep ticking the emulator + calling scene.update() concurrently, the
    # way EmulatorLoop/SceneManagerService do in production.
    stop = threading.Event()

    def _drive():
        now = 0.0
        frame = 0
        while not stop.is_set():
            frame += 1
            if not session.tick_once():
                return
            now += 1 / 60
            if frame % 60 == 0:
                button = session.pop_button()
                if button is not None:
                    session.press_button(button)
            if frame % 6 == 3:
                scene.update(now)

    driver = threading.Thread(target=_drive, daemon=True)
    driver.start()
    try:
        observation, reward, done, info = controller.step(cmd)
    finally:
        stop.set()
        driver.join(timeout=2.0)
        session.stop(save=False)

    assert info.get("timeout") is not True, f"never completed: {info}"
    assert done is True, "is_scene_complete() never saw the real BattleTypeID flip to 0"
    assert info["won"] is True
    assert reward > 0, f"win bonus should dominate a single clean kill, got {reward}"
