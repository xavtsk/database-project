# AGENTS.md

# INF2003 PokéDex & Battle Analytics Platform

## 1. Project Context

This repository is for a university group project for:

INF2003 Database Systems

The project is being developed by a group of 5 students.

The objective is to design and develop a database application that uses BOTH:

- A relational database
- A non-relational (NoSQL) database

The project should demonstrate proper database design, CRUD operations, relationships, queries, constraints, and more advanced database functionality where appropriate.

This is primarily a DATABASE SYSTEMS project.

Do not turn the project into an unnecessarily complex software engineering, AI, or full Pokémon game project.

---

# 2. Project Name

PokéDex & Battle Analytics Platform

Repository:

pokedex-battle-analytics

---

# 3. Application Concept

The application is a Pokémon database and battle analytics platform.

The overall user flow is intended to be:

PokéDex
    ↓
Explore Pokémon
    ↓
Build Team
    ↓
Analyse Team
    ↓
Simulate Battle
    ↓
Store Battle Logs
    ↓
Battle Analytics

The application combines structured Pokémon/game data with flexible battle data.

---

# 4. Confirmed Core Features

There are currently FIVE confirmed core features.

## Feature 1 — PokéDex

Users should be able to browse and explore Pokémon.

Potential functionality includes:

- Browse Pokémon
- Search Pokémon
- Filter Pokémon
- View Pokémon details
- View Pokémon stats
- View Pokémon types
- View Pokémon moves

The exact filtering options and UI have NOT been finalised.

---

## Feature 2 — Team Builder

Users should be able to create and manage Pokémon teams.

Expected functionality includes:

- Create a team
- Add Pokémon
- Remove Pokémon
- Edit a team
- Delete a team
- View a team
- Maximum of 6 Pokémon per team

Trainer/user functionality may be associated with teams.

The exact trainer/account design has NOT been finalised.

---

## Feature 3 — Team Analysis

The application should analyse a Pokémon team.

Potential analysis includes:

- Team statistics
- Type distribution
- Type weaknesses
- Type resistances
- Offensive type coverage
- Average team statistics

Example:

A team may have several Pokémon weak to Ground.

The system could identify Ground as a significant team weakness.

This feature should ideally demonstrate meaningful relational database queries rather than simply performing calculations entirely in frontend code.

The exact analysis algorithms have NOT been finalised.

---

## Feature 4 — Battle Simulator

Users should be able to simulate Pokémon battles.

The simulator will initially use SIMPLIFIED battle mechanics.

Potential inputs include:

- Pokémon stats
- Pokémon types
- Moves
- Type effectiveness

Potential outputs include:

- Damage
- Turns
- Winner
- Moves used
- Battle result

IMPORTANT:

We are NOT currently trying to reproduce the complete official Pokémon battle engine.

Do not implement complex mechanics such as weather, held items, breeding, abilities, terrains, competitive formats, etc. unless they are explicitly approved later.

The battle formula has NOT been finalised.

---

## Feature 5 — Battle Analytics

Battle results and battle logs should be stored and analysed.

Potential analytics include:

- Battle history
- Pokémon usage
- Pokémon win rates
- Most-used moves
- Average battle duration
- Number of turns
- Trainer wins/losses

MongoDB is expected to play an important role here.

The exact analytics queries have NOT been finalised.

---

# 5. Relational Database

Planned technology:

MySQL or MariaDB

The final choice between MySQL and MariaDB has not necessarily been locked yet.

The relational database will primarily contain structured game/application data.

Potential entities include:

- Pokemon
- Type
- Move
- Trainer
- Team
- TeamMember
- PokemonType
- PokemonMove
- TypeEffectiveness

These are CURRENT DESIGN IDEAS and NOT a final schema.

Do NOT assume these tables are final.

---

# 6. Why Relational Database

Pokémon game data is highly structured and contains clear relationships.

Examples:

Pokemon ↔ Type
Many-to-many

Pokemon ↔ Move
Many-to-many

Trainer → Team
Potentially one-to-many

Team ↔ Pokemon
Many-to-many through TeamMember

The relational database should demonstrate database concepts such as:

- Primary keys
- Foreign keys
- Relationships
- Junction tables
- Constraints
- JOINs
- Aggregate queries
- Nested queries where appropriate
- Views where useful
- Triggers where justified

Do not add advanced database features merely for complexity.

They should serve an actual application/database purpose.

---

# 7. NoSQL Database

Planned technology:

MongoDB

MongoDB will primarily be used for flexible battle-related data.

The main expected use is battle logs.

A battle may contain:

- Different numbers of turns
- Different moves
- Damage values
- Critical hits
- Status effects
- Switching events
- Other battle events

Because battle structures can vary, document-oriented storage may be suitable.

Conceptual example ONLY:

{
    "battle_id": 1001,
    "trainer_a": 1,
    "trainer_b": 2,
    "winner": 1,
    "turns": [
        {
            "turn": 1,
            "pokemon": "Charizard",
            "move": "Flamethrower",
            "damage": 65
        },
        {
            "turn": 2,
            "pokemon": "Venusaur",
            "move": "Sludge Bomb",
            "damage": 30,
            "status": "poison"
        }
    ]
}

This is NOT the final MongoDB schema.

Do not treat it as final.

---

# 8. Why MongoDB

Battle data can be variable in structure.

One battle might have:

5 turns

while another might have:

30 turns

Some turns might contain only:

- move
- damage

while others could contain:

- move
- damage
- status
- critical hit
- switching information

