# INF2003 Group 13

## INF2003 Database Systems Group Project

A five-person university database project combining a Pokémon collection and battle application with **MySQL** and **MongoDB**. The original 151 Pokémon are available in a Pokémon-coloured browser interface. Repository name: `pokedex-battle-analytics`.

The playable prototype is on `feature/core-features`. Its database schema and simplified mechanics follow the [approved design](docs/database-design/playable-prototype-proposal.md). This is a local demonstration with selectable trainer profiles, not an authenticated public service.

See the [application architecture](docs/diagrams/application-architecture.md) for the data flow and proposed EXP, levels and evolution extension. Progression is not implemented yet.

For presentation preparation, start with the [project explanation guide](docs/database-design/project-explanation-guide.md). It walks through each feature in plain English: the user action, database work, purpose and a short spoken explanation. It covers the MySQL/MongoDB split, useful queries, data preparation, transactions, battle analytics and measured limitations. Detailed normal-form examples are kept in an optional [normalisation reference](docs/database-design/normalisation-reference.md).

The [lecture-to-project map](docs/database-design/lecture-to-project-map.md) links the seven supplied INF2003 lecture PDFs to code and demo explanations, including functional dependencies, closure, BCNF, indexing and ACID transactions, with PDF page references.

The [Excellent-band readiness audit](docs/progress-report/rubric-readiness.md) maps the actual marking rubric to verified evidence and outstanding submission gates. It links the [user manual](docs/submission/user-manual.md), report/presentation plans and a reproducible read-only SQL/MongoDB comparison; it is not a claim that the final assessed deliverables are complete.

## Play locally

After completing the [Windows MySQL setup](docs/database-design/mysql-setup.md) and starting both databases, run from the repository root:

```sh
python scripts/run_local.py
```

Open **http://127.0.0.1:5050**. If an existing app is already running there, open that address without starting a second copy.

For the shared Google Cloud MySQL + MongoDB Atlas setup, start the MySQL SSH tunnel before launching the app. The original development computer uses private `.local/gcp/start-tunnel.cmd` and `.local/gcp/run-cloud.cmd` launchers in separate terminals. The first reconnects dropped SSH sessions; the second starts the app with the saved `.env` connection settings. Teammates should follow the [cloud connection guide](docs/database-design/google-cloud-mysql.md) with their own access. The local database services are unnecessary when both configured databases are in the cloud.

After updating backend code, restart the running app: press **Ctrl+C in its terminal**, run `python scripts/run_local.py` again, then refresh the browser. An old Python process can serve updated frontend files while still missing new API routes. This causes HTML 404 responses and errors such as `Unexpected token '<'` or the newer explicit restart message.

1. Click **Choose trainer**, create a profile and select Bulbasaur, Charmander or Squirtle.
2. In **Collection & teams**, edit the initial team, stay within 30 points and select four distinct moves for each member. Save the team.
3. Review **Team analysis** for stats, type weaknesses, selected-move coverage and recommended partners.
4. In **Battle arena**, select a saved team and Easy, Medium or Hard. Review the pre-battle prediction, then pick a move, switch Pokémon or click **Auto Battle**. Attacks, damage, misses and switches are animated. **Pause Auto Battle** lets you take over after the current submitted turn finishes.
5. After a win, click **Open reward case** to reveal your Pokémon with a scrolling case animation, or skip straight to the reveal. The reward enters your collection automatically. Add it to a team if desired. Review **Battle analytics** for history, win rates, usage and duration.

Teams can contain 1–6 Pokémon. Reloading resumes an active battle. Saved-team edits do not change an existing battle's snapshots. Reopening a winning battle retries any pending reward delivery without awarding twice.

New battle setup preselects the trainer's most recently used team that still exists and has members, including after a reload or clicking Battle again. Without a usable team in the latest 50 battles, it selects the first non-empty saved team. You can choose a different team before starting.

Each non-legendary species allows **six normal copies and six shiny copies separately** in your collection. Victory rewards have independent shiny chances of **1% on Easy, 2% on Medium and 3% on Hard**, with shiny colours, badges and sparkle animations. Legendary/mythical base rates are **3%, 5% and 7%** respectively. Collection cards are grouped by Pokédex number with separate variant counts. Teams allow **one of each legendary/mythical species**, counting normal and shiny together; different legendary species may share a team within the usual size/budget limits. Full reward variants are rerolled to another eligible Pokémon without changing the shiny result. See [collection and shiny rules](docs/database-design/collection-rewards.md).

Existing installations need the additive shiny-storage migration once, then an app restart and browser refresh. It has already been applied on this development computer. Other computers can run:

```sh
python -m scripts.migrate_collection_rewards
```

Fresh setup and `python -m scripts.setup_databases` also apply this migration. Existing owned Pokémon remain normal, and no collection entries are removed.

The collection panel matches the height of the roster section beside it and scrolls internally. On narrow screens it sits below the roster and is capped at 70% of the viewport height. Cards show type, rarity, cost and owned ID; buttons identify members already in the team, full teams and additions over budget. Move displays show hit/miss chances in the Pokédex, team builder and arena. Battle analytics also shows observed miss rate from the filtered saved attacks, which can differ from a move's listed chance.

