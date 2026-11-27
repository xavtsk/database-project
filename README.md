# PokéDB — INF2003 Group 13

PokéDB is a Pokémon collection, team analysis and battle-history application built with Flask, MySQL and MongoDB. It supports the original 151 species, saved teams built from owned copies, simplified battles and database-computed analytics.

## Start here

Choose the setup route that matches the databases you will use:

| Setup route | Instructions |
| --- | --- |
| **Assessment using the team's existing cloud databases** | Follow the [cloud assessor guide](docs/submission/cloud-assessor-guide.md). Install Python and Google Cloud CLI, obtain access and credentials privately, start your SSH tunnel, then run the app. The databases and data are already initialised. |
| **Independent installation with your own databases** | Follow the [user manual](docs/submission/user-manual.md). Install/configure MySQL and MongoDB, create an application account, then build the schema and import the supplied cached data. |

The cloud route runs the application on the assessor's computer. The team's personal computer does not need to stay on; the Google Cloud VM and Atlas cluster must remain available. It uses shared data, so use your own labelled demonstration trainer and teams.

Do not run database setup, imports, migrations or database-write tests against the shared assessment connection. Use independent databases and appropriate test credentials for those operations.

Commands must be run from the project root, the folder containing this README, `requirements.txt`, `backend` and `scripts`. After completing either setup guide, start the application with:

```text
python scripts/run_local.py
```

