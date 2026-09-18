"""Launches ONE freshly randomized battle (via battle_randomizer's
load_random_base_battle -- same function a future reset() will call) in a
real SDL2 window, prints what was picked, then hands you the keyboard.
Nothing auto-plays -- you're in full control, same as
scripts/watch_menu_state.py's manual-play style.

Usage:
    python scripts/play_random_battle.py
    python scripts/play_random_battle.py --seed 7
"""
import argparse
import os
import random
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")  # names like "Nidoran(female)" break Windows' default console codepage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import game.training.battle_randomizer as br  # noqa: E402

PRINT_INTERVAL = 10.0  # seconds


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for a reproducible draw (default: random each run).")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    session, scene, picks = br.load_random_base_battle(rng, window="SDL2")

    d = scene.to_dict()
    print(f"battle_type: {d['battle_type']}")
    print(f"Your team ({len(picks['player'])}): {[(p['name'], p['level']) for p in d['party']]}")
    print(f"Active: {d['on_battle']['name']} (level {d['on_battle']['level']}), "
          f"moves {[m['name'] for m in d['on_battle']['moves'] if m['name'] != 'Unknown']}")
    if d["battle_type"] == "trainer":
        print(f"Opponent team ({len(picks['opponent'])}): {[(p['name'], p['level']) for p in d['enemy_party']]}")
    print(f"Opponent active: {d['enemy']['name']} (level {d['enemy']['level']}), "
          f"moves {[m['name'] for m in d['enemy']['moves'] if m['name'] != 'Unknown']}")
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
                print(f"  opponent: {snap['enemy']['name']} HP={snap['enemy']['hp']}"
                      + (f" ({snap['enemy_remaining_count']} left)" if d["battle_type"] == "trainer" else ""))
                print(flush=True)
                last_print = time.monotonic()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        session.stop(save=False)
        print("Done.")


if __name__ == "__main__":
    main()
