# Attack effectiveness messages — 21 October 2026

The collection's `Owned #` is the SQL primary key for an individual owned copy. Two copies of the same species have different IDs so team membership, shiny status and rewards can refer to the correct instance. It does not indicate a level or rarity.

Added **Super effective!**, **Not very effective.** and **No effect.** to successful attacks using their saved combined type multipliers. Floating damage labels show the message above the target. The battle log and completed-turn summary retain the wording afterward, including when a later event is a faint/switch. Misses stay labelled as misses, normal 1× hits have no extra wording and legacy events without the multiplier stay readable. Reduced motion keeps the static summary/log. Damage, type calculations, predictions and database records are unchanged.

## Verification

Extended the existing `scripts/check_auto_battle.py` browser fixtures for 2×/4× super-effective hits, 0.5×/0.25× resisted hits and 0× immunity. All checks passed in headless Edge: floating labels, static summary, history after reload, unchanged HP for immune hits, a missed super-effective attack, ordinary/missing multipliers and reduced motion. Existing manual/auto battle, pause, replacement, navigation, failed-request and mobile checks also passed. API calls are intercepted and fixture battles resolve in memory, with no player database writes.

`git diff --check` passes. No backend/schema changes or new dependencies are needed. The temporary verification server on 5051 was stopped after checking; the user's server on 5050 was left running.

Created: this report.

Modified:

- `frontend/static/app.js`: shared effectiveness wording, attack log text and full turn summary.
- `frontend/static/battle-effects.js`: floating matchup messages from recorded events.
- `frontend/static/style.css`: readable two-line damage labels and effectiveness colours.
- `frontend/index.html`: refreshed asset cache versions.
- `scripts/check_auto_battle.py`: effectiveness browser fixtures.
- `README.md`, `docs/database-design/battle-rules.md`: behaviour and owned-ID explanation.

Press Ctrl+F5 to load the updated display. Use a super-effective, resisted or immune matchup to see the floating text and battle log. No database setup is required.
