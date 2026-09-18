"""Tests for SceneManagerService, using a real PyBoy session (a fake one
would need to fake every RAM read BattleScene/PartyPokemon make -- easier
and more honest to just use a real fixture)."""
from loguru import logger

from game.services.scene_manger_service import SceneManagerService


class _FakeMQTTClient:
    def publish(self, topic, payload, qos: int = 0, retain: bool = False) -> None:
        pass


def test_first_tick_polls_immediately_regardless_of_the_clock_scale(load_fixture):
    """Regression test for a real bug: __init__/start() used to compute
    _next_poll_at via seconds_from_now(poll_interval) with its default
    clock (real time.monotonic(), a huge epoch-scale number), while tick()
    compares it against whatever `now` the caller passes in. That's fine
    when the caller is EmulatorLoop's default real clock too, but breaks
    completely with a substitute clock meant for training (e.g. FrameClock,
    which produces small frame-count-based numbers like 0.05) -- the
    deadline could never be reached, so _poll() (and therefore scene
    creation) would silently never fire. Calling tick() here with a tiny
    `now`, as a FrameClock would produce moments after startup, must still
    poll and find the battle on the very first call.
    """
    session = load_fixture("wild_ratatta_par.state")
    scene_manager = SceneManagerService(session, _FakeMQTTClient(), logger, poll_interval=0.1)

    scene_manager.start()
    scene_manager.tick(now=0.05)  # small, frame-count-scale `now` -- not a real epoch time

    assert scene_manager.current_scene is not None, (
        "tick() never polled -- _next_poll_at must be on the same clock "
        "scale as the `now` values tick() is compared against, not "
        "hardcoded to real time.monotonic()"
    )
