"""Discovery tool, NOT a test -- prints the real (X,Y) cursor coordinates for
the party-select screen and the SWITCH/STATS/CANCEL sub-menu, by actually
driving there through a real switch command (fast synthetic-clock harness,
same style as tests/conftest.py's _SceneDriver). Nothing here asserts
anything; it exists to hand-fill/re-verify
BattleScene.MenuLocation.POKEMON_SELECTION / POKEMON_SUB_MENU when needed.

This used to live in tests/test_switch_menu_coords.py as a "test" that just
printed values and never asserted -- moved here since it isn't actually a
test, and updated to drive through the fixtures that exist now
(battle_party_select_screen.state for the voluntary path,
ratata_just_died.state for the forced path) instead of three placeholder
fixture names that were never captured under those names.

Currently confirmed (already hardcoded in MenuLocation, this script just
re-derives them independently as a sanity check):
    POKEMON_SELECTION = (0, 1)
    POKEMON_SUB_MENU   = (12, 12)

Usage:
    python scripts/discover_switch_menu_coords.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.core.emulator import EmulatorSession  # noqa: E402
from game.core.version import GameVersion  # noqa: E402
from game.data.ram_reader import MainPokemonData, MoveROMBank  # noqa: E402
from game.scenes.battle_scene import create_battle_scene  # noqa: E402
from game.scenes.commands import BattleCommand  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")

FRAME_DT = 1 / 60
POP_EVERY = 60
UPDATE_EVERY = 6
UPDATE_OFFSET = 3


def _load(state_name: str) -> EmulatorSession:
    MoveROMBank._instance = None
    session = EmulatorSession(
        GameVersion.RED, save_state_path=os.path.join(FIXTURES_DIR, state_name), window="null"
    )
    assert session.load_state_from_disk(), f"fixture failed to load: {state_name}"
    return session


def _print_coords(label: str, session: EmulatorSession) -> None:
    fields = [
        ("MenuCursorXPos", MainPokemonData.MenuCursorXPos),
        ("MenuCursorYPos", MainPokemonData.MenuCursorYPos),
        ("MenuSelectedItem", MainPokemonData.MenuSelectedItem),
        ("MenuLastPartyPos", MainPokemonData.MenuLastPartyPos),
        ("MenuCurrentPartyIndex", MainPokemonData.MenuCurrentPartyIndex),
    ]
    print(f"\n{label}:")
    for name, field in fields:
        raw = session.read_memory(field)
        print(f"  {name} = {raw[0] if raw else None!r}")


def _drive(session, scene, now, condition, max_frames=3000):
    for frame in range(1, max_frames + 1):
        session.tick_once()
        now += FRAME_DT
        if frame % POP_EVERY == 0:
            button = session.pop_button()
            if button is not None:
                session.press_button(button)
        if frame % UPDATE_EVERY == UPDATE_OFFSET:
            scene.update(now)
            if condition():
                return now, True
    return now, False


def discover_party_select_and_submenu() -> None:
    """Drives a real voluntary switch from battle_party_select_screen.state
    (ready main menu) all the way through -- passes through both the
    party-select screen and the SWITCH/STATS/CANCEL popup on the way."""
    session = _load("battle_party_select_screen.state")
    scene = create_battle_scene(session, 0)
    now = 0.0

    cmd = BattleCommand(kind="switch", party_slot=2)
    scene.enqueue_command(cmd)

    now, reached = _drive(session, scene, now, lambda: scene._phase == scene._PHASE_SWITCH_SELECT_SLOT)
    if reached:
        _print_coords("party_select (voluntary path)", session)
    else:
        print("never reached the party-select screen")
        session.stop(save=False)
        return

    # Phase flips to SWITCH_SUBMENU the instant the confirm-A is enqueued,
    # before it's even been physically pressed -- drive a bit further so the
    # popup has actually appeared before reading its coordinates.
    now, reached = _drive(session, scene, now, lambda: scene._phase == scene._PHASE_SWITCH_SUBMENU)
    now, _ = _drive(session, scene, now, lambda: False, max_frames=120)  # let the popup render
    if reached:
        _print_coords("party_submenu (SWITCH/STATS/CANCEL popup)", session)
    else:
        print("never reached the SWITCH/STATS/CANCEL submenu")

    session.stop(save=False)


def discover_forced_switch_screen() -> None:
    """Drives the idle auto-advance from ratata_just_died.state (captured at
    the "<name> fainted!" message, not yet at the party-select screen) with
    NO command active, exactly like _ensure_ready_main_menu does in
    production once current_hp == 0."""
    session = _load("ratata_just_died.state")
    scene = create_battle_scene(session, 0)
    now = 0.0

    now, reached = _drive(session, scene, now, lambda: scene.is_forced_switch_pending)
    if reached:
        _print_coords("forced_switch (party-select screen, forced path)", session)
    else:
        print("never reached the forced party-select screen")

    session.stop(save=False)


if __name__ == "__main__":
    discover_party_select_and_submenu()
    discover_forced_switch_screen()
