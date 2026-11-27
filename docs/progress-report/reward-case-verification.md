# Victory case reveal

Implemented on 2026-10-20 at the user's request to make winning rewards feel like a case opening.

## Behaviour

- A winning battle presents a Poké Ball case with an **Open reward case** button.
- Opening scrolls a strip of Pokémon cards beneath a central marker, slows to the saved reward, then reveals the Pokémon with its rarity colour and delivery status. The reel takes 4.6 seconds; **Skip animation** reveals immediately.
- The server continues choosing and awarding exactly one Pokémon using the existing rarity odds and unique battle-reward record. The browser's decorative cards do not choose the reward or send a grant request. No schema or backend reward changes are involved.
- Revealed battle IDs are remembered in browser local storage, with an in-memory fallback when storage is unavailable. Refreshing or reviewing the battle shows the existing reward. Another browser may replay the cosmetic opening, but it cannot grant another Pokémon.
- Navigation cancels the visual cleanly. Reduced-motion preferences skip the reel. Missing decorative catalogue data uses mystery cards and still reveals the saved reward; text remains available when sprites cannot load.
- Losses and draws retain their existing result screens. Reward delivery pending/retry text remains available.

## Verification

The new `scripts/check_reward_case.py` was run headlessly against the running local app using installed Microsoft Edge and the existing optional Playwright dependency. Browser API responses were intercepted with fixture data; the script rejects all non-GET API requests, so it creates or changes no trainers, battles or collection entries.

Verified full animation, the server-fixture winner, skipping, browser reload persistence, double-click protection, navigation cancellation, reduced motion, pending reward delivery, decorative catalogue failure, mobile width and absence of cases for losses/draws. JavaScript reported no page errors. Screenshots of sealed, opening, revealed and mobile states were inspected under ignored `.local/reward-case-*.png`.

`node --check frontend/static/app.js`, Python parsing of the browser scripts and `git diff --check` also passed. The existing live browser check was updated to open/skip a winning case before inspecting the delivered reward; the full randomized battle browser suite was not rerun for this frontend-only change.

## Files created

- `scripts/check_reward_case.py`
- `docs/progress-report/reward-case-verification.md`

## Files modified

- `frontend/static/app.js`
- `frontend/static/style.css`
- `frontend/index.html` (asset cache versions)
- `scripts/check_browser.py`
- `README.md`

## Try it

With the existing app running, hard-refresh the browser (Ctrl+F5), win a battle and select **Open reward case**. Check **Skip animation**, then review the same winning battle from history. The saved Pokémon should remain the same. Existing wins can also be opened from history to see the new presentation.

For repeatable browser checks with the current local Edge installation:

```powershell
$env:BROWSER_CHANNEL = 'msedge'
python scripts/check_reward_case.py
```

Install the existing `requirements-dev.txt` first, or use its Playwright Chromium installation and omit `BROWSER_CHANNEL`. `APP_URL` can select another running app address. The app itself has no new dependencies.
