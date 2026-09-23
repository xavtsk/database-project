# Playable prototype proposal

Status: approved by the user on 2026-09-22 and implemented on `feature/core-features`. This document preserves the design choices reviewed before coding; see `battle-rules.md` and the root README for the current implementation and setup.

## Agreed product requirements

- Five features: Pokédex, Team Builder, Team Analysis, Battle Simulator and Battle Analytics.
- Original 151 Pokémon, using the existing locally cached raw data.
- Players choose a starter, collect Pokémon through battle wins, and field teams of 1–6.
- Players choose four moves from a fixed pool for each Pokémon.
- Player chooses actions each turn against a system-generated opponent.
- Three proposed difficulties: Easy, Medium and Hard.
- Winning awards one randomly selected Pokémon, with probabilities based on rarity.
- Relational data and flexible battle logs must use the two planned database technologies.

The recommendations below were approved, including option 1 for game-specific move-pool exceptions.

## Technology decisions

| Decision | Options and tradeoffs | Recommendation |
| --- | --- | --- |
| Web backend | Flask offers a small Python web layer; Django includes more built-in account/admin features but introduces more framework conventions. | Flask. |
| Browser interface | HTML/CSS with small JavaScript interactions keeps setup simple; React provides more frontend structure but adds a separate toolchain. | Flask templates, CSS and JavaScript. |
| Relational database | MySQL or MariaDB both match the planned project scope. MariaDB command-line tools are already available locally, though server connectivity is not yet verified. | MariaDB with explicit SQL through PyMySQL. |
| Battle storage | MongoDB matches the planned flexible turn logs and aggregation requirements. A working server or connection still needs setup. | MongoDB through PyMongo. |
| Local identity | A local trainer selector is simple for testing but provides no account isolation; authenticated accounts add login, credential handling and additional tests. | Local trainer profiles for this first local prototype, explicitly not public accounts. |

New direct Python dependencies would be Flask, PyMySQL and PyMongo. Keep the existing requests dependency for data collection. No virtual environment will be created automatically, following the user's earlier preference.

