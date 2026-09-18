"""Loads ONE hand-crafted test scenario (see scripts/create_test_scenarios.py)
in a real SDL2 window and hands you the keyboard -- same manual-play style
as play_random_battle.py, but for a specific, fixed, non-random scenario
where the "correct" play is knowable ahead of time.

The scenario's own description is printed, but NOT what the "correct"
action is -- the point is deciding for yourself first. Pass --reveal to
print it anyway, or just open the matching .json afterward.

Usage:
    python scripts/play_scenario.py 01_super_effective_move
    python scripts/play_scenario.py 02_must_switch_no_chance --reveal
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game.core.emulator import EmulatorSession  # noqa: E402
from game.core.version import GameVersion  # noqa: E402
from game.data.ram_reader import MoveROMBank  # noqa: E402
from game.scenes.battle_scene import create_battle_scene  # noqa: E402

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "scenarios")
PRINT_INTERVAL = 10.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="Scenario file name without extension, e.g. 01_super_effective_move (see tests/fixtures/scenarios/).")
    parser.add_argument("--reveal", action="store_true", help="Print the expected correct action upfront instead of deciding for yourself first.")
    args = parser.parse_args()

    state_path = os.path.join(SCENARIOS_DIR, f"{args.name}.state")
    json_path = os.path.join(SCENARIOS_DIR, f"{args.name}.json")
    if not os.path.isfile(state_path):
        available = sorted(f[:-6] for f in os.listdir(SCENARIOS_DIR) if f.endswith(".state"))
        raise SystemExit(f"No scenario at {state_path!r}. Available:\n" + "\n".join(f"  - {a}" for a in available))

    with open(json_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    MoveROMBank._instance = None
    session = EmulatorSession(GameVersion.RED, save_state_path=state_path, window="SDL2")
    session.load_state_from_disk()
    scene = create_battle_scene(session, 0)

    d = scene.to_dict()
    print(f"Scenario: {args.name}")
    print(f"  {meta['description']}\n")
    print(f"Your team ({len(d['party'])}): {[(p['name'], p['level']) for p in d['party']]}")
    print(f"Active: {d['on_battle']['name']} (level {d['on_battle']['level']}), HP={d['on_battle']['hp']}, "
          f"moves {[m['name'] for m in d['on_battle']['moves'] if m['name'] != 'Unknown']}")
    print(f"Opponent: {d['enemy']['name']} (level {d['enemy']['level']}), HP={d['enemy']['hp']}")
    if args.reveal:
        print(f"\n[REVEALED] expected: {meta['expected']}")
    else:
        print(f"\nDecide for yourself, then check {os.path.basename(json_path)} afterward.")
    print()
    print("Play with the keyboard (arrows, Z=A, X=B, Enter=Start).")
    print(f"Snapshot prints every {PRINT_INTERVAL:.0f}s -- close the window (or Ctrl+C) to stop.\n")

    now = 0.0
    last_print = time.monotonic()
    try:
        while session.tick_once():
            now += 1 / 60
            if time.monotonic() - last_print >= PRINT_INTERVAL:
                scene.update(now)
                snap = scene.to_dict()
                print(f"[snapshot] phase={scene._phase} menu_top={scene.menu_top} menu_id={scene.menu_id}")
                print(f"  you:      {snap['on_battle']['name']} HP={snap['on_battle']['hp']}")
                print(f"  opponent: {snap['enemy']['name']} HP={snap['enemy']['hp']}")
                print(flush=True)
                last_print = time.monotonic()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        session.stop(save=False)
        print("Done.")


if __name__ == "__main__":
    main()
