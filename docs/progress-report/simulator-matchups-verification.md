# Own-battle 1v1 matchups — 21 October 2026

Replaced the visible external 1v1 panel with **1v1 matchups from your battles**, using MongoDB simulator logs for the currently selected trainer. No external battle rows are mixed into the result. Existing historical SQL tables, import tooling and the historical API are preserved for the group's earlier database work.

Results require exactly one member in each **starting snapshot**, a completed win/loss/draw, the selected rules and optional difficulty, and the selected species pair in either orientation. Team battles, active battles, forfeits and missing/malformed starting arrays are excluded. Wins/losses refer to the selected species even when it was controlled by the AI. Draws remain in the win-rate denominator. Normal/shiny appearances share species evidence. One document counts once; the query has no latest-50 history limit.

The panel shows total counts, observed win rate, small-sample guidance and a breakdown by difficulty/player-or-AI side with average turns. It uses the strategy filters above and preserves selected species while filters change. Empty results explain how to create qualifying data: save a one-member team, finish battles and return. Pokémon dropdown choices remain relational catalogue data. No schema migration, new dependency, generated battle data or prediction-formula change is needed.

## Verification

- `RUN_QUERY_TESTS=1 python -m unittest discover -s tests -q`: **107 discovered, 98 passed, 9 skipped**. The skipped class is the existing full-database integration suite requiring broader MySQL database-creation permissions.
- New tests run the actual MongoDB pipeline with a validator in unique disposable databases: selected-species orientation and reversed queries, draws/denominators, trainer/rules/difficulty scope, forfeits, wrong pairs, two-member/duplicate-member teams, final-survivor false positives, empty/malformed snapshots, empty rates, shiny metadata and 60 distinct battles with repeated events. An API test verifies session scope and ignores a forged `trainer_id` query parameter. Fixture databases are removed afterward.
- `scripts/check_database_evidence.py` passed in headless Edge with all API calls intercepted and writes rejected. Checks cover MongoDB attribution, no Kaggle attribution, both player/AI roles, counts/draws/rates, empty-state instructions, preserved selections, shared rules/difficulty filters, 390px fit and stale-backend HTML error handling, alongside the existing strategy metrics.
- `git diff --check` passed. The browser previews are ignored `.local/simulator-matchups-desktop.png` and `.local/simulator-matchups-mobile.png`.
- A subsequent read of live player data could not run because the local MongoDB service was stopped (connection refused). No live battle data was generated or changed to fill the panel. Start MongoDB before testing the app. The pipeline itself passed the real fixture tests while MongoDB was available.

## Files

Created:

- `backend/analytics/matchups.py`: read-only observed 1v1 aggregation.
- `tests/test_simulator_matchups.py`: validation, actual MongoDB pipeline and API fixtures.
- This verification report.

Modified:

- `backend/app.py`: trainer-scoped matchup endpoint.
- `frontend/static/app.js`: own-battle panel, shared filters, outcomes and empty state.
- `frontend/index.html`: JavaScript cache version.
- `scripts/check_database_evidence.py`: MongoDB panel fixtures and assertions.
- `tests/test_api_errors.py`: new endpoint's profile requirement.
- `README.md`, `docs/database-design/database-evidence.md`: data source and query walkthrough.

## Try it

Start both database services. Restart the app with Ctrl+C, then `python scripts/run_local.py`, and press Ctrl+F5. Open Battle analytics and the 1v1 panel. Finish genuine one-member-team battles to add observations; six-member team results do not establish a species 1v1 win rate. Existing qualifying records are picked up automatically when the panel is loaded; no import/setup is needed.

The temporary verification server on 5051 is stopped after checking; the user's existing app on 5050 is left alone. No commit or push was requested or made.
