# Playable prototype verification — 2026-09-22

Branch: `feature/core-features`. No merge or push was performed.

## Implemented and exercised

- Pokédex search, type filtering, details and supported move pools for all 151 Pokémon.
- Local trainer selection, one starter per trainer, collection, saved-team CRUD, ownership and move validation.
- SQL-backed team statistics, type distribution, defensive matchups and selected-move coverage.
- Turn-based battles, same-size system opponents, Easy/Medium/Hard, switching, fainting, PP and battle results.
- Weighted Pokémon rewards, durable battle history and MongoDB analytics.

## Automated tests

`RUN_DB_TESTS=1 python3 -m unittest discover -s tests -v` completed **29 tests successfully** using actual MariaDB and MongoDB. Integration tests created uniquely named temporary databases and dropped those databases afterwards.

Coverage includes existing data/downloader checks, full-catalogue eligibility, damage and immunity, miss/PP behaviour, priority and Speed, fainted actors, free/voluntary switching, fallback recoil, simultaneous defeat, the turn cap, invalid actions, all team sizes/difficulties, ownership, team CRUD, revision replay protection, one active battle per trainer, starter uniqueness, rarity boundaries, reward recovery and analytics with known fixtures.

`python3 scripts/check_browser.py` passed against the running local app in Chromium:

- All five screens, Pokédex search/details and starter selection.
- Easy, Medium and Hard battles through completion.
- Reloading/resuming an active battle and switching team members.
- A victory delivered a reward; the new Pokémon could be added to the saved team.
- Team creation, editing to an empty draft, and deletion.
- History/analytics after completed battles.
- Desktop 1440×1000 and mobile 390×844; no horizontal overflow on the checked mobile page.
- No JavaScript page errors in the successful run.

The test trainer and its real battle records remain visible as a labelled local profile. Earlier exploratory checks also created `Prototype test` and `Browser tester` profiles; create a new profile to start your own game. Browser screenshots and logs are kept in ignored `.local/`.

## Persistence, source data and startup

- All 911 previously tracked raw JSON responses were compared against Git and remain unchanged. The newly approved Dark response brings the cache to **912 JSON files**.
- Imported 151 Pokémon, 18 types, 353 supported moves, 218 Pokémon-type rows, 8,103 eligibility rows and 324 effectiveness pairs.
- Reward retry tests simulate a failed MongoDB delivery-marker write after SQL delivery and verify that no duplicate is awarded.
- Restarted the app using `python3 scripts/run_local.py`, verified both database health checks, and confirmed the browser test's collection and completed battles remained available.
- Python compilation and `git diff --check` passed.

## Scope limits

This is the approved local prototype: selectable profiles do not authenticate different people. Simplified moves and project-specific move exceptions are documented in the UI and `docs/database-design/battle-rules.md`. Opponent difficulty remains a heuristic requiring gameplay calibration. No public deployment or multi-user security hardening was performed.

## File changes

Created:

- `.env.example`
- `backend/__init__.py`
- `backend/analytics/service.py`
- `backend/app.py`
- `backend/battles/engine.py`
- `backend/battles/service.py`
- `backend/catalog.py`
- `backend/config.py`
- `backend/db.py`
- `backend/errors.py`
- `backend/pokedex/service.py`
- `backend/team_analysis/service.py`
- `backend/teams/service.py`
- `data/processed/game_data.json`
- `data/raw/types/dark.json`
- `database/nosql/battle_validator.json`
- `database/relational/schema.sql`
- `docs/database-design/battle-rules.md`
- `docs/database-design/playable-prototype-proposal.md`
- `docs/diagrams/relational-er.md`
- `docs/progress-report/playable-prototype-verification.md`
- `frontend/index.html`
- `frontend/static/app.js`
- `frontend/static/style.css`
- `requirements-dev.txt`
- `scripts/check_browser.py`
- `scripts/data_import/prepare_game_data.py`
- `scripts/run_local.py`
- `scripts/setup_databases.py`
- `tests/test_app_integration.py`
- `tests/test_battle_engine.py`

Modified:

- `.gitignore`
- `README.md`
- `requirements.txt`
