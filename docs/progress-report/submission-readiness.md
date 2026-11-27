# Repository submission audit

Reviewed 20 November 2026. Scope: the project repository and source archive. The final report, slides and recording are separate deliverables and were outside this audit's final scope.

## Checks completed

| Check | Result |
| --- | --- |
| Offline Python suite | 124 collected; 88 passed; 36 opt-in database tests skipped; 0 failures/errors; 6.030 seconds |
| Frontend checks | 11 passed; 0 failed; no npm dependencies required |
| Frontend JavaScript syntax | Both app.js and battle-effects.js passed node --check |
| Cached gameplay sources | 912 files validated; 0 audit issues |
| Prepared catalogue | Exactly matches the catalogue rebuilt in memory from the audited raw sources |
| Historical cache | 50,000 labelled results and 10,000 unlabelled matchups inspected; no inspection issues; 1,589 distinct catalogue-eligible labelled results |
| Python compatibility parsing | All 57 Python files parsed with Python 3.10 grammar |
| JSON parsing | All 918 repository JSON files parsed successfully |
| Local documentation links | Checked after documentation reorganisation; no missing file targets |
| Configuration and secrets | Private environment files, local credentials and SSH keys ignored; no current private values found in publishable files; no Git history entries for .env, .env.cloud or .local |
| Extracted source archive | Offline Python suite passed again: 88 passed, 36 skipped, 9.534 seconds; all 11 frontend checks passed; 912 cached sources audited with 0 issues |

The archive was extracted to a temporary directory and checked without a private .env, inherited SQL/Mongo settings or local launchers. The documented named query-test command also imported successfully in the extracted copy (3 offline checks passed, 12 database checks skipped). It overlaps the broader suite and is not an additional pass count. This verifies archive completeness for the offline checks, not a fresh dependency install or database rebuild.

Audit environment: Python 3.13.7, Node.js 24.14.0, Flask 3.1.2, PyMySQL 1.2.3, PyMongo 4.19.0, requests 2.32.5 and cryptography 50.0.2. Node.js is optional for running the application.

The 36 skips comprise the nine full database integration checks and 27 query/persistence checks behind RUN_QUERY_TESTS. They are expected in this offline run and are not new live-database passes. Earlier real-database results remain in [the test evidence](test-results/README.md), including 115 broader-suite passes and nine separate integration passes.

The local application was not running during this audit, so the live health endpoint could not be checked. This review does not establish a new cloud connection, new database-write test run or independent database installation.

## Handoff documentation

- The project README starts with the shared-cloud assessor route and independent installation route.
- The user manual contains installation, feature use and troubleshooting. The internal submission checklist was removed.
- Earlier report/presentation scaffolds and workstation notes are preserved in docs/development. Old paths have short redirects for existing references.
- .env.example contains placeholders and distinguishes independent settings from the cloud guide.
- The source archive is built from tracked and unignored repository files, excluding agent instructions, private settings, .git, .local, virtual environments and generated caches. It includes source, schema, queries, raw/prepared data, dependencies, manuals, design and verification records.

## Before handing over access

Supply the MySQL application username/password and complete Atlas URI privately. Professors must use Google accounts authorised for the cloud SSH route. Keep the VM and Atlas cluster available for assessment. Those access settings and the private handoff are not established by a source-code audit.

## Git handoff

The reviewed implementation is on `feature/core-features`. At audit time it is 12 commits ahead of local `main`, with 146 differing files; local `main` has no `backend/app.py`. The remote branch state was not fetched or checked. If submitting a repository link, identify the implementation branch/commit explicitly or review and merge the implementation into the submission branch. Do not assume the local main branch already contains the project.

The source archive represents the reviewed working tree, including this documentation cleanup. Review and commit those changes separately if submitting through Git; no stage, commit, merge or push was performed by this audit.
