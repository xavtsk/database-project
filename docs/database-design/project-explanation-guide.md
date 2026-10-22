# Explaining the current database project

Use this guide to explain what the application does, how its databases support
each feature, and why the design is useful. The examples describe the current
implementation. The [lecture map](lecture-to-project-map.md) supplies course
topics and PDF page references; the [query evidence guide](database-evidence.md)
contains more detailed SQL and MongoDB walkthroughs.

## 1. The project in plain English

> Our application helps a trainer explore Pokémon, build a team from their
> collection, identify its weaknesses, and review their battle results. MySQL
> manages the catalogue, ownership and team relationships. MongoDB records
> battles and lets us analyse their outcomes and individual events. Together,
> they support a cycle of building, testing and improving a team.

The application flow is:

```text
Browse Pokémon → Choose owned copies → Save a team → Analyse and improve it
                                                        ↓
Review battle analytics ← Store results and events ← Simulate a battle
```

The browser sends requests to the Flask backend. The backend validates the
request, reads or writes the appropriate database, and returns the result for
the screen. Battle calculations run in Python; SQL queries and MongoDB
aggregations perform the database analysis described below.

## 2. Why there are two databases

| Store | What it holds | Why it suits this part of the application |
| --- | --- | --- |
| MySQL | Species, types, moves, effectiveness, trainers, owned copies, teams, selected moves and reward records | These facts have shared identities and clear relationships. Keys, foreign keys, joins and transactions help keep them consistent. |
| MongoDB | Battle snapshots, current battle state, turns/events, starting predictions and reward-delivery state | A battle can be read as one document containing its nested events. Aggregations can summarise many documents or inspect individual attacks. |

For example, Pikachu's base stats belong to the shared species record in
MySQL. A completed battle keeps a snapshot of the actual participants in
MongoDB. Editing a saved team later therefore does not rewrite what fought
in an earlier battle.

This is a choice based on the application's access patterns. A relational
event-log design would also be possible, but would involve more related rows
to reconstruct the battle document. Embedding repeats some facts and makes
document size a design concern. SQL and MongoDB references do not create a
foreign key spanning both stores.

Evidence: [relational ER diagram](../diagrams/relational-er.md),
[MongoDB model](../diagrams/mongodb-model.md),
[core SQL schema](../../database/relational/schema.sql) and
[battle validator](../../database/nosql/battle_validator.json).

## 3. Understand species, owned copies and teams first

These are three different things:

| Concept | Example | Representation |
| --- | --- | --- |
| Species | Pikachu, with shared base stats and eligible moves | `pokemon`, linked to `types` and `moves` through association tables |
| Owned copy | One trainer's particular normal or shiny Pikachu | `owned_pokemon`, with its own ID, trainer ID and species ID |
| Saved team | A named selection of owned copies and their chosen moves | `teams`, `team_members` and `team_member_moves` |

The “Owned #” is the owned-copy ID, rather than the Pokédex species number.
Two owned Pikachu can share one species record while having different owned
IDs and shiny flags. Team membership points to the chosen owned copy.

> We separate what a Pokémon species is from who owns a particular copy.
> A team then links those owned copies to roster slots and selected moves.

This gives useful relationship examples: one trainer owns many copies and
teams; one species has many owned copies; species and eligible moves have a
many-to-many relationship. Each saved team contains at most six members,
with four selected moves per member when saved through the application.

## 4. Walk through the features

### Pokédex: finding the right information

**User action:** search a name or ID, filter by type, then inspect stats and moves.

**Database work:** `browse()` uses parameterised SQL to find matching species.
A nested query joins type associations to type names for the type filter.
The backend attaches catalogue details from its SQL-backed reference cache.
Search/filter results identify species; they do not create owned copies.

**Why it matters:** type and move associations can be queried individually,
and the shared catalogue avoids maintaining a separate set of base stats for
every trainer's collection. Parameterisation keeps entered values separate
from SQL instructions.

> The Pokédex is a searchable catalogue. MySQL stores the relationships between
> species, types and moves, so the screen can retrieve the relevant information
> without storing repeated lists in each trainer's collection.

