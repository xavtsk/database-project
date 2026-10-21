# Pixel battlefield and sprite placement — 21 October 2026

Replaced the stretched gradient arena with an original pixel-art meadow: block clouds, a layered tree line, grass texture and stepped grass platforms. Both SVG assets are local, contain no external references and use crisp edges. No image-generation service, asset download, new dataset or dependency is required.

Your back-facing Pokémon sits in the lower-left foreground; the front-facing opponent sits in the upper-right background. Name, type, HP and team indicators are in separate opposite-corner panels. Sprite frames are sized independently of those panels and the platform position accounts for the transparent sprite canvas. Shiny variants, faint styling and the existing attack/replacement effects use the same selectors. Moves remain beside the arena on desktop and analysis stays below; the duplicate turn-summary box remains removed.

## Verification

`scripts/check_auto_battle.py` verifies diagonal placement, sprite frames inside the arena, no sprite-frame/HP-panel overlap, locally referenced background, control/analysis layout and no horizontal overflow at 1440, 1280, 1024, 390 and 320px. It also exercises manual/auto attacks, diagonal projectile paths, switching/replacements, type messages, pause/navigation/error handling, reduced motion and victory stopping with intercepted API fixtures.

`scripts/check_collection_rewards.py` checks normal/shiny front/back sprites, sparkles, variant labels, legendary team rules, reduced motion and reward reveals. All browser actions use in-memory fixtures, with no player database writes. Desktop/mobile previews are saved under ignored `.local/pixel-battle-desktop.png` and `.local/pixel-battle-mobile.png`. External sprite loading is allowed to time out during preview capture without blocking layout verification.

Both browser scripts passed in headless Edge after the final platform adjustment. Desktop/mobile previews were visually inspected with both sprites loaded and resting on their platforms. `git diff --check` passed. These are controlled preview fixtures, not live trainer battles.

## Files

Created:

- `frontend/static/battlefield.svg`: original pixel meadow background.
- `frontend/static/battle-platform.svg`: original stepped grass platform.
- This verification report.

Modified:

- `frontend/static/app.js`: separate sprite stages and status panels.
- `frontend/static/style.css`: diagonal placement, canvas/platform alignment, pixel scenery, status panels and mobile sizing.
- `frontend/index.html`: refreshed CSS/JS cache versions.
- `scripts/check_auto_battle.py`: placement, overlap and background assertions and previews.
- `README.md`: current visual behaviour.

No backend, database, damage, prediction or reward changes are needed. Press Ctrl+F5 to load the update. The temporary test server on 5051 is stopped after verification, leaving the user's existing app on 5050 alone.
