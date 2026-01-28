# pokemon-yellow-bot

An experimental Pokémon Yellow bot / framework built on top of the **PyBoy** emulator.  
It reads game memory (WRAM/HRAM) to understand state and exposes an API that a separate **Pokemon-Client** (POC) can use to drive decisions.

> Right now it only handles **battles**: selecting a move and executing it.  
> It **will not** automatically switch Pokémon, use items, or flee.

---

## What works today

- Launch Pokémon (Gen I) via PyBoy
- Auto-load the latest **save state** if one exists
- **Auto-save state every 2 minutes** (configurable)
- Battle loop (via the client):
  - Move selection
  - Move execution

## What is NOT supported (for now)

- Automatic Pokémon switching
- Item usage (in or out of battle)
- Running away
- Overworld exploration / navigation
- Team / inventory management

---

## Requirements

- Python 3.x
- A legal copy of a Pokémon ROM (**not included**)
- Optional: an existing save state (recommended)

> **Legal note:** This repository does not include ROMs or copyrighted game assets.  
> You must provide your own legally obtained ROM.

---

## ROM files and game version (important)

The project selects a game version (`red`, `blue`, `yellow`) and maps it to a ROM path (see `game/core/version.py`).

By default, it expects ROMs here:

- `games/PokemonRed.gb`
- `games/PokemonBleu.gb`
- `games/PokemonJaune.gb`

If your filenames differ, either rename your ROMs to match or edit the `ROM_PATHS` mapping.

In `app.py`, the game is currently started with:
```python
game = EmulatorSession.from_choice("red", ...)
```
Change `"red"` to `"blue"` or `"yellow"` if needed.

---

## Setup

Create and activate a virtual environment, then install dependencies.

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

### 1) Configure save-state location + autosave interval
In `app.py` you can set where the save state is stored:
```python
SAVE_STATE_PATH = "games/red_test.gb.state"
```

Autosave is handled by `AutosaveService`. Set the interval to **120 seconds** for 2 minutes:
```python
autosave = AutosaveService(game, logger, 120)
```

- On startup the app tries to load the save state from `SAVE_STATE_PATH`.
- If the file doesn't exist yet, it will be created once autosave runs.

### 2) Start the emulator + API
From the repo root:
```bash
python app.py
```

### 3) Start the Pokemon-Client (POC) in a second terminal
The client demonstrates how to use the API and performs the move-selection logic correctly.

- Pokemon-Client: https://github.com/irdof321/pokemon-client

```bash
# Example (adjust to your actual client entrypoint)
python path/to/read.py
```

### 4) In-game: enter a battle and let it run
Once a battle starts, the bot will handle **move selection + execution**.

---

## Project notes / references

These links helped build the memory-level understanding of Gen I Pokémon and PyBoy’s memory access:

- RAM map (Pokémon Red/Blue): https://datacrystal.tcrf.net/wiki/Pok%C3%A9mon_Red_and_Blue/RAM_map
- Pokémon Yellow (Glitch City Wiki): https://glitchcity.wiki/wiki/Pok%C3%A9mon_Yellow
- PyBoy memory API: https://docs.pyboy.dk/index.html#pyboy.PyBoyMemoryView
- Gen I character encoding: https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_I)
- Gen I Pokémon data structure: https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_I)

---

## Quick troubleshooting

- **The game won’t start:** verify the ROM file exists at the expected path (see “ROM files and game version”).
- **No save state loaded:** that’s fine—start a game normally; the autosave will create one later.
- **Client can’t connect:** verify the API host/port matches what the client expects, and start `app.py` first.
