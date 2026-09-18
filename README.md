# pokemon-yellow-bot

A **Pokémon Red (Generation I) battle-automation framework** built on top of
the **PyBoy** emulator: real RAM reading, explicit game-state
reconstruction, and a command-queue-driven battle loop (move selection,
move execution, switching).

This repository owns the battle logic itself, not any particular decision
strategy. Two different decision layers have been built against it, in
[pokemon-client](https://github.com/irdof321/pokemon-client):

- **Reinforcement learning (current, active work)**: a MaskablePPO agent
  trains against `game.training.battle_randomizer` here, which mutates a
  captured fixture into a fresh, randomized battle live in RAM on every
  `reset()`, no pre-generated dataset. See that repo's README for
  `rl/train.py` and `rl/watch_agent.py`.
- **LLM-driven decision-making (original direction, now reference-only)**:
  the project's starting point was exploring state reconstruction and
  decision/execution decoupling with an LLM as the high-level planner, via
  `read.py` (an LLM/MQTT bridge). Kept for reference, not actively
  developed.

---

## Project intent

This project explores:

- Interaction with a **legacy deterministic system** via direct memory inspection (WRAM / HRAM)
- Explicit **game-state reconstruction** from emulator RAM
- Clear separation between:
  - Environment perception
  - State modeling
  - Decision logic
  - Action execution
- Randomized battle generation as a cheap, storage-free way to produce
  effectively unlimited training scenarios from a handful of captured
  fixtures, instead of a large pre-generated dataset
- Originally, use of a **Large Language Model (LLM)** as a high-level
  decision engine/planner, and informally evaluating where that helps or
  hurts in a deterministic system, still available via `read.py` but no
  longer the active direction

Pokémon is used strictly as a **technical testbed**, not as an end goal.

---

## What this project is NOT

- ❌ Not a full game automation system: battles only, no items, no fleeing,
  no overworld

This framework's own job is **correct, RAM-verified battle automation**,
not gameplay performance: it just needs to execute whatever a decision
layer decides, reliably. That's still the whole story for the LLM track
(`read.py`), which was never about winning, just about testing where
LLM-based decisions hold up in a deterministic system.

The RL track is different: the agent trained on top of this framework
(see pokemon-client's `rl/` package) is explicitly optimizing to win
battles as reliably and quickly as possible, within the battle-only scope
this framework supports. "Not gameplay performance for its own sake" is a
statement about this repo, not about that agent's goal.

---

## Current scope (v0.1.0)

> Development and testing are currently done on **Pokémon Red only**.

### Supported
- Launch Pokémon (Gen I) via PyBoy
- Auto-load the latest save state (if present)
- **Auto-save emulator state every 2 minutes** (configurable)
- Battle-only loop:
  - Move selection
  - Move execution
  - Pokémon switching (voluntary, from the FIGHT/PKMN menu, and forced after a faint)
- **F5 hotkey** (manual play, real SDL2 window only): captures the current
  state to its own uniquely-named file under `tests/fixtures/battles/`
  (or wherever `capture_dir` points). Useful for building up a library of
  battle-start fixtures, or for reporting a stuck/incorrect turn with a
  concrete state to replay instead of just a description.
- `game.training.battle_randomizer`: species, levels (matched band per
  side), movesets, and party sizes, mutated live in RAM (see intro above).

### Not supported (for now)
- Item usage (in or out of battle)
- Running away
- Overworld exploration / navigation
- Team or inventory management

---

## High-level architecture

```
PyBoy Emulator
   ↓
Memory Reader (WRAM / HRAM)
   ↓
Explicit Game State Model
   ↓
Decision Engine (rules / heuristics / LLM)
   ↓
Command Queue
   ↓
Emulator Input Execution
```

Decision logic is **intentionally decoupled** from emulator control and can live in a separate process.

### UML

- Class diagram: `doc/UML_CLASS.png`

---

## Requirements

- Python 3.x
- A legally obtained Pokémon ROM (**not included**)
- Optional: existing save state (recommended)

> **Legal note:** This repository does not include ROMs or copyrighted assets.  
> You must provide your own legally obtained ROM.

---

## ROM files and game version

At the moment, **only Pokémon Red is validated**.

ROM selection is handled in `game/core/version.py`.

Expected paths:
- `games/PokemonRed.gb`
- `games/PokemonBleu.gb`
- `games/PokemonJaune.gb`

Even if `blue` or `yellow` exist in the codebase, only `red` is currently tested.

In `app.py`:
```python
game = EmulatorSession.from_choice("red", ...)
```

---

## Setup

### Windows (PowerShell)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Using this repo from another project (e.g. pokemon-client)
This repo is packaged (`pyproject.toml`, src-layout) so it can be installed
editable into another project's venv instead of copy-pasting code:
```bash
pip install -e /path/to/pokemon-yellow-bot
```
`pyboy` is pinned **exactly** (`==2.6.0`) in `pyproject.toml`, since
`.state` files are version-sensitive binary data: a mismatch fails with a
cryptic `PyBoyAssertException`, not a clear version message.

---

## How to run

### 1) Configure save-state + autosave
In `app.py`:
```python
SAVE_STATE_PATH = "games/red_test.gb.state"
autosave = AutosaveService(game, logger, 120)
```

### 2) Start emulator + API
```bash
python app.py
```

### 3) Decision logic: two separate paths in pokemon-client
https://github.com/irdof321/pokemon-client

- **RL agent** (current, active work): trains a MaskablePPO agent against
  randomized battles instead of live emulator+API wiring. Doesn't use
  `app.py`/steps 1-2 above at all; see that repo's README for
  `rl/train.py` and `rl/watch_agent.py`.
- **`read.py`** (older LLM/MQTT bridge, kept for reference): consumes
  this repo's live API and implements decision logic via an LLM. Run
  `python path/to/read.py` after steps 1-2.

### 4) Enter a battle
Once a battle starts, the framework handles move selection and execution.

---

## Assistant / pre-prompt (important)

When using an AI assistant inside this repository, it should follow these rules:

- Work strictly within the scope of **Pokémon Red battle logic**
- Prefer **RAM-driven state checks** over screen-based guesses
- Keep emulator I/O isolated from decision logic
- Prefer **B (back)** to exit menus or dialogues unless A is explicitly required
- Do not claim or optimize for "perfect play"
- Use the Red/Blue RAM map as reference:
  https://datacrystal.tcrf.net/wiki/Pok%C3%A9mon_Red_and_Blue/RAM_map

### Pokémon Yellow RAM caveat (for later)
Pokémon Yellow has a single structural difference:
- `wGBC` at `$CF1A` (Red/Blue) is moved to HRAM as `hGBC` at `$FFFE`
- All WRAM addresses **after `$CF1A` are shifted by -1** in Yellow

Unless explicitly stated, **assume Pokémon Red addressing**.

---

## Testing

Tests are built around real PyBoy save states (`tests/fixtures/*.state` + matching `*.json`
ground truth), not mocks — see `tests/fixtures/README.md` for the fixture-capture workflow.

```bash
pytest tests/
```

By default tests run headless, as fast as the CPU allows. Pass `--visual` to instead run
with a real SDL2 window and live logs of what's being driven (menu state, phase, etc.),
useful to actually watch a test instead of trusting a pass/fail:

```bash
pytest tests/test_battle_switch_execution.py -v -s --visual
```

(`-s` is required, otherwise pytest captures the logs). Add `--visual-speed=N` to run
faster than real-time while still watching (`0` = uncapped, too fast to follow; `2`-`5` is
a good middle ground):

```bash
pytest tests/ -v -s --visual --visual-speed=3
```

`scripts/` also has a few standalone debugging scripts (real SDL2 window, real threaded
`EmulatorLoop`) for manually stepping through specific bugs outside of pytest.

---

## References

- Gen I RAM map (Red/Blue): https://datacrystal.tcrf.net/wiki/Pok%C3%A9mon_Red_and_Blue/RAM_map
- Pokémon Yellow (Glitch City Wiki): https://glitchcity.wiki/wiki/Pok%C3%A9mon_Yellow
- PyBoy memory API: https://docs.pyboy.dk/index.html#pyboy.PyBoyMemoryView
- Gen I character encoding: https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_I)
- Gen I Pokémon data structure: https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_I)

---

## Status

- Tag: `v0.1.0`
- Focus: battle-only automation framework, packaged (`pyproject.toml`) for
  reuse from another project's venv
- Active application: RL agent training (MaskablePPO), via pokemon-client's
  `rl/` package, using this repo's live in-RAM battle randomization
- Reference/inactive: LLM-driven decision-making, via pokemon-client's
  `read.py`
