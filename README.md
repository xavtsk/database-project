# INF2003 Group 13

## INF2003 Database Systems Group Project

A five-person university database project combining a Pokémon collection and battle application with **MySQL** and **MongoDB**. The original 151 Pokémon are available in a Pokémon-coloured browser interface. Repository name: `pokedex-battle-analytics`.

The playable prototype is on `feature/core-features`. Its database schema and simplified mechanics follow the [approved design](docs/database-design/playable-prototype-proposal.md). This is a local demonstration with selectable trainer profiles, not an authenticated public service.

See the [application architecture](docs/diagrams/application-architecture.md) for the data flow and proposed EXP, levels and evolution extension. Progression is not implemented yet.

## Play locally

After completing the [Windows MySQL setup](docs/database-design/mysql-setup.md) and starting both databases, run from the repository root:

```sh
python scripts/run_local.py
```

Open **http://127.0.0.1:5050**. If an existing app is already running there, open that address without starting a second copy.

1. Click **Choose trainer**, create a profile and select Bulbasaur, Charmander or Squirtle.
2. In **Collection & teams**, edit the initial team, stay within 30 points and select four distinct moves for each member. Save the team.
3. Review **Team analysis** for stats, type weaknesses, selected-move coverage and recommended partners.
4. In **Battle arena**, select a saved team and Easy, Medium or Hard. Review the pre-battle prediction, then pick a move each turn or switch Pokémon.
5. After a win, click **Open reward case** to reveal your Pokémon with a scrolling case animation, or skip straight to the reveal. The reward enters your collection automatically. Add it to a team if desired. Review **Battle analytics** for history, win rates, usage and duration.

Teams can contain 1–6 Pokémon. Reloading resumes an active battle. Saved-team edits do not change an existing battle's snapshots. Reopening a winning battle retries any pending reward delivery without awarding twice.

Victory cases show the server's saved reward; opening, skipping or replaying the visual never rolls or grants another Pokémon. Revealed cases are remembered in the current browser. Reduced-motion settings reveal the reward immediately. A failed sprite or decorative catalogue request does not prevent the reward text from appearing.

## Team budget, recommendations and predictions

These extensions follow the [approved design](docs/database-design/predictions-recommendations-proposal.md).

- **Team Builder:** each Pokémon costs `ceil(total six base stats / 100)` points, with a **30-point team budget**. For example, Squirtle's 314 total stats cost 4 points. Costs and remaining budget update as you edit. The server checks the limit on save and before starting a battle. Existing teams stay visible; teams above the limit must be adjusted before saving or starting a new battle. Existing active battles continue under their saved rules.
- **Team Analysis:** recommended partners come from your own collection outside the selected saved team. Suggestions reduce average defensive exposure or improve selected-move coverage while staying in budget. Full teams receive replacement suggestions; empty teams receive affordable choices. Suggested default moves and before/after figures are shown. Review and save changes in Team Builder; recommendations never edit teams automatically.
- **Battle Arena:** each new battle displays **favoured / evenly matched / disadvantaged** before the first turn, based on both actual teams and selected moves. The prediction is saved with the starting snapshots and stays fixed when resuming. Accuracy, damage caps and type effectiveness affect the score. Speed and base stats are supporting explanations; the score does not simulate a complete battle and is not a win probability.
- **Historical evidence:** MongoDB supplies counts from your own prior battles. Prediction context matches rules, difficulty and team size; recommendation context describes species appearances. Forfeits are excluded from both. Different teams and opponents may be included, and small samples are labelled. Context does not change the heuristic prediction.
- **Battle Analytics:** predictions are compared with outcomes, grouped by method and battle rules, with counts for wins, losses and draws. Favoured wins and disadvantaged losses are correct directional calls; evenly matched labels and draws are shown separately. Older battles without predictions remain readable and are excluded from prediction evaluation.

After updating an existing installation, load `.env` and rerun database setup to apply the MongoDB validator. No new dependencies or relational table changes are required. From PowerShell or another shell, this command loads the existing local configuration before setup:

```sh
python -c "from scripts.run_local import load_environment; load_environment(); from scripts.setup_databases import setup; setup()"
```

Then restart the app and try Collection & teams → Team analysis → Battle arena → Battle analytics. New trainers need battle rewards before additional owned Pokémon can be recommended. Historical Kaggle 1v1 data has **not** been imported; dataset inspection and identifier mapping are pending.

## Set up another computer

Requirements: Python 3.10+, **MySQL Server 8.0.19+ (8.4 LTS recommended)**, and MongoDB 8.0+. Earlier prototype verification used MariaDB; see the [MySQL switch notes](docs/progress-report/mysql-switch-verification.md) for current checks. MySQL Workbench is the database client; install MySQL Server separately. Both database services must be running locally or accessible through your configured connection. No frontend build tool is required.

