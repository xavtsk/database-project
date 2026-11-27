# Last used battle team — 21 October 2026

New battle setup preselects the selected trainer's most recently used team that still exists and has members. It uses the existing newest-first MongoDB battle history, now including `team_id`. No new preference table, migration or browser-only storage is needed. If none of the latest 50 battles references an available non-empty team, the first non-empty saved team is selected. With no usable teams, the placeholder remains and starting a battle stays disabled. The server still validates team ownership and eligibility on submission.

Selection persists across reloads and computers using the same databases. Battle again uses the trainer's latest battle rather than the particular older result being reviewed. Active battles still resume, and the user can choose a different saved team before starting.

Browser fixtures in ignored `.local/check_last_battle_team.py` passed for: initial last-team selection, reload, submitting a manually chosen team, remembering that new choice, active-battle resume, Battle again, deleted/empty teams, legacy history without team IDs, a different trainer and no teams. All API requests were intercepted, with submitted battles kept in memory and no database writes. The real read-only MongoDB history check returned the stored team ID. The API error tests and `git diff --check` passed.

Created: this report (plus the ignored local verification script).

Modified:

- `backend/analytics/service.py`: include `team_id` in the existing history projection.
- `frontend/static/app.js`: select the most recent usable team, with a first-team fallback.
- `frontend/index.html`: refresh the JavaScript cache version.
- `README.md`: describe defaults and fallbacks.

To try it, restart the Python app and press Ctrl+F5. Start a battle with a different saved team, finish/forfeit it, then click Battle again or reload the arena: that team should already be selected. No database setup is required. The temporary verification server on 5051 was stopped; the existing user server on 5050 was left running.
