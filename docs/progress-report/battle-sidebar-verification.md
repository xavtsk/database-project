# Battle controls beside the arena — 21 October 2026

## Follow-up: remove duplicate turn summary

The user subsequently requested removal of the extra text box repeating both attacks below the arena. Removed the summary markup, its animation updates and unused styling. Floating damage/effectiveness text and the Battle log remain. Updated browser checks require the summary to be absent while preserving attacks, Auto Battle, effectiveness messages and reduced-motion log text.

This follow-up modifies `frontend/static/app.js`, `frontend/static/battle-effects.js`, `frontend/static/style.css`, `frontend/index.html`, `scripts/check_auto_battle.py`, `README.md`, `docs/database-design/battle-rules.md` and this report. No files were created. Press Ctrl+F5; no backend or database update is needed.

The updated browser check passed in headless Edge, including no summary element, working manual/auto actions and retained effectiveness log messages. `git diff --check` passed. The temporary server on 5051 was stopped after verification.

## Original layout verification

Moved moves, Auto Battle/Pause, switching and forfeit controls into a panel to the right of the arena. Prediction, the battle log and opponent matching now appear in a Battle analysis section underneath. The arena stretches alongside the controls on desktop. At widths of 1200px or less, controls stack below the arena and analysis follows. Completed battles retain the result/reward case above the analysis.

Verified with headless Edge and intercepted API fixtures:

- Side-by-side arena/controls at 1440px and 1280px; controls below the arena at 1024px and 390px.
- Analysis begins below the complete battle layout; move buttons and the page have no horizontal overflow.
- Existing manual attacks/switches, effectiveness messages, Auto Battle/Pause, replacements, failed requests, navigation, reduced motion and victory stopping all pass in `scripts/check_auto_battle.py`.
- Shiny sprites, badges, case opening/skip/reload and reduced motion still pass in `scripts/check_collection_rewards.py`.
- Desktop/mobile screenshots were inspected: ignored `.local/battle-sidebar-desktop.png` and `.local/battle-sidebar-mobile.png`.
- `git diff --check` passes. All browser battle actions used in-memory fixtures and no player database writes occurred.

Created: this report.

Modified: `frontend/static/app.js` (panel ordering and grouping), `frontend/static/style.css` (responsive battle layout), `frontend/index.html` (asset cache versions), `scripts/check_auto_battle.py` (position/overflow assertions and screenshots), and `README.md` (current layout).

No backend, combat-rule, prediction or database changes were needed. Press Ctrl+F5 to see the layout. The temporary test server on 5051 was stopped; the user's existing server on 5050 was left running.