```sh
python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your own MySQL project-account credentials, database names, MongoDB URI, a random session secret and `PORT=5050`. The project defaults to `SQL_PORT=3307` so the existing MariaDB service on 3306 does not conflict; set this to your actual MySQL port. Virtual environments are optional; use the Python environment appropriate for your machine. Never commit `.env` or credentials.

The setup command needs a MySQL account allowed to create tables and import data in the selected database. A local database administrator can provision an account, for example:

```sql
CREATE DATABASE IF NOT EXISTS pokedex_battle CHARACTER SET utf8mb4;
CREATE USER 'pokedex'@'localhost' IDENTIFIED BY 'replace-with-your-local-password';
GRANT ALL PRIVILEGES ON pokedex_battle.* TO 'pokedex'@'localhost';
```

For a local Unix socket connection, set `SQL_SOCKET` to your MySQL socket path. Otherwise use `SQL_HOST` and `SQL_PORT`. Credentials in `.env.example` are placeholders, not working accounts.

Initialize both databases (`.env` is loaded automatically):

```sh
python -m scripts.setup_databases
python scripts/run_local.py
```

`setup_databases` verifies the MySQL server version, creates missing InnoDB schema objects and upserts catalogue records using MySQL row aliases; it does not reset trainer collections, teams or history. `--fetch-dark` retrieves only the missing Dark-type resource if it is not already cached. Existing raw files are reused. Restart the app after changing imported catalogue data because it caches catalogue lookups in memory.

On the original development computer, MongoDB was installed in ignored `.local/mongodb/`, with storage in `.local/mongo-data/`. The launcher can restart that local binary when needed. Other machines must install/configure their own MongoDB service; these binaries and database files are not in Git. The launcher uses the configured MySQL Server; it does not install or start MySQL. Setup and startup reject connections to MariaDB. The existing MariaDB service may stay installed on its own port.

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
python scripts/data_import/fetch_pokeapi.py --start-id 1 --end-id 151
# Reproduce stats and types: 151 Pokémon rows, 218 type relationships.
python scripts/data_import/process_pokemon.py
# Optional original small experiment, written to data/processed/sample/.
python scripts/data_import/process_pokemon.py --sample
# Reproduce the gameplay catalogue, without network access.
python scripts/data_import/prepare_game_data.py
```

`data/processed/game_data.json` contains 151 Pokémon, 18 types, 353 supported moves, 218 Pokémon-type relationships, 8,103 eligible Pokémon-move relationships and 324 type-effectiveness pairs. Every move-pool override is identified with `source: project_override`. Battle data comes from our own simulator, separately from PokéAPI.

## Verification

Run offline tests:

```sh
python -m unittest discover -s tests -v
```

To reproduce the battle-pacing comparison (180 seeded starter battles per rule version, in memory, with no saved battles or rewards):

```sh
python -m scripts.check_battle_balance
```

Integration tests use real MySQL/MongoDB services and **uniquely named disposable test databases**. They require a MySQL test account with permission to create and drop those test databases. The regular app account has access only to the application database. In PowerShell, load a test account into the environment and run:

```sh
$env:RUN_DB_TESTS = '1'
python -m unittest discover -s tests -v
```

Optional browser checks require a running app. They create a labelled test trainer and real battle history in the selected application's databases:

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/check_browser.py
```

The browser check covers all five screens, all difficulties, reload/resume, reward collection, team CRUD and a mobile viewport. It writes screenshots to ignored `.local/`. Battles are randomized; if no victory occurs in a browser run, rerun to exercise the reward screen. Backend reward tests use controlled randomness.

## Repository guide

- `backend/`: Flask entry point, shared database helpers and the five feature modules.
- `frontend/`: browser page, CSS and JavaScript.
- `database/relational/`: MySQL InnoDB schema.
- `database/nosql/`: MongoDB battle validation rules; setup also creates indexes.
- `scripts/`: raw collection, processing, database setup, app launcher and optional browser check.
- `tests/`: data, battle-rule and real-database integration tests.
- `data/raw/`, `data/processed/`, `data/generated/`: source data, prepared data and future generated exports. Live battles reside in MongoDB.
- `docs/`: design decisions, diagrams and verification notes.
- `.local/`: ignored local binaries, database storage, logs and screenshots.

Pokémon names and sprites belong to their respective owners. See [PokéAPI's project information](https://pokeapi.co/about/) for source attribution. Data selection and simplified mechanics are documented for this educational project.
