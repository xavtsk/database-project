# Final report working outline

This is an evidence-based writing scaffold, not a finished assessed report.
Transfer it into the official XSite template and replace the prompts with the
group's own explanation, selected figures and conclusions. Verify the final
PDF is within the brief's 10 main-content pages, Calibri Body 12; cover,
references and appendix are excluded. The suggested allocations below total
nine pages, leaving a page for layout variation. Do not use the appendix to
hide essential design/implementation explanations.

## 1. Problem, application and datasets — about 1 page

Explain the user questions: which Pokémon fit a collection/team, what weaknesses
the roster has, how to choose improvements within budget, and what the user's
saved battles show about outcomes and move use.

Describe the original-151 scope and simplified mechanics. Identify PokéAPI as
reference data, the reviewed Kaggle source as external synthetic 1v1 results,
and simulator battle logs as generated application data. Include attribution,
retrieval/scope information, missing-name/form mapping, duplicate handling and
the ten labelled move-pool overrides. Do not imply external synthetic outcomes
are official competitive results or that all source Pokémon are playable.

Evidence: [data/query guide](../database-design/database-evidence.md),
[historical design](../database-design/historical-import-proposal.md),
[fresh counts](../progress-report/rubric-data-snapshot.json).

## 2. Architecture and data flow — about 0.75 page

Include the current parts of the [architecture](../diagrams/application-architecture.md),
omitting or clearly labelling the planned progression extension. Explain the
browser/Flask/DBMS boundary, SQL catalogue/ownership and MongoDB snapshots/events.
Explain how a battle reads a SQL roster and produces a MongoDB document.
Clearly distinguish current local profiles from secure public authentication.

## 3. Relational design and implementation — about 2.25 pages

- Insert a readable [ER diagram](../diagrams/relational-er.md) and explain
  cardinality/participation, species versus owned copies and selected moves.
- List the important candidate/composite keys, domain constraints, foreign
  keys and cascading behaviour; distinguish SQL rules from Python validation.
- Explain the design through its purpose: shared catalogue facts, separate
  owned-copy identities, team membership and reliable ownership checks. Use
  the [feature guide](../database-design/project-explanation-guide.md) for the
  main narrative. If including normal forms, use the optional
  [normalisation reference](../database-design/normalisation-reference.md)
  and acknowledge the membership ownership redundancy. Detailed proofs can
  support an appendix; they should not displace the query methods and results.
- Demonstrate team CRUD and an invalid save. Show that grouped writes commit
  together and selected moves are inserted after their member rows.
- Explain one actual analysis SQL query and one recommendation pipeline:
  inputs → candidate filtering → scoring → ranking → returned result.
- Identify ordinary views, CTEs, NOT EXISTS, aggregates and window ranking by
  their useful purpose. Keep full SQL listings in the source/appendix.

## 4. NoSQL design and implementation — about 2 pages

Include the [MongoDB model](../diagrams/mongodb-model.md) and one real document
from an isolated demonstration database. Explain initial snapshots, current
state, events, prediction/rule versions and reward state. Discuss embedding
versus references and why saved historical facts must not depend on today's
editable SQL team.

Show the validator and two application-specific indexes. Walk through an
actual aggregation: initial rule/difficulty/status filter, event unwinding or
1v1 qualification, grouping, counts and denominator. Explain observed miss/win
rates with sample size and exclusions. Describe revision-based conditional
replacement during a turn. This section must demonstrate substantial MongoDB
work, not just state that JSON is flexible.

## 5. Cross-database correctness and comparison — about 0.75 page

Explain the reward's SQL transaction followed by MongoDB delivery-marker
update. Describe the failure window and unique award identity used for repair.
There is no foreign key or atomic transaction spanning both stores.

Use these comparison dimensions, with actual code/examples:

| Dimension | MySQL in this project | MongoDB in this project |
| --- | --- | --- |
| Data shape | Related species, moves, ownership and membership rows | Battle-local arrays/objects and versioned snapshots |
| Duplication | Catalogue facts maintained separately; membership ownership ID repeated for composite-FK enforcement | Names/stats/team facts embedded for historical stability |
| Integrity | Keys/FKs/CHECKs plus transactional application validation | Validator, indexes, conditional writes and application validation; no cross-store FK |
| Query work | Joins, grouping, views, candidate/ranking CTEs | Document lookup and nested-event aggregation/facets |
| Atomicity/concurrency | Multi-row transaction, trainer row lock | Conditional single-document replacement and active-battle uniqueness |
| Cost/limits | Small Oregon VM; network trips and fixed connection allowance | Atlas deployment; document size/array growth and quota constraints |

Neither store is universally better. Explain why this workload split is
appropriate and where the trade-offs or alternatives lie.

## 6. Evaluation and results — about 1.5 pages

Separate four kinds of evidence:

1. Automated correctness tests, including tests skipped in the fresh run and
   the distinction between offline fixtures and live integration checks.
2. A clean-machine installation plus current end-to-end demo/write-flow record.
   This is still outstanding; add the actual results when performed.
3. [Before/after request measurements](../progress-report/google-cloud-mysql-verification.md)
   from fewer network trips/caching. State warm-up, deployment and timing scope.
4. [Equivalent-award comparison](../progress-report/database-comparison-results.json):
   same 37 matched records, one excluded warm-up, seven alternating samples,
   persistent connections, verified canonical results and raw sample timings.

For the new comparison, medians were approximately 0.188 s SQL and 0.035 s
MongoDB. Interpret this as deployment/query-shape latency; it does not isolate
engine speed because hosting/network paths and models differ. Do not turn
these sequential warm reads into a throughput or scalability claim.

For analytics, state what the current data can support: 70 completed battles,
64 non-forfeit completions and 40 initial 1v1 observations across pairs at the
snapshot time. Counts will change. Show a real populated pair/filter and its
sample size; do not aggregate unrelated rules into an unexplained prediction.

## 7. Reflection, limitations and conclusion — about 0.75 page

Discuss simplified mechanics, non-calibrated prediction, source differences,
small/uneven cohorts, local profile security, cross-store repair, ownership
redundancy, US-region latency and the unverified fresh-install gate. Explain
which improvements are worthwhile and which would add unjustified complexity.
Conclude with what the implemented database work achieved for the user.

## Final editorial checks

Use the latest approved behaviour: four moves per saved member, legendary
duplicates restricted per team, and current own-battle MongoDB evidence. Mark
stat-range search, progression and other unimplemented proposal ideas as scope
changes/future work. Keep methods, results and conclusions distinct. Add actual
member contributions, sources and any course-required acknowledgements; do not
invent authorship, measurements or a completed clean-install result.

Source of assessment constraints: `INF2003_project_description (2).pdf`,
pp. 2–6. See the [rubric audit](../progress-report/rubric-readiness.md).
