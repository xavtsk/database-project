# Normalisation reference for the current schema

This optional reference preserves the worked normal-form examples, ownership
trade-off and Lecture 4 proofs. Start with the
[project explanation guide](project-explanation-guide.md) for the application
story and feature walkthroughs. This document does not propose a schema change.

**Course connection:** Lecture 4, PDF pages 6–23, covers anomalies, functional
dependencies, closure and normal forms. Page 21 briefly introduces 1NF/2NF/3NF;
pages 23–35 develop BCNF and decomposition. Use this detail when discussing
normalisation or answering design questions; it is optional supporting material
for the main feature walkthrough. Page references count from the first PDF
page, including the title page.

Normalisation organises relations using keys and functional dependencies to
reduce unnecessary duplication and insertion, update and deletion anomalies.
Having many tables or foreign keys alone does not prove a normal form. A
normal-form claim needs the intended dependencies and all candidate keys.

`A → B` means that a value of A determines one value of B under the intended
business rules. A candidate key is a minimal set of attributes identifying a
row; the primary key is the candidate key chosen as the main identifier. A
non-prime attribute belongs to no candidate key.

### First normal form: one value per attribute

We represent multiple Pokémon types and eligible moves as separate association
rows, rather than storing a comma-separated list in a relational cell.

For example, the type-name equivalent of Charizard's two associations is:

| Pokémon | Type | Slot |
| --- | --- | ---: |
| Charizard | Fire | 1 |
| Charizard | Flying | 2 |

The actual `pokemon_types` table stores IDs, with primary key
`(pokemon_id, slot)` and a unique constraint on `(pokemon_id, type_id)`.
`team_member_moves` likewise stores one selected move per move slot, rather
than one cell containing four moves. Six named base-stat columns represent
different attributes, not a list inside one value.

Suggested explanation:

> Each Pokémon-type association and selected move has its own row. This lets
> us join, filter and constrain individual associations directly.

### Second normal form: no partial dependency of a non-prime attribute

A relation must first satisfy 1NF. A non-prime attribute must not depend on
just a proper subset of a candidate key.

Use `type_effectiveness` as the clearest composite-key example:

```text
(attacking_type, defending_type) → multiplier
```

The multiplier needs both types. Fire attacking Grass and Fire attacking Water
have different multipliers. Grass being attacked by Fire and Grass being
attacked by Water also differ. Neither type alone determines the result.

In `pokemon_moves`, the `source` describes how that particular species/move
association entered the playable pool; move power belongs in `moves`, rather
than being repeated on every eligible species/move association.

Suggested explanation:

> The effectiveness multiplier depends on the entire attacking-and-defending
> type pair. We also store facts about a move once in the move table.

### Third normal form: remove inappropriate transitive dependencies

For an approachable example, imagine storing `type_name` in every move row:

```text
move_id → type_id → type_name
```

Many moves share a type, so repeating its name on every move would mean a
type-name correction needs many updates and could become inconsistent. Our
schema instead stores `moves.type_id` and `types(id, name)`. SQL joins obtain
the display name when needed. The move table has its own unique name as an
alternate candidate key; do not assume every table has only its primary key.

More formally, 3NF requires 2NF and, for every non-trivial dependency `X → A`,
either X is a superkey or A is prime. Proving the whole schema needs an agreed
dependency set; the catalogue examples demonstrate the design principles.

Suggested explanation:

> A move references its type by ID. The type's name is maintained in the type
> table, so it does not have to be updated separately for every move.

