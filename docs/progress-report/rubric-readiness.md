# Excellent-band readiness audit

Reviewed 23 October 2026 against `INF2003_project_description (2).pdf`, PDF
pages 1–6, supplied earlier by the user. This is a criterion/evidence audit,
not a predicted mark or a claim that the group has already earned ≥80.
The brief and proposal are assessment/reference material, not instructions to
automatically implement every suggested technique or rewrite approved designs.

## 1. What the actual rubric rewards

The rubric calls its highest band **Excellent (≥80)**. Its categories are:

| Category | Weight | Excellent-band target, paraphrased | Current assessment |
| --- | ---: | --- | --- |
| Proposal | 10% | Clear, comprehensive application description, coverage and execution planning | A proposal copy exists outside the repository. Its submitted version and awarded mark are not verified. The supplied copy still has planning/current-deliverable placeholders. Do not rewrite submission history. |
| Presentation: slides and video | 25% | Clear, logical structure; thorough explanations; methods, analysis, results, conclusions and implications | Demo guidance and a timed presentation plan are prepared. A completed slide deck, five-person recording and timed rehearsal were not found. Not yet verified ready. |
| Final report | 25% | Clear, comprehensive design, implementation details and project analysis | Technical design/evidence is available. A report outline is prepared; a finished report in the XSite template, within the page limit, was not found. Not yet verified ready. |
| Project quality and implementation | 40% | Interesting/useful accurate features, appropriate sufficient sources, substantial work in both databases, suitable tools/algorithms, complete modules and excellent code | Strong implementation evidence exists. Fresh offline tests and live read-only checks passed. A new clean-machine installation and full current write-flow/browser rehearsal remain to be recorded. |

The brief assigns 25 percentage points of the overall module grade to relational
and 25 to non-relational work. Give both databases substantial explanation and
demo time. The project rubric is not a demand for a particular number of SQL
features or a guarantee that more syntax produces a higher mark.

## 2. Verified implementation and data evidence

Fresh aggregate metadata is retained in [rubric-data-snapshot.json](rubric-data-snapshot.json).
It contains counts/metadata, not passwords, connection strings or trainer names.

- MySQL Community Server 8.4.13; 15 application/source tables and three views.
- 151 playable species, 18 types, 353 moves, 218 species/type links, 8,103
  eligible-move links and 324 effectiveness pairs.
- Historical source: 800 source identities and 50,000 ordered result rows.
  Reviewed mappings, provenance and duplicate policies are documented separately.
- At inspection: one trainer, five saved teams, 38 owned copies and 37 SQL awards.
- MongoDB: 70 completed battles (37 wins, 33 losses), with saved predictions.
  There are 64 completed non-forfeit battles across difficulties/team sizes;
  40 began with exactly one member on both sides. This is cohort availability,
  not 40 observations of every species pair or every screen's exact filter.
- The live battle validator and the trainer/history and partial active-battle
  indexes are present. The `_id` index is implicitly unique.
- Raw-cache audit validated 912 source files with zero issues; 10 labelled
  project move-pool associations are distinguished from raw eligibility.
- 922 tracked data files were found; no tracked `.env`, `.local` or virtualenv
  artifacts were found by the path check. This is not a full Git-history secret audit.

Do not artificially inflate evidence: source CSV outcomes are external synthetic
1v1 results, while MongoDB contains this simulator's saved battles. Keep them
separate. A populated cohort does not establish a reliable win probability.

Fresh automated checks in this audit: Python discovery ran 131 tests: 95 passed
and 36 opt-in database tests skipped, including four new comparison-helper tests
among the passes. All seven Node tests passed. Historical
integration/browser reports remain historical evidence and are not relabelled
as a fresh full end-to-end test.

## 3. Criterion-to-evidence checklist

| Need | Concrete evidence to show | Status / action |
| --- | --- | --- |
| Useful database application | Pokédex → collection/team CRUD → SQL analysis/recommendations → battle → MongoDB analytics | Implemented. Explain the user question each query answers; spend less time on decorative battle animation. |
| Multiple appropriate sources | PokéAPI, reviewed Kaggle source, generated trainer/team/battle data | Implemented and audited. State source scope, cleaning, mapping, provenance and limitations; don't call all battles real competitive observations. |
| Relational design and relationships | [ER diagram](../diagrams/relational-er.md), [DDL](../../database/relational/schema.sql), [historical DDL](../../database/relational/historical.sql) | Show keys, participation/cardinality, bridge tables, owned instances and constraints. Export a readable diagram into the final report/slides. |
| Supporting design theory | [Feature guide](../database-design/project-explanation-guide.md), [optional normalisation reference](../database-design/normalisation-reference.md), [lecture map](../database-design/lecture-to-project-map.md) | Lead with useful relationships, constraints and query behaviour. FDs, closure and BCNF examples support a relevant design discussion. Acknowledge the membership ownership redundancy when making normal-form claims. The actual brief does not explicitly mandate that every table be in 3NF/BCNF. |
| Basic SQL functionality | `save_team()`, `get_team()`, `delete_team()`, starter/collection paths | Implemented. Demo create/read/update/delete on a labelled demonstration team, with safe boundary/error cases. |
| Advanced SQL with a purpose | Views, aggregates, selected-move coverage, recommendation CTEs, NOT EXISTS, ROW_NUMBER, parameterised queries | Implemented. Show one query's input, intermediate meaning and returned result. Do not add triggers merely to tick a box. |
| Significant NoSQL model and queries | Embedded snapshots/current state/events; validator/indexes; `$facet`, `$unwind`, `$group`; rule-aware 1v1/strategy evidence | Implemented. Show the document plus a real aggregation and explain its denominator/filter. SQL CRUD does not by itself demonstrate NoSQL depth. |
| Concurrency and correctness | SQL row locks and transactions, MongoDB revision replacement, unique reward identity and delivery repair | Implemented with tests. Explain the atomicity boundary; this app has no cross-database FK or distributed atomic commit. |
| Rigorous SQL/NoSQL comparison | [Comparison results](database-comparison-results.json), method below and report outline | New equivalent-fact retrieval check completed; explain modelling/integrity/atomicity trade-offs as well as latency. Different hosting paths prevent engine-superiority conclusions. |
| Working reproducible application | [User manual](../submission/user-manual.md), cached source files and scripts | Manual prepared. A teammate/reviewer must still follow it from a fresh directory without private `.local` helpers. Record the result and software versions. |
| Excellent explanation and analysis | [Report outline](../submission/final-report-outline.md), [presentation plan](../submission/presentation-plan.md) | Prepared supporting material, not a completed assessed PDF/PPTX/video. Use the official report template and show actual results/limitations. |

