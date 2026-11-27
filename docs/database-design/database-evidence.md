# Database queries and import evidence

These changes strengthen the existing database features without changing combat mechanics or the saved prediction formula. External CSV inspection and the approved import are separate: see the [historical import design](historical-import-proposal.md).

## 1. Audited PokéAPI import

```sh
python -m scripts.data_import.audit_game_data
python -m scripts.data_import.audit_game_data --stage
python -m scripts.setup_databases
```

The first command inspects only; the second also replaces the staged catalogue after validation. Setup runs the audit itself before any SQL import. All commands run from the repository root. Setup loads `.env` automatically.

`scripts/data_import/audit_game_data.py` reads the exact cached source bytes, hashes them, validates required identities/stats/types/move references, and normalizes that same in-memory snapshot. It then checks normalized primary keys, unique names and foreign references. Invalid required data rejects the entire batch and preserves the last staged catalogue. Raw source files are never rewritten by the audit.

The report in ignored `.local/import-audit.json` records:

- Per-file SHA-256 and size, plus a fingerprint of the ordered source manifest.
- Invalid/missing records with file and reason; out-of-scope files are explicitly listed.
- Unsupported status/zero-power/null-power moves, excluded under the existing simplified move policy.
- Normalized table counts and the number of labelled project move overrides.
- After a successful SQL commit, the server version, database name and submitted row counts. These are batch counts, not a claim that pre-existing extra rows were deleted.

Current cached batch: 912 readable files (151 Pokémon, 151 species, 18 types and 592 moves), no audit issues, 353 supported moves and 239 filtered moves. Output remains 151 Pokémon, 218 type links, 8,103 move links and 324 effectiveness pairs. The source-file count includes readable bytes even when invalid JSON later rejects a batch.

Catalogue upserts commit together using the existing transaction. Schema/view DDL uses MySQL's normal implicit-commit behaviour; the audit report is a local artifact, not part of an atomic transaction spanning MySQL, MongoDB and the filesystem. Setup does not remove obsolete catalogue rows or reset player data.

## 2. SQL team analysis and recommendations

Definitions live in `database/relational/views.sql`:

| View | Application purpose |
| --- | --- |
| `v_pokemon_cost` | Derive existing points from six base stats |
| `v_pokemon_defense` | Multiply the first and optional second defensive type multipliers; preserve immunity at zero and double weakness at four |
| `v_ranked_default_moves` | `ROW_NUMBER()` chooses suggested attacks using the same type/power/ID order as Team Builder |

`queries/team_matchups.sql` counts weak, 4×-weak, resistant and immune members for each attacking type. `queries/team_coverage.sql` joins **saved selected moves** to type effectiveness and calculates the best multiplier against each single defending type. Python formats the resulting numbers.

`queries/team_recommendations.sql` performs candidate evaluation and ranking in MySQL:

1. `settings` and `roster` bind the trainer/team and derive the current roster and cost. The service also checks team ownership before querying.
2. Baseline CTEs calculate average defensive exposure and offensive coverage.
3. `candidates` joins the trainer's collection; `NOT EXISTS` excludes instances already in the team.
4. `plans` proposes additions below six members, or each possible replacement for a six-member team. `affordable` excludes results over 30 points.
5. Defensive CTEs evaluate combined type multipliers. Move CTEs preserve retained members' saved choices and use the candidate's first four ranked defaults.
6. `improving` keeps reduced exposure, or unchanged exposure with increased coverage. Empty teams instead receive affordable choices without a baseline-improvement claim.
7. Two `ROW_NUMBER()` stages select one best plan per species, then the best three species. Ties use coverage gain, lower candidate cost, stable owned ID and replacement ID. Exposure differences are rounded to nine decimal places for stable ordering.

Exposure = `SUM(MAX(combined multiplier - 1, 0)) / team size`, across all 18 incoming types. Coverage = number of single defending types hit super-effectively by any selected move. These implement the previously approved scores; neither measures a probability of victory. A final left join returns baseline information even if no suggestion qualifies.

This demonstrates JOINs, anti-joins, grouping, CTEs, derived views, window ranking and JSON aggregates for an actual feature. `backend/team_analysis/recommendations.py` keeps the original Python scorer as an offline test reference; production calls execute the SQL query.

To inspect the optimizer plan with actual saved-team parameters:

```sh
python -m scripts.explain_recommendations --trainer-id 1 --team-id 1
```

Use a team owned by that trainer. The command saves `EXPLAIN FORMAT=JSON` to `.local/recommendation-explain.json`. It does not edit teams. This describes the chosen plan; it is **not** a measured speedup or a benchmark. Existing foreign-key/unique indexes support the joins; the catalogue is small, so no speculative index changes were added.

