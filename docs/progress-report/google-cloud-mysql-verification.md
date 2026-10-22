# Google Cloud MySQL migration verification

Date: 22 October 2026 (Asia/Singapore).

## Result

The existing project database was migrated to MySQL Community Server 8.4.13 on
the selected `e2-micro` VM in Oregon, project `pokedex-project-512319`, VM
`pokedex-mysql`, zone `us-west1-b`. MongoDB remains on Atlas. The app remains a
local Flask application; this work does not publish a public website.

The development computer's `.env` now selects the cloud MySQL database through
an SSH tunnel on `127.0.0.1:3308`. Its Atlas URI, MongoDB database and session
secret were preserved. Project database credentials and SSH keys are private,
ignored files. Root database credentials were entered by the owner in the VM's
SSH terminal and were not shared with the agent or stored in the repository.

## Data checks

The source was MySQL Community Server 26.7.0 on the development computer. The
local app was stopped during the final export. The export held read locks on
the 15 source tables while dumping and hashing their contents. The original
database and earlier backups remain intact.

The transfer package is in ignored
`.local/backups/mysql-cloud-transfer-20261022T075756892281Z/`. It contains the
original SQL dump, a manifest, the private restore package and an import script.
The script verifies its SQL checksum and creates a fresh project database and
account; it does not overwrite an existing database. The VM owner completed
the import, after which the cloud comparison passed:

- All 15 base tables contain exactly the same 60,145 rows, checked with ordered
  row-content SHA-256 hashes and sessions using UTC for timestamp comparisons.
- Next auto-increment values match the SQL dump's `CREATE TABLE` definitions.
  These definitions are authoritative for the restore, unlike potentially
  cached `INFORMATION_SCHEMA` statistics.
- All three analysis views exist and can be queried by the project account.
- Counts include 151 Pokémon, one trainer, five teams, 36 owned Pokémon and
  35 SQL reward records.
- Atlas still holds 65 battles, with analytics reporting 35 wins and 30 losses.

## Connection and application checks

Windows OpenSSH authenticated using the computer's registered OS Login public
key. Private key ownership/permissions were set for the actual Windows user
used by network-enabled commands. The MySQL tunnel binds to localhost only.

The running cloud MySQL configuration reports loopback binding, a 128 MB InnoDB
buffer pool, 25 maximum connections and disabled Performance Schema. The app
uses a project-scoped database account rather than root.

Read-only checks through Flask's test client against the real cloud databases
returned HTTP 200 for the page, health, session, Pokédex, collection, teams,
battle history, analytics, 1v1 matchups, team analysis and recommendations.
Health reports both SQL and MongoDB ready. The collection and teams match the
counts above. Battle history returns the latest 50 records as implemented;
analytics and the underlying collection confirm that all 65 are present.

No test trainers, Pokémon, rewards or battles were inserted. A new gameplay
write/reward cycle has not been simulated as part of these read-only checks.
The owner can test that using a normal battle after starting the app.

## Files and operation

Created: `docs/database-design/google-cloud-mysql.md` and this verification
record. Modified: `README.md` and the private, ignored `.env`. Private operational
files under `.local/gcp/` prepare/verify the transfer and start the SSH tunnel;
they add no runtime dependency or application feature. No application Python
code or logical database schema was changed.

From the project root, start `.\.local\gcp\start-tunnel.cmd` in one terminal and
leave it open, then run `.\.local\gcp\run-cloud.cmd` in another. This private
launcher reuses an existing listener on port 3308. Teammates need their own
cloud/SSH and database access; those users have not been provisioned by this
migration. The low-cost US VM may add latency compared with local databases.

## Startup connection recovery

During follow-up troubleshooting, the SSH connection ended with `Connection
reset`, closing port 3308 and reproducing a startup failure. Both database
connections and the full startup sequence had passed immediately beforehand.
The original terminal's inherited environment could not be inspected directly.

The private tunnel launcher now retries after five seconds if its SSH process
exits. The private `run-cloud.cmd` launcher clears inherited SQL/MongoDB
connection overrides only within its own process before running the app. The
normal environment precedence and explicit `PORT` overrides are preserved.

Modified `scripts/run_local.py` to warn about connection keys whose terminal
values differ from `.env`, printing names rather than values, and to replace
the generic setup message with service-specific, credential-safe diagnostics.
Created `tests/test_startup_diagnostics.py` to cover environment precedence,
quoted Atlas URIs, MySQL tunnel/auth/catalogue errors, MongoDB network/auth/URI
errors and credential redaction. The five new tests and four API-error tests
passed (`9 tests`). `git diff --check` passed.

After restarting the reconnecting tunnel and clean app launcher, actual HTTP
requests to `http://127.0.0.1:5050/` and `/api/health` returned 200. Health reports
both SQL and MongoDB ready. Player data was not changed or reimported during
this recovery. Unlike the earlier migration, this follow-up does change the
local Python launcher; the application backend and schema remain unchanged.

