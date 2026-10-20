# Team budgets, recommendations and predictions

Implemented on `feature/core-features` following approval of `docs/database-design/predictions-recommendations-proposal.md` on 2026-10-19.

## Behaviour

- Team saves and new battles enforce a 30-point budget, with species costs derived by rounding total base stats divided by 100 up to an integer. Budget validation happens before team writes. Existing team reads and active battles remain available.
- Team Analysis queries owned candidate instances and suggests affordable additions or full-team replacements. Ranking considers combined defensive type weaknesses and selected-move coverage; explanations identify improved attacking-type exposure and new coverage. Candidate moves use the existing eligible default selection, and users review/save changes themselves.
- New battles save a qualitative prediction and its input summary before the first action. It uses the actual generated opponent, selected moves, accuracy and versioned battle damage rules. Historical simulator evidence is contextual rather than a fitted win probability.
- MongoDB aggregates provide historical context and prediction/outcome counts. Forfeits are excluded from this evidence/evaluation, while existing overall battle analytics retain their definitions. Draws, evenly matched predictions and older documents are handled separately.
- The MongoDB validator accepts optional prediction/budget fields. Setup updates an existing collection's validator with `collMod`; it does not backfill history. No SQL schema changes or application dependencies were added.

## Checks run in this checkout

- Python unittest discovery: **45 tests discovered, 36 passed, 9 database integration tests skipped**. The new offline tests cover rounding/budget boundaries, invalid saves before mutations, legacy active battles, combined weaknesses, recommendations/replacements, candidate deduplication, prediction thresholds/accuracy/immunity/legacy caps, and prediction persistence.
- `node --check frontend/static/app.js` passed.
- Node rendering smoke checks passed for the budget display, old-battle fallback, HTML escaping in predictions, limited-history display and prediction/outcome grouping.
- `git diff --check` passed.

This Windows checkout has no `.env` and no running MongoDB on the default local port. Actual database integration, validator updates and the full browser flow were **not run** here. Existing database drivers were downloaded only into ignored `.local/test-dependencies` for offline imports; requirements files were unchanged. The sandbox could not read those downloaded packages, so the offline suite ran with elevated tool permission and `PYTHONPATH=.local/test-dependencies`.

## Reproduce with configured databases

1. Install existing `requirements.txt`, configure `.env` and start MariaDB and MongoDB as described in README.
2. Apply setup with the environment loaded, then restart the app. The README includes a shell-independent Python command to load `.env` and run setup.
3. Run `python -m unittest discover -s tests -v` for offline tests.
4. Set `RUN_DB_TESTS=1` in the same shell with database credentials loaded, then run unittest discovery. These integration checks create/drop uniquely named test databases and require corresponding permissions. Added fixtures exercise budget rejection without team changes, recommendation ownership, history cohort filters, legacy documents and prediction outcome aggregates.
5. With the app running and the existing optional development browser dependencies installed, run `python scripts/check_browser.py`. This creates labelled application trainer/history data. The script now also checks budget rendering, the recommendation panel, and fixed predictions across reload.
6. Manually inspect Team Analysis recommendations using a trainer with additional owned Pokémon. Review suggested replacements on a full team and confirm that changing the saved team does not rewrite earlier battle predictions.

## Files created

- `backend/teams/budget.py`
- `backend/team_analysis/recommendations.py`
- `backend/battles/prediction.py`
- `tests/test_team_advice.py`
- `docs/database-design/predictions-recommendations-proposal.md`
- `docs/progress-report/team-advice-verification.md`

## Files modified

- `backend/teams/service.py`
- `backend/team_analysis/service.py`
- `backend/battles/service.py`
- `backend/analytics/service.py`
- `backend/app.py`
- `database/nosql/battle_validator.json`
- `scripts/setup_databases.py`
- `frontend/static/app.js`
- `frontend/index.html`
- `tests/test_app_integration.py`
- `scripts/check_browser.py`
- `README.md`

## Remaining work

Kaggle data selection, identifier inspection and historical SQL schema approval remain pending. No external dataset was downloaded. Predictions are uncalibrated heuristics; thresholds and budget balance still require evaluation using held-out simulator results. No merge or push was performed.
