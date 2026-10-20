# Team budgets, recommendations and predictions

Status: approved by the user on 2026-10-19. Budget, owned-Pokémon recommendations and snapshot-based predictions are implemented on `feature/core-features`. Kaggle import remains pending dataset review and schema approval.

## Purpose

Extend the existing playable prototype using MySQL queries and MongoDB aggregations. Keep calculations explainable, use the existing Flask/browser stack, and add no machine-learning dependencies.

## Approved decisions

| Decision | Options and tradeoffs | Recommended first version |
| --- | --- | --- |
| Team cost | Rarity costs are easy to explain but rarity currently describes reward frequency. Base-stat costs relate to strength but do not capture every matchup or move advantage. | Each member costs `ceil(sum of six base stats / 100)` points. A team has a 30-point budget and still contains 1–6 members. These are project rules, not official Pokémon rules. |
| Recommendation pool | Owned Pokémon can be used immediately. The whole Pokédex offers more choices but includes Pokémon the trainer cannot currently use. | Recommend owned instances outside the team. A separate future Pokédex suggestion feature is outside this change. |
| Recommendation ranking | Overall historical win rate is simple but mixes opponents, difficulties and player decisions. Team weaknesses and selected-move coverage directly explain an improvement. | Rank valid additions or replacements by reduced defensive weaknesses, then improved offensive coverage. Show historical evidence separately when available. |
| Prediction target | 1v1 predictions fit the proposed Kaggle records. Team battles match the existing application but require team-level comparisons. | Predict the existing 1–6 versus equal-size system team, using its actual starting snapshot. |
| Prediction output | A percentage looks precise but needs calibration. Qualitative labels can describe a transparent heuristic immediately. | Show favoured, evenly matched or disadvantaged, plus reasons and a method version. Do not call a heuristic score a win probability. |
| Historical sources | Simulator logs match our rules but start sparse. Kaggle supplies external 1v1 evidence whose identifiers, scope and mechanics need inspection. | Use simulator history as contextual evidence now. Add Kaggle matchup evidence only after reviewing a supplied dataset and approving its mapping. Do not download a dataset automatically. |

## Budget behaviour

- Calculate costs from the existing species stats in the backend; return per-member cost, total and remaining points to the browser.
- Validate cost when saving a team and immediately before starting a new battle. The browser may preview costs but cannot override validation.
- Keep existing teams visible and editable. An existing team above the budget must be adjusted before saving or starting another battle.
- Leave saved battle snapshots and active battles unchanged. Record the budget-rule version and starting cost on new battles.
- Derive costs from the catalogue rather than adding a redundant SQL column in this first version. No new relational tables are needed for budgets.

The 30-point limit is an initial balance choice to evaluate, not a demonstrated fair limit. Tests should cover rounding, exactly 30 points, exceeding 30 points and an existing over-budget team.

## Recommendations

1. Validate that the trainer owns the requested team.
2. Query MySQL for owned instances outside that team, joining species, stats, types and eligible moves.
3. For a team below six members, evaluate additions. For a full team, evaluate replacements and identify the outgoing member. Users can manually remove members from a smaller team to explore alternatives.
4. Discard proposals exceeding the team budget or violating ownership rules.
5. Score defensive exposure as the sum of `max(type multiplier - 1, 0)` over all 18 attacking types and team members, divided by team size. Lower is better. This accounts for dual types and double weaknesses; an empty team's score is undefined.
6. Score offensive coverage as the number of defending types against which at least one selected move is super-effective. Preserve current members' selected moves; use the existing default four moves as an explicitly labelled suggestion for the candidate.
7. Keep proposals that reduce defensive exposure, or preserve it and increase coverage. Rank by exposure reduction, then coverage gain, then lower cost, then stable instance ID. Return up to three distinct species with before/after figures and suggested moves. Offer no recommendation when no qualifying improvement exists.
8. Treat empty teams as starter selection: list affordable owned choices without claiming they improve a nonexistent baseline.

Explain limitations: coverage is against individual defending types; the score does not prove a team will win. Candidates use suggested moves until the user chooses and saves them. The service only suggests changes; it does not edit teams automatically.

## Predictions

