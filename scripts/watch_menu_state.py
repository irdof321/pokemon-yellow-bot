"""Manual menu-state observation script.

Loads a save state with a real SDL2 window and lets YOU play manually (the
keyboard controls the game directly -- PyBoy's default mapping, nothing
BattleScene-related involved here) while printing the full MenuState every
~30 real seconds. Use it to navigate to a screen you don't have real
coordinates for yet (e.g. the party-select screen after opening PKMN, or the
SWITCH/STATS/CANCEL sub-menu) and read off cursor_x_top/cursor_y_top +
selected_item_id to fill in MenuLocation.POKEMON_SELECTION / POKEMON_SUB_MENU
in src/game/scenes/battle_scene.py.

Usage:
    python scripts/watch_menu_state.py [fixture.state]
    (default: battle_must_go_on_fight.state, same fixture the other debug
    scripts use)

Everything runs on the main thread (ticks the emulator directly, no
EmulatorLoop/threads) -- keeps this simple, and matches the one rule learned
the hard way earlier: the thread that owns the SDL2 window must be the one
ticking it, or it freezes.

Ctrl+C to stop.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.core.emulator import EmulatorSession  # noqa: E402
from game.core.version import GameVersion  # noqa: E402
from game.data.menu import get_menu_state  # noqa: E402
from game.data.ram_reader import MoveROMBank  # noqa: E402
from game.utils.logging_config import setup_logging  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")
PRINT_INTERVAL = 10.0  # seconds


def main() -> None:
    fixture_name = sys.argv[1] if len(sys.argv) > 1 else "ratata_just_died.state"
    fixture_path = os.path.join(FIXTURES_DIR, fixture_name)

    logger = setup_logging(level="INFO")
    MoveROMBank._instance = None

    session = EmulatorSession(
        GameVersion.RED, logger=logger, save_state_path=fixture_path, window="SDL2"
    )
    assert session.load_state_from_disk(), f"fixture failed to load from {fixture_path}"

    print(f"Loaded {fixture_name}.", flush=True)
    print("Play manually with the keyboard (arrow keys + Z/X, PyBoy's default mapping).", flush=True)
    print(f"MenuState prints every {PRINT_INTERVAL:.0f}s -- Ctrl+C to stop.\n", flush=True)

    print(get_menu_state(), flush=True)  # once immediately, so you're not staring at nothing
    last_print = time.monotonic()

    try:
        while session.tick_once():
            now = time.monotonic()
            if now - last_print >= PRINT_INTERVAL:
                print(get_menu_state(), flush=True)
                last_print = now
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
    finally:
        session.stop(save=False)
        print("Done.", flush=True)


if __name__ == "__main__":
    main()
