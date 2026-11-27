# Database evidence work — 21 October 2026

Implemented on `feature/core-features` following the user's approval of database-focused improvements, the specific Kaggle download/inspection and then the concrete three-table historical import design. No commit or push was made.

## What changed

- MySQL now evaluates team defensive matchups, selected-move coverage and affordable owned-Pokémon recommendations. Reusable views and CTE/window queries implement the approved scores. Suggestions preserve ownership, budget, replacement and distinct-species rules.
- PokéAPI staging/setup now produces a reproducible audit of exact source hashes, required fields, filtered moves and normalized keys/references. Invalid required data rejects a batch before import and preserves the previous staged catalogue.
- MongoDB computes rule/difficulty-filtered attempted-move damage, move-repetition cohorts and saved-prediction outcomes. The UI shows denominators, sample sizes and limitations.
- The approved historical dataset is cached with source attribution and hashes. Three MySQL tables preserve source versions, all 800 external identities and all 50,000 valid ordered results. Reviewed mappings link 150 base forms. Evidence excludes repeat copies and unmapped participants: 1,589 distinct results remain.
- Battle analytics includes a separate external 1v1 matchup picker with source/version, first/second-attacker counts and explicit no-evidence states. It does not change combat mechanics, the saved prediction formula or recommendation scoring.

## Verification completed

Environment: local MySQL Server 26.7.0 and MongoDB; regular project-scoped SQL account. Setup completed successfully after the changes. Historical import committed, then repeated runs returned `verified_existing`; stored totals remained one source, 800 identities and 50,000 results. A SQL anti-join found no unresolved duplicate references in the imported data.

- `RUN_QUERY_TESTS=1 python -m unittest discover -s tests -q`: **67 discovered, 58 passed, 9 skipped**. The ten new opt-in database checks ran against the real services. The nine older full-application tests remain skipped because they require a separate MySQL account authorized to create/drop disposable databases.
- Live SQL fixtures verify recommendation/reference equivalence, zero immunities, 4× weaknesses, additions/replacements, empty/over-budget teams and ownership. Historical fixtures verify ordered role counts, duplicate/form exclusions, idempotent reads, invalid-outcome/participant constraints, mapping constraints and rejection of bad duplicate lineage before import.
- A Flask test-client check exercises the actual historical endpoint with transactional MySQL fixtures: selected-profile requirement, live counts, source details and invalid pair rejection.
- Mongo fixtures verify misses in attempt denominators, ignored opponent attacks, rules/trainer/difficulty filters, forfeit/active exclusions, repetition minimum and 75% boundary, and missing predictions.
- Offline tests verify raw-data audit rejection/preservation, exact historical identity mismatches, missing-name policy, duplicate lineage, approved hash/mapping checks and source changes.
- `scripts/check_database_evidence.py`: headless Edge fixtures passed rules/difficulty filters, hit/damage metrics, prediction outcome counts, historical first/second roles, missing evidence, preserved matchup selection and 390px mobile overflow. API requests were intercepted with controlled responses; no API writes occurred. Screenshots are ignored `.local/database-evidence-{desktop,mobile}.png` and `.local/historical-evidence-{desktop,mobile}.png`.
- `EXPLAIN FORMAT=JSON` of the actual bound recommendation query was saved to `.local/recommendation-explain.json`. It is an optimizer plan, not a measured speedup.
- `git diff --check` passed; Git emitted only Windows line-ending notices.

MySQL fixture rows were rolled back; auto-increment gaps can remain. Mongo fixtures used and dropped unique test databases. The temporary verification app on port 5051 was stopped after checks; an existing app on 5050 was left running and needs a restart to load the new backend.

## How to see it

On this computer setup and the historical import have already run. In the terminal running the app, press Ctrl+C and restart:

```sh
python scripts/run_local.py
```

Open `http://127.0.0.1:5050`, select a trainer and open **Team analysis** or **Battle analytics**. In external matchups, **Venusaur vs Muk** has two source results; Charmander vs Squirtle has none. Own-battle evidence needs completed simulator battles. New trainers need collection rewards before partner recommendations are possible.

