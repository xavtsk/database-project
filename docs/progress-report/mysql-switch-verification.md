# Switch from MariaDB to MySQL

The user explicitly requested MySQL on 2026-10-19. This supersedes the prototype's earlier MariaDB selection. Existing feature changes on `feature/core-features` were preserved.

## Changes

- Relational setup and app startup verify the configured server is MySQL 8.0.19+; MySQL 8.4 LTS is recommended. Connections to MariaDB receive a configuration message before schema writes.
- Default SQL port is 3307, matching the documented plan to run MySQL alongside the existing MariaDB service on 3306. Any other installed MySQL port remains configurable through `SQL_PORT`.
- `requirements.txt` uses `PyMySQL[rsa]` for the default MySQL `caching_sha2_password` authentication. No replacement driver is required.
- The schema requests InnoDB explicitly. Its existing primary/unique keys, composite ownership foreign keys and CHECK constraints are retained.
- Catalogue upserts use MySQL's inserted-row aliases instead of deprecated `VALUES(column)` references. Tables and IDs are not redesigned.
- The setup CLI loads `.env` automatically and supports `--sql-only`; full setup and the browser application still require MongoDB.
- `.env.example`, README and current architecture guidance now describe MySQL. The prototype proposal has an explicit dated override; earlier MariaDB verification results remain historical evidence.
- The local ignored `.env` had port 3306 changed to 3307. Its username, password and other settings were preserved. It still requires a valid account for the new MySQL installation.

## Verification

Unittest discovery completed **48 tests: 39 passed, 9 live database tests skipped**. Added checks cover supported versions, rejection of MariaDB/older versions, a read-only server probe, the local default port and environment overrides. Existing data-processing, battle and team-advice tests still pass.

`git diff --check`, Python syntax parsing and JavaScript syntax checking also passed.

The environment inspection found a running MariaDB service and MySQL Workbench, but no installed MySQL Server service or server directory. MongoDB is also unavailable locally. No claim is made that schema creation, upserts, RSA authentication or the full application have been tested against a real MySQL instance in this checkout. The new RSA extra is declared in requirements; install requirements before connecting to MySQL. Offline tests used the existing ignored test drivers.

## Run the real verification

Follow `docs/database-design/mysql-setup.md` to install MySQL Server, create the project account and configure `.env`.

```cmd
python -m pip install -r requirements.txt
python -m scripts.setup_databases --sql-only
```

Inspect tables in MySQL Workbench on port 3307. Repeat SQL-only setup to check idempotent imports. Start MongoDB and run full setup before launching the app:

```cmd
python -m scripts.setup_databases
python scripts/run_local.py
```

For integration tests, configure an account authorized to create/drop uniquely named temporary test databases and set `RUN_DB_TESTS=1`. Run `python -m unittest discover -s tests -v`. The normal app account is scoped to the application database, so use separate test credentials. Check trainer/starter → teams/budget → recommendations → battle/prediction → reward/history/analytics in the browser.

## Files created

- `tests/test_mysql_setup.py`
- `docs/database-design/mysql-setup.md`
- `docs/progress-report/mysql-switch-verification.md`

## Files modified for this switch

- `requirements.txt`
- `.env.example`
- `backend/config.py`
- `backend/db.py`
- `backend/app.py`
- `backend/team_analysis/service.py`
- `database/relational/schema.sql`
- `scripts/setup_databases.py`
- `scripts/run_local.py`
- `tests/test_app_integration.py`
- `README.md`
- `docs/diagrams/application-architecture.md`
- `docs/database-design/playable-prototype-proposal.md`
- `docs/database-design/predictions-recommendations-proposal.md`
- `.env` (ignored local configuration; never committed)

## Remaining environment work

MySQL Server installation and real database verification remain pending. This change does not stop/uninstall MariaDB or migrate existing MariaDB application rows. Existing populated MongoDB history must not be paired with new unrelated trainer IDs; review migration first if old trainer/history data needs preserving. No external Pokémon dataset was downloaded, and no push or merge was performed.