Code: [Pokédex service](../../backend/pokedex/service.py) and
[catalogue loader](../../backend/catalog.py).

### Collection and teams: managing persistent user data

**User action:** view owned copies, create a team, change its members or moves,
save it, and later edit or delete it.

**Database work:** collection reads are filtered by trainer and ordered by
species, normal/shiny variant and owned ID. A joined team read retrieves the
team, owned members and selected moves. Team saving validates ownership,
eligible moves, duplicate rules and the 30-point budget, then writes the
team/member/move rows in one SQL transaction.

**Why it matters:** a failed save rolls back the grouped writes. The database
does not retain a team with only half of the requested changes. Deleting a
team cascades to its membership and selected-move rows; it keeps the owned
collection, species records and historical battle snapshots.

> Team management demonstrates CRUD: we create, read, update and delete saved
> teams. A transaction keeps the related team and move changes together, while
> foreign keys prevent invalid references and mismatched ownership.

Code: [team service](../../backend/teams/service.py).

### Team analysis: turning related rows into useful summaries

**User action:** choose a saved team and inspect its stats, type distribution,
weaknesses, resistances, immunities and offensive coverage.

**Database work:** MySQL uses `COUNT`, `SUM`, `AVG` and `GROUP BY` over joined
membership, ownership, species and type data. A defense view combines the
effectiveness of both defensive types. Coverage follows the team's actual
selected moves and finds their best multiplier against each defending type.

**Why it matters:** the database answers questions such as “How many members
are weak to Ground?” A member's two defensive types are combined before
classifying that weakness. Offensive coverage is a type-level summary;
having coverage does not establish that a team will win a complete battle.

> We use SQL aggregation to turn the roster into a summary the player can act
> on. For example, several members sharing a Ground weakness suggests that
> the next team change should address that exposure.

Code: [analysis service](../../backend/team_analysis/service.py),
[defensive matchup query](../../database/relational/queries/team_matchups.sql)
and [coverage query](../../database/relational/queries/team_coverage.sql).

### Recommendations: filtering and ranking practical improvements

**User action:** ask for suggestions for a saved team.

**Database work:** the recommendation SQL considers unused owned copies. It
evaluates additions when there is space, or replacements for a full team,
checks budget and legendary restrictions, and scores the resulting roster.
It favours reduced defensive exposure, then improved offensive coverage,
with cost and IDs used for deterministic tie-breaking. CTEs organise these
steps, `NOT EXISTS` excludes already-used copies, and `ROW_NUMBER()` helps
rank the best plans across distinct species. At most three are returned.

MongoDB supplies separate species-history context from qualifying completed
battles. That context does not change the SQL ranking score. Recommendations
use default eligible moves for the incoming candidate; the user must review
the suggestion and save any change themselves.

> The database does more than return a strong Pokémon. It checks which owned
> candidates fit this roster and budget, compares their effect on weaknesses
> and coverage, and returns ranked suggestions with reasons.

Code: [recommendation SQL](../../database/relational/queries/team_recommendations.sql)
and [result formatting](../../backend/team_analysis/recommendations.py).

### Battles and predictions: using the roster and recording what happens

**User action:** start a battle from a saved team, choose moves or enable auto
battle, and see the outcome.

**Database work:** the backend reads the SQL roster and creates a MongoDB
battle document containing starting snapshots, selected moves, rules,
difficulty and prediction. Each action calculates the next state in Python,
then conditionally replaces the document using its expected revision and
active status. A stale request cannot overwrite a newer turn.

The starting predictor compares each side's best accuracy-adjusted damage
relative to opposing HP across participant pairings. It returns a heuristic
label such as “favoured”, rather than a trained or calibrated win probability.
Separate MongoDB context summarises that trainer's previous non-forfeit
completions with the same rules, difficulty and starting team size. Those
previous battles may contain different species and opponents.

**Why it matters:** initial snapshots preserve the battle's inputs, while
events preserve what actually happened. Manual and automatic actions use
the same battle mechanics; the server's auto policy chooses actions.

