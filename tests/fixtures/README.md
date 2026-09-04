# Test fixtures — real save states

This directory holds real PyBoy save states (`.state` files) captured during actual gameplay,
used as fixtures for tests that read game state from RAM (`ram_reader.py`, `pokemon.py`,
`battle_scene.py`, ...). Real save states are used instead of mocks because this codebase's
whole job is reading raw memory layouts correctly — a mock would only prove the code matches
our *assumptions* about the RAM layout, not the real one.

## Capturing a fixture

1. Play until you're in the exact situation you want to freeze (a specific battle, a specific
   party composition, a status condition, low HP, etc.).
2. **Immediately** copy the live save file (the path pointed to by `SAVE_STATE_PATH` in `.env`)
   into this directory, under a new name — do not rely on the autosave rotation to still have
   it later. `SaveStateManager` only keeps 5 rotating backups
   (`AUTOSAVE_INTERVAL_SECONDS` apart, 120s by default) — about 10 minutes of history. A state
   from an hour ago will be gone.
3. Write down the ground-truth values for that exact moment in a matching `.json` file
   (same base name as the `.state` file) — see the format below. This is what tests will
   assert against, so it needs to be correct, not guessed after the fact.

## Naming convention

One pair of files per captured situation, same base name:
```
tests/fixtures/<short_description>.state
tests/fixtures/<short_description>.json
```
Examples: `battle_pikachu_vs_rattata.state`, `battle_status_poisoned.state`,
`party_full_six_pokemon.state`, `battle_low_hp_critical.state`.

## Metadata format (`.json`)

Mirrors the shape of `NormalBattle.to_dict()` (`enemy` / `on_battle` / `party`), so a test can
compare it almost directly against what the code produces. See `_TEMPLATE.json` in this
directory for a fillable example — copy it, rename it, fill in the real values you observed
in-game (in-game menus, not guessed from the state file).

Top-level fields:
- `description` — one line, human-readable, what this fixture represents.
- `game_version` — `"red"`, `"blue"`, or `"yellow"` (which ROM this state was captured on —
  matters for the Yellow RAM shift).
- `captured_at` — date you captured it (`YYYY-MM-DD`), so stale fixtures are easy to spot later.
- `expected.enemy` / `expected.on_battle` / `expected.party` — same shape as `Pokemon.to_dict()`:
  `dex`, `name`, `level`, `hp` (`[current, max]`), `types` (`[type1, type2]`), `status`
  (list of strings), `moves` (list of move names). Only fill in what you actually verified
  in-game — leave a field out rather than guess.

## Notes

- Fixture `.state` files are committed to the repo (not gitignored) — they're small and are
  the whole point of this directory.
- These fixtures assume `EmulatorSession.version` matches `game_version` in the metadata —
  a Red-captured state loaded under a Yellow session (or vice versa) will read garbage due to
  the RAM shift, so keep them paired correctly when writing tests.