## Navigation performance follow-up

Updated `backend/db.py` and `backend/app.py` to reuse up to four exclusive MySQL
connections per app. Existing transaction commit/rollback boundaries remain;
failed connections are discarded and writes are not retried. No dependency or
schema was added. Idle sockets are checked after 30 seconds; connection settings
are captured at app creation, so changing `.env` requires an app restart.

Updated `frontend/static/app.js` to omit the unused collection download from
team analysis and display the main analysis before recommendations finish.
Recommendation errors stay within that panel, and responses for an earlier
screen cannot replace the current panel. Updated `frontend/index.html`'s script
version so refreshing loads the new JavaScript.

Paired read-only checks against the existing cloud databases, with the immutable
catalogue already warm, produced these individual request timings:

| Endpoint | Fresh connections | Reused connections |
| --- | ---: | ---: |
| Pokédex | 2.70 s | 0.85 s |
| Saved teams | 5.34 s | 1.44 s |
| Collection | 5.58 s | 1.44 s |
| Team analysis | 17.22 s | 4.48 s |
| Recommendations | 9.39 s | 2.99 s |

All five paired JSON response hashes matched, with status 200. This check did
not create or modify player records. The measurements exclude the first
catalogue load and are not full browser navigation timings. US-region latency
remains, and a cold/idle pool may need fresh connections.

Created `tests/test_sql_pool.py` for reuse, rollback/discard, failed commits,
idle reconnect checks, capacity after failed connects and concurrent exclusive
checkout. Created `tests/frontend_analysis.test.cjs` for early rendering,
late-response isolation and recommendation errors. Python discovery ran 118
tests: 82 passed, 36 database-dependent tests skipped. All three Node tests
passed, JavaScript syntax checking passed, and `git diff --check` passed.

## General performance follow-up

Standalone read queries now use autocommit, removing the extra `COMMIT` trip.
Grouped writes still use explicit `BEGIN`/commit/rollback. A standalone read
retries once after disconnect codes 2006/2013; authentication/query failures and
writes are never retried. This follows an observed connection reset during the
first comparison attempt, which was aborted and then rerun successfully.

Saved-team reads use a single ownership-filtered LEFT JOIN for the team, owned
members and selected moves. Empty teams, duplicate non-legendary species,
shiny flags and move-slot ordering are preserved. Team saves insert members as
one batch, then their moves as another batch within the same transaction.
Starter move inserts are also batched. No persistent schema or dataset changed.

The browser caches up to 20 successful reference-catalogue responses for the
current page session. Filters have distinct cache entries, failed responses
are not cached, and refreshing clears the cache. Profile/collection/team/battle
and analytics requests continue to fetch current data.

The successful paired comparison used existing player records without writes:

| Request | Initial pool | Updated reads/JOIN |
| --- | ---: | ---: |
| Saved teams | 1.67 s | 0.60 s |
| Collection | 1.66 s | 0.77 s |
| Team 1 details | 2.43 s | 0.88 s |
| Team analysis | 4.72 s | 1.36 s |
| Recommendations | 3.56 s | 1.46 s |
| Battle history | 0.84 s | 0.28 s |
| Analytics | 0.81 s | 0.31 s |
| Strategy evidence | 0.86 s | 0.44 s |
| 1v1 evidence | 1.50 s | 0.62 s |

All 14 paired JSON response hashes matched, including details for all five saved
teams. Reference-catalogue and connection warm-up costs are excluded from the
table. These single-run request measurements vary with network conditions and
are not browser navigation or battle-action timing guarantees.

Two actual MySQL probes used only uniquely named connection-local temporary
InnoDB tables. Both verified committed rows and rolled-back changes. The batch
probe also verified all eight move rows retained their team/member/move slot
associations. Closing each probe connection removed its temporary table. No
player table was written and no persistent test schema was created.

Modified files in this pass: `backend/db.py`, `backend/teams/service.py`,
`frontend/static/app.js`, `frontend/index.html`, `tests/test_sql_pool.py`,
`tests/test_auto_battle_database.py`, `tests/test_collection_rewards_database.py`,
`tests/test_database_queries.py`, `tests/test_historical_queries.py`, and the
two cloud setup/verification documents. The four opt-in fixture helpers now
accept the read-only flag while preserving their caller-owned rollback fixture.
Created `tests/test_team_loading.py` and `tests/frontend_catalogue.test.cjs`.

Python discovery ran 127 tests: 91 passed and 36 database-dependent tests
skipped. All seven Node tests passed. These cover cache boundaries, retry limits,
transaction failure handling, concurrent checkout, owned-team hydration and
batched save associations. JavaScript syntax and `git diff --check` passed.
