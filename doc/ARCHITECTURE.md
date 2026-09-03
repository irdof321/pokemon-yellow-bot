# Architecture du code — pokemon-yellow-bot

Doc de référence technique pour se repérer dans le code après une pause. Complète le `README.md` (qui décrit l'intention du projet) avec le détail des modules, classes et flux de données.

## Vue d'ensemble

```
PyBoy (émulateur)
   │
   ▼
EmulatorSession (game/core/emulator.py)       ← wrapper PyBoy + queue de boutons + save state
   │
   ▼
EmulatorLoop (game/core/loop.py)               ← boucle principale (thread 1) + boucle services (thread 2)
   │                                              │
   ▼                                              ▼
appuie les boutons en attente              Services.tick() toutes les 0.1s
                                                   │
                                    ┌──────────────┼──────────────────┐
                                    ▼              ▼                  ▼
                          SceneManagerService  BattleService   AutosaveService
                          (lit la RAM,         (reçoit les     (sauvegarde
                           construit la scène,  commandes MQTT, périodique)
                           publie sur MQTT)      les pousse
                                                  dans la scène)
                                    │
                                    ▼
                              BattleScene / NormalBattle
                          (machine à états qui décide quels
                           boutons mettre dans la queue de
                           EmulatorSession pour exécuter
                           la commande demandée)
```

Le client de décision (LLM, dans `../pokemon-client`) n'est **pas** dans ce repo : il s'abonne à `battle/info` sur MQTT, décide, et publie sur `battle/move`. Ce repo ne fait que lire l'état du jeu et exécuter les commandes reçues — aucune logique de décision ici (cf. `Conventions` du CLAUDE.md).

## Point d'entrée

`src/app.py` :
1. `setup_logging()` — configure Loguru (fichier tournant + stdout).
2. `EmulatorSession.from_choice("red", ...)` — démarre PyBoy avec la ROM Red (choix actuellement en dur, voir README § ROM files).
3. Crée le `MQTTClient` (broker public `test.mosquitto.org` par défaut).
4. Assemble la liste `services` : `AutosaveService` (si `AUTOLOAD_STATE=true`), `SceneManagerService`, puis `BattleService` (qui reçoit `SceneManagerService` comme `scene_provider` pour accéder à `current_scene`).
5. Construit `EmulatorLoop` et l'exécute (`loop.run()`), avec `mqtt_client.disconnect()` en `finally`.

## `game/core/` — émulateur et boucle

- **`emulator.py` — `EmulatorSession(PyBoy)`**
  Sous-classe de `pyboy.PyBoy`. Ajoute :
  - `self.version` (`GameVersion`, pas `game_version` — piège classique, voir plus bas) ;
  - `self.buttons` : `ThreadSafeQueue[GBAButton]`, remplie par les scènes, vidée par `EmulatorLoop` ;
  - `self.save_state_ma` : `SaveStateManager` (state.py) ;
  - `self._tick_lock` (`RLock`) : protège tout accès à PyBoy (tick, lecture mémoire, appui bouton) car le jeu tourne dans un thread pendant que les services tournent dans un autre ;
  - `read_memory(elem)` : point d'entrée unique pour lire une zone RAM — applique le shift Yellow (`MemoryData.get_pkm_yellow_addresses`) puis délègue à `SavedPokemonData.get_data`.
  - Au constructeur, initialise `MemoryData.set_game(self)` (singleton global côté classe) et précharge `MoveROMBank(self)` (cache des données de moves lues en ROM).

- **`loop.py` — `EmulatorLoop`**
  Deux boucles concurrentes :
  - **Boucle principale** (thread appelant) : `session.tick_once()` en continu ; toutes les 60 frames, dépile un bouton (`_maybe_pop_button`) et l'appuie via `session.press_button()`, avec un cooldown (`button_cooldown`, 1s par défaut).
  - **Boucle services** (thread séparé, `_services_loop`) : appelle `service.tick(now)` sur chaque service toutes les `service_tick_interval` (0.1s par défaut). Chaque exception de `tick()` est attrapée et loguée pour ne pas tuer le thread.
  - À l'arrêt (`finally` de `run()`), appelle `service.start()`... pardon, `service.quit()` sur chaque service. **C'est ici que le bug "quit() manquant" se manifeste** si un service ne l'implémente pas.

- **`queue.py` — `ThreadSafeQueue`** : FIFO générique avec `Lock`, utilisée pour la queue de boutons.

- **`state.py` — `SaveStateManager`** : sauvegarde/chargement de l'état PyBoy avec rotation de 5 backups (`.state.bak_1`...`.bak_5`) et écriture atomique (fichier temporaire + `os.replace`).

- **`version.py` — `GameVersion`** (enum `RED`/`BLUE`/`YELLOW`) : expose `.rom_path` et `.is_yellow`. `ROM_PATHS` est construit depuis les variables d'env (`PKM_REOM_*_NAME`, `ROM_BASE_PATH`).

## `game/data/` — lecture RAM et modèles

C'est la couche la plus dense. Tout part de deux idées :

1. **`MemoryData`** (`ram_reader.py`) : une simple paire d'adresses `(start_address, end_address)` + description, avec un `shift` global optionnel. `MemoryData.get_pkm_yellow_addresses(md)` compense le décalage de -1 octet spécifique à Pokémon Yellow pour toute adresse WRAM ≥ `0xCF1A` (Yellow a `hGBC` déplacé en HRAM, ce qui décale tout ce qui suit — cf. README § "Pokémon Yellow RAM caveat").
2. **Des classes "tables d'adresses"** qui héritent de `DataType` (dont `get_data(pyboy, elem)` lit juste `pyboy.memory[start:end+1]`) et déclarent une adresse par attribut de classe :
   - `SavedPokemonData` : zones SRAM (bank 0-3 : sprites, hall of fame, données de sauvegarde, boîtes 1-12) — **et** l'utilitaire `start_pokemon_logger` (thread de debug qui logue périodiquement un Pokémon donné).
   - `MainPokemonData` (fin de fichier, après `class SavedPokemonData`) : très grosse table d'adresses WRAM — audio, sprites à l'écran, état des menus, données de combat (`BattleTurnCounter`, `PlayerAtkModifier`...), les 6 emplacements `Pokemon1..6`/`Nickname1..6`, etc.

Au-dessus de ces tables d'adresses, `helpers.py` fournit les primitives de lecture bas niveau (`read_u8_mem`, `read_u16_mem`, `read_bytes`, leurs équivalents `write_*`, et `fix()` qui applique le shift Yellow si besoin) — toutes passent par `MemoryData.game.memory[...]` (le singleton PyBoy défini via `MemoryData.set_game`).

### Modèle Pokémon (`pokemon.py`)

- `Pokemon(ABC)` : classe de base abstraite. Déclare les propriétés attendues (`species_id`, `level`, `current_hp`, `max_hp`, `status`, `types`, `moves` — toutes `@property @abstractmethod`) et fournit les propriétés dérivées communes (`number` via `POKEMON_ROM_ID_TO_PKDX_ID`, `name` via `POKDX_ID_TO_NAME`, `to_dict()`, `__str__()`).
  ⚠️ Une méthode abstraite qui perd son `@property` (comme le bug `species_id` déjà corrigé) casse silencieusement toute la chaîne `number`/`name`/`to_dict`, car `self.species_id` devient une *bound method*, pas un entier.

- `PartyPokemon(Pokemon)` : lit un des 6 slots de party WRAM (`SLOT_BLOCKS`, offsets définis dans `POKEMON_LAYOUT_PARTY`). Un seul Pokémon = 44 octets + nickname séparé.

- `EnemyPokemon(Pokemon)` / `PlayerPokemonBattle(Pokemon)` : lisent le struct de combat (`POKEMON_LAYOUT_BATTLE`, 40 octets), via des adresses dédiées de `MainPokemonData` (`EnemyPokemonID2`, `PlayerPokemonNumber`, etc.) plutôt que le layout générique par offset.

- `move.py` — `Move` : chargé soit depuis un ID (`Move.load_from_id`, lit 6 octets dans `MoveROMBank` + décode le nom depuis la ROM), soit depuis des octets bruts. Le mapping code-effet → texte humain vient de `FUNCTION_CODE_EFFECT` (`data.py`).

- `decoder.py` — `decode_pkm_text` : décodage du texte encodé Gen I (table de correspondance byte → caractère, terminateur `0x50`).

- `data.py` : constantes pures — types Gen I, mapping ROM-id ↔ dex national (`POKEMON_ROM_ID_TO_PKDX_ID` / `POKDX_ID_TO_ROM_ID`), noms EN/FR par dex (`POKDX_ID_TO_NAME`), table des effets de moves, et l'enum `GBAButton` (boutons PyBoy).

- `menu.py` — `get_menu_state()` : construit un `MenuState` (position du curseur, item sélectionné, etc.) à partir de plusieurs champs `MainPokemonData.Menu*`. C'est ce que `BattleScene` utilise pour savoir "où" on est dans les menus (voir plus bas).

## `game/scenes/` — logique de combat

- **`scene.py` — `Scene`** : dataclass de base (`session`, `battle_id`), interface `update()`/`_refresh()`/`to_dict()`/`is_ready()`.

- **`battle_scene.py` — `BattleScene(Scene)`** : machine à états qui pilote un combat **sans jamais appuyer sur un bouton directement** — elle empile des `GBAButton` dans `session.buttons`, et c'est `EmulatorLoop` qui les dépile un par un (throttling déjà géré à ce niveau aussi via `_input_cooldown` côté scène et `button_cooldown` côté loop).

  Le combat est piloté par **position du curseur menu**, pas par du texte OCR : `MenuLocation` définit trois positions connues (`MAIN_MENU_LEFT`/`RIGHT`, `MOVES_OR_TEXT` — ce dernier étant ambigu car partagé entre la liste de moves et les dialogues post-action, d'où le state interne `_phase` : `idle` / `select_move` / `post_dialog`).

  - `update(now)` : rafraîchit `_menu_state` (RAM), maintient le curseur sur le menu principal quand rien n'est en cours (`_ensure_ready_main_menu`), puis fait progresser la commande active (`_drive_commands`).
  - `enqueue_command(cmd)` : appelé par `BattleService` pour empiler une `BattleCommand` (thread-safe, `ThreadSafeQueue`).
  - `_execute_move(now, move_index)` : automate à deux phases — ouvrir/naviguer jusqu'au bon move (`select_move`), puis avancer les dialogues post-action jusqu'à retrouver le menu principal (`post_dialog`). Retourne `True` quand la commande est terminée.
  - `is_ready()` : `True` seulement quand on est positionné sur le menu principal, item 0 — c'est la condition utilisée par `SceneManagerService` pour savoir quand publier un snapshot cohérent sur MQTT.

  - **`NormalBattle(BattleScene)`** : implémentation concrète — construit `player_party` (6× `PartyPokemon`), `player_active` (`PlayerPokemonBattle`) et `enemy` (`EnemyPokemon`), et fournit `to_dict()` pour la sérialisation MQTT.
  - `create_battle_scene(session, battle_id)` : factory, renvoie toujours un `NormalBattle` aujourd'hui (point d'extension si d'autres types de combat sont ajoutés).

- **`commands.py` — `BattleCommand`** : dataclass frozen (`kind`, `move_index`, `request_id`, `created_at`). Seul `kind="move"` est supporté pour l'instant.

- **`common.py`** : enum `BATTLE_ACTION` (`MOVE`/`ITEM`/`PKM`/`RUN` — seul `MOVE` est câblé) + `str_to_battle_action`.

- **`menu_scene.py`** : fichier vide, stub non utilisé.

## `game/services/` — orchestration

Toutes héritent implicitement du `Protocol` `Service` (`service.py` : `start()`, `tick(now)`, `quit()` — **non vérifié à l'exécution**, donc un service qui oublie `quit()` ne plante qu'au moment de l'appel, pas à la définition de la classe).

- **`SceneManagerService`** : poll la RAM toutes les `poll_interval` (0.5s), lit `BattleTypeID` pour savoir si un combat est en cours. Si oui, crée/maintient une `NormalBattle` (`_ensure_battle_scene`), l'update, et publie sur `BATTLE_INFO_TOPIC` seulement si le tour a changé (`_last_published_turn`) et que la scène est `is_ready()`. Expose `current_scene` (utilisé par `BattleService`).

- **`BattleService`** : s'abonne à `BATTLE_MOVE_TOPIC`, parse le payload JSON (`{"action": "move", "choice": N}`), construit une `BattleCommand`, et l'enfile dans `scene_provider.current_scene` via `enqueue_command`. Toute la validation (JSON invalide, action inconnue, `choice` hors bornes) est découpée en petites méthodes privées qui loguent un warning et abandonnent sans lever d'exception.

- **`AutosaveService`** : sauvegarde périodique (`interval_seconds`) via `SaveStateManager`, protégée par un `Lock` (`_save_gate`) — `quit()` acquiert/relâche ce lock pour attendre la fin d'une sauvegarde en cours avant de couper. **Bon modèle** à suivre pour implémenter `quit()` sur les deux autres services.

## `game/mqtt/` — transport

- **`topics.py`** : constantes de topics, préfixées par `MQTT_BASE_TOPIC` (env, défaut `/dforirdod/PKM/`) : `battle/info`, `battle/move`, `start`, `status` (ce dernier n'est publié nulle part actuellement).
- **`client.py` — `MQTTClient`** : wrapper autour de `paho.mqtt.client` (API v2). `connect()` est appelé dans `__init__` et bloque jusqu'à 5s en attendant l'event `on_connect`. `publish`/`subscribe`/`unsubscribe` délèguent directement à paho ; `_message_handlers` route chaque topic vers le handler enregistré par `subscribe()`.

## `game/utils/`

- `json_utils.py` : `to_json` (compact) / `pretty_json` (indenté, pour debug/logs).
- `time_utils.py` : `monotonic()`, `seconds_from_now()`, `has_expired()` — utilisés partout pour le scheduling sans bloquer (pattern "deadline" plutôt que `sleep`).
- `logging_config.py` : configure Loguru (fichier tournant hebdo + stdout), retourne le logger partagé injecté dans toutes les classes (`self.logger`).

## Concurrence — ce qu'il faut garder en tête

Deux threads tournent en permanence pendant `loop.run()` :
1. Le thread appelant (boucle émulateur : `tick_once()` + dépile un bouton toutes les 60 frames).
2. `_services_thread` (tick de chaque service toutes les 0.1s).

Tout ce qui touche PyBoy passe par `EmulatorSession._tick_lock` (un `RLock`, donc ré-entrant). Les échanges entre les deux threads passent par des structures thread-safe dédiées : `ThreadSafeQueue` pour les boutons et les commandes de combat.

## Points d'attention actuels

Ce document décrit l'état du code, pas son historique de bugs — pour la liste des bugs connus et en cours de correction, se référer à l'historique de conversation / au `CLAUDE.md` du projet (`git show HEAD:CLAUDE.md` si le fichier a été supprimé du working tree).

Quelques choses à garder en tête en lisant le code :
- `MemoryData.game` et `Pokemon.game` sont des **singletons de classe** (un seul jeu actif à la fois) — logique pour ce projet (un seul émulateur), mais à ne pas reproduire par réflexe ailleurs.
- Le choix Red/Blue/Yellow est actuellement câblé en dur dans `app.py` (`from_choice("red", ...)`) — le `.env` déclare des variables pour les noms de ROM mais rien ne lit le choix de version depuis l'environnement.
- `doc/menu.pptx` et `doc/UML_CLASS.png` / `doc/class.puml` contiennent des schémas visuels complémentaires à ce document (mapping des menus, diagramme de classes).