> MySQL supplies the saved team, Python resolves the battle, and MongoDB keeps
> its state and event history. We save the starting prediction so we can later
> compare it with the observed outcome.

Code: [battle service](../../backend/battles/service.py),
[prediction](../../backend/battles/prediction.py),
[engine](../../backend/battles/engine.py) and
[auto policy](../../backend/battles/automation.py).

### Rewards: coordinating writes across the databases

**User action:** finish a win and reveal a normal or shiny reward.

**Database work:** the battle stores the selected reward in MongoDB. Delivery
locks the trainer's SQL row, checks collection availability, and inserts the
owned copy and its reward record together. The battle ID is the reward
record's primary key. MongoDB is then marked as delivered.

If the SQL commit succeeds but the MongoDB marker update fails, a later
read finds that existing SQL reward and repairs the marker. It does not grant
the reward twice. Collection availability counts normal and shiny variants
separately, allowing up to six of each for a non-legendary species.

> The two stores commit separately. We use a unique reward identity and a
> recovery check so repeating delivery is safe. The opening animation reveals
> the server's saved reward; the animation does not decide what is awarded.

Code: `deliver_reward()` in the
[battle service](../../backend/battles/service.py) and
[reward eligibility SQL](../../database/relational/queries/reward_pool.sql).

### History and analytics: learning from stored battles

**User action:** review past battles, move-use statistics or a species matchup.

**Database work:** history uses trainer filtering, field projection, sorting
and a result limit. Analytics uses MongoDB aggregation stages:

| Stage | Meaning in this project |
| --- | --- |
| `$match` | Select the relevant trainer, completion status, rules or difficulty |
| `$unwind` | Inspect individual turns/events within qualifying battles |
| `$group` | Count outcomes or attacks, and accumulate damage or duration |
| `$facet` | Produce several summaries from the qualifying input |

Move evidence counts actual attempts, hits and damage. The observed miss rate
can differ from the move's listed miss chance because the sample is finite.
Repetition statistics describe move use; they do not establish that repetition
caused a win or loss.

The visible 1v1 matchup feature uses the selected trainer's own MongoDB logs.
Both sides must have started with exactly one Pokémon. Active battles, team
battles and forfeits are excluded. Either species can have been on the player
side; wins and losses are interpreted from the selected species' perspective.
Its win rate is wins divided by all matching battles, including draws.

> MongoDB is used for analysis as well as storage. We filter relevant battles,
> inspect their events and calculate summaries. Every observed win or miss
> rate needs a sample count and clear filters to be interpreted fairly.

Code: [history and summaries](../../backend/analytics/service.py),
[move evidence](../../backend/analytics/strategy.py) and
[own-battle matchups](../../backend/analytics/matchups.py).

## 5. Explain where the data comes from

| Source | Role | Important preparation or limitation |
| --- | --- | --- |
| PokéAPI | Reference species, types, stats and eligible damaging moves | Cached source JSON is checked and transformed into related SQL tables. The playable scope is the original 151 species; project move-pool overrides are explicitly labelled. |
| Kaggle “Pokémon—Weedle's Cave” | Separate historical SQL dataset with source records, reviewed species mappings and ordered combat results | External IDs are mapped explicitly; unresolved forms/names are kept unresolved. Duplicate copies remain traceable but are excluded from evidence counts. Outcomes came from the source's custom algorithm. |
| Our simulator | MongoDB battle snapshots, turns and outcomes | Results depend on our simplified rules, participants, moves, decisions and difficulty. Small samples have limited predictive value. |

> We do not assume that two sources with Pokémon names describe identical
> data. We validate and map their identities, retain provenance, and keep
> external synthetic history separate from our own simulator observations.

The external import currently has 150 reviewed matches to playable species;
an unnamed source record remains unresolved. Its stats are preserved rather
than silently replacing the playable catalogue. The visible 1v1 screen uses
our MongoDB logs, not these imported Kaggle results.

