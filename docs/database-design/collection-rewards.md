# Collection copies and shiny rewards

Approved in the user request on 21 October 2026, including separate six-copy limits and rerolling full variants.

## Behaviour

| Rule | Result |
| --- | --- |
| Non-legendary collection | Up to six normal **and** six shiny copies of each species per trainer |
| Legendary/mythical collection | Copies can remain in the collection without a six-copy limit |
| Legendary/mythical team | One of each species, counting normal and shiny together |
| Non-legendary team | Duplicate species allowed, using different owned instances |
| Team size/budget | Existing six-member and 30-point limits still apply |
| Shiny chance | Independent draw below `0.01` on Easy, `0.02` on Medium, `0.03` on Hard |
| Starter | Normal; not a victory reward |
| Shiny effect | Appearance only; identical stats, moves, cost and prediction inputs |

The existing `pokemon.rarity='legendary'` mapping includes mythicals. Two different legendary species can share a team. A normal Mewtwo and a shiny Mewtwo cannot share a team. Six normal Bulbasaur copies do not block a shiny Bulbasaur reward.

The chance is per reward, with no guarantee of a shiny within any particular number of wins. Shiny status is rolled and saved once when the win is resolved. Opening a case, skipping the animation, reloading, and collection-limit rerolls do not draw shiny status again. Older rewards without the flag are normal.

Difficulty bonuses were requested on 21 October 2026:

| Difficulty | Common | Uncommon | Rare | Legendary / mythical | Independent shiny |
| --- | ---: | ---: | ---: | ---: | ---: |
| Easy | 60% | 25% | 12% | 3% | 1% |
| Medium | 58% | 25% | 12% | 5% | 2% |
| Hard | 56% | 25% | 12% | 7% | 3% |

Extra legendary probability comes from common probability; rarity tiers still sum to 100%. A shiny can occur in any tier. A new battle snapshots its reward odds, and each winning reward stores its odds and policy version. Existing active battles without the snapshot use their saved difficulty when they next win. Already rolled rewards retain their results and original odds; older rewards without odds metadata use the original 60/25/12/3 and 1% display/fallback. The backend supplies the UI rate table, avoiding a separate set of browser probabilities. No schema migration is required.

## SQL storage and award transaction

`owned_pokemon.is_shiny BOOLEAN NOT NULL DEFAULT FALSE CHECK(is_shiny IN (0,1))` records the variant of each owned copy. Catalogue species remain shared and unchanged. The migration adds this column when missing; setup applies it too. Existing rows default to normal, and rerunning the migration does nothing.

Award delivery first locks the trainer row with `SELECT ... FOR UPDATE`. Starter selection and team saves use the same lock. The [reward-pool query](../../database/relational/queries/reward_pool.sql) uses a variant-filtered `LEFT JOIN`, `GROUP BY` and `HAVING COUNT(o.id)<6`, with an explicit exception for legendary species. A full normal variant is excluded only for a normal reward, and likewise for shiny.

If the saved species is full, delivery chooses another eligible species in the same rarity tier. If that entire tier is full, it chooses among available tiers using the reward's saved difficulty weights (original weights for legacy rewards), then a species within the selected tier. Therefore displayed base rarity percentages can change when a tier fills. Shiny status stays unchanged. Legendary species remain available, so a complete catalogue always has an eligible reward. A missing/empty eligible catalogue leaves the saved reward pending instead of discarding it.

The replacement choice is stable for a battle and the current eligible pool. The unique `battle_rewards.battle_id` record and its owned instance become authoritative when SQL commits. If the following MongoDB marker fails, the next read joins back to that record and restores the actual species and variant without granting another copy. The saved reward retains its original roll and, when replaced, a `rerolled_from` explanation. A legacy excessive collection is preserved, but new application rewards do not add to its full variants.

The aggregate cap is enforced by the application transaction, not by the Boolean check itself. Direct manual SQL inserts can bypass application count rules. This change adds no trigger, dependency or background job.

## Teams, recommendations and display

Saving a team validates species after ownership/move checks and before editing rows. New battle entry validates the rule too, so older duplicate-legend teams must be repaired. Existing battle snapshots continue as saved. SQL recommendation plans exclude duplicate legendary species after the proposed addition/replacement; the Python reference scorer follows the same rule. A replacement may remove an old duplicate to repair a team.

Collection groups sort by Pokédex number, then normal before shiny, then owned ID. Group headings show separate counts. Shiny copies use badges, gold borders and twinkling stars; roster/battle images use the matching front/back variants from the existing [PokéAPI sprite repository](https://github.com/PokeAPI/sprites). The saved shiny reward appears in the case reel and reveal. Reduced-motion preferences disable the new movement effects and preserve labels/colours.

## Apply and verify

```sh
python -m scripts.migrate_collection_rewards
python scripts/run_local.py
```

Restart any existing app process and refresh the browser. The migration was applied to the local development database on 21 October 2026; teammates need to apply it to their own databases. See [verification](../progress-report/collection-rewards-verification.md) for checks and changed files.
