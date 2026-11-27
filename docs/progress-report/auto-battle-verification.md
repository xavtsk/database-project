# Auto Battle and animation verification — 21 October 2026

Implemented the user's request for an optional auto-battle controller and animations within the existing turn-based arena. Work stays on `feature/core-features`; no commit or push was made. The workspace was clean at the start of this change.

## Behaviour

- **Auto Battle** submits one player action at a time. The server chooses an available attack using estimated damage, accuracy, type effectiveness, target HP, PP and the saved rules version. Fainted members are replaced automatically. There is no new battle formula or machine-learning dependency.
- **Pause Auto Battle** stops further scheduling and allows manual control after any submitted turn completes. Navigation, a hidden tab, reload, completion or a failed request also stop the loop. A failed POST is followed by at most one state-recovery GET rather than an automatic POST retry.
- Both manual and automatic actions animate the saved event sequence: attack lunge, type-coloured projectile, hit/miss/immune text, HP changes, recoil, fainting and switches. Reduced motion shows saved results immediately. Navigation/pause clean up playback effects; final state is redrawn from the server response.
- MongoDB turn entries record manual/auto controller, actual action and, for auto decisions, policy `expected-damage-1` and explanation. Switch slots and move types support unambiguous playback. Existing documents and predictions remain readable without backfilling.
- Existing revision checks, active-battle limits, result handling and idempotent reward delivery are reused. Auto victories retain the reward-case opening flow.

## Checks completed

- Full suite with `RUN_QUERY_TESTS=1`: **80 tests discovered, 71 passed, 9 skipped**. The skipped tests are the pre-existing full-application suite requiring a different MySQL account with disposable-database creation privileges.
- Seven new offline tests verify accuracy/PP/immunity, stable choices, fallback, legacy damage caps, free replacement, eventual completion, policy/action recording, preserved predictions, manual metadata, stale revisions/ownership and a lost replacement race without reward delivery.
- Two new real-service tests passed against local MySQL 26.7.0 and MongoDB, including a follow-up extension through the actual Flask action endpoint with a selected session and CSRF token. They verify accepted validator fields, auto/manual turn persistence, free replacement, stale rejection and an auto win producing exactly one SQL collection reward across repeated reads. SQL fixtures roll back; unique MongoDB test databases are dropped. Auto-increment gaps can remain.
- `scripts/check_auto_battle.py` passed in headless Edge with every API request intercepted. Fixture POSTs use the real in-memory policy/resolver. Checks cover visible projectiles, manual moves/switches/misses, saved HP, explanations, pause during a held request, forced replacement, navigation during a request, hidden-tab stop, failure recovery without retry, reduced-motion effects, 390px layout and automatic stop at victory with the reward case intact. No application database writes occur in this browser check.
- The existing `scripts/check_database_evidence.py` browser fixtures passed with the new scripts loaded, covering analytics filters, metric displays, external evidence, mobile layout and error handling.
- `git diff --check` passed, with only a Windows line-ending notice.

Screenshots (ignored local artifacts): `.local/battle-attack-desktop.png` and `.local/battle-arena-mobile.png`. These use controlled battle fixtures, not claimed real player statistics. Images were visually inspected. A temporary app on port 5051 served the updated code for browser checks and was stopped afterward. The user's existing server on port 5050 was left running.

## Try it

Stop the running app in its terminal with **Ctrl+C**, then run:

```cmd
python scripts/run_local.py
```

Refresh `http://127.0.0.1:5050` with **Ctrl+F5**, select a trainer and start/resume a battle. Click **Auto Battle** to watch; click **Pause Auto Battle** to take over. The battle log shows each AI reason. Manual attacks also animate. No database setup/import command is required for this update.

## Limits

The controller is a simple one-step heuristic and can repeat its best move. It chooses a replacement after fainting but does not plan voluntary switches, future PP use or complete battle sequences. The browser must remain on the visible battle screen for automation to continue; an already submitted action can still finish after a pause/navigation.

Existing overall statistics/prediction history still include different player decisions. Per-turn controller/policy metadata enables future comparisons; a battle containing both manual and auto turns must be treated as mixed. Animation timing also affects recorded wall-clock duration, which already includes thinking time. See the [design notes](../database-design/auto-battle.md) for a sample MongoDB query and interpretation limits.

## Files created

- `backend/battles/automation.py`: deterministic policy and explanations.
- `frontend/static/battle-effects.js`: cancellable event playback.
- `scripts/check_auto_battle.py`: in-memory browser fixtures.
- `tests/test_auto_battle.py`, `tests/test_auto_battle_database.py`: policy, persistence and reward checks.
- `docs/database-design/auto-battle.md` and this verification report.

## Files modified

- `backend/battles/service.py`: server-side auto actions and controller/policy metadata.
- `backend/battles/engine.py`: move-type and exact switch-slot event metadata.
- `frontend/static/app.js`: Auto/Pause controls, serialized requests, recovery and log explanations.
- `frontend/static/style.css`: arena effects, sprite stages and responsive/reduced-motion styles.
- `frontend/index.html`: ordered effect-script loading and updated asset cache versions.
- `README.md`, `docs/database-design/battle-rules.md`: run instructions and current behaviour.