Open [the application](http://127.0.0.1:5050) and [database health](http://127.0.0.1:5050/api/health). The health response should be:

```json
{"mongodb":"ready","sql":"ready"}
```

The cloud route requires the SSH tunnel to remain running in a separate terminal. Its guide uses the virtual environment's Python explicitly; use the same interpreter that installed your dependencies. `.env.example` contains placeholders only. Actual `.env`/`.env.cloud` files, passwords and SSH keys must be supplied or created privately and kept out of Git.

## Requirements

- Python 3.13 was used for project verification; the Python source supports 3.10 or later.
- Runtime packages are listed in [requirements.txt](requirements.txt). No Node.js build step is required to run the application.
- Independent databases require MySQL Server 8.0.19 or later, with 8.4 LTS recommended, and MongoDB 8.0 or later. MySQL Workbench and MongoDB Compass are optional clients.
- Internet access is needed for the cloud connections and external Pokémon sprites/fonts. The data supplied in the repository can be processed without downloading it again.

## Application features

| Feature | Behaviour | Database work |
| --- | --- | --- |
| Pokédex | Browse species, search by name/ID, filter by type and inspect supported moves | Parameterised SQL search, joins and nested type membership query |
| Collection and teams | Select one starter, manage owned copies, create/read/update/delete saved teams | Ownership foreign keys, transactions, row locks and cascades |
| Team analysis | Totals, averages, weaknesses, selected-move coverage and owned-partner recommendations | SQL views, aggregates, CTEs, `NOT EXISTS` and `ROW_NUMBER()` ranking |
| Battle arena | Manual or automatic battles, saved state, predictions, three difficulties and victory rewards | SQL catalogue/ownership and reward transactions; revision-checked MongoDB battle documents |
| Battle analytics | History, move usage, damage per attempt, repetition, prediction outcomes and observed 1v1 results | MongoDB aggregation over snapshots and nested turn events |

Trainer profiles are demonstration selections, not password-protected user accounts. Applications connected to the same databases can select the same profiles. The server binds to localhost for this project demonstration.

Teams may contain up to six members within 30 points, with four distinct eligible moves per member. A draft may be empty; entering battle requires at least one member. Each owned copy can appear once per team. The same legendary species can appear only once per team across normal/shiny variants. Recommendations propose additions or replacements and do not edit the saved team automatically.

New battles use `prototype-2` rules, including the 40% maximum-HP per-hit damage cap. Older battles retain their recorded rules. The opponent matches your starting team size. The project uses simplified single-hit attacks and omits status/secondary effects, abilities, items and critical hits. Read the [battle rules](docs/database-design/battle-rules.md), [collection/reward rules](docs/database-design/collection-rewards.md) and [Auto Battle behaviour](docs/database-design/auto-battle.md) for details.

## Database design

MySQL contains 15 application/catalogue/historical tables and three analysis views. Composite ownership foreign keys ensure saved team members belong to the team's trainer. MongoDB holds battle starting snapshots, changing state and turn events, with validation and indexes including one active battle per trainer.

- [Application architecture](docs/diagrams/application-architecture.md)
- [Relational ER relationships and constraints](docs/diagrams/relational-er.md)
- [MongoDB document model](docs/diagrams/mongodb-model.md)
- [Database evidence and metric definitions](docs/database-design/database-evidence.md)
- [Normalisation decisions and trade-offs](docs/database-design/normalisation-reference.md)

Expand **Database evidence**, **View SQL** or **View MongoDB** on the website to inspect explanatory excerpts and source filenames. In-page help defines recommendation scores, rules versions, difficulty, filter scope and prediction limits. The excerpts are reference text and do not execute queries.

## Supplied data and attribution

[PokéAPI v2](https://pokeapi.co/docs/v2/) supplies the cached catalogue data. Unmodified raw responses include 151 Pokémon, 151 species, 18 types and 592 referenced moves. The audited playable catalogue contains 151 Pokémon, 18 types, 353 supported damaging moves, 218 Pokémon/type links, 8,103 eligible Pokémon/move links and 324 type-effectiveness pairs. Project-specific move-pool additions are labelled `project_override` and marked with ★ in the application.

The separately cached [Weedle's Cave Pokémon Challenge dataset](https://www.kaggle.com/datasets/terminus7/pokemon-challenge) contains 800 entries, 50,000 synthetic 1v1 results and 10,000 unlabelled matchups. Its external IDs, forms and rules differ from the simulator. Reviewed mappings and historical SQL tables preserve that source separately; it does not populate the website's simulator matchup results or determine recommendation ranking. See the [historical import design](docs/database-design/historical-import-proposal.md).

Pokémon names and sprites belong to their respective owners. Sprites are loaded from the PokéAPI sprite repository. Prepared data and source manifests are included under `data/`; live trainer collections and simulator history reside in the configured databases and are not a database dump in this repository.

## Verification

Run offline checks from the project root. In PowerShell, explicitly disable opt-in database tests:

```powershell
$env:RUN_DB_TESTS = '0'
$env:RUN_QUERY_TESTS = '0'
python -m unittest discover -s tests -v
python -m scripts.data_import.audit_game_data
```

Database-dependent tests are skipped in this mode. Their skipped status is not a fresh live-database pass. If Node.js is available, the frontend checks require no npm packages:

```text
node --test tests/frontend_analysis.test.cjs tests/frontend_catalogue.test.cjs
```

Earlier real-database test results and their reproduction instructions are retained in [the test evidence](docs/progress-report/test-results/README.md). Opt-in query fixtures roll back SQL writes and create disposable MongoDB collections. The full integration tests create/drop uniquely named test databases and need a dedicated SQL test account. Configure those credentials privately and use an isolated test environment; do not enable the flags on the shared assessment account.

Optional browser checks use [requirements-dev.txt](requirements-dev.txt). Some create demonstration records, so inspect their instructions and use an agreed test environment before running them. They are not needed to start the application.

The [recorded database comparison](docs/progress-report/database-comparison-results.json) verifies equivalent delivered-reward facts and reports warm-read latency. Its deployments, network paths and data representations differ; it does not measure throughput, concurrent-user performance or isolated database-engine speed.

## Repository contents

| Folder | Contents |
| --- | --- |
| `backend/` | Flask routes, database connections, services and battle engine |
| `frontend/` | Browser page, styles, scripts and local arena artwork |
| `database/` | MySQL schema/views/queries and MongoDB validator |
| `data/raw/`, `data/processed/` | Cached source data, provenance and prepared catalogue/mappings |
| `scripts/` | Data audits/imports, setup, launcher and optional verification tools |
| `tests/` | Offline, frontend and opt-in database tests |
| `docs/submission/` | The two assessor installation/user guides |
| `docs/database-design/`, `docs/diagrams/` | Design explanations and relationships |
| `docs/progress-report/` | Dated verification records and recorded evidence |
| `docs/development/` | Archived team preparation notes, separate from assessor setup |

Development history and earlier workstation instructions are preserved in the [development archive](docs/development/README.md). Use the two setup guides at the top for the current assessment routes.
