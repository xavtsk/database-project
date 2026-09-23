# INF2003 Group 13

## INF2003 Database Systems Group Project

A five-person university database project combining a Pokémon collection and battle application with **MariaDB** and **MongoDB**. The original 151 Pokémon are available in a Pokémon-coloured browser interface. Repository name: `pokedex-battle-analytics`.

The playable prototype is on `feature/core-features`. Its database schema and simplified mechanics follow the [approved design](docs/database-design/playable-prototype-proposal.md). This is a local demonstration with selectable trainer profiles, not an authenticated public service.

See the [application architecture](docs/diagrams/application-architecture.md) for the data flow and proposed EXP, levels and evolution extension. Progression is not implemented yet.

## Play locally

On the development computer, the databases and ignored `.env` have been configured. Start the app from the repository root:

```sh
python3 scripts/run_local.py
```

Open **http://127.0.0.1:5050**. If an existing app is already running there, open that address without starting a second copy.

1. Click **Choose trainer**, create a profile and select Bulbasaur, Charmander or Squirtle.
2. In **Collection & teams**, edit the initial team and select four distinct moves for each member. Save the team.
3. Review **Team analysis** for stats, type weaknesses and selected-move coverage.
4. In **Battle arena**, select a saved team and Easy, Medium or Hard. Pick a move each turn, or switch Pokémon.
5. A win awards one random Pokémon to your collection. Add it to a team if desired. Review **Battle analytics** for history, win rates, usage and duration.

Teams can contain 1–6 Pokémon. Reloading resumes an active battle. Saved-team edits do not change an existing battle's snapshots. Reopening a winning battle retries any pending reward delivery without awarding twice.

## Set up another computer

Requirements: Python 3.10+, MariaDB 10.6+ (tested with 12.3), and MongoDB 8.0+ (tested with 8.0.12). Both database services must be running locally or accessible through your configured connection. No frontend build tool is required.

