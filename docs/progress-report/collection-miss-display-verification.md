# Collection layout and miss displays — 21 October 2026

## Latest layout adjustment

The user subsequently requested internal collection scrolling with the panel extending to the end of the roster beside it. The collection now stretches to the left roster section's height on desktop; only its list scrolls. Adding/removing members automatically grows/shrinks the panel. On stacked layouts at widths of 1100px or less, the collection sits below the roster and is capped at 70% of the viewport height.

The updated `scripts/check_collection_display.py` passed in headless Edge using read-only API fixtures: matching panel/roster bottoms, growing/shrinking with members, scrolling to the last owned copy, mobile height cap and fit, empty roster/collection, plus the existing team buttons and miss-chance checks. The updated desktop screenshot was visually inspected. `git diff --check` passed. No database or backend change is needed; press Ctrl+F5 to load the new CSS.

This follow-up modifies `frontend/static/style.css`, `frontend/index.html`, `scripts/check_collection_display.py`, `README.md` and this report. It creates no files. The notes below describe the earlier page-scroll version, which this adjustment replaces.

## Earlier verification

The user clarified that the collection was constrained to a small internal scroll area instead of expanding with the page. The fixed maximum height and internal scrolling are now overridden: every owned Pokémon stays in normal page flow and the document scrollbar reaches the final card.

Collection cards also separate the sprite/name/types from rarity/cost and owned-instance actions, preserving duplicate species as separate owned IDs. The side panel fits its content, names can wrap and status buttons explain `In team`, `Team full` or `Over budget`. Add/remove behaviour, six-member and 30-point limits remain intact. The roster's stray `?` between name and cost is corrected.

Move displays show hit chance and miss chance in the Pokédex details, team builder and battle buttons. The team builder's selected-move hint updates immediately when a move changes, preserving other unsaved edits. Display calculation follows the existing engine: numeric accuracy is the hit percentage; null accuracy and Fallback Strike bypass the accuracy check, so their miss chance is zero. Zero accuracy remains 0% hit / 100% miss. An unrecognized missing accuracy is shown as unavailable rather than inventing a percentage.

The existing analytics move table now also displays **observed miss rate = 1 − observed hit rate**, using its existing filtered aggregation result. It explains the difference from configured per-attack chance. A hit against an immune target remains a hit even when damage is zero. There is no change to combat formulas, predictions, database schema or stored data.

## Verification

- `scripts/check_collection_display.py` passed in headless Edge with all API calls intercepted and writes rejected. A 43-instance fixture confirms no collection height cap/internal scrollbar, document scrolling to the final owned instance, desktop/390px fit, long-name wrapping, distinct duplicate IDs, add/remove, full-team/budget labels, preserved unsaved names and an empty state.
- The same check verifies 85%/15%, null accuracy's 100%/0%, numeric zero's 0%/100%, dynamic move hints, Pokédex columns and Fallback Strike's guaranteed hit. It verifies battle displays by reading fixture snapshots without submitting turns.
- The updated `scripts/check_database_evidence.py` passed, verifying a fixture with 11 hits in 15 attempts displays 73.3% hit / 26.7% miss, alongside existing filters, empty cohorts, prediction counts, external evidence, mobile layout and HTML/JSON error handling.
- Desktop/mobile screenshots were visually inspected: ignored `.local/collection-desktop.png` and `.local/collection-mobile.png`. Fixtures are controlled display examples, not live player statistics.
- `git diff --check` passed with only existing Windows line-ending notices.

This display-only follow-up did not rerun or change the previously verified combat engine. Browser checks created no application trainers, teams, battles or rewards. A temporary server on port 5051 served updated assets for verification and was stopped afterward; the user's server on port 5050 was left running.

## Try it

Refresh the running application with **Ctrl+F5**. Open **Collection & teams**, scroll normally down the page and inspect the move hints. Open **Battle analytics → Battle strategy evidence** for observed miss rates. No database setup/import is needed. If an old page continues to appear, restart the Python app and refresh again.

## Created files

- `scripts/check_collection_display.py`.
- This verification report.

## Modified files

- `frontend/static/app.js`: collection cards/status labels, move chance helpers, selected-move hints, battle/Pokédex chance displays and observed analytics miss rate.
- `frontend/static/style.css`: normal page-flow collection, card layout, wrapping and move hint styling.
- `frontend/index.html`: updated CSS/JS cache versions.
- `scripts/check_database_evidence.py`: observed miss-rate display assertions.
- `README.md`, `docs/database-design/database-evidence.md`: current display behaviour and metric definition.

The previously requested auto-battle changes were already present in the working tree and are preserved.
