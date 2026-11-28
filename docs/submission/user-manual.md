# User manual: Pokédex and Battle Analytics

**Using the team's existing cloud databases for assessment?** Follow the
[cloud assessor setup guide](cloud-assessor-guide.md). That route installs the
application and client tools, uses separately supplied credentials, and does
not initialise or import into the shared databases. The instructions below
cover an independent database installation.

This manual covers creating independent databases and running the application
locally. For assessment using the supplied cloud databases, start with the
cloud assessor setup guide linked above.

## 1. Install and configure

Use the provided source folder, including `data/raw/` and `data/processed/`.
The current application has been exercised with Python 3.13 and MySQL 8.4 LTS.
Install Python, MySQL Server and MongoDB Community Server, or use your own
Atlas database. MySQL Workbench is an optional client, not the database server.
Keep local database services listening on localhost for this demonstration.

Provision a project database/user using the
[Windows MySQL instructions](../database-design/mysql-setup.md). The account
needs setup privileges on its project database. To avoid touching a team's
shared data, use an independent local database/account. The MongoDB setup
account must be allowed to create/configure the collection, validator and
indexes in its selected database; a fresh Atlas database may need project-DB
`dbAdmin` in addition to `readWrite` during setup, then remove the extra setup
role for normal use. Do not use an Atlas account administrator as the app user.

Open a terminal in the source root and install application dependencies:

```text
python -m pip install -r requirements.txt
```

Create your private environment file. In **Command Prompt**:

```bat
copy .env.example .env
```

Or in **PowerShell**:

```powershell
Copy-Item .env.example .env
```

Edit `.env` using your own values. SQL_PORT must match the running MySQL
service (commonly 3306; the original development computer used 3307). Set
SQL_DATABASE and MONGO_DATABASE to your independent project databases.
Set SQL_USER/SQL_PASSWORD and MONGO_URI appropriately; keep credentials private.
Use an independent secret for Flask sessions:

```text
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste that value into FLASK_SECRET_KEY. The command prints only a newly
generated secret; it does not require a database password as a command argument.

Start the selected MySQL and MongoDB services, then initialize:

```text
python -m scripts.setup_databases
```

This loads the cached playable catalogue and creates tables/views plus the
MongoDB validator/indexes. It does not copy the owner's live collection/battle
history. It creates historical tables, but import their cached dataset separately:

```text
python -m scripts.data_import.import_historical
```

The historical importer verifies the reviewed source/mapping. It does not
create MongoDB simulator history. No new online dataset download is required
when the supplied raw cache is complete.

## 2. Run and check

```text
python -m scripts.run_local
```

Leave that terminal running. Open `http://127.0.0.1:5050` and
`http://127.0.0.1:5050/api/health`. Health should report both databases ready.
If port 5050 is occupied, stop the old app you started or configure a free PORT
in your own `.env`. Changing `.env` or backend code requires an app restart.

## 3. Demonstrate the features

1. Choose/create a labelled demonstration trainer and select a starter.
2. Browse/filter species and inspect stats, types, damaging moves and miss rate.
3. In Collection & teams, create a team, choose four eligible distinct moves per
   member and save. Edit and delete an extra demonstration team to show CRUD.
4. Open Team analysis. Explain SQL aggregates, weaknesses, coverage and partner
   recommendations. A fresh collection may have no unused candidate yet.
5. Start a battle. Show its saved starting prediction, manual/Auto Battle,
   switching and event messages. Reload to demonstrate saved-state recovery.
6. Complete battles to populate history and the collection. A win awards a saved
   Pokémon; the case animation reveals it. Random outcomes do not guarantee a
   shiny, legendary or win in any fixed number of attempts.
7. Open Battle analytics. Explain rules/difficulty filters, sample counts,
   recorded move accuracy/damage, prediction outcomes and 1v1 observations.
8. To populate 1v1 evidence, save a team with one member and finish battles.
   Select a species pair actually present in those results; larger-team battles
   and forfeits do not contribute to that panel. Small-sample warnings are expected.

The application uses selectable profiles for a local demonstration; it is not
public multi-user authentication. Keep the local server on loopback. This
independent installation uses your own databases and does not require access
to the team's cloud VM.

## 4. Checks and troubleshooting

Offline Python checks:

```text
python -m unittest discover -s tests -v
```

If Node.js is available, run the dependency-free JavaScript behaviour checks:

```text
node --test tests/frontend_analysis.test.cjs tests/frontend_catalogue.test.cjs tests/frontend_rewards.test.cjs
```

Database integration tests are opt-in and some create/drop disposable databases.
Use isolated test credentials/databases and the instructions in README. A skipped
integration test is not evidence that the live write flow was tested.

After winning battles in your isolated demo, a read-only equivalent-fact
comparison is available:

```text
python -m scripts.benchmark_databases --samples 7
```

It requires at least one delivered reward recorded in both SQL and MongoDB.
The comparison measures read latency for matching reward facts; hosting,
network conditions and data models affect the results. It does not measure
throughput or isolate database-engine performance.

| Symptom | Check |
| --- | --- |
| `python` not recognised | Install Python and reopen the terminal with Python available on PATH |
| Access denied in MySQL | Actual project account/password, project DB grants and configured host/port |
| MongoDB unavailable | Local service or Atlas URI/credentials/allowed IP; check the selected DB |
| Empty analytics | Fresh setup has no simulator history; complete actual demo battles |
| No recommendations | No unused affordable owned candidate improves the selected team; collect more or show the empty-result explanation |
| Missing catalogue | Run setup with the intended database after checking `.env` |
| HTML instead of API JSON | Restart the app after updating backend routes, then refresh |
| Cloud port 3308 unavailable | Start your authorised SSH tunnel first; local-only installations do not need it |