References: [Flask documentation](https://flask.palletsprojects.com/en/stable/), [PyMySQL documentation](https://pymysql.readthedocs.io/en/latest/), [PyMongo documentation](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/).

## Proposed feature behaviour

1. **Pokédex:** search by name/ID, filter by type, browse all 151, view stats and the project's supported move pool.
2. **Team Builder:** choose Bulbasaur, Charmander or Squirtle once per trainer; manage saved teams and four move selections per member; draw members from the owned collection. Duplicate reward species are allowed as separately owned Pokémon. A team may not contain the same owned instance twice.
3. **Team Analysis:** SQL joins and aggregates for stat totals/averages and type distribution; relational effectiveness lookups for combined weaknesses/resistances; offensive coverage based on the four selected moves. Coverage counts effective damage against target types, not a guaranteed win prediction.
4. **Battle Simulator:** one active Pokémon per side, action buttons each turn, optional switching, visible HP/PP, a chronological event log, and a result screen. Opponent has the same team size as the player.
5. **Battle Analytics:** MongoDB aggregation pipelines for completed-battle win rate, results by difficulty, Pokémon appearance counts and wins in those appearances, move usage, average turns and elapsed time. Display definitions and denominators; elapsed time includes player thinking time.

## Proposed data model for review

These are logical table proposals, not SQL definitions or a final ER diagram.

| Proposed relational data | Main fields and relationships |
| --- | --- |
| Pokemon | PokéAPI ID, name, six base stats, rarity tier. |
| Type | PokéAPI ID, name. |
| PokemonType | Pokémon ID, type ID, slot; one or two entries per Pokémon. |
| Move | PokéAPI ID, name, type ID, damage class, power, accuracy, PP, priority. Preserve meaningful null values. |
| PokemonMove | Pokémon ID, move ID, source of eligibility (raw reference or explicit game-specific override). Defines the fixed supported pool. |
| TypeEffectiveness | Attacking type, defending type, multiplier. |
| Trainer | Local profile ID, display name, creation time. |
| OwnedPokemon | Owned instance ID, trainer ID, Pokémon ID, acquisition time/source. |
| Team | Team ID, trainer ID, name. |
| TeamMember | Team ID, slot 1–6, owned instance ID. |
| TeamMemberMove | Team/member slot, move slot 1–4, move ID. |
| BattleReward | Unique battle ID, trainer ID, awarded owned instance ID and rarity roll. Ensures a victory cannot award twice. |

Use primary/foreign keys and uniqueness/check constraints where applicable. Validate ownership, allowed moves and complete battle-ready teams on the server within transactions. Empty draft teams are allowed; starting a battle requires 1–6 members with four distinct eligible moves each.

Proposed MongoDB `battles` document:

- UUID battle ID, trainer reference, difficulty, rule version, state revision and status.
- Start/end timestamps, turn count, result and winner.
- Immutable starting snapshots of both teams, stats, selected moves and difficulty-generation details.
- Current active slots, HP and remaining PP for each member.
- Ordered turns containing selected actions, executed moves, misses, damage, switching and fainting events.
- Selected reward and delivery status, allowing interrupted reward delivery to be retried.

MongoDB snapshots preserve history when a saved team is edited. Store the authoritative battle outcome before granting a reward. The unique relational battle-reward key makes retries safe; the two databases do not share one automatic transaction. Use conditional revision updates to prevent a repeated turn submission from resolving twice.

## Battle rules proposed for the first version

- Use current cached stats/types, not historical Generation I mechanics. No experience, levels gained or evolution in this version.
- All combatants use an effective level of 50. Maximum HP is `2 * base_hp + 60`; offensive/defensive stats use `base_stat + 5`.
- Damage is `floor((22 * power * attack / defense / 50 + 2) * STAB * effectiveness * random_factor)`.
- Match physical moves to Attack/Defense and special moves to Special Attack/Special Defense. STAB is 1.5 when the move matches an attacker's type; otherwise 1. The random factor is uniformly selected from 0.85–1.0. Immunity deals zero; a successful nonimmune hit deals at least one damage.
- Numeric accuracy gives the hit probability; null accuracy means the supported move bypasses that check. Moves consume PP even on a miss.
- Moves resolve by priority, then Speed, then a random tie-break. Fainted combatants do not execute their queued move.
- Voluntary switching consumes an action and occurs before attacks. Forced replacement after fainting is free. The player selects the replacement; the opponent uses its next healthy member.
- When no move has PP, provide an explicitly defined fallback attack: neutral 50-power physical damage with recoil equal to one quarter of the damage dealt, minimum one.
- No held items, abilities, weather, status conditions, critical hits or secondary effects. Supported attacks act as single-target, single-hit attacks; explain these simplified rules in the UI.
- A battle ends when one side has no healthy members. Simultaneous defeat or 200 completed turns results in a draw, with no reward. Battle HP/PP reset for each new battle.

### Four-move edge case requiring approval

The existing cached data has fewer than four positive-power physical/special moves for Ditto (0), Kakuna (2), Metapod (2), Magikarp (3) and Weedle (3). A damage-only simulator cannot give these species four distinct moves solely from those eligible raw references.

Options:

1. **Recommended for the prototype:** retain four distinct moves by adding a small, explicitly documented game-specific fallback pool for those five species, using existing cached damage moves. Preserve the raw responses and mark every override in the processed eligibility data. This meets the four-button interaction but departs from official learnsets.
2. Support special/status mechanics and allow fewer than four moves where the source pool remains too small. This adds simulator work and changes the four-move requirement.
3. Keep those species visible in the Pokédex but temporarily exclude them from battles and rewards. This reduces playable coverage.

For other Pokémon, use their cached positive-power physical/special move references as the fixed eligible pool. The UI must describe these as simplified supported moves, not full official move behaviour. Players choose their four moves; generated opponents receive four eligible moves.

## Difficulty and reward recommendations

Difficulty is an initial heuristic that must be evaluated using battle results, not a promise of a particular win rate.

- Base strength is the sum of all six base stats across the team.
- Generate up to 100 candidate teams of the same size. Easy targets 85% of player strength, Medium 100%, Hard 115%; choose the closest candidate when exact matching is impossible.
- Easy prefers weaker type matchups among similar-strength candidates and chooses random usable moves. Medium prefers neutral matchups and mixes random moves with moves ranked by expected damage. Hard prefers stronger type matchups and chooses the highest expected-damage move. The opponent never examines the player's hidden next action.
- Record requested strength, actual strength and matchup estimates in the battle document to evaluate the rules later. Rarity does not enter the difficulty score.

Proposed starter choices: Bulbasaur, Charmander and Squirtle. Grant exactly one starter per trainer profile, transactionally.

Proposed reward tiers: Common 60%, Uncommon 25%, Rare 12%, Legendary/Mythical 3%. First select a tier, then uniformly select a species in that tier. Allow duplicates as separately owned instances. Display these probabilities.

For a transparent initial assignment, use cached species flags for the Legendary/Mythical tier. For other species, use capture-rate bands: at least 150 is Common, 75–149 is Uncommon, below 75 is Rare. This is a project-specific reward rule, not an official rarity classification, and can be replaced by a curated mapping after review.

## Data and environment follow-up after approval

- Preserve all existing raw files and deterministic stats/type processing.
- Fetch only the missing Dark-type resource required by the cached moves, then process all 18 type definitions and effectiveness relations.
- Process move definitions and eligible move relationships, with explicit exception records for the approved move-pool policy.
- Add a versioned rarity mapping and selection rules; no extra dataset is required.
- Configure MariaDB and MongoDB via environment variables and a placeholder-only `.env.example`.
- Verify local database services. MariaDB CLI tools are present; MongoDB and Docker were not found on the current PATH. Do not assume a functioning database connection or substitute an unrelated storage technology silently.

## Validation and delivery

- Test all 151 Pokémon, type relations, move eligibility and source preservation.
- Test team size/ownership, duplicate members, four distinct eligible moves and transactional updates.
- Test damage, immunity, accuracy, PP, fainting, switching and every end condition with controlled randomness.
- Test opponent size/eligibility, difficulty estimates, starter uniqueness, weighted reward selection and reward retry safety.
- Test battle persistence and recovery against actual MariaDB/MongoDB services and verify analytics against known battle fixtures.
- Exercise the complete browser path: starter → team/moves → analysis → each difficulty → turns → result/reward → history/analytics.
- Document exact setup and run commands, implemented limitations and any unverified integration steps.

Implementation stays on `feature/core-features`. No merge or push is implied by approval of this design.