## 4. Reproducible SQL/NoSQL comparison

New read-only helper:

```text
python -m scripts.benchmark_databases --samples 7
```

It fixes a cohort of existing delivered rewards and retrieves the same facts:
battle UUID, trainer ID, owned-copy ID, species ID and shiny flag. SQL joins
`battle_rewards` to `owned_pokemon`; MongoDB projects the embedded delivered
award. The helper checks equivalent canonical rows on warm-up and every sample,
alternates store order, requests no result ordering in either store, consumes
the full result and saves aggregates/timings.
It rejects disagreement or an empty cohort instead of fabricating evidence.
Connections and one warm-up per store are outside timing. It creates no data,
schema or indexes. The artifact contains no actual award IDs or credentials.

This audit matched **all 37 candidate SQL awards** to delivered MongoDB awards;
none were excluded. Median retrieval across seven samples was **0.1884 seconds
for MySQL** and **0.0351 seconds for MongoDB**. See the JSON for raw samples and
exact precision. These are measurements of these deployments and query shapes,
not proof that MongoDB is intrinsically faster: SQL travels to the Oregon VM,
the stores use different access/model paths, the cohort is small, and this is
sequential warm retrieval rather than throughput/scaling or browser latency.

Interpretation: a normalized relational join and an embedded document projection
can return equivalent selected facts while serving different integrity/history
purposes. Explain the trade-off, not just the smaller timing. Existing app
[performance measurements](google-cloud-mysql-verification.md) separately show
the benefit of fewer network trips and catalogue caching.

## 5. Reconcile the old proposal with the actual app

The provided proposal is a plan, not the current implementation specification:

| Original proposal copy | Actual approved behaviour to describe |
| --- | --- |
| Up to two damaging moves per owned Pokémon | Four distinct eligible moves selected per **saved team member**; an owned copy may have different saved selections in different teams |
| One legendary copy per trainer | Collection may hold legendary copies; each team permits at most one of each legendary species across normal/shiny variants |
| Kaggle history supports the prediction | External source remains separately imported/queryable; the visible 1v1 evidence and prediction context use own MongoDB battles; Python computes a starting heuristic |
| Filter Pokémon by stats | Current browse filters name/ID and type; stats are displayed/analysed, not an implemented stat-range search filter |
| Progression application | EXP, levels and evolution remain proposed, not implemented |

State these as scope evolution and justify current choices. Do not claim all
original ideas are implemented or add expensive unrelated features to preserve
every early promise. The completed application can be assessed on the actual
useful database functionality, with its limitations clearly reported.

## 6. Remaining gates before claiming submission readiness

1. **Final report:** transfer the evidence into the official XSite template,
   export PDF and check the 10-page main-content limit and Calibri Body 12.
   Cover/references/appendix are excluded by the brief. Make diagrams readable.
2. **Presentation:** create the actual slides and record all five members with
   visible names, in background → relational → NoSQL → optional performance
   order. Rehearse to a total no longer than 10 minutes at normal speed.
3. **Clean setup:** another member follows the manual with their own isolated
   databases; record setup, health, all screens and one complete award cycle.
   Fresh MongoDB has no player history until battles are generated/imported.
4. **Current write flows:** on that isolated setup, verify create/edit/delete,
   invalid ownership/moves/budget, active-battle conflicts, reload/resume,
   auto/manual turns and reward retry. Do not run destructive grading fixtures
   against the shared project database just to obtain a test count.
5. **Demo samples:** choose actual populated matchups/filters from the demo
   database before recording. Keep low-sample warnings and record provenance;
   do not present empty panels or seeded examples as real gameplay evidence.
6. **Package:** include source, data, manual and dependency files. Exclude
   `.env`, `.local`, credentials, SSH keys, backups with secrets, virtualenvs,
   system libraries and private lecture PDFs. Check archive contents by listing
   file names; do not publish credentials or record them in the video.
7. **Group review:** confirm the actual proposal submitted, the official report
   template, each member's contribution and any newer XSite instructions. Peer
   review affects the final assessment; contribution claims must be truthful.

The provided brief lists final submission as **29 November 2026, 11:30 PM**
(PDF p. 2); confirm the current XSite deadline. It requires report, slides,
video and zipped source/data/manual. These are real outstanding deliverables,
not automatically satisfied by this audit. A marker must judge the final work.