On another machine, follow [MySQL setup](../database-design/mysql-setup.md), then run setup and `python -m scripts.data_import.import_historical` before launching. All commands load the existing `.env` where applicable; do not copy another member's credentials.

## Limits to explain in the presentation

The source describes a custom synthetic 1v1 algorithm with first-attacker order. It includes alternate forms, one missing name and six matched species with stats differing from the current catalogue. These records cannot establish team win probabilities. There are at most two distinct results for an unordered pair in the approved base-form subset; many pairs have no records. Deduplication is conservative, not proof of independent observations.

Duplicate lineage is explicitly checked by the importer and reverified against stored rows on rerun. A local direct-insert probe did not reject one missing self-reference despite the declared MySQL self FK; do not claim that constraint alone enforces provenance. The approved read-only historical API offers no way to edit these records. See the [historical design](../database-design/historical-import-proposal.md) for the complete policy and enforcement limits.

Move repetition statistics describe associations within rules/difficulty/team-size groups. They do not prove a strategy caused wins. Averages use actual logged HP removal and include misses; they do not estimate a move's unrestricted theoretical damage. No new status effects, cooldowns or battle rules were introduced. Grade outcomes depend on the rubric, evaluation and explanation.

## Created files

- `backend/analytics/historical.py`, `backend/analytics/strategy.py`.
- `database/relational/views.sql`, `database/relational/historical.sql`.
- `database/relational/queries/team_matchups.sql`, `team_coverage.sql`, `team_recommendations.sql`, `historical_matchups.sql`.
- `scripts/data_import/audit_game_data.py`, `fetch_historical.py`, `inspect_historical.py`, `import_historical.py`.
- `scripts/explain_recommendations.py`, `scripts/check_database_evidence.py`.
- `tests/test_import_audit.py`, `tests/test_database_queries.py`, `tests/test_historical_inspection.py`, `tests/test_historical_queries.py`.
- `data/processed/historical_mapping.json`.
- `data/raw/historical/weedles_cave/pokemon.csv`, `combats.csv`, `tests.csv`, `source.json`.
- `docs/database-design/database-evidence.md`, `docs/database-design/historical-import-proposal.md`, this verification report.

## Modified files

- `backend/app.py`, `backend/team_analysis/service.py`, `backend/team_analysis/recommendations.py`.
- `scripts/data_import/prepare_game_data.py`, `scripts/setup_databases.py`.
- `frontend/index.html`, `frontend/static/app.js`.
- `README.md`, `docs/database-design/mysql-setup.md`, `docs/database-design/predictions-recommendations-proposal.md`, `docs/diagrams/relational-er.md`.

## Follow-up: HTML received instead of JSON

The reported `Unexpected token '<', "<!doctype "...` was reproduced against the existing app on port 5050. `/api/session` and `/api/health` returned JSON/200, but the newly added `/api/analytics/strategy` and `/api/analytics/historical` returned HTML/404. That running backend predates the new routes. Its static files update from disk, so the browser can run new JavaScript against old Python route registrations.

The frontend now checks the response content type before parsing, identifies the failed API path/status and gives restart instructions for HTML 404s. HTML server errors and malformed JSON get readable diagnostics; normal JSON error messages are preserved. New backend HTTP errors return JSON for API paths while ordinary page errors retain HTML. HTTP headers such as `Allow` remain intact, and unexpected API failures expose a generic message while logging details in the terminal. The script cache version was updated.

Verification: four new offline Flask tests passed for missing routes, method errors/headers, logged server failures and registration of the new analytics routes. The updated headless Edge check passed the existing evidence display checks plus HTML 404, HTML 500 and JSON 503 fixtures, without API writes. The old user-owned server was left running; restart it with Ctrl+C followed by `python scripts/run_local.py`, then refresh.

Additional created file: `tests/test_api_errors.py`. Follow-up modifications: `backend/app.py`, `frontend/static/app.js`, `frontend/index.html`, `scripts/check_database_evidence.py`, `README.md` and this report.
