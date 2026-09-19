# pokedex-battle-analytics

## INF2003 Database Systems Group Project

A planned Pokédex & Battle Analytics Platform for a group of five students, using relational and NoSQL databases to explore Pokémon information, team building, battle simulation and battle analytics.

## Planned Core Features

1. **Pokédex** — Browse, search and filter Pokémon, and view their stats, types and moves.
2. **Team Builder** — Create and manage teams of up to six Pokémon.
3. **Team Analysis** — Analyse team statistics, type strengths, weaknesses and coverage.
4. **Battle Simulator** — Simulate Pokémon battles using stats, moves and type effectiveness, initially with simplified mechanics.
5. **Battle Analytics** — Store battle history and turn-by-turn logs, and analyse win rates, Pokémon usage, moves used and battle duration.

## Planned Database Technologies

- **MySQL/MariaDB:** Structured data such as Pokémon, types, moves, trainers and teams.
- **MongoDB:** Flexible battle logs and battle analytics data.

The relational schema, ER diagram and MongoDB document schema have not been finalised. Database design and the application technology stack are still being finalised.

## Repository Structure

| Folder | Intended purpose |
| --- | --- |
| `data/raw/` | Original source datasets. |
| `data/processed/` | Cleaned and transformed datasets. |
| `data/generated/` | Generated or synthetic datasets. |
| `database/relational/` | Future relational database files. |
| `database/nosql/` | Future NoSQL database files. |
| `backend/pokedex/` | Planned Pokédex functionality. |
| `backend/teams/` | Planned team management functionality. |
| `backend/team_analysis/` | Planned team analysis functionality. |
| `backend/battles/` | Planned battle simulation functionality. |
| `backend/analytics/` | Planned battle analytics functionality. |
| `frontend/` | Future user interface files. |
| `scripts/` | Future data preparation and utility scripts. |
| `tests/` | Future automated tests. |
| `docs/database-design/` | Database design notes and decisions. |
| `docs/diagrams/` | Project diagrams, including the future ER diagram. |
| `docs/progress-report/` | Group progress reports. |

This repository currently contains only the initial folder structure and documentation. No application features, database schemas or battle mechanics have been implemented. Dependencies will be added to `requirements.txt` after the technology stack is finalised.