Victory cases show the server's saved reward; opening, skipping or replaying the visual never rolls or grants another Pokémon. Revealed cases are remembered in the current browser. Reduced-motion settings reveal the reward immediately. A failed sprite or decorative catalogue request does not prevent the reward text from appearing.

Auto Battle chooses attacks on the server using accuracy, type effectiveness, remaining PP, target HP and the saved damage rules. It replaces fainted members automatically. Each auto decision and policy version is recorded in the MongoDB turn log. Leaving the battle screen, hiding the tab, reloading or a failed request pauses automation; an already submitted action can finish. Reload to resume the saved battle, then click Auto Battle again if desired. Reduced-motion settings skip battle movement effects while keeping each event message readable. See [auto-battle behaviour](docs/database-design/auto-battle.md).

The compact message box beneath the arena shows **one event at a time**: your move, the opponent's move, damage, **Super effective!**, **Not very effective.**, **No effect.**, misses, fainting and replacements. Messages follow saved event order and pause briefly for reading; the latest event remains visible afterward and on reload. The combined summary of both attacks stays removed, and the full battle log remains below. Floating damage/effectiveness labels are also retained. In the collection, **Owned #** identifies a specific owned copy, allowing separate normal/shiny or duplicate Pokémon to be tracked independently.

During battle, moves, Auto Battle and switching controls sit to the right of the arena on desktop. Prediction, the battle log and opponent matching appear below the battle. On narrow screens the controls stack below the arena, followed by the analysis panels.

The arena uses an original local pixel-art meadow background and grassy platforms. Your Pokémon appears in the lower-left foreground, facing an opponent in the upper-right; separate name/HP panels keep the sprites clear. The background needs no external image service. Existing front/back and shiny sprites still come from the PokéAPI sprite repository.

The auto-battle/animation update needs only an app restart and browser refresh; it adds no database migration or runtime dependency.

## Team budget, recommendations and predictions

These extensions follow the [approved design](docs/database-design/predictions-recommendations-proposal.md).

- **Team Builder:** each Pokémon costs `ceil(total six base stats / 100)` points, with a **30-point team budget**. For example, Squirtle's 314 total stats cost 4 points. Costs and remaining budget update as you edit. The server checks the limit on save and before starting a battle. Existing teams stay visible; teams above the limit must be adjusted before saving or starting a new battle. Existing active battles continue under their saved rules.
- **Team Analysis:** recommended partners come from your own collection outside the selected saved team. Suggestions reduce average defensive exposure or improve selected-move coverage while staying in budget. Full teams receive replacement suggestions; empty teams receive affordable choices. Suggested default moves and before/after figures are shown. Review and save changes in Team Builder; recommendations never edit teams automatically.
- **Battle Arena:** each new battle displays **favoured / evenly matched / disadvantaged** before the first turn, based on both actual teams and selected moves. The prediction is saved with the starting snapshots and stays fixed when resuming. Accuracy, damage caps and type effectiveness affect the score. Speed and base stats are supporting explanations; the score does not simulate a complete battle and is not a win probability.
- **Historical evidence:** MongoDB supplies counts from your own prior battles. Prediction context matches rules, difficulty and team size; recommendation context describes species appearances. Forfeits are excluded from both. Different teams and opponents may be included, and small samples are labelled. Context does not change the heuristic prediction.
- **Battle Analytics:** predictions are compared with outcomes, grouped by method and battle rules, with counts for wins, losses and draws. Favoured wins and disadvantaged losses are correct directional calls; evenly matched labels and draws are shown separately. Older battles without predictions remain readable and are excluded from prediction evaluation.
- **1v1 matchups from your battles:** compares two species using the selected trainer's completed MongoDB battles that started with one Pokémon per side. It counts both player/opponent orientations, shows wins/losses/draws and observed win rates, and follows the same rules/difficulty filters. Team battles and forfeits are excluded. The panel updates as qualifying battles are saved; it needs no Kaggle import.

After updating an existing installation, rerun database setup to apply the MongoDB validator, SQL analysis views and three approved historical tables, then restart the app. Setup loads `.env` automatically. No new runtime dependencies are required:

```sh
python -m scripts.setup_databases
python -m scripts.data_import.import_historical
```

Then restart the app and try Collection & teams → Team analysis → Battle arena → Battle analytics. New trainers need battle rewards before additional owned Pokémon can be recommended. The 1v1 matchup panel uses your own MongoDB battle history; pairs without qualifying battles show an empty state with instructions to build a one-member team and finish battles.

## Set up another computer