- At battle creation, generate the opponent once, build both starting snapshots, then calculate and save the prediction before either side acts. Display it before the first turn; refreshing must not generate a different opponent or prediction.
- Compare selected moves through the existing battle engine's expected-damage calculation and the battle's rule version. For each attacker/defender pair, take the best expected damage as a fraction of defender maximum HP, adjusted for move accuracy. Average across pairs for each side and compare the two values.
- Initially classify a player/opponent pressure ratio above 1.10 as favoured, below `1 / 1.10` as disadvantaged, otherwise evenly matched. If both pressures are zero, report evenly matched; if only one side has positive pressure, favour that side. Explain that these are proposed heuristic thresholds.
- Include relative base-stat totals and average Speed as supporting explanations. The label does not simulate player choices, switching sequences or an entire battle.
- Store method version, input summary, score, label and explanations on the battle document. Historical documents without predictions remain readable; do not backfill predictions using their known outcomes.
- Aggregate previous completed simulator battles with the same battle rules, difficulty and team size. Show the battle count and win/loss/draw breakdown as broad context, explicitly not a win rate for this exact matchup. Exclude forfeits from prediction evidence; do not change existing analytics definitions.
- Keep contextual history separate from the heuristic label initially. This avoids treating results against different opponents as a calibrated estimate for the current team.
- In analytics, compare saved predictions with subsequent results, displaying sample sizes, a favoured/disadvantaged correctness table and draws separately. Evaluate evenly matched labels separately. Do not fit and evaluate thresholds on the same battle records.

## Kaggle follow-up

The dataset mentioned in the project proposal is not present in the repository. Before importing:

1. Inspect the supplied source files, source/license information, columns, identifier meanings and included Pokémon forms.
2. Map external Pokémon identifiers explicitly to PokéAPI species IDs. Do not assume matching row numbers or names prove matching IDs.
3. Keep raw files unchanged and report unmatched records, records outside IDs 1–151, invalid winners, self-matchups and duplicates. Agree on treatment before import; do not silently discard records.
4. Propose a source mapping and historical-combat schema for approval, then implement an importer and SQL matchup aggregates with battle counts.
5. Label external 1v1 evidence separately from simulator team history. Do not convert 1v1 win rates into a team win probability.

## Implementation sequence

1. Add budget calculation and validation to the existing team service and UI.
2. Add owned-Pokémon recommendations through team analysis, a read-only API and an explanation panel.
3. Add snapshot-based predictions to battle creation, the MongoDB validator, battle display and outcome analytics.
4. Review supplied Kaggle data and prepare the separate import design. Dataset selection and historical schema approval remain prerequisites for that phase.

## Verification

- Meaningful unit checks for budget boundaries, dual-type exposure, valid recommendations, full-team replacements, empty collections, accuracy adjustment, prediction thresholds and zero-pressure cases.
- Database integration checks for ownership, eligible candidate queries, budget rejection without partial updates, aggregation filters and prediction persistence across turns/resume.
- Verify compatibility with older battle documents and use controlled fixtures for prediction evaluation, including draws, forfeits and missing predictions.
- Browser checks for cost display, recommendation explanations, a prediction before the first action and results after completion. Update README and current design notes to match approved behaviour.
- Do not merge, push, download external data or modify existing live battle records as part of design approval.

## Implementation notes

- Recommendations are available through `GET /api/teams/<id>/recommendations` and the Team Analysis screen. Historical species evidence is trainer-specific, uses current battle rules, counts each species once per battle and excludes forfeits. It is contextual team-result evidence, not part of candidate ranking.
- New battle documents have optional-at-schema-level `budget` and `prediction` fields. They are always written by the new battle-creation code. Old battles do not require backfilling.
- Prediction pressure uses a representative random damage factor of 0.925, the engine's current damage cap and accuracy-adjusted selected moves. It is an approximation, not the exact expectation of the random battle process. Supporting Speed uses the battle stat (`base speed + 5`).
- Prediction evaluation is grouped by method version, battle rules, predicted label and actual outcome. Existing overall battle analytics continue to include forfeits; prediction evidence and evaluation exclude them.
- Database setup now applies the versioned validator to existing battle collections using `collMod`. Run setup after updating code; no relational schema migration is needed for this extension.
