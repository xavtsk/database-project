# INF2003 Group 13 — UI and battle balance verification

The prototype now displays INF2003 Group 13, with a red, yellow and blue Pokémon theme, type-coloured cards and moves, and a stadium background for battles.

The previous battle formula allowed strong moves and type multipliers to remove all HP in one attack. New battles use `prototype-2`: each attack is capped at 40% of the defender's maximum HP. Type immunities still cause zero damage. This is a simplified project rule, not an official Pokémon mechanic. Saved `prototype-1` battles retain their original rules; start a new battle to use the change.

## Verification

- All 32 unit and database integration tests passed. Regression coverage checks the damage cap, type immunity and legacy rules.
- A deterministic comparison used 180 starter battles per rules version (three starters, three difficulties and 20 seeds). One-turn battles fell from 42 to zero. The new battles lasted 3–8 turns, with a median of 3.
- Browser checks passed for all five screens, all three difficulties, battle resumption, rewards, team CRUD and mobile layout, with no JavaScript errors.
- These starter scenarios do not establish balance for every possible team. Hard mode remains challenging: the scripted player won 4 of 60 hard-mode battles in this comparison.

## Files

Created for this follow-up:

- `scripts/check_battle_balance.py`
- `docs/progress-report/ui-balance-v2-verification.md`

Updated for this follow-up:

- `frontend/index.html`
- `frontend/static/style.css`
- `frontend/static/app.js`
- `backend/battles/engine.py`
- `backend/battles/service.py`
- `tests/test_battle_engine.py`
- `scripts/check_browser.py`
- `docs/database-design/battle-rules.md`
- `README.md`

## Reproduce

With the local databases running and `.env` loaded:

```sh
RUN_DB_TESTS=1 python3 -m unittest discover -s tests -v
python3 -m scripts.check_battle_balance
```

With the app running, use `python3 scripts/check_browser.py` for the optional browser check. It requires the development dependencies and Chromium and creates labelled test profiles and battle records.

Pokémon evolution, experience and levelling are not implemented.