## 3. Rule-aware MongoDB battle analytics

Open **Battle analytics → Battle strategy evidence**. Select battle rules and optionally a difficulty, then apply filters. The read-only endpoint is `GET /api/analytics/strategy` with `rules_version` and optional `difficulty` query parameters. It uses the currently selected trainer, consistent with this local profile-based application.

`backend/analytics/strategy.py` starts with `$match` on trainer, exact saved rules, completed outcome and optional difficulty. It excludes forfeits before a `$facet` computes three analyses from embedded turn events:

| Analysis | Pipeline / denominator |
| --- | --- |
| Damage per attempted move | `$unwind` turns/events, keep player moves, group by move ID; misses count as attempts and contribute zero damage; hit rate = hits / attempts; the UI also shows observed miss rate = 1 − hit rate; damage = recorded actual HP removed |
| Repetition and outcomes | Group by battle/move, then battle; require at least five attempted player attacks; “high repetition” = one move accounts for at least 75%; group by difficulty, initial player-team size and repetition pattern; show wins/losses/draws and count |
| Saved prediction outcomes | Require a saved method and known prediction label; group by method, label and actual outcome; old documents lacking predictions remain excluded |

The endpoint also returns the matching battle count and trainer-specific rules options. The UI labels counts below ten as small samples. The thresholds five, 75% and ten are descriptive display choices, not statistically validated cutoffs.

Grouping by rules avoids pooling different damage caps or future mechanics. Difficulty and team size reduce obvious differences in the repetition comparison, but team strength, opponent, moves and player decisions still vary. An association does not establish that repeating a move caused a win. Recorded damage is capped by remaining HP and cannot establish an attack's theoretical damage potential.

Prediction evaluation distinguishes favoured-win and disadvantaged-loss directional calls from draws and evenly-matched labels. It does not establish calibrated probabilities. These filters apply to the new evidence panel; existing overall analytics keep their original definitions, including forfeits.

## 4. Observed 1v1 matchups from MongoDB

The visible matchup panel now uses `GET /api/analytics/matchups`, implemented in `backend/analytics/matchups.py`. The original external source remains separately queryable; it does not fill this panel. No new stored schema is introduced.

The aggregation starts with `$match` on the selected trainer, exact saved rules, completed outcome and optional difficulty. It excludes both turn-level and event-level forfeits. `$expr`, `$isArray` and `$size` require exactly one member in **both initial snapshots**, with malformed/missing arrays safely excluded. A final team with one survivor is not evidence that a battle started as a 1v1.

`$arrayElemAt` extracts each starting species. A pair filter accepts both orientations. `$cond` identifies whether the selected species was the player's Pokémon or the AI opponent; conditional expressions reverse wins/losses for the latter. `$facet` computes overall counts and rows grouped by difficulty and selected-species side, with `$group`/`$sum`, `$avg` turns and `$divide` win rates. Each battle document contributes once, regardless of turns, moves or shiny appearance. All matching documents are read, rather than the history screen's latest 50.

Rate denominator = wins + losses + draws, with wins from the selected species' perspective. Empty cohorts return no rate rather than an invented zero. Small samples are labelled. Different moves, stats and human/AI choices still affect outcomes; observed rates are not calibrated predictions. The UI uses the existing rules/difficulty filters, preserves pair selections and shows instructions when no qualifying data exists. Pokémon dropdown names still come from the relational catalogue; outcome evidence comes entirely from MongoDB.

## Verification

```powershell
# Offline validation, rule and parsing checks.
python -m unittest discover -s tests -v
# Ten real MySQL/MongoDB query checks using the existing .env account.
$env:RUN_QUERY_TESTS = '1'
python -m unittest tests.test_database_queries tests.test_historical_queries tests.test_simulator_matchups -v
# Optional read-only browser fixtures; requires requirements-dev.txt and an app.
python scripts/check_database_evidence.py
```

Real query checks run temporary MySQL fixtures in a transaction and roll them back. Auto-increment gaps can remain. Mongo fixtures use a unique disposable test database, which is dropped after the test; the local Mongo configuration must permit that. The checks cover SQL/reference ranking equivalence, immunity/4× weakness, duplicate species, full/empty teams, budgets/ownership, cohort filters, misses, repetition boundaries and old/missing predictions.

Browser checks intercept API reads with controlled fixture responses and reject API writes. They verify rule/difficulty filters, the metric display, empty cohorts, sample labels and mobile overflow. They do not validate end-to-end live database connectivity; real query tests cover the database pipelines separately.

For an existing installation, rerun setup to create the views and restart the app before opening the updated screens. No additional runtime dependency is needed. A higher grade depends on the rubric and your explanation/evaluation; additional SQL syntax alone does not guarantee it.
