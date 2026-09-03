# CLAUDE.md — pokemon-yellow-bot

## How we work together

I'm learning by building this project. Default to **pairing, not autopiloting**:

- **Explain before you edit.** When something's wrong or unclear, tell me what/why first. Point me to the file and line. Let me write the fix myself when it's something I should learn from (most bugs, most new features).
- **You may edit directly** for: mechanical/boilerplate changes I explicitly ask for, formatting, or once I say "go ahead and do it."
- **Ask before big structural changes** (new files, changing an existing module's public interface, adding a dependency). One question at a time, not a wall of them.
- If you notice something broken or smelly while working on something else, mention it briefly and move on — don't fix it unprompted unless it blocks the task at hand.
- Keep diffs small and reviewable. I'd rather do five small steps I understand than one big one I don't.

## Project in one paragraph

PyBoy-based agent framework for Pokémon Red (Gen I). Emulator reads game state directly from RAM (`game/data/ram_reader.py`, `pokemon.py`, `move.py`), reconstructs it into scene objects (`game/scenes/`), and publishes it over MQTT (`game/mqtt/`). A separate decision client (LLM via Ollama, see `../pokemon-client/read.py`) subscribes, decides a move, and publishes it back. `EmulatorLoop` (`game/core/loop.py`) executes the resulting input on the emulator. Currently battle-only.

## Known bugs (from last review — fix these before adding new features on top)

- `MemoryData.get_pkm_yellow_addresses` checks `cls.game.game_version`, but `EmulatorSession` sets `self.version` — the Yellow RAM shift never applies. (`ram_reader.py`)
- `PlayerPokemonBattle.species_id` is missing `@property` — active battle Pokémon always reports as "Unknown"/dex 0 in published state. (`pokemon.py`)
- `doc/requirements.txt` is missing `loguru` and `paho-mqtt`, and lives in `doc/` instead of the repo root.
- `MQTTClient.disconnect()` starts with a bare `return` — it's a no-op.
- `SavedPokemonData` is defined twice in `ram_reader.py`; the second definition silently discards the first (all SRAM field mappings).
- `BattleService` and `SceneManagerService` don't implement `quit()` — shutdown logs a caught exception for each.
- `.env` exists but nothing loads it (no `python-dotenv`).
- `EmulatorLoop.run()`'s success-path log message says "did not terminate" (copy-paste from the error branch).

## Current roadmap (in rough priority order)

1. Fix the bugs above, one at a time, starting with `species_id` (one-line fix, highest impact).
2. Add a thin FastAPI layer *alongside* MQTT (not replacing it): `/health`, `/battle/current` (snapshot), `/battle/history`, optional `/battle/move` override for debugging, and a WebSocket endpoint that re-broadcasts MQTT messages to a browser dashboard.
3. Write tests for the memory readers and state builders (there were tests once — `.pytest_cache` proves it — but they were never committed; start fresh).
4. Later: extend beyond battle-only. When we get to overworld movement, MQTT publish policy shifts from event-driven (on state change) to tick-driven (fixed interval) — same transport, different cadence, no protocol swap needed.

## Conventions

- Python 3.13, project structure under `src/game/`.
- Prefer reading RAM through `MemoryData`/`EmulatorSession.read_memory`, not ad-hoc `pyboy.memory[...]` calls, for consistency with the existing locking (`_tick_lock`).
- Keep decision logic (LLM, heuristics) out of this repo — it talks to the emulator only via MQTT.
