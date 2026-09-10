"""True end-to-end test: constructs the REAL EmulatorLoop + SceneManagerService
+ SceneController -- the actual production classes, actually threaded the way
app.py wires them -- and submits a command through SceneController, the real
public interface (not the hand-rolled drive_scene/drive_until harness used
everywhere else in this suite, which calls BattleScene directly and bypasses
the orchestration layer entirely).

This exists specifically to catch bugs the fast tests structurally cannot:
threading issues between EmulatorLoop's main loop and the services thread,
SceneManagerService's real polling/publish logic, and the actual
Service/SceneController contract. It's slower and less deterministic than the
rest of the suite by nature (real threads, real timing) -- keep this file
small, and prefer the fast BattleScene-direct tests for anything that doesn't
specifically need the real orchestration.

No MQTT broker involved: SceneManagerService only calls mqtt.publish(), so a
tiny fake client stands in rather than depending on a real (and possibly
unreachable) broker for what is fundamentally a test of local wiring.

Timings (button_cooldown, service_tick_interval, poll_interval) are configured
faster than app.py's production defaults, to keep this test in the
low-single-digit-seconds range instead of the ~15-20s the real defaults would
need for one move selection. IMPORTANT, learned the hard way (2026-09-09):
this DOES weaken what's being verified past a certain point -- it isn't just
a "make the test faster" knob. The original values here (button_cooldown=0.05,
service_tick_interval=0.02) made the command complete without ever pressing A
to confirm the move (only LEFT/A/B got sent, PP never changed) -- not a
BattleScene bug, but these timings being genuinely too fast for the real
menu-transition animation to settle in real wall-clock time before the next
decision was made. A sweep (button_cooldown 0.05/0.1/0.2/0.3/0.4/0.5/1.0,
scaled proportionally) found 0.2 already flaky (occasional silent failure)
and 0.3 reliable across 13/13 runs -- the values below keep a safety margin
above that measured threshold rather than sitting right on it.

KNOWN RESIDUAL FLAKE (2026-09-10), accepted rather than fixed: re-swept
0.3/0.4/0.5 at 8 runs each and found roughly the same ~1/8 failure rate at
every value (including 0.5) -- raising button_cooldown further does NOT fix
this, so don't try that as the first move if this test flakes again.
Root-caused via scratch capture harnesses (loop the real test body until a
failure hits, log menu_top/menu_id/phase/_screen_stable every 1ms): when the
move-selection menu opens, MenuSelectedItem (menu_id) can very rarely settle
at 0 and then just... stop responding to DOWN. The button genuinely gets
enqueued and physically pressed every cooldown cycle (confirmed in
EmulatorLoop's own debug log), _screen_stable reads True throughout (the
pixel-diff gate is NOT what's missing here -- the screen looks settled), and
yet menu_id never advances past 0 for the rest of the 30s timeout. This isn't
a BattleScene logic bug or a cooldown-margin problem: it looks like a genuine
Gen1 quirk where the moves menu can be visually done drawing before the game
is internally ready to accept directional input, and our only readiness
signal (screen pixels) can't see that gap. Measured rate: 1 failure in 36
real runs (~3%) across the whole investigation. Not worth chasing further
right now -- if it starts failing more often, or someone wants to actually
fix it rather than accept it, the two next moves discussed were (a) retry the
same button if menu_id doesn't move for N consecutive decisions -- cheap,
general, doesn't require understanding the ROM, or (b) disassemble the
moves-menu-open routine the way WaitForTextScrollButtonPress was disassembled
earlier, to find a real input-acceptance signal instead of guessing.
"""
import threading
import time

from game.core.loop import EmulatorLoop
from game.data.ram_reader import MainPokemonData
from game.scenes.commands import BattleCommand
from game.scenes.scene_controller import SceneController
from game.services.scene_manger_service import SceneManagerService


class _FakeMQTTClient:
    """SceneManagerService only ever calls .publish() on this -- no real
    broker needed to test the wiring between EmulatorLoop, SceneManagerService,
    and SceneController."""

    def publish(self, topic, payload, qos: int = 0, retain: bool = False) -> None:
        pass


def test_real_wiring_move_selection_via_scene_controller(load_fixture):
    session = load_fixture("battle_must_go_on_fight.state")

    scene_manager = SceneManagerService(
        session, _FakeMQTTClient(), session.logger, poll_interval=0.1
    )
    controller = SceneController(scene_manager, session.logger)
    loop = EmulatorLoop(
        session,
        services=[scene_manager],
        button_cooldown=0.3,
        service_tick_interval=0.05,
    )

    loop_thread = threading.Thread(target=loop.run, daemon=True)
    loop_thread.start()

    try:
        # SceneManagerService only builds a scene once its own poll notices the
        # battle (real background thread, real wall-clock polling) -- wait for
        # it rather than assuming it exists the instant the thread starts.
        deadline = time.monotonic() + 5.0
        while scene_manager.current_scene is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert scene_manager.current_scene is not None, "no battle scene appeared within 5s"

        scratch_pp_before = scene_manager.current_scene.to_dict()["on_battle"]["moves"][0]["pp"][0]

        cmd = BattleCommand(kind="move", move_index=1)
        observation, reward, done, info = controller.step(cmd, timeout=30.0)

        assert info.get("timeout") is not True, f"SceneController.step() timed out: {info}"
        assert observation["on_battle"]["moves"][0]["pp"][0] == scratch_pp_before - 1
        assert session.read_memory(MainPokemonData.BattlePlayerMove)[0] == 10  # Scratch's ROM move ID
    finally:
        # session.stop() makes the NEXT tick_once() return False, which is
        # what makes EmulatorLoop.run()'s own while-loop exit on its own --
        # there's no separate external "stop" flag for the main loop itself
        # (only _stop_services covers the services thread).
        session.stop(save=False)
        loop_thread.join(timeout=15.0)
        assert not loop_thread.is_alive(), "EmulatorLoop thread did not shut down cleanly"
