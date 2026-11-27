# Collection limits and shiny rewards — 21 October 2026

Implemented the requested six normal plus six shiny copies per non-legendary species, one of each legendary species per team across both variants, rerolls for full reward variants, grouped collection cards and shiny animations. Legendary collection copies remain unlimited, as clarified in the question/answer. Existing collections are preserved.

## Checks

- `RUN_QUERY_TESTS=1 python -m unittest discover -s tests -v`: **96 tests discovered, 87 passed, 9 skipped**. The skipped older full-database integration class requires global MySQL database creation privileges; the ordinary project account was used for the enabled rollback fixtures instead.
- New probability tests check independent shiny draws across every rarity and the strict 1% boundary, including `0.009999` shiny / `0.01` normal. Other unit cases cover retry-stable rerolls, same-tier preference, unavailable-tier fallback, legacy normal rewards, species restrictions, battle entry and unchanged combat stats.
- Real MySQL/MongoDB fixtures verify six normal and six shiny copies coexist, both full variants reroll, full normal does not block shiny and vice versa, legendary collections can exceed six, old excessive copies remain, SQL awards repair a failed Mongo marker without another grant, invalid team edits preserve old rows, distinct legends work, and per-instance flags survive collection/team reads. SQL fixtures roll back; MongoDB uses unique disposable databases.
- Recommendation SQL matches the reference scorer, excludes a shiny duplicate of a retained legendary and supports replacing an old duplicate with a different species. Existing budget/type/coverage checks pass.
- `python -m scripts.migrate_collection_rewards` applied the additive column locally; a repeat reports `Shiny storage is already present`. No existing owned entries were deleted or turned shiny.
- `scripts/check_collection_rewards.py` passed in headless Edge. All API requests are intercepted and writes rejected. It checks species order, normal-before-shiny order, separate counts, legendary disabled buttons, different legendary eligibility, shiny front/back sprites and roster labels, desktop/390px layout, sparkle animations/reduced-motion preferences, saved shiny winner in the reel, skip/reload reveal and replacement explanation.
- Existing `scripts/check_collection_display.py` and `scripts/check_auto_battle.py` both pass, covering page scrolling, move miss chances, add/remove/budget labels, manual/auto attacks, switching, pause/error handling, navigation, mobile fit and reward stopping.
- Screenshots inspected: ignored `.local/shiny-collection-desktop.png`, `.local/shiny-collection-mobile.png` and `.local/shiny-case-mobile.png`. These are controlled fixtures, not evidence of naturally winning a shiny.
- `git diff --check` passes. No runtime dependency was added. The temporary test server on 5051 was stopped; the user's existing app on 5050 was left running.

The new rollback tests exercise failure after the award SQL statements but do not commit their fixture rows or simulate a real concurrent request race. Production uses the existing trainer-row transaction lock and unique battle reward key to serialize grants. Aggregate limits apply to application writes; manual SQL can bypass them.

## Try it

On this computer the migration is already applied. Restart the existing app by pressing Ctrl+C in its terminal, then:

```sh
python scripts/run_local.py
```

Open `http://127.0.0.1:5050` and press Ctrl+F5. Collection & teams shows species groups and separate normal/shiny counts. New victory rewards have a 1% shiny chance; existing Pokémon remain normal. Shiny rewards have changed sprite colours, badges and animated sparkles. A particular number of wins does not guarantee a shiny.

Other computers need `python -m scripts.migrate_collection_rewards` first, or the regular `python -m scripts.setup_databases`, followed by restart/refresh. See the [complete rules](../database-design/collection-rewards.md).

## Created files

- `backend/teams/limits.py`: shared legendary species validation.
- `database/relational/queries/reward_pool.sql`: variant-specific eligible collection query.
- `scripts/migrate_collection_rewards.py`: additive, repeatable shiny-column migration.
- `scripts/check_collection_rewards.py`: read-only browser fixtures.
- `tests/test_collection_rewards.py`, `tests/test_collection_rewards_database.py`: unit and real database checks.
- `docs/database-design/collection-rewards.md` and this verification report.

## Modified files

- `backend/teams/service.py`: starter cap, sorted collection variants, owned/team shiny metadata and team validation.
- `backend/battles/service.py`: independent shiny roll, locked eligible rerolls and retry recovery from the recorded SQL award.
- `backend/battles/engine.py`: shiny appearance in saved combatant snapshots.
- `backend/team_analysis/recommendations.py`, `database/relational/queries/team_recommendations.sql`: legal species plans.
- `database/relational/schema.sql`, `scripts/setup_databases.py`: shiny column and migration during setup.
- `frontend/static/app.js`, `frontend/static/style.css`, `frontend/index.html`: grouped cards/counts, variant sprites/badges, team guard, shiny case/battle effects and asset cache versions.
- `tests/test_database_queries.py`: real SQL legendary recommendation cases.
- `README.md`, `docs/database-design/battle-rules.md`, `docs/diagrams/relational-er.md`: behaviour, migration and storage documentation.

The earlier uncommitted Auto Battle and collection/miss-display work is preserved. No commit or push was requested or made.