MongoDB allows battle events to be stored naturally as embedded documents/arrays.

The project should eventually demonstrate meaningful MongoDB functionality such as:

- Document insertion
- Queries
- Updates where appropriate
- Aggregation pipelines
- Battle analytics

---

# 9. Possible Dataset Sources

Potential sources currently being considered include:

- PokéAPI
- Kaggle Pokémon datasets

Potential data includes:

- Pokémon names
- Pokédex IDs
- Types
- Stats
- Moves
- Abilities
- Generations
- Evolution information

Battle-log data may be generated by our own battle simulator.

IMPORTANT:

The final datasets have NOT yet been selected.

Do not automatically download or integrate datasets without approval.

---

# 10. Data Philosophy

Do NOT simply import one large Pokémon CSV and treat it as the final relational database.

Part of the database project is designing a proper relational structure.

A flat dataset may eventually be transformed/normalised into multiple related tables.

Example concept:

Pokemon
    ↓
PokemonType
    ↓
Type

and:

Pokemon
    ↓
PokemonMove
    ↓
Move

Normalization decisions should be discussed and approved before implementation.

---

# 11. Potential Advanced Features

These are NOT currently confirmed core requirements.

Possible future/stretch features include:

- Counter Pokémon recommendation
- Pokémon comparison
- Community team builds
- Ratings
- Comments
- Trainer leaderboard
- SQL vs NoSQL performance comparison
- More advanced battle analytics

Do NOT implement these unless explicitly requested.

---

# 12. Current Project Stage

The project is currently in the EARLY DESIGN/STAGING phase.

Completed decisions:

- Project concept selected
- Five core features selected
- Relational + NoSQL approach selected
- MySQL/MariaDB planned
- MongoDB planned
- GitHub repository being established

NOT completed:

- Final dataset selection
- Final ER diagram
- Final relational schema
- Final MongoDB schema
- Final technology stack
- Final frontend framework
- Final backend framework
- Battle formula
- API design
- UI design
- Advanced feature selection

Therefore:

DO NOT prematurely make these decisions.

---

# 13. Repository Structure

The initial repository should use approximately this structure:

pokedex-battle-analytics/
│
├── README.md
├── .gitignore
├── requirements.txt
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── generated/
│
├── database/
│   ├── relational/
│   └── nosql/
│
├── backend/
│   ├── pokedex/
│   ├── teams/
│   ├── team_analysis/
│   ├── battles/
│   └── analytics/
│
├── frontend/
│
├── scripts/
│
├── tests/
│
└── docs/
    ├── database-design/
    ├── diagrams/
    └── progress-report/

The structure may evolve as the project architecture becomes clearer.

Do not over-engineer it at this stage.

---

# 14. Git Workflow

There are 5 team members.

main should contain stable/approved work.

Do NOT encourage members to maintain permanent personal branches such as:

xavier
john
member1
member2

Instead, use short-lived task/feature branches.

Examples:

feature/sql-schema
feature/pokemon-import
feature/team-builder
feature/team-analysis
feature/battle-engine
feature/mongodb-battle-logs
feature/battle-analytics

Workflow:

main
  ↓
create feature branch
  ↓
make changes
  ↓
commit
  ↓
push
  ↓
Pull Request
  ↓
review
  ↓
merge into main
  ↓
delete feature branch

Do not push experimental or incomplete work directly to main.

---

# 15. Secrets and Environment Files

Never commit:

.env

Database passwords, API credentials and other secrets must not be committed.

.gitignore should include at minimum:

.env
.venv/
venv/
__pycache__/
*.pyc
.DS_Store
.vscode/
.idea/
*.log

If environment variables are eventually required, create:

.env.example

containing placeholder values only.

---

# 16. Coding Principles

Keep the project:

- Simple
- Modular
- Understandable
- Well documented
- Appropriate for a university Database Systems project

Prioritise database concepts over unnecessary application complexity.

Avoid:

- Over-engineering
- Unnecessary frameworks
- Huge dependency lists
- Premature optimisation
- Implementing features that were never approved
- Reproducing the entire Pokémon game engine

Code should be understandable by all five group members.

---

# 17. Important Rule for Codex

Before making a major architectural decision that has not been specified in this document, STOP and explain:

1. What decision needs to be made
2. What options exist
3. Advantages/disadvantages
4. Your recommendation

Then wait for approval before implementing it.

Examples include:

- Selecting backend framework
- Selecting frontend framework
- Designing final SQL schema
- Designing final MongoDB schema
- Selecting datasets
- Designing battle formula
- Adding major dependencies
- Adding new core features

Do not silently make these decisions.

---

# 18. When Asked to Implement Something

Before coding:

1. Inspect the existing repository.
2. Understand the current architecture.
3. Check whether the requested feature already exists.
4. Identify which files need modification.
5. Avoid modifying unrelated files.
6. Preserve existing working functionality.
7. Explain major assumptions.
8. Keep commits focused.

When finished:

1. Summarise what changed.
2. List files created.
3. List files modified.
4. Explain how to test the change.
5. Mention any unresolved issues.

---

# 19. Current Immediate Goal

The immediate goal is ONLY to establish a clean GitHub repository that the five-person team can collaborate on.

Do not implement:

- SQL schema
- MongoDB schema
- Pokédex
- Team Builder
- Team Analysis
- Battle Simulator
- Battle Analytics
- Frontend
- API

until the relevant design decisions are approved.

The next major project task after repository setup will be database/application design.