# pokemon-yellow-bot

An **experimental agent framework** built on top of the **PyBoy** emulator, currently targeting **Pokémon Red (Generation I)** as a controlled sandbox.

This repository is **not** about building a perfect or competitive Pokémon bot.
It is a **software engineering and agent-architecture project**, using Pokémon as a deterministic legacy environment to experiment with **state reconstruction, decision decoupling, and LLM-driven planning**.

> ⚠️ Classical rule-based or reinforcement learning approaches can play Pokémon **far more efficiently**.  
> This project deliberately explores a different design space.

---

## Project intent

This project is designed to explore:

- Interaction with a **legacy deterministic system** via direct memory inspection (WRAM / HRAM)
- Explicit **game-state reconstruction** from emulator RAM
- Clear separation between:
  - Environment perception
  - State modeling
  - Decision logic
  - Action execution
- Use of a **Large Language Model (LLM)** as a **high-level decision engine / planner**
- Informal evaluation, during development, of where LLM-based decision-making helps or hurts in a deterministic system

Pokémon is used strictly as a **technical testbed**, not as an end goal.

---

## What this project is NOT

- ❌ Not a competitive Pokémon bot
- ❌ Not a reinforcement learning benchmark
- ❌ Not a "perfect play" agent
- ❌ Not a full game automation system

The focus is **architecture and engineering clarity**, not gameplay performance.

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

### Not supported (for now)
- Pokémon switching
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

### 3) Start the Pokemon-Client (POC)
The client consumes the API and implements decision logic
(e.g. rules, heuristics, or LLM-based reasoning).

Client repo:
https://github.com/irdof321/pokemon-client

```bash
python path/to/read.py
```

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

## References

- Gen I RAM map (Red/Blue): https://datacrystal.tcrf.net/wiki/Pok%C3%A9mon_Red_and_Blue/RAM_map
- Pokémon Yellow (Glitch City Wiki): https://glitchcity.wiki/wiki/Pok%C3%A9mon_Yellow
- PyBoy memory API: https://docs.pyboy.dk/index.html#pyboy.PyBoyMemoryView
- Gen I character encoding: https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_I)
- Gen I Pokémon data structure: https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_I)

---

## Status

- Tag: `v0.1.0`
- Focus: battle-only agent framework
- Purpose: architecture & decision-system experimentation