For the selected shared-database hosting plan, see the [low-cost Google Cloud MySQL setup](docs/database-design/google-cloud-mysql.md). It uses an `e2-micro` VM for MySQL and MongoDB Atlas for battle logs, with an SSH tunnel from each teammate's computer. Migration must preserve existing SQL IDs before switching the app.

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
| Team Analysis | Stat totals/averages, type distribution, defensive matchups, selected-move coverage and owned-partner recommendations | SQL views, CTEs, joins, aggregates and window ranking, including combined defensive multipliers |
| Battle Simulator | System-generated equal-size opponents, three difficulties, move/switch turns, HP/PP, rewards | Relational catalogue/collections; MongoDB state, snapshots and turn events |
| Battle Analytics | History/resume, win rates, usage, duration, rule/difficulty filters, damage per attempt, move repetition and prediction outcomes | MongoDB aggregation pipelines over embedded turn events |

## Rules and limits

Read the [implemented battle rules](docs/database-design/battle-rules.md) and [relational ER diagram](docs/diagrams/relational-er.md).

- Current cached values for the original 151; not historical Generation I mechanics.
- Four moves selected from a fixed supported pool. Moves use simplified single-hit damage; status effects, abilities, weather, held items, charging and secondary effects are omitted.
- New battles use rules v2: a hit deals at most 40% of the defender's maximum HP, for both sides. This gives healthy Pokémon time to respond. Weakened Pokémon can still faint; type immunity still deals zero damage. Older saved battles retain their original rules and history.
- Ditto, Kakuna, Metapod, Magikarp and Weedle have explicitly labelled project-specific move-pool exceptions to support four selectable attacks.
- Opponent generation uses team strength and type matchups. Difficulty is a heuristic, not a calibrated win-rate guarantee.
- Base reward tiers: Easy 60% common / 25% uncommon / 12% rare / 3% legendary; Medium 58% / 25% / 12% / 5%; Hard 56% / 25% / 12% / 7%. Independent shiny chances are 1% / 2% / 3% respectively. Non-legendary duplicates stop at six per variant; full variants are rerolled within the same tier when possible, otherwise among available tiers. Rarity is a project-defined mapping, not an official Pokémon classification.
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
# Audit cached sources and normalized keys/references; no SQL writes.
python -m scripts.data_import.audit_game_data
# Audit, then replace the staged catalogue only if the whole batch is valid.
python -m scripts.data_import.audit_game_data --stage
```

`data/processed/game_data.json` contains 151 Pokémon, 18 types, 353 supported moves, 218 Pokémon-type relationships, 8,103 eligible Pokémon-move relationships and 324 type-effectiveness pairs. Every move-pool override is identified with `source: project_override`. Battle data comes from our own simulator, separately from PokéAPI.

Setup runs the audited pipeline before SQL import. Its ignored `.local/import-audit.json` lists source hashes, validation issues, filtered moves and submitted table counts. See the [database evidence walkthrough](docs/database-design/database-evidence.md) for the parsing policy, SQL recommendation query, MongoDB metric definitions and query-plan command.

The approved [Weedle's Cave dataset](https://www.kaggle.com/terminus7/pokemon-challenge) is cached separately under `data/raw/historical/weedles_cave/`: 800 Pokémon entries, 50,000 synthetic 1v1 results and 10,000 unlabelled matchups. External IDs differ from Pokédex IDs. The [approved historical design](docs/database-design/historical-import-proposal.md) uses three MySQL tables, 150 reviewed base-form mappings and 1,589 distinct in-scope results. These tables, their importer and the read-only `/api/analytics/historical` endpoint remain available for earlier database work. The visible matchup panel now uses **our own simulator results in MongoDB** through `/api/analytics/matchups`; external rows do not contribute to it or change simulator predictions/recommendation rankings.

```sh
# Optional: verify/reuse the approved source cache, downloading only if absent.
python -m scripts.data_import.fetch_historical
# Inspect without database writes.
python -m scripts.data_import.inspect_historical
# Import approved mappings/results after setup; safe reruns verify existing rows.
python -m scripts.data_import.import_historical
```

The importer records an audit in `.local/historical-import.json`. It leaves the unnamed entry unresolved, excludes alternate forms from evidence, retains duplicate rows for traceability and excludes repeat copies from counts. Unlabelled test matchups are never treated as outcomes. The source algorithm and some base stats differ from this simulator; 1v1 rates are not team win probabilities.

## Verification

Run offline tests:

```sh
python -m unittest discover -s tests -v
```

The ten query-specific integration checks can use the regular `.env` account after setup. They roll back MySQL fixtures and use a separate disposable MongoDB database. PowerShell:

```powershell
$env:RUN_QUERY_TESTS = '1'
python -m unittest tests.test_database_queries tests.test_historical_queries -v
```

For the new analytics screen, `python scripts/check_database_evidence.py` runs controlled browser fixtures with API reads intercepted and no API writes. It requires the optional browser dependencies described below and a running app.

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

For Auto Battle, `python scripts/check_auto_battle.py` intercepts every API request and resolves in-memory fixture battles with the real engine. It checks manual/auto actions, animations, pause, navigation, errors, reduced motion, mobile layout and victory stopping without database writes. It uses the same optional browser dependencies as the other browser checks. `RUN_QUERY_TESTS=1` also enables two auto-battle persistence/reward tests using disposable MongoDB fixtures and rolled-back MySQL rows.

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
