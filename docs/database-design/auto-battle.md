# Auto Battle and saved-event animations

Approved by the user on 21 October 2026 as an optional extension to the existing turn-based simulator. Uses the existing Flask endpoints, battle engine, MySQL rewards and MongoDB documents. No new dependency or schema migration is needed.

## Player policy

`backend/battles/automation.py` implements `expected-damage-1`:

1. Read only the current saved player/opponent state. Do not inspect the opponent's next random choice.
2. For each move with PP, estimate damage with the existing formula and a representative random factor of 0.925. Apply the saved rule version's damage cap and limit damage to the target's remaining HP. Multiply by accuracy; null accuracy counts as 100%.
3. Pick the highest score. Tie-break by higher accuracy, more remaining PP and lower move ID. This is deterministic given the snapshot and chart.
4. If all four moves have no PP, choose the existing Fallback Strike, including its existing recoil rules.
5. If the active member has fainted, choose a healthy replacement with the best available estimated attack, then higher remaining HP fraction and lower slot. The existing engine handles the free replacement.

This is a simple rule-based controller, not trained AI or a complete search of future turns. The score is an approximation, not the exact expected value of the randomized combat process. It does not plan voluntary switches, future PP conservation or move-order knockouts. A move can still be chosen repeatedly if its score stays highest.

## Actions and storage

The browser posts one action at a time to the existing endpoint:

```json
{"revision": 3, "action": {"kind": "auto"}}
```

The server checks profile ownership, active status and revision, chooses the concrete move/replacement, and passes that action into the existing resolver. The conditional MongoDB replacement still accepts at most one write at a revision. Reward selection/delivery stays on the existing save-then-deliver path with its unique SQL battle key.

Each new turn stores:

```json
{
  "controller": "auto",
  "policy": "expected-damage-1",
  "action": {"kind": "move", "move_id": 55},
  "decision": "Chose ... highest estimated accuracy-adjusted damage ...",
  "events": []
}
```

Manual turns store `controller: manual` and their action. Auto policy and explanation come from the server; a client-supplied policy/move in an auto request cannot override them. The metadata records an intended choice; a Pokémon knocked out before acting still has no executed attack event. Forced replacement is an action/revision but does not increase the combat-turn count.

The existing validator allows these embedded turn fields. There is no backfill. Older missing-controller turns predate this feature and are displayed as manual; their original data is preserved. Battle rules and saved pre-battle predictions stay unchanged when switching controllers.

## Browser lifecycle

- **Auto Battle** starts a local paced loop: send one request, display its events, then wait 700ms before another request. There is no unattended server worker.
- Manual move/switch/forfeit buttons are disabled while auto control or a submitted request is active. **Pause Auto Battle** stays usable during an auto request or animation.
- Pause cancels future scheduling; an already submitted request may finish and persist one action. The user can take over after it finishes.
- Navigation, profile actions, a hidden tab, reload, a finished battle or an error stop automation. Reload reads the saved battle without automatically restarting the loop.
- If a request fails, stop and attempt one read to recover canonical state. Do not automatically retry the POST, since it might already have committed. Existing revision checks protect against stale or competing requests, including another tab.
- A response for a previous trainer/battle cannot replace the new selection. A response arriving after navigation can update the saved local battle reference without recreating the arena or submitting another turn.

## Animation

`frontend/static/battle-effects.js` replays only the newly saved events against a display copy of the previous snapshot. It never calculates outcomes. Attack motion, type-coloured projectiles, damage/miss/immune labels, HP bars, recoil, fainting and switches follow event order. The final display is always redrawn from the server's returned state.

Move events store `move_type` for colour. Switch events store the exact zero-based team slot, avoiding ambiguity when two members share a species name. Playback is cancelled safely on navigation/pause and cleans up transient elements. A compact message box shows one saved event at a time, including both sides' attacks, misses/effectiveness, fainting and switches. Moves remain readable for at least 1.6 seconds, faints 1.2 seconds and other events one second, including when reduced-motion preferences bypass movement effects. Cancellation releases any pending reading delay immediately. Reload shows only the latest saved event and never replays historical turns. Sprite loading is decorative; it does not gate a turn or require new image assets.

## Database demonstration

Controllers can be mixed in one battle, so do not label an entire battle “AI” from its last action alone. For example, count chosen actions by controller/policy rather than treating each action as an independent battle outcome:

```javascript
db.battles.aggregate([
  {$match: {trainer_id: 1, rules_version: "prototype-2"}},
  {$unwind: "$turns"},
  {$match: {"turns.kind": {$in: ["turn", "replacement"]}}},
  {$group: {
    _id: {controller: {$ifNull: ["$turns.controller", "manual"]},
          policy: {$ifNull: ["$turns.policy", "manual"]}},
    chosen_actions: {$sum: 1}
  }}
])
```

This includes free replacements and choices that did not execute after a knockout; use move events to count executed attacks. Existing overall analytics and prediction-context definitions continue to pool player decisions. A future strategy comparison should separate manual-only, auto-only and mixed battles, policy versions, rules, difficulty and team size. Auto and manual play can differ in outcomes; saving the policy makes that distinction possible without mislabelling source rules.

## Verification commands

```powershell
python -m unittest tests.test_auto_battle -v
$env:RUN_QUERY_TESTS = '1'
python -m unittest tests.test_auto_battle_database -v
python scripts/check_auto_battle.py
```

The two real-service tests use uniquely named disposable MongoDB databases and MySQL fixture rows in a rolled-back transaction; auto-increment gaps may remain. Browser checks intercept every API call and resolve fixture POSTs in memory. They do not create trainers, battles or rewards in the application's databases. See the [verification report](../progress-report/auto-battle-verification.md).
