# INF2003 lecture notes mapped to the implemented project

Read this alongside the [project explanation guide](project-explanation-guide.md).
This mapping uses the seven PDFs supplied on 23 October 2026 and the current
repository. It is an explanation of existing work, not authority to implement
every lab exercise, example, future topic or project idea mentioned in slides.

All page references below are **PDF page numbers starting at 1**, including
title pages. Some slides omit or use different printed numbers. The original
PDFs and extracted lecture text are not included in the tracked repository.

## 1. Which file covers which topic?

| Reference | Supplied filename | Pages | Main content |
| --- | --- | ---: | --- |
| L1 | `INF2003 Lec01.pdf` | 35 | DBMS purpose, abstraction/independence, relational model, keys, project overview |
| L2 | `INF2003 Lec02.pdf` | 46 | ER modelling, cardinality/participation, integrity constraints, SQL types and DDL |
| L3 | `INF2003 Lec03.pdf` | 43 | CRUD, subqueries, aggregates, grouping, JOINs, constraints and views |
| L4 | `INF2003 Lec04.pdf` | 41 | Anomalies, FDs, closure, normal forms, BCNF and decomposition |
| L5 | `INF2003  Lec05.pdf` | 36 | Relational algebra, query optimisation and execution plans |
| L6 | `INF2003 AY2627 T1 Lec 06 261016.pdf` | 16 | Files/pages, hash/tree indexes and B+ tree operations |
| L7 | `INF2003 AY2627 T1 Lec 07 261021.pdf` | 14 | Transactions, schedules, ACID, commit/rollback, recovery and concurrency control |

There are 231 PDF pages in total. L6 page 3 and L7 page 2 list NoSQL as a
later topic; they do not teach MongoDB queries. Explain MongoDB from the
implemented document model and pipelines, and add course-specific NoSQL
references when those slides become available. Do not label all seven PDFs as
NoSQL or machine-learning material.

## 2. Lecture concepts you can demonstrate

