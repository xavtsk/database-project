# Sequential battle messages — 22 October 2026

Added one compact message box beneath the pixel arena. It shows saved events individually in their actual order: player move, enemy move, damage, effectiveness or miss, recoil, fainting and switching. The combined paragraph summarizing both attacks remains removed. The complete history stays in the Battle log below.

Move messages remain readable for at least 1.6 seconds, faint messages 1.2 seconds and other events one second. The latest event stays visible after playback and on reload. Reduced-motion preferences skip movement effects while preserving the readable sequence. Pause/navigation cancellation clears pending reading timers and animations. Messages use text content or escaped saved values; they do not calculate damage or create battle events.

The pixel scene retains its fixed minimum size; a separate grid row holds the message box so changing text does not compress the fighters. Mobile text has extra reading space. No backend, database or combat-rule changes are needed.

## Verification

- Updated `scripts/check_auto_battle.py` passed in headless Edge. A DOM observer verifies every event's message appears in order and that the final event remains visible.
- Checks cover player/enemy moves, 2×/4× super-effective hits, 0.5×/0.25× resistance, immunity, misses, player fainting before replacement, opponent fainting at victory, reduced motion and reload. Existing Auto Battle, pause, replacement, navigation, failed-request, layout and victory-stop checks also pass.
- Layout checks verify one message box beneath the arena, no old summary element, diagonal sprite placement and no overflow from 320px to desktop. Desktop/mobile screenshots were inspected; previews are fixture examples.
- Verification used an isolated template/asset preview on port 5051 with intercepted API calls and in-memory battles. It requires no running database and writes no player data. The preview server was stopped afterward; the user's app on 5050 was left alone.
- `git diff --check` passes.

## Files

Created: this report and ignored `.local/run_browser_preview.py` (fixture preview host).

Modified:

- `frontend/static/app.js`: current-event message and latest saved event on reload.
- `frontend/static/battle-effects.js`: sequential messages, reading delays, reduced-motion support and cancellable timers.
- `frontend/static/style.css`: message box and stable responsive sizing.
- `frontend/index.html`: refreshed asset cache versions.
- `scripts/check_auto_battle.py`: ordered message, fainting and layout assertions.
- `README.md`, `docs/database-design/auto-battle.md`, `docs/database-design/battle-rules.md`: current message behaviour.

Press Ctrl+F5, start/resume a battle and choose a move or Auto Battle. The message box should announce each attack and any resulting faint/replacement. No setup/import is required.
