# INF2003 Group 13 — battle rules v2

The implementation follows the approved [proposal](playable-prototype-proposal.md), with the damage pacing fix requested on 2026-09-23. These are simplified project rules, not the complete official battle engine.

## Data and move pools

- Original 151 species, current cached stats/types and move references across game versions.
- All 18 types, including the added Dark resource; 324 attacking/defending effectiveness pairs.
- The supported pool contains 353 physical/special moves with numeric positive power.
- Each Pokémon has a fixed eligible pool. Players select four distinct moves; suggested defaults can be edited.
- Every supported move is treated as a single-target, single-hit attack. Charging, secondary effects, variable hit counts, drain, status effects and similar special behaviour are deliberately omitted.
- Ditto, Kakuna, Metapod, Magikarp and Weedle receive enough fallback entries from Tackle, Pound, Quick Attack and Swift to reach four supported moves. Additions are tagged `project_override` and displayed with ★. These are game-specific additions, not official learnsets.
- `data/processed/game_data.json` contains every prepared catalogue row, including all eligibility overrides. Raw JSON is unchanged.

## Turns

HP is `2 × base HP + 60`. Other combat stats are `base stat + 5`, using an effective level of 50.

Damage is `floor((22 × power × attack / defense / 50 + 2) × STAB × type factor × random factor)`.

Use Attack/Defense for physical damage and Special Attack/Special Defense for special damage. STAB is 1.5 for a matching attack type and 1 otherwise. Type factors multiply for dual-type defenders. Random factor is uniform from 0.85 to 1.0. Immunities cause zero damage; other successful hits cause at least one.

**Rules v2 pacing:** after the formula, cap a hit at `max(1, floor(defender maximum HP × 0.40))`. Apply the same limit to both sides and to Fallback Strike; the AI evaluates the capped damage when choosing a move. The limit uses maximum HP rather than remaining HP, so low-HP targets can still faint. Existing rule-v1 battles keep uncapped damage; new battles are recorded as `prototype-2`. This cap is a project-specific balancing rule, not an official Pokémon mechanic.

In 180 deterministic starter simulations per version, v1 had 42 one-turn battles and a median of two turns. V2 had zero one-turn battles and a median of three turns, with a range of 3–8 turns. These checks cover starters with suggested moves, not every possible team; difficulty still needs wider gameplay calibration. Reproduce with `python3 -m scripts.check_battle_balance`.

Accuracy is checked per attempted move. Null accuracy bypasses that check. PP decreases even when a move misses. Priority acts first, followed by Speed and a random tie break. A fainted Pokémon loses its queued action.

Voluntary switching uses the player's action and happens before the opponent attacks. Forced replacement after fainting is free. The opponent selects its next healthy member. The opponent selects its move using only information available before the player's action.

If no move has PP, Fallback Strike is available: neutral 50-power physical damage, no STAB or immunity, and recoil equal to one quarter of actual damage dealt (minimum one).

All opponents defeated is a win; all player members defeated is a loss. Simultaneous defeat or 200 completed turns is a draw. Forfeiting is a loss. Only wins grant rewards. HP/PP reset each battle.

## Optional player automation and animation

The user approved adding Auto Battle and animations on 21 October 2026. Auto Battle uses policy `expected-damage-1` to choose one player action per request through the existing action endpoint. It chooses the available move with the highest estimated accuracy-adjusted damage under the saved rules, or a healthy replacement after fainting. Manual attacks/switches remain available when automation is paused. See the [policy and lifecycle details](auto-battle.md).

This changes the player controller, not the damage formula or battle rules version. Turn logs record `controller`, the actual chosen `action`, and, for auto decisions, `policy` and `decision`. Move events add `move_type`; switch events add the exact member `slot` for unambiguous visual playback, including duplicate species. Older logs stay readable.

The browser animates only saved events: lunge, coloured projectile, HP changes, miss/immune text, recoil, fainting and switches. Animation never resolves damage or awards a reward. Reduced-motion preferences skip the movement sequence.

Successful attacks show **Super effective!** for combined multipliers above 1, **Not very effective.** for multipliers between 0 and 1, and **No effect.** for immunity (0). A compact message box below the arena shows each saved event individually: player/enemy moves and damage, effectiveness or miss, fainting and switching. Floating attack labels and the saved battle log remain. The combined two-attack summary stays removed. Misses never receive an effectiveness message; ordinary 1× hits and older events without a multiplier have no extra message. Reduced-motion preferences skip movement while retaining readable event messages and log text.

## Difficulty and rewards

The opponent always matches the player's team size. Generate 100 candidate teams and aim for 85%, 100% or 115% of the player's total base stats. Among candidates within 5% of the closest strength gap, Easy prefers weaker type matchups, Medium neutral matchups and Hard stronger matchups. Record the actual selected strength. This is a heuristic, not a calibrated win-rate guarantee.

Easy chooses random usable moves. Medium chooses randomly half the time and otherwise maximizes expected damage. Hard maximizes expected damage, accounting for accuracy and immunity.

Rewards first select a tier, then a species uniformly within that tier. Easy uses 60% common / 25% uncommon / 12% rare / 3% legendary; Medium uses 58% / 25% / 12% / 5%; Hard uses 56% / 25% / 12% / 7%. Duplicates become separate owned instances. Legendary/mythical flags define the top tier; other species use capture-rate bands of at least 150, 75–149, and below 75. This is a project-specific rarity mapping, separate from combat strength.

Each new victory reward also gets an independent shiny roll: 1% on Easy, 2% on Medium and 3% on Hard, saved once. New battles snapshot their reward odds; already rolled rewards retain their results and saved odds. Non-legendary species allow six normal and six shiny owned copies separately; full reward variants are rerolled within the same tier, or among available tiers using saved weights if necessary, without changing shiny status. Legendary collection copies remain unlimited, but teams allow one of each legendary species across both variants. Shiny appearance changes no combat values. See [collection and shiny rules](collection-rewards.md).

## Persistence and analytics

- One active battle per trainer, enforced with a partial unique MongoDB index.
- Actions carry a revision. Conditional document replacement accepts at most one action for that revision.
- The outcome and initial selected reward are saved to MongoDB before SQL reward delivery. A full collection variant may require an eligible replacement during delivery. A unique battle UUID in SQL and a trainer row lock make delivery retry-safe: once SQL records the award, retries restore that same owned instance and shiny status.
- Both teams' initial snapshots are immutable. Editing/deleting a saved team preserves existing battle history.
- Win rate is wins divided by all completed battles, including draws and forfeits. Active battles are excluded.
- Pokémon usage counts battles in which the species appeared on the player's initial team, once per species per battle. Its win rate is the team's result, not an individual knockout metric.
- Move usage counts executed player moves, including misses; skipped moves after fainting are excluded.
- Duration includes player thinking time. MongoDB aggregation pipelines calculate the summaries.