| Notes and pages | Topic | Current project evidence | Simple explanation and limits |
| --- | --- | --- | --- |
| L1 pp. 7–11 | Why a DBMS; abstraction | [Schema](../../database/relational/schema.sql), [API](../../backend/app.py), [architecture](../diagrams/application-architecture.md) | The browser requests features, Python submits database operations, and the DBMS manages storage and constraints. Logical layers need not be three separate computers. |
| L1 pp. 18–23; L2 pp. 23–25 | Relations, domains, keys and FKs | `pokemon`, `types`, `owned_pokemon`, `team_members` in the schema | Identify a row with a key; limit legal values; reference existing related rows. Trainer names are not declared unique and are not candidate keys. |
| L2 pp. 9–13 | Entities, attributes, relationships, cardinality and participation | [ER diagram](../diagrams/relational-er.md) | A trainer may own zero or many copies; each owned copy must reference one trainer and species. Pokémon and moves are many-to-many through `pokemon_moves`. |
| L2 pp. 10, 16 | Derived attributes and dependent children | [Views](../../database/relational/views.sql), `team_member_moves` | Pokémon cost is derived from stats. A selected-move row is identified relative to its parent member and move slot; deleting its parent cascades to it. This does not mean every cascading relation is automatically a weak entity. |
| L2 pp. 22–26, 42–44; L3 pp. 26–28, 32–33 | Integrity constraints and DDL | PK, FK, UNIQUE, NOT NULL, CHECK and DEFAULT clauses in [schema.sql](../../database/relational/schema.sql) | The database rejects invalid references and duplicate keys. A nullable UNIQUE declaration is not automatically a candidate key; `historical_pokemon.pokemon_id` may be NULL. |
| L3 pp. 3–11 | CRUD, parameters and ordering | `create_profile()`, `save_team()`, `get_team()`, `delete_team()` in [teams/service.py](../../backend/teams/service.py) | Save and edit teams, read them back, then delete them. `%s` parameters keep input separate from SQL text. Ordering is explicit; SQL does not promise insertion order. |
| L3 pp. 19, 29 | IN subqueries and NOT EXISTS | `browse()` in [pokedex/service.py](../../backend/pokedex/service.py); `candidates` in [recommendation SQL](../../database/relational/queries/team_recommendations.sql) | Filter Pokémon by type membership; exclude owned instances already in the selected team. |
| L3 pp. 20–25 | Aggregates, GROUP BY and HAVING | `analyse()` in [analysis service](../../backend/team_analysis/service.py); `affordable` in recommendation SQL | Compute totals/averages and type counts in SQL. The recommendation query's HAVING checks grouped legendary-species duplication. SUM/AVG over no rows may return NULL, so formatting/defaults matter. |
| L3 p. 34; L5 pp. 19–20 | JOINs and outer joins | `get_team()` and `list_teams()` in the team service | Join team IDs to members, owned species and moves. LEFT JOIN keeps an empty saved team visible. These are explicit ON joins, not SQL NATURAL JOIN statements. |
| L3 pp. 36–40 | Views and materialised views | `v_pokemon_cost`, `v_pokemon_defense`, `v_ranked_default_moves` in [views.sql](../../database/relational/views.sql) | Reuse derived SQL definitions. These are ordinary views; the Python/browser catalogue caches are not materialised SQL views. |
| L4 pp. 6–11 | Anomalies and functional dependencies | Species/move/type separation in the schema | Change a move's power in one reference row instead of updating every Pokémon that can use it. A business FD must hold for all legal instances, not just today's small sample. |
| L4 pp. 12–23 | Armstrong's rules, closure, 1NF/2NF/3NF/BCNF | [Optional normalisation reference](normalisation-reference.md#bcnf-and-closure-the-lectures-main-refinement-test) | Derive candidate keys from stated FDs and check determinants. `team_members` contains a concrete violation; do not claim the whole schema is BCNF. |
| L4 pp. 26–36 | Decomposition, losslessness, dependency preservation and trade-offs | [Worked membership example](normalisation-reference.md#lossless-decomposition-and-dependency-preservation) | Separating tables must preserve the original information. Losslessness does not guarantee every original dependency remains locally enforceable. The example is explanatory, not an implemented migration. |
| L5 pp. 6–20 | Relational algebra | SQL selections, projected columns, joins and recommendation candidate exclusion | Explain a query as filtering rows, selecting columns and joining relations. The app executes SQL; it does not implement its own relational-algebra engine. |
| L5 pp. 24–35 | Query optimisation and EXPLAIN | [EXPLAIN helper](../../scripts/explain_recommendations.py), joined team reads, explicit field lists | Inspect an execution plan before adding indexes. Connection reuse and batching also reduce network trips, but are separate from proving a better SQL execution plan. |
| L6 pp. 4–10 | Files/pages; hash versus tree indexes | Declared SQL keys; two MongoDB indexes in [setup](../../scripts/setup_databases.py) | Indexes support data access and uniqueness. The DBMS manages physical structures; this project does not implement B+ tree insertion/deletion code. Verify actual use with a plan, not merely the existence of a key. |
| L7 pp. 3–10 | Transactions, schedules and ACID | `transaction()` in [db.py](../../backend/db.py); team saves and SQL awards | Group related writes into one commit, or roll them all back. The app does not explicitly set SERIALIZABLE isolation, so do not claim every request uses that isolation level. |
| L7 p. 12 | Locking | `SELECT ... FOR UPDATE` in starter, save and reward paths | Competing application updates for the same trainer lock that trainer row. This is not an application-wide lock on all trainers or all reads. |
| L7 p. 13 | Optimistic concurrency | Revision/status filter in `act()` in [battle service](../../backend/battles/service.py) | Read a battle, calculate the next state, then replace it only if the saved revision still matches. This is a version check, not a claim to implement a complete general-purpose three-phase OCC algorithm. |
| L7 pp. 9–11 | Durability and recovery | InnoDB commits, backups and `deliver_reward()` | Distinguish engine crash recovery, backup/restore and application retry recovery. The project has migration backups and reward recovery, not proof of a tested high-availability or disaster-recovery service. |

CTEs, `ROW_NUMBER()` and MySQL JSON aggregates in recommendations go beyond the
basic SQL explicitly developed in these slides. MongoDB validators, embedded
snapshots, aggregation pipelines and partial unique indexes are also project
extensions. They are useful evidence, but cite their actual code rather than
inventing lecture-page coverage.

## 3. How to explain each main function during a demo

### A. Browsing the Pokédex

1. Input: a search string and optional type from the screen.
2. `browse()` filters names/IDs and uses an IN subquery to test type membership.
3. SQL returns matching IDs; the application attaches cached SQL catalogue data.
4. The screen shows each matching species once, with its types and stats.

Say: “Type membership is stored in a junction table. We use a subquery and JOIN
to filter it, rather than search a comma-separated type string.”

Use L2 pp. 11–13 and L3 pp. 19, 34. Cache behaviour is a separate application
optimisation; revisiting a cached reference page may not execute another query.

### B. Collection and saved teams

1. `collection()` returns this trainer's owned instance IDs, species IDs and
   shiny flags, ordered by species, variant and owned ID.
2. `get_team()` performs one ownership-filtered LEFT JOIN to read the team,
   members and selected moves. Python groups joined rows into the response.
3. `save_team()` validates distinct owned instances, eligible selected moves,
   legendary rules and budget. It locks the trainer and writes the team,
   member rows and move rows within one SQL transaction.
4. `delete_team()` removes the owned team; member/move rows cascade, while
   species data, the collection and MongoDB battle snapshots remain available.

Say: “The species and the owned copy have different IDs. We store the roster as
relationships, and commit a complete team edit as one transaction.”

Use L1 pp. 21–23; L2 pp. 12–13, 22–26; L3 pp. 3–5, 34; L7 pp. 7–10, 12.
Use the guide's correctness table to distinguish SQL constraints from Python
validation. Explain how composite foreign keys enforce matching ownership.
If discussing normal forms, use the optional reference to explain the repeated
trainer ID accurately; the formal proof need not interrupt the feature demo.

### C. Team statistics and weaknesses

1. `analyse()` verifies the saved team belongs to the selected trainer.
2. SQL COUNT/SUM/AVG calculates size, stat totals and averages.
3. SQL GROUP BY counts type distribution. The defense view combines both
   defensive types; the matchup query counts weaknesses/resistances/immunities.
4. Coverage SQL follows saved selected moves to their types and finds MAX
   effectiveness against each defending type.

Say: “The database computes the summaries. Python formats them for the screen.
For a dual-type member, we combine both type multipliers rather than counting
each defensive slot as a separate Pokémon.”

Use L3 pp. 20–25, 34, 36. Show
[team_matchups.sql](../../database/relational/queries/team_matchups.sql) and
[team_coverage.sql](../../database/relational/queries/team_coverage.sql).

### D. Partner recommendations

1. `recommend()` validates ownership before running the recommendation SQL.
2. CTEs obtain the saved roster and unused owned candidates using NOT EXISTS.
3. SQL proposes additions/replacements, rejects plans above budget or with
   duplicate legendary species, and scores defensive exposure and coverage.
4. Window ranking chooses a best plan per species, then the best three species.
5. MongoDB supplies separate past species-appearance evidence. Nothing edits
   the saved team automatically.

Say: “This is an explainable SQL ranking over our collection. We can show the
candidate filters, scoring expressions and final ranking instead of calling
the recommendation a black-box AI prediction.”

Use L3 pp. 19–24, 29, 34, 36, then identify window functions/CTEs as extensions.
The [query evidence guide](database-evidence.md) walks through each CTE.

### E. Starting a battle and making a prediction

1. `start_battle()` reads the SQL team and validates battle entry.
2. Python constructs the opponent and computes `predict()` from actual starting
   members, moves, accuracy, type effectiveness and saved damage rules.
3. MongoDB supplies prior comparable battle counts, stored as separate context.
4. The battle document saves initial snapshots, prediction, rule version,
   difficulty, current state and an initially empty turn list.

Say: “The starting prediction is a deterministic scoring heuristic in Python,
and the battle evidence is aggregated from MongoDB. We store both so we can
later compare the starting assessment with the actual outcome.”

Use L1 p. 33 for the combined application/database project context. Detailed
MongoDB modelling is an extension beyond these PDFs. Neither this function nor
the supplied notes establishes a trained ML model or calibrated win probability.

### F. Resolving manual and automatic turns

1. `act()` reads the trainer's battle and checks status/revision.
2. Python resolves the chosen action; Auto Battle first chooses an action using
   the server policy. Moves/damage/animation messages are game logic, not SQL.
3. A conditional MongoDB replacement requires the expected revision and active
   status. A mismatching revision reports a conflict instead of overwriting.
4. The saved turn records actual actions/events and, for automatic choices,
   controller/policy/decision details for analytics.

Say: “Two requests based on the same battle revision cannot both replace that
document. We preserve turn events so the analytics can inspect what happened.”

Use L7 pp. 3–6, 13 for the concurrency motivation. MongoDB's document-level
write is the concrete mechanism; this is not a transaction spanning MySQL and
MongoDB and not a proof of global serializability.

### G. Awarding a Pokémon after a win

1. The battle stores the server-selected rarity/shiny result.
2. `deliver_reward()` locks the SQL trainer and looks up `battle_rewards` by
   battle UUID. If an award already exists, it reuses that record.
3. Otherwise, the reward-pool query checks eligible variants, and SQL inserts
   the owned instance plus award record in the same transaction.
4. After SQL commits, MongoDB receives the delivered marker. If that fails, a
   later read can repair the marker using the existing award.

Say: “The award is idempotent: retrying delivery does not grant another copy.
The SQL insert is atomic, but the two databases do not share an atomic commit;
we explicitly handle the gap between them.”

Use L2 pp. 24–26 and L7 pp. 7–13. The opening animation reveals the saved
reward and is not a new database roll. The copy cap is checked under the trainer
lock; it is not a CHECK constraint that counts other collection rows.

### H. Battle analytics and observed matchups

1. `history()` filters by trainer, projects selected fields and returns the
   latest 50 battles in descending start-time order.
2. `analytics()` aggregates outcomes, species usage, moves and duration.
3. Strategy `report()` filters rules/difficulty and uses saved events to count
   attempts, hits, damage and repeated-move patterns.
4. Matchup `report()` requires one initial member on both sides, accepts both
   species orientations and reverses win/loss interpretation when necessary.

Say: “These are database aggregations over our saved battles. We report the
sample size and filters because an observed win rate is not automatically a
prediction or proof that one move choice caused a win.”

Use L3 pp. 20–25 as the familiar grouping/aggregation idea, while labelling
`$match`, `$unwind`, `$group` and `$facet` as MongoDB syntax, not SQL syntax
taught on those pages. The visible 1v1 panel uses MongoDB simulator evidence;
the historical CSV results in SQL remain a separate source.

## 4. A short worked relational-algebra explanation

L5 pp. 8, 10, 19–20 gives selection, projection and join/outer join. A small
query over current tables can be described as:

```text
π_id,name (σ_trainer_id=t (teams))
```

This means filter `teams` to trainer t, then keep the ID and name. SQL's output
column list is projection; WHERE corresponds to row selection. A joined team
read adds relationships to members/owned instances/moves; LEFT JOIN preserves
an empty team. In classical relational algebra projection has set semantics;
ordinary SQL SELECT does not automatically eliminate duplicate output rows.
The expression above is a teaching example, not a claim that `list_teams()`
only returns those columns or that the app runs this notation directly.

## 5. Indexing and performance: evidence you can actually show

L5 pp. 24–35 and L6 pp. 4–10 explain why data access paths matter. The SQL DDL
declares primary/unique keys and foreign-key relationships; inspect live index
metadata and the chosen plan before claiming a particular index was used.
Setup explicitly creates these MongoDB indexes:

- `(trainer_id ASC, started_at DESC)` for trainer history queries and ordering.
- Unique `trainer_id` restricted to `status='active'` to limit active battles.

For the existing recommendation query, the read-only helper is:

```text
python -m scripts.explain_recommendations --trainer-id 1 --team-id 1
```

Replace the example IDs with a real team belonging to that trainer. The helper
loads the configured environment and saves EXPLAIN FORMAT=JSON under `.local/`.
It gives the optimiser's plan/estimates, not measured execution time. L5 p. 34
distinguishes EXPLAIN from execution-based analysis; its MariaDB examples should
not be copied unmodified into this MySQL project.

Important limitation from L5 pp. 26, 33: current Pokédex substring search uses
`LIKE '%term%'`, and its ID text comparison uses CAST. Do not claim that an
ordinary name/ID index makes that whole OR predicate a direct indexed lookup.
Changing to prefix-only search would change behaviour and needs consideration;
with 151 playable species, network round trips can matter more than scanning
this small catalogue. The retained
[performance evidence](../progress-report/google-cloud-mysql-verification.md)
measures request latency, not isolated SQL disk I/O or B+ tree complexity.

## 6. ACID explanation using a team save

| Property | Course reference | Your example | Boundary |
| --- | --- | --- | --- |
| Atomicity | L7 p. 7 | Team/member/move writes commit together or roll back | Schema DDL/import setup has different commit behaviour from ordinary team edits |
| Consistency | L7 p. 8 | FKs/keys/domain checks plus ownership, moves and budget validation preserve intended rules | The programmer must implement game rules correctly; a transaction alone cannot fix wrong logic |
| Isolation | L7 pp. 8, 12 | Application writes for a trainer use SELECT FOR UPDATE and hold the lock until transaction end | No explicit SERIALIZABLE setting or proof that all unrelated operations are serialised |
| Durability | L7 pp. 9–11 | The app uses InnoDB commit to make successful SQL writes persistent | Exact crash guarantees depend on server/storage settings; backups are still necessary, and no new crash test was performed for this guide |

COMMIT and ROLLBACK are implemented in the transaction helper. SAVEPOINT is
taught in L7 p. 10 but is not used by the current application. MySQL row locks
and MongoDB revision checks are separate concurrency mechanisms. Reward
recovery provides eventual repair across the stores, not distributed ACID.

## 7. What to present, and what still needs a decision

Use this order: user problem and data sources → DBMS split → entities and
relationships → team CRUD and transactions → useful SQL analysis and rankings
→ MongoDB battle documents and aggregations → cross-store recovery → measured
results and limitations. For each feature, connect a user question to its data,
query, output and practical meaning. Normalisation is supporting design
material when relevant, rather than the organising theme of the presentation.

The supplied project brief's rubric has now been checked: it does not explicitly
require every operational SQL relation to be in 3NF or BCNF. The membership
ownership redundancy remains a real exception; explain its enforcement purpose
rather than presenting it as full normalisation. Removing the column would need
alternative ownership enforcement and design approval. A formal whole-schema
audit would also need an agreed complete dependency set, not just keys or a scan
of today's rows. See the [Excellent-band readiness audit](../progress-report/rubric-readiness.md)
for actual descriptors, verified evidence and remaining deliverables.

L1 p. 33 mentions CRUD, the NoSQL model, more complex database functionality,
performance analysis and reflection. That is useful context, but these lecture
slides are not a complete marking rubric and cannot guarantee a grade.