Evidence: [import design](historical-import-proposal.md) and
[data/query guide](database-evidence.md).

## 6. Explain correctness through concrete examples

| Example | Database protection | Backend responsibility |
| --- | --- | --- |
| Save a roster | Slot CHECK 1–6 and primary key; unique owned copy per team | Validate the complete proposed team and 30-point budget |
| Choose members | Composite foreign keys require matching team/copy ownership | Check the selected trainer and reject invalid requests |
| Choose moves | Slot CHECK 1–4, keys and foreign keys | Require exactly four distinct moves eligible for that species |
| Restrict legendary duplicates | No species-level uniqueness rule in the team schema | Reject repeated legendary species, including across normal/shiny copies |
| Enforce collection caps | SQL availability query runs while holding the trainer row lock | Reroll an ineligible species; count normal/shiny caps separately |
| Avoid conflicting turns | Conditional MongoDB single-document replacement by revision/status | Report a stale action and use the current state |
| Avoid two active battles | MongoDB partial unique index per trainer | Return a readable error on another active start |
| Avoid duplicate rewards | SQL primary key on the battle's reward identity | Reuse the existing award and repair delivery state |

Three SQL views provide derived costs, combined defense and ranked default
moves. An ordinary view is a saved query, rather than a cached result or
trigger. The current DDL has no SQL triggers. MongoDB also has a document
validator and indexes, although its validator does not check every game rule.

For a transaction example, show a team edit: related writes commit together
or roll back. For concurrency, show a trainer row lock or a battle revision
check. Reward recovery illustrates the boundary between SQL and MongoDB;
there is no single atomic transaction across both stores.

Normalisation can support the design discussion when relevant. Shared species,
types and moves are separated into related tables. Membership deliberately
repeats the trainer ID for composite ownership foreign keys, so do not claim
every table is fully in 3NF/BCNF. The optional
[normalisation reference](normalisation-reference.md) preserves the detailed
examples and proofs; it need not lead the presentation.

## 7. Present evidence and explain its limits

For each feature, use the same sequence:

```text
User question → Data and query → Actual output → Interpretation → Limitation
```

For example, show an actual team's weaknesses, explain the SQL aggregate,
show a ranked recommendation, and describe why that suggestion helps. Explain
that type coverage alone does not guarantee victory. Use real
outputs or clearly labelled illustrative examples; do not invent results.

Performance work already includes SQL connection reuse, joined team reads,
batched writes and reference-data caching. Mutable collections, teams and
battle results still need fresh reads. See the
[verification record](../progress-report/google-cloud-mysql-verification.md).
Network trips to the US-hosted MySQL server still affect responsiveness.

The [SQL/MongoDB comparison](../progress-report/database-comparison-results.json)
checks equivalent award facts across the stores and records repeated read
timings. Different hosting, network paths and data models limit the conclusion:
the result describes those deployed queries, rather than proving one database
engine is universally faster. Label fixture tests, live checks and measurements
separately, and state any skipped or outstanding validation.

The current trainer selection is for a local demonstration rather than secure
public authentication. Predictions remain heuristics, observed analytics need
sample-size context, and proposal-only features must be labelled as future
work. The [rubric audit](../progress-report/rubric-readiness.md) tracks evidence
and unfinished deliverables; a guide alone cannot guarantee a grade.

## 8. Suggested presentation flow

1. State the user problem and introduce the data sources and database split.
2. Show species, owned copies and teams on a small ER-diagram section.
3. Demonstrate team CRUD, one invalid save and a successful transaction.
4. Explain team analysis and one useful SQL recommendation query.
5. Show a MongoDB battle snapshot, a turn update and an analytics pipeline.
6. Explain reward recovery and the SQL/NoSQL trade-offs.
7. Finish with measured results, limitations and justified improvements.

This follows the brief's background → relational → NoSQL → optional performance
order. The [five-person presentation plan](../submission/presentation-plan.md)
allocates time within ten minutes. Use the
[report outline](../submission/final-report-outline.md) to turn the same
feature evidence into methods, results, conclusions and implications.
