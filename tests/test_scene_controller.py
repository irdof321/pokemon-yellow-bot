import threading
import time

from game.scenes.commands import BattleCommand
from game.scenes.scene_controller import SceneController


class FakeBattleScene:
    """Minimal stand-in for BattleScene: mimics enqueue_command()/to_dict()
    without needing PyBoy or a ROM."""

    def __init__(self):
        self._commands = []
        self._lock = threading.Lock()

    def enqueue_command(self, cmd):
        with self._lock:
            self._commands.append(cmd)

    def to_dict(self):
        return {"ok": True}

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
