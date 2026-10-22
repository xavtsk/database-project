# Presentation and recording plan

This is a script/slide plan, not a completed PPTX or recording. The brief
requires all five members to present, names visible, background → relational
implementation → NoSQL implementation → optional performance in that order,
and a video no longer than ten minutes at normal speed. Target **9:30**.
Replace Member 1–5 with actual names and agree truthful contribution claims.

| Time | Speaker | Slides / demonstration | What the audience must understand |
| --- | --- | --- | --- |
| 0:00–1:15 | Member 1 | Problem, original-151 scope, three source categories, architecture | Why both stores suit different data; external synthetic history versus own simulator logs |
| 1:15–3:05 | Member 2 | ER diagram, species/owned-instance distinction, keys/constraints, team CRUD | How ownership and membership relationships support a safe team edit; show one invalid save and explain the transaction |
| 3:05–4:55 | Member 3 | Team stats/coverage and recommendations; one SQL/view/CTE walkthrough | Useful aggregates/ranking, not just game animation; SQL inputs and actual output |
| 4:55–7:05 | Member 4 | MongoDB model, one document, turn revision, history and a populated analytics panel | Embedded snapshots/events, validator/indexes and a meaningful aggregation |
| 7:05–8:20 | Member 5 | Remaining NoSQL/cross-store comparison and reward recovery | Matching award identities, transaction boundary and idempotent repair; honest SQL/NoSQL trade-offs |
| 8:20–9:30 | Member 5 | Measurements, limitations and conclusion | Reproducible method, actual results, network confound, justified future improvements |

The durations total 9:30. Keep transitions, title screens and credits inside
that total. Display the current speaker's name. Prepare roughly 8–10 readable
slides; full source listings belong in the code/report, not tiny slide text.

Use the [feature explanation guide](../database-design/project-explanation-guide.md)
for short spoken examples. Lead with what each feature helps the user do,
then show its database work and result. Normalisation is optional supporting
design material; keep formal proofs for questions or a relevant report appendix.
If making a normal-form claim, explain the documented ownership redundancy.

## Prepare the demonstration before recording

- Use an isolated labelled demo trainer/database. Show the real stored data;
  do not replay a fixture as though it were observed gameplay.
- Have a saved team with useful coverage/weaknesses and an affordable unused
  collection candidate so the recommendation example is meaningful.
- Select a populated 1v1 pair and rule/difficulty filter. The audit counted 40
  initial 1v1 battles across pairs, not 40 for every chosen pair. Keep the
  sample-size label visible and explain it.
- Keep one completed battle ready for document/history inspection. Demonstrate
  a short actual turn if needed; do not spend minutes waiting for random wins.
- Prepare an extra disposable team for CRUD; do not delete the only team needed
  for the rest of the video. Show an invalid change before a successful save.
- Show a validator/index definition and one aggregation stage sequence.
- Use captured comparison results with the exact method and limits. If a
  database/network is unavailable during recording, label any backup screen
  capture honestly instead of implying a live run.
- Do not show `.env`, passwords, connection URIs, SSH keys or billing details.

## Suggested spoken transitions

“Our relational catalogue separates shared species data from owned copies.
Next we show how those relationships support a safe team edit.”

“These summaries and partner rankings are calculated by MySQL. The battle
creates another kind of data: nested snapshots and events, which we store in
MongoDB.”

“The MongoDB pipeline describes what happened under selected rules and
difficulty. An observed sample win rate is not a trained prediction.”

“The SQL award and MongoDB marker have separate commits. A unique battle award
lets a later read repair delivery without granting a second Pokémon.”

## Before declaring the recording ready

- All five people speak with their names shown.
- Background, SQL, NoSQL and performance appear in the required order.
- Methods, analysis, results, conclusions and implications are explicit.
- Slides match current features rather than outdated proposal promises.
- Text/ER diagram/document snippets remain readable at normal video size.
- A normal-speed timed rehearsal and final recording both fit within ten minutes.
- The actual PPTX, MP4 and final-report PDF exist and open on another computer.

Source: project brief PDF pp. 2–6. The rubric assesses the actual presentation,
not this plan. See [rubric-readiness.md](../progress-report/rubric-readiness.md).