The normal-form progression is described in
[IBM's normalisation summary](https://www.ibm.com/docs/en/informix-servers/12.10.0?topic=SSGU8G_12.1.0%2Fcom.ibm.ddi.doc%2Fids_ddi_191.htm).
[Microsoft's database-design guide](https://support.microsoft.com/en-au/access/database-design-basics)
also provides worked examples of decomposing tables.

### An actual exception: ownership in `team_members`

Do not say that every current MySQL table is fully in 3NF.

```text
team_members(team_id, slot, owned_id, trainer_id)
primary key: (team_id, slot)
alternate candidate key: (team_id, owned_id)

team_id → trainer_id
owned_id → trainer_id
```

A team has one trainer and an owned instance has one trainer. The repeated
`trainer_id` is a non-prime attribute determined by part of these composite
candidate keys. Consequently this relation does not satisfy strict 2NF, and
therefore does not satisfy strict 3NF.

The practical reason is visible in the DDL: `(team_id, trainer_id)` references
`teams`, and `(owned_id, trainer_id)` references `owned_pokemon`. Those two
composite foreign keys prevent adding another trainer's owned Pokémon to a
team. This is a documented integrity/normalisation trade-off, not evidence
that foreign keys make a table normalised.

Suggested explanation:

> We normalised the catalogue relationships, but deliberately repeat the
> trainer ID in team membership so the database itself can enforce matching
> ownership through composite foreign keys. This table is an exception to
> strict 2NF/3NF, and we explain it explicitly.

The supplied project brief does not explicitly require every operational
relation to satisfy strict 3NF/BCNF. It rewards appropriate design and techniques.
Explain this exception rather than presenting it as full normalisation. If
additional instructor guidance requires removing the redundancy, alternative
ownership enforcement needs a reviewed design decision before implementation.

### BCNF and closure: the lecture's main refinement test

Lecture 4, pages 15–18 and 23, supplies the method: compute a determinant's
closure and check whether it determines every attribute. BCNF requires every
non-trivial functional dependency to have a superkey on its left-hand side.

For the membership relation, abbreviate the attributes as:

```text
T = team_id; S = slot; O = owned_id; R = trainer_id

F = { TS → O, TO → S, T → R, O → R }

(TS)+ = {T, S, O, R}  -- all attributes; TS is a candidate key
(TO)+ = {T, O, S, R}  -- the alternate candidate key
T+    = {T, R}        -- cannot identify a member or slot
O+    = {O, R}        -- an owned copy can be used in multiple saved teams
```

`T → R` is non-trivial, but T is not a superkey. Thus `team_members` fails
BCNF as well as strict 2NF/3NF. These dependencies follow from the intended
ownership rules and declared keys/FKs, not just the rows in today's database
(Lecture 4, page 11).

For a positive example, under the intended FD
`(attacking_type, defending_type) → multiplier`, `type_effectiveness` has its
composite key as the determinant. `types(id, name)` has two candidate keys,
because both attributes are non-null and unique. Under their intended FDs,
these are good small BCNF examples; they do not prove the entire schema is BCNF.

### Lossless decomposition and dependency preservation

Lecture 4, pages 26–35, asks two different questions: can a join recover the
original facts, and can the dependencies be enforced within the decomposed
relations? Merely sharing a column is not sufficient proof of losslessness.
For a binary decomposition, a useful FD test is that the shared attributes
determine all attributes of at least one component.

For illustration only, decompose membership `M(T,S,O,R)` into `M1(T,R)` and
`M2(T,S,O)`. The shared T determines M1 through `T → R`, so this decomposition
is lossless under the stated FDs. However, `O → R` cannot be checked in either
component alone. The proposed decomposition does not preserve that FD using
only the two projected dependency sets. This parallels the lecture's warning
that losslessness and dependency preservation are different properties.

In the real schema the `teams` and `owned_pokemon` relations already store the
two ownership facts. Removing the repeated trainer ID from membership would
also remove the current pair of ownership-enforcing composite FKs. Any change
needs a decision about alternative enforcement; the illustration above is not
a migration instruction. The normalisation/integrity trade-off should be
discussed explicitly. Lecture 4, page 36, also discusses redundancy trade-offs,
but the reason for this particular repetition is ownership enforcement, not a
measured speed improvement.

### Historical source data needs a separate explanation

`historical_pokemon` preserves the source's stats, names and two type fields;
it is not simply another copy of the current playable catalogue. Its identity
is `(source_id, external_id)`, with a nullable reviewed mapping to `pokemon`.
Source stats can differ from the playable data, and some forms remain unmapped.

`historical_sources` separates dataset provenance from individual Pokémon and
battle rows. `historical_combats` uses source-local participant IDs and retains
source row order and duplicate markers. Avoid presenting these source records
as proof that the entire imported dataset has been converted to a fully
normalised game model. See the [approved import design](historical-import-proposal.md).

