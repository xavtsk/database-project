# Prototype relational relationships

Implemented in `database/relational/schema.sql`. Composite ownership foreign keys ensure a team's members belong to that team's trainer.

```mermaid
erDiagram
    POKEMON ||--o{ POKEMON_TYPES : has
    TYPES ||--o{ POKEMON_TYPES : classifies
    POKEMON ||--o{ POKEMON_MOVES : can_use
    MOVES ||--o{ POKEMON_MOVES : eligible
    TYPES ||--o{ MOVES : classifies
    TYPES ||--o{ TYPE_EFFECTIVENESS : attacking_type
    TYPES ||--o{ TYPE_EFFECTIVENESS : defending_type
    TRAINERS ||--o{ OWNED_POKEMON : owns
    POKEMON ||--o{ OWNED_POKEMON : species
    TRAINERS ||--o{ TEAMS : saves
    TEAMS ||--o{ TEAM_MEMBERS : contains
    OWNED_POKEMON ||--o{ TEAM_MEMBERS : selected_as
    TEAM_MEMBERS ||--o{ TEAM_MEMBER_MOVES : selects
    MOVES ||--o{ TEAM_MEMBER_MOVES : selected_move
    TRAINERS ||--o{ BATTLE_REWARDS : receives
    OWNED_POKEMON ||--o| BATTLE_REWARDS : awarded_instance
```

- Team slots are 1–6, move slots 1–4 and Pokémon type slots 1–2.
- Draft teams may be empty. Battle entry requires 1–6 members and four distinct eligible moves each.
- A trainer can own multiple instances of a species. The same owned instance cannot appear twice in one team.
- Unique `(team_id, trainer_id)` and `(owned_id, trainer_id)` references enforce ownership in SQL.
- Server-side transactional validation checks move eligibility and the four-move requirement.
- `battle_rewards.battle_id` is unique and references a MongoDB battle UUID logically; cross-database foreign keys are not available.
- MongoDB stores immutable team snapshots for history, mutable HP/PP for play, and flexible turn events. Deleting a saved team does not delete its battle history.