```sh
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your own SQL credentials, database names, MongoDB URI, a random session secret and `PORT=5050`. Virtual environments are optional; use the Python environment appropriate for your machine. Never commit `.env` or credentials.

The setup command needs a SQL account allowed to create tables and import data in the selected database. A local database administrator can provision an account, for example:

```sql
CREATE DATABASE pokedex_battle CHARACTER SET utf8mb4;
CREATE USER 'pokedex'@'localhost' IDENTIFIED BY 'replace-with-your-local-password';
GRANT ALL PRIVILEGES ON pokedex_battle.* TO 'pokedex'@'localhost';
```

For a local socket connection, set `SQL_SOCKET` to your MariaDB socket path. Otherwise use `SQL_HOST` and `SQL_PORT`. Credentials in `.env.example` are placeholders, not working accounts.

Load the environment and initialize both databases:

```sh
set -a
source .env
set +a
python3 -m scripts.setup_databases --fetch-dark
python3 scripts/run_local.py
```

`setup_databases` creates missing schema objects and upserts catalogue records; it does not reset trainer collections, teams or history. `--fetch-dark` retrieves only the missing Dark-type resource if it is not already cached. Existing raw files are reused. Restart the app after changing imported catalogue data because it caches catalogue lookups in memory.

On the original development computer, MongoDB was installed in ignored `.local/mongodb/`, with storage in `.local/mongo-data/`. The launcher can restart that local binary when needed. Other machines must install/configure their own MongoDB service; these binaries and database files are not in Git. An existing local MariaDB service is reused, not installed by the launcher.

## Five implemented features

| Feature | Current behaviour | Database work |
| --- | --- | --- |
| Pokédex | Browse all 151, search name/ID, filter by type, inspect stats and move pools | Parameterized SQL queries, joins and a nested type-membership query |
| Team Builder | Starter selection, collection, saved-team CRUD, 1–6 members, four distinct eligible moves each | Transactions, ownership foreign keys, slot checks and uniqueness constraints |
| Team Analysis | Stat totals/averages, type distribution, defensive matchups and selected-move coverage | SQL aggregates and joins; combined type multipliers calculated in the backend |
| Battle Simulator | System-generated equal-size opponents, three difficulties, move/switch turns, HP/PP, rewards | Relational catalogue/collections; MongoDB state, snapshots and turn events |
| Battle Analytics | History/resume, win rates, difficulty results, Pokémon appearances, move usage, turns and duration | MongoDB aggregation pipelines |

## Rules and limits

Read the [implemented battle rules](docs/database-design/battle-rules.md) and [relational ER diagram](docs/diagrams/relational-er.md).

- Current cached values for the original 151; not historical Generation I mechanics.
- Four moves selected from a fixed supported pool. Moves use simplified single-hit damage; status effects, abilities, weather, held items, charging and secondary effects are omitted.
- New battles use rules v2: a hit deals at most 40% of the defender's maximum HP, for both sides. This gives healthy Pokémon time to respond. Weakened Pokémon can still faint; type immunity still deals zero damage. Older saved battles retain their original rules and history.
- Ditto, Kakuna, Metapod, Magikarp and Weedle have explicitly labelled project-specific move-pool exceptions to support four selectable attacks.
- Opponent generation uses team strength and type matchups. Difficulty is a heuristic, not a calibrated win-rate guarantee.
- Reward odds are Common 60%, Uncommon 25%, Rare 12%, Legendary/Mythical 3%. Duplicates are allowed. Rarity is a project-defined mapping, not an official Pokémon classification.
- HP/PP reset each battle. No experience, evolution, multiplayer or account authentication in this version.
- One active battle per trainer. Revisions prevent duplicate turn submissions. A unique reward key prevents duplicate awards across MongoDB/SQL retries.
- Statistics include completed battles, draws and forfeits. Duration includes player thinking time. Pokémon appearances count a species once per team per battle.
- The UI loads sprites from the PokéAPI sprite repository and fonts from Google Fonts; text and controls remain usable when those assets are unavailable.

## Raw data and processing

Source: [PokéAPI v2](https://pokeapi.co/docs/v2/). Complete raw JSON response bodies remain unchanged under `data/raw/`:

| Folder | Resources |
| --- | ---: |
| `pokemon/` | 151 |
| `species/` | 151 |
| `types/` | 18 (17 Pokémon-referenced types plus Dark, needed by moves) |
| `moves/` | 592 unique referenced moves |

The downloader uses sequential requests, a short delay, timeouts, and a local cache. Cached files cause no HTTP request. Invalid cache files are reported without being overwritten.

```sh
# Reuse the original 151-resource scope and fill any missing references.
python3 scripts/data_import/fetch_pokeapi.py --start-id 1 --end-id 151
# Reproduce stats and types: 151 Pokémon rows, 218 type relationships.
python3 scripts/data_import/process_pokemon.py
# Optional original small experiment, written to data/processed/sample/.
python3 scripts/data_import/process_pokemon.py --sample
# Reproduce the gameplay catalogue, without network access.
python3 scripts/data_import/prepare_game_data.py
```

`data/processed/game_data.json` contains 151 Pokémon, 18 types, 353 supported moves, 218 Pokémon-type relationships, 8,103 eligible Pokémon-move relationships and 324 type-effectiveness pairs. Every move-pool override is identified with `source: project_override`. Battle data comes from our own simulator, separately from PokéAPI.

## Verification

Run offline tests:

```sh
python3 -m unittest discover -s tests -v
```

To reproduce the battle-pacing comparison (180 seeded starter battles per rule version, in memory, with no saved battles or rewards):

```sh
python3 -m scripts.check_battle_balance
```

Integration tests use real database services and **uniquely named disposable test databases**. They require a SQL account with permission to create and drop those test databases. Load the configured credentials as above, then run:

```sh
RUN_DB_TESTS=1 python3 -m unittest discover -s tests -v
```

Optional browser checks require a running app. They create a labelled test trainer and real battle history in the selected application's databases:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 scripts/check_browser.py
```

The browser check covers all five screens, all difficulties, reload/resume, reward collection, team CRUD and a mobile viewport. It writes screenshots to ignored `.local/`. Battles are randomized; if no victory occurs in a browser run, rerun to exercise the reward screen. Backend reward tests use controlled randomness.

## Repository guide

- `backend/`: Flask entry point, shared database helpers and the five feature modules.
- `frontend/`: browser page, CSS and JavaScript.
- `database/relational/`: MariaDB schema.
- `database/nosql/`: MongoDB battle validation rules; setup also creates indexes.
- `scripts/`: raw collection, processing, database setup, app launcher and optional browser check.
- `tests/`: data, battle-rule and real-database integration tests.
- `data/raw/`, `data/processed/`, `data/generated/`: source data, prepared data and future generated exports. Live battles reside in MongoDB.
- `docs/`: design decisions, diagrams and verification notes.
- `.local/`: ignored local binaries, database storage, logs and screenshots.

Pokémon names and sprites belong to their respective owners. See [PokéAPI's project information](https://pokeapi.co/about/) for source attribution. Data selection and simplified mechanics are documented for this educational project.
