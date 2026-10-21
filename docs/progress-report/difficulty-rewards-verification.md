# Difficulty reward bonuses — 21 October 2026

Implemented the user's requested Medium/Hard shiny and legendary bonuses. Increased legendary odds come from the common tier, keeping each rarity distribution at 100%:

| Difficulty | Common | Uncommon | Rare | Legendary / mythical | Independent shiny |
| --- | ---: | ---: | ---: | ---: | ---: |
| Easy | 60% | 25% | 12% | 3% | 1% |
| Medium | 58% | 25% | 12% | 5% | 2% |
| Hard | 56% | 25% | 12% | 7% | 3% |

Shiny remains independent of rarity and cosmetic. Manual and Auto Battle use the saved server difficulty, not a client-supplied difficulty in an action. New battles snapshot their reward odds; each rolled reward also stores its odds, difficulty and policy version. Existing active battles without an odds snapshot use their saved difficulty when they win. Existing rolled rewards retain their results and original odds. Collection caps, eligible rerolls, starter behaviour and SQL reward retry protection remain in place. Cross-tier rerolls use the reward's saved rarity weights; older rewards use their original weights.

The backend supplies the rate configuration to the page as JSON. Battle difficulty cards and the rate table show the new chances; cases show the odds saved with their reward. Older cases without odds metadata show the original 60/25/12/3 and 1% chances. No database schema migration, new dependency or data rewrite is needed.

## Verification

- `RUN_QUERY_TESTS=1 python -m unittest discover -s tests -q`: **101 discovered, 92 passed, 9 skipped**. Skips are the existing full-database integration class requiring broader MySQL database-creation permissions. Regular-account SQL rollback fixtures and disposable MongoDB tests passed.
- Probability boundaries checked on each difficulty, including immediately below and exactly at the shiny threshold and legendary threshold. Rarity distributions sum to 100%.
- Tests verify server-side difficulty selection for manual/auto wins, saved-odds independence from later configuration changes, and weighted fallback when a rarity tier is full.
- Real MySQL/MongoDB fixtures verify different outcomes from the same draw on Easy/Medium/Hard and unchanged odds, owned instance and shiny status after resetting/retrying the MongoDB delivery marker.
- Ignored `.local/check_last_battle_team.py` verifies difficulty cards, a 390px rate table, saved odds for all three difficulties and original odds for a legacy Hard battle. Existing last-team selection/resume/fallback checks also pass. All API data is mocked; no player database writes occur.
- `scripts/check_collection_rewards.py` passes: grouped shiny display, legendary team guard, front/back sprites, sparkles, reduced motion, case opening/skip/reload and mobile layout.
- `git diff --check` passes. The temporary server on 5051 was stopped; the user's existing app on 5050 was left running.

## Files

Created: this verification report. Extended the ignored local browser verification script.

Modified:

- `backend/battles/service.py`: difficulty odds, snapshots, independent rolls and saved reroll weights.
- `backend/app.py`: pass the backend rate table to the page.
- `frontend/index.html`, `frontend/static/app.js`: JSON configuration, refreshed script cache, difficulty hints, full rate table and saved case odds.
- `tests/test_collection_rewards.py`, `tests/test_collection_rewards_database.py`, `tests/test_team_advice.py`: probability, delivery and snapshot checks.
- `README.md`, `docs/database-design/collection-rewards.md`, `docs/database-design/battle-rules.md`: current rates and compatibility behaviour.

Restart the app (`Ctrl+C`, then `python scripts/run_local.py`) and press Ctrl+F5. Open Battle arena to compare the difficulty rates before starting. Existing collections and rolled rewards are unchanged. No commit or push was requested or made.
