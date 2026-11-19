'use strict';
const state = {csrf: '', trainer: null, profiles: [], view: 'pokedex', collection: [], teams: [], draft: null, battle: null, busy: false};
const main = document.querySelector('#main');
const dialog = document.querySelector('#dialog');
const stats = ['hp','attack','defense','special_attack','special_defense','speed'];
const TYPE_COLORS = {normal:'#929aa4',fire:'#f08135',water:'#3d93db',electric:'#e5b821',grass:'#6ca944',ice:'#67bcc1',fighting:'#c75842',poison:'#9d62bd',ground:'#caa559',flying:'#839bd7',psychic:'#e1648e',bug:'#91a73a',rock:'#a59359',ghost:'#74629f',dragon:'#6479c9',dark:'#665c6b',steel:'#7898ac',fairy:'#d97eb4'};
const typeColor = name => TYPE_COLORS[name] || '#7c8caa';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const title = value => String(value).replaceAll('-', ' ').replaceAll('_', ' ');
const sprite = (id, back=false, shiny=false) => `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${back?'back/':''}${shiny?'shiny/':''}${Number(id)}.png`;
const img = (p, back=false) => `<img src="${sprite(p.id,back,p.is_shiny)}" alt="${p.is_shiny?'Shiny ':''}${esc(title(p.name))}" loading="lazy">`;
const shinyBadge = p => p.is_shiny?'<span class="shiny-badge">✦ Shiny</span>':'';
const tags = types => `<div class="tags">${types.map(t=>`<span class="type ${esc(t)}">${esc(t)}</span>`).join('')}</div>`;
const statLabel = s => ({hp:'HP',attack:'Attack',defense:'Defense',special_attack:'Sp. Attack',special_defense:'Sp. Defense',speed:'Speed'}[s]);
const button = (text, action, value='', cls='quiet') => `<button type="button" class="${cls}" data-action="${action}" data-value="${esc(value)}">${esc(text)}</button>`;
const table = (headers, rows) => `<div class="table-scroll"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const heading = (eyebrow, name, text) => `<div class="page-heading"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(name)}</h1><p>${esc(text)}</p></div></div>`;
const empty = text => `<div class="card empty">${esc(text)}</div>`;
const metric = (name,value) => `<div class="metric"><span>${esc(name)}</span><strong>${esc(value)}</strong></div>`;
function databaseEvidence({database,operation,data,techniques,changes,query,title='Database evidence',explanation='',source=''}) {
  const mongo=database==='MongoDB';
  return `<details class="database-evidence spacer"><summary><span><b>${esc(title)}</b><small>${esc(database)} · ${esc(operation)}</small></span><span class="evidence-change ${changes.startsWith('No')?'read-only':'writes-data'}">Changes data: ${esc(changes)}</span></summary><div class="evidence-body">${explanation?`<p class="evidence-explanation">${esc(explanation)}</p>`:''}<dl><div><dt>Tables / collection</dt><dd>${esc(data)}</dd></div><div><dt>Techniques</dt><dd>${esc(techniques)}</dd></div></dl><h4>${mongo?'MongoDB pipeline / query excerpt':'Query excerpt'}</h4><pre><code>${esc(query)}</code></pre>${source?`<p class="evidence-source">Source: <code>${esc(source)}</code></p>`:''}<p class="note">${mongo?'JavaScript driver notation for the PyMongo operations used by the backend. Named variables represent validated request values; comments identify omitted stages.':'Excerpts for explanation; comments or ellipses identify omitted code. The backend binds %s parameters separately.'} These panels display reference code and do not execute it. Credentials and live values are not displayed.</p></div></details>`;
}
const DB_EVIDENCE = {
  pokedex:{database:'MySQL',operation:'SELECT · read-only',data:'pokemon, pokemon_types, types',techniques:'Parameterised search, nested type-membership query, JOIN',changes:'No',source:'backend/pokedex/service.py · browse',explanation:'The backend binds the search text and selected type as parameters. The nested membership query finds species with the requested type; cached catalogue data supplies their display details.',query:`SELECT p.id
FROM pokemon p
WHERE (p.name LIKE %s OR CAST(p.id AS CHAR)=%s)
  AND (%s='' OR p.id IN (
    SELECT pt.pokemon_id
    FROM pokemon_types pt JOIN types t ON t.id=pt.type_id
    WHERE t.name=%s
  ))
ORDER BY p.id;`},
  teams:{database:'MySQL',operation:'SELECT / INSERT / UPDATE / DELETE',data:'teams, team_members, owned_pokemon, team_member_moves',techniques:'LEFT JOIN, row lock, transaction, batch insert, rollback, cascades',changes:'Yes, when Save or Delete is clicked',source:'backend/teams/service.py · save_team / delete_team',explanation:'Saving validates ownership, four distinct eligible moves, species limits and the budget before changing rows. A transaction commits the team and moves together or rolls back on failure. This excerpt shows editing; creating inserts a team, while deletion uses an ownership-filtered DELETE with member/move cascades.',query:`START TRANSACTION;
SELECT id FROM trainers WHERE id=%s FOR UPDATE;
SELECT id FROM teams WHERE id=%s AND trainer_id=%s FOR UPDATE;
-- Ownership, move, species and budget validation omitted.
UPDATE teams SET name=%s WHERE id=%s;
DELETE FROM team_members WHERE team_id=%s;
INSERT INTO team_members (...) VALUES (...);
INSERT INTO team_member_moves (...) VALUES (...);
COMMIT;`},
  analysis:{database:'MySQL',operation:'SELECT · read-only',data:'team/member/species/type/move tables and three SQL views',techniques:'JOIN, COUNT, SUM, AVG, GROUP BY, CTE, NOT EXISTS, ROW_NUMBER',changes:'No; recommendations are proposals only',source:'backend/team_analysis/service.py · database/relational/queries/team_recommendations.sql',explanation:'MySQL computes the displayed statistics, type matchups, coverage and recommendation ranking. Open the View SQL panels beside each result for its query and explanation.',query:`SELECT t.name, COUNT(*)
FROM team_members tm
JOIN owned_pokemon o ON o.id=tm.owned_id
JOIN pokemon_types pt ON pt.pokemon_id=o.pokemon_id
JOIN types t ON t.id=pt.type_id
WHERE tm.team_id=%s
GROUP BY t.id,t.name;

WITH roster AS (...), candidates AS (...), ranked AS (...)
SELECT * FROM ranked WHERE recommendation_rank <= 3;`},
  battle:{database:'MySQL → MongoDB',operation:'SELECT / INSERT, insert_one, replace_one',data:'SQL saved team/catalogue/rewards; MongoDB battles',techniques:'SQL roster JOIN and transaction; embedded snapshot; revision-checked replacement',changes:'Yes, when a battle starts, a turn resolves or a reward is delivered',source:'backend/battles/service.py · backend/teams/service.py',explanation:'A battle copies the saved SQL team into a MongoDB snapshot. Each turn replaces only the matching active revision, preventing stale updates. Winning rewards use a separate SQL transaction; the two databases do not share a distributed transaction. MongoDB operations below use JavaScript notation for PyMongo calls.',query:`-- Read the owned SQL roster
SELECT ... FROM teams t
LEFT JOIN team_members tm ON tm.team_id=t.id
WHERE t.id=%s AND t.trainer_id=%s;

// Store/update the MongoDB battle
insertOne(battleSnapshot)
replaceOne({_id, trainer_id, revision, status:'active'}, updatedBattle)

-- On a win, deliver one SQL reward transaction
INSERT INTO owned_pokemon (...) VALUES (...);
INSERT INTO battle_rewards (...) VALUES (...);`},
  analytics:{database:'MongoDB',operation:'aggregate · read-only',data:'battles',techniques:'$match, $facet, $unwind, $group, $sort',changes:'No',source:'backend/analytics/service.py · analytics',explanation:'One aggregation uses facets to derive several summaries from this trainer’s completed battles. Each result section below has its own pipeline excerpt. Strategy and 1v1 sections apply additional rules/difficulty and non-forfeit filters.',query:`[
  {$match: {trainer_id, status: {$in: ['win','loss','draw']}}},
  {$facet: {
    summary: [{$group: {_id: null, battles: {$sum: 1}}}],
    moves: [{$unwind: '$turns'}, {$unwind: '$turns.events'},
            {$match: {'turns.events.kind': 'move', 'turns.events.side': 'player'}},
            {$group: {_id: '$turns.events.move_id', uses: {$sum: 1}}}]
  }}
]`}
};
const SECTION_EVIDENCE = {
  statistics:{title:'View SQL · Team statistics',database:'MySQL',operation:'SELECT',changes:'No',
    data:'team_members, owned_pokemon, pokemon',techniques:'JOIN, COUNT, SUM, AVG',
    explanation:'MySQL totals and averages the base stats of the saved team. Each owned copy contributes once. The backend generates the same SUM/AVG expressions for all six stats.',
    source:'backend/team_analysis/service.py · analyse',query:`SELECT COUNT(*) AS size,
       SUM(p.hp) AS total_hp, AVG(p.hp) AS average_hp,
       AVG(p.speed) AS average_speed
       -- Other stat expressions omitted from this excerpt.
FROM team_members tm
JOIN owned_pokemon o ON o.id=tm.owned_id
JOIN pokemon p ON p.id=o.pokemon_id
WHERE tm.team_id=%s;`},
  distribution:{title:'View SQL · Type distribution',database:'MySQL',operation:'SELECT',changes:'No',
    data:'team_members, owned_pokemon, pokemon_types, types',techniques:'JOIN, COUNT, GROUP BY',
    explanation:'Counts members with each type. A dual-type Pokémon contributes to both types, so the counts can add up to more than the team size.',
    source:'backend/team_analysis/service.py · analyse',query:`SELECT t.name,COUNT(*) AS count
FROM team_members tm
JOIN owned_pokemon o ON o.id=tm.owned_id
JOIN pokemon_types pt ON pt.pokemon_id=o.pokemon_id
JOIN types t ON t.id=pt.type_id
WHERE tm.team_id=%s
GROUP BY t.id,t.name
ORDER BY count DESC,t.name;`},
  defense:{title:'View SQL · Defensive matchups',database:'MySQL',operation:'SELECT',changes:'No',
    data:'types, team_members, owned_pokemon, v_pokemon_defense',techniques:'SQL view, LEFT JOIN, conditional SUM, COALESCE',
    explanation:'The defense view multiplies the two defensive type multipliers, preserving zero for immunity. This query counts weak, resistant and immune members for every attacking type, including types with zero matches.',
    source:'database/relational/queries/team_matchups.sql · view in database/relational/views.sql',query:`SELECT t.name,
       COALESCE(SUM(d.multiplier>1),0) AS weak,
       COALESCE(SUM(d.multiplier>2),0) AS double_weak,
       COALESCE(SUM(d.multiplier>0 AND d.multiplier<1),0) AS resistant,
       COALESCE(SUM(d.multiplier=0),0) AS immune
FROM types t
LEFT JOIN (
    SELECT o.pokemon_id FROM team_members tm
    JOIN owned_pokemon o ON o.id=tm.owned_id
    WHERE tm.team_id=%s
) r ON TRUE
LEFT JOIN v_pokemon_defense d
  ON d.pokemon_id=r.pokemon_id AND d.type_id=t.id
GROUP BY t.id,t.name ORDER BY t.id;`},
  coverage:{title:'View SQL · Offensive coverage',database:'MySQL',operation:'SELECT',changes:'No',
    data:'team_member_moves, moves, types, type_effectiveness',techniques:'DISTINCT, LEFT JOIN, MAX, GROUP BY',
    explanation:'Uses the moves actually saved on the team. For each single defending type, MySQL finds the best available attack multiplier. An empty team returns zero coverage.',
    source:'database/relational/queries/team_coverage.sql',query:`SELECT t.name AS type,
       COALESCE(MAX(te.multiplier),0) AS best_multiplier
FROM types t
LEFT JOIN (
    SELECT DISTINCT m.type_id FROM team_member_moves mm
    JOIN moves m ON m.id=mm.move_id WHERE mm.team_id=%s
) mt ON TRUE
LEFT JOIN type_effectiveness te
  ON te.attacking_type=mt.type_id AND te.defending_type=t.id
GROUP BY t.id,t.name ORDER BY t.id;`},
  recommendations:{title:'View SQL · Recommended partners',database:'MySQL',operation:'SELECT',changes:'No; suggestions only',
    data:'owned_pokemon, roster CTE, cost/defense/default-move views, scoring CTEs',techniques:'CTEs, NOT EXISTS, budget filtering, ROW_NUMBER, PARTITION BY',
    explanation:'MySQL evaluates unused owned copies as additions, or replacements for a full team. It filters budget and legendary conflicts, scores exposure/coverage changes, keeps one plan per species and returns up to three improvements. No saved team is changed. Battle-history counts on the cards are separate MongoDB evidence, not the SQL ranking score.',
    source:'database/relational/queries/team_recommendations.sql · backend/analytics/service.py (species_evidence)',query:`-- Excerpts from a larger WITH query, not a standalone statement.
candidates AS (
    SELECT o.id AS owned_id,o.pokemon_id,pc.name,pc.cost,p.rarity
    FROM settings s JOIN owned_pokemon o ON o.trainer_id=s.trainer_id
    JOIN v_pokemon_cost pc ON pc.pokemon_id=o.pokemon_id
    JOIN pokemon p ON p.id=o.pokemon_id
    WHERE NOT EXISTS (SELECT 1 FROM roster r WHERE r.owned_id=o.id)
),
-- plans/scoring CTEs omitted. The affordability stage includes:
-- WHERE p.proposed_cost<=s.point_limit (plus legendary checks).
-- The improving stage keeps lower exposure, or equal exposure
-- with better coverage; an empty team can accept any eligible plan.
species_choices AS (
    SELECT i.*,ROW_NUMBER() OVER (
        PARTITION BY pokemon_id
        ORDER BY ROUND(exposure_reduction,9) DESC,
                 coverage_gain DESC,cost,owned_id,replace_owned_id
    ) AS species_rank FROM improving i
),
ranked AS (
    SELECT c.*,ROW_NUMBER() OVER (
        ORDER BY ROUND(exposure_reduction,9) DESC,
                 coverage_gain DESC,cost,owned_id,replace_owned_id
    ) AS recommendation_rank
    FROM species_choices c WHERE species_rank=1
)
-- Final SELECT retains the baseline if no plan qualifies:
-- LEFT JOIN ranked r ON r.recommendation_rank<=3`},
  summary:{title:'View MongoDB · Battle totals',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles · summary branch',techniques:'$match, $facet, $group, $sum, $avg',
    explanation:'Filters to this trainer’s completed battles. The summary facet counts battles and wins and averages turns and elapsed seconds. The browser formats wins divided by completed battles as a percentage.',
    source:'backend/analytics/service.py · analytics',query:`[
  {$match: {trainer_id, status: {$in: ['win','loss','draw']}}},
  {$facet: {
    summary: [{$group: {
      _id: null, battles: {$sum: 1},
      wins: {$sum: {$cond: [{$eq: ['$status','win']},1,0]}},
      average_turns: {$avg: '$turn_count'},
      average_seconds: {$avg: '$elapsed_seconds'}
      // Loss/draw totals and other facet branches omitted.
    }}]
  }}
]`},
  difficulty:{title:'View MongoDB · Results by difficulty',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles · difficulty branch',techniques:'$group, $cond, $sum, $sort',
    explanation:'After the trainer/completed-battle filter, the difficulty facet groups results by Easy, Medium and Hard. This excerpt shows the counts; the same group also computes average turns and duration.',
    source:'backend/analytics/service.py · analytics',query:`// difficulty facet, after the shared completed-battle $match:
[
  {$group: {_id: '$difficulty', battles: {$sum: 1},
    wins: {$sum: {$cond: [{$eq: ['$status','win']},1,0]}},
    losses: {$sum: {$cond: [{$eq: ['$status','loss']},1,0]}},
    draws: {$sum: {$cond: [{$eq: ['$status','draw']},1,0]}}
  }},
  {$sort: {_id: 1}}
]`},
  moves:{title:'View MongoDB · Most-used moves',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles.turns.events · moves branch',techniques:'$unwind, $match, $group, $sort, $limit',
    explanation:'Unwinds turns and events, selects executed player moves and counts each move ID. Misses are included; opponent attacks and non-move events are excluded. The panel shows the top 20.',
    source:'backend/analytics/service.py · analytics',query:`// moves facet, after the shared completed-battle $match:
[
  {$unwind: '$turns'}, {$unwind: '$turns.events'},
  {$match: {'turns.events.kind': 'move',
            'turns.events.side': 'player'}},
  {$group: {_id: '$turns.events.move_id',
    name: {$first: '$turns.events.move'}, uses: {$sum: 1}}},
  {$sort: {uses: -1, _id: 1}}, {$limit: 20}
]`},
  performance:{title:'View MongoDB · Pokémon performance',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles.initial.player.members · pokemon branch',techniques:'$unwind, two $group stages, $first, $sum',
    explanation:'Groups by battle and species before counting appearances. Two copies of the same species on one team count as one appearance. Wins describe that team’s result, not individual knockouts.',
    source:'backend/analytics/service.py · analytics',query:`// pokemon facet, after the shared completed-battle $match:
[
  {$unwind: '$initial.player.members'},
  {$group: {_id: {battle: '$_id',
                  pokemon: '$initial.player.members.id'},
    name: {$first: '$initial.player.members.name'},
    status: {$first: '$status'}}},
  {$group: {_id: '$_id.pokemon', name: {$first: '$name'},
    appearances: {$sum: 1},
    wins: {$sum: {$cond: [{$eq: ['$status','win']},1,0]}}}},
  {$sort: {appearances: -1, _id: 1}}
]`},
  damage:{title:'View MongoDB · Damage per attempt',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles.turns.events · strategy moves branch',techniques:'$match, $unwind, $group, $ifNull, $divide',
    explanation:'The shared strategy filter selects this trainer, rules version, optional difficulty and completed non-forfeit battles. Within that cohort, player move events are grouped into attempts, hits and actual damage. Damage per attempt includes misses.',
    source:'backend/analytics/strategy.py · report',query:`// moves facet, after the shared strategy filter:
[
  {$unwind: '$turns'}, {$unwind: '$turns.events'},
  {$match: {'turns.events.kind': 'move',
            'turns.events.side': 'player'}},
  {$group: {_id: '$turns.events.move_id',
    attempts: {$sum: 1},
    damage: {$sum: {$ifNull: ['$turns.events.damage',0]}},
    hits: {$sum: {$cond: [{$eq: ['$turns.events.hit',true]},1,0]}}
    // Display name omitted.
  }},
  {$set: {damage_per_attempt: {$divide: ['$damage','$attempts']},
          hit_rate: {$divide: ['$hits','$attempts']}}}
  // Final sort and top-20 limit omitted.
]`},
  repetition:{title:'View MongoDB · Move repetition',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles.turns.events · strategy repetition branch',techniques:'Two $group stages, $max, $divide, $cond',
    explanation:'Within the filtered cohort, the pipeline first counts each move per battle, then totals attempts and the largest move count per battle. At least five attacks are required; a top-move share of 75% or more is high repetition. Final groups also separate difficulty and starting team size.',
    source:'backend/analytics/strategy.py · report',query:`// After the shared filter, player-move unwinds and match:
{$group: {_id: {battle: '$_id', move: '$turns.events.move_id'},
  uses: {$sum: 1}
  // Status, difficulty and initial team size also retained.
}},
{$group: {_id: '$_id.battle', attempts: {$sum: '$uses'},
  top_uses: {$max: '$uses'}
  // Other retained fields omitted.
}},
{$match: {attempts: {$gte: 5}}},
{$set: {top_share: {$divide: ['$top_uses','$attempts']}}},
// Final group key (counts and averages omitted):
{$group: {_id: {difficulty: '$difficulty', team_size: '$team_size',
  pattern: {$cond: [{$gte: ['$top_share',0.75]},
                    'high repetition','mixed moves']}}}}`},
  predictions:{title:'View MongoDB · Prediction outcomes',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles.prediction, status · strategy predictions branch',techniques:'$match, $group, $sum, $sort',
    explanation:'After the same rules/difficulty and non-forfeit filter, MongoDB counts combinations of prediction method, label and actual result. The browser lays these counts out as wins/losses/draws and directional calls. This is descriptive evidence, not a calibrated probability.',
    source:'backend/analytics/strategy.py · report',query:`// predictions facet, after the shared strategy filter:
[
  {$match: {'prediction.method': {$type: 'string'},
    'prediction.label': {$in: ['favoured','evenly matched','disadvantaged']}}},
  {$group: {_id: {method: '$prediction.method',
    label: '$prediction.label', outcome: '$status'}, battles: {$sum: 1}}},
  {$sort: {'_id.method': 1, '_id.label': 1, '_id.outcome': 1}}
]`},
  matchups:{title:'View MongoDB · 1v1 matchups',database:'MongoDB',operation:'aggregate',changes:'No',
    data:'battles.initial.player/opponent.members',techniques:'$expr, $size, $project, $arrayElemAt, $facet',
    explanation:'The shared filter excludes active battles and forfeits. Both starting teams must contain exactly one member. The pipeline matches the selected species pair in either orientation, determines the selected species’ side, then groups its outcomes. SQL only supplies names for the selection lists.',
    source:'backend/analytics/matchups.py · report',query:`// After trainer/rules/difficulty/completed/non-forfeit $match:
{$match: {$expr: {$and: [
  {$eq: [{$size: {$cond: [{$isArray: '$initial.player.members'},
                         '$initial.player.members',[]]}},1]},
  {$eq: [{$size: {$cond: [{$isArray: '$initial.opponent.members'},
                         '$initial.opponent.members',[]]}},1]}
]}}},
{$project: {difficulty: 1, status: 1, turn_count: 1,
  player_id: {$arrayElemAt: ['$initial.player.members.id',0]},
  opponent_id: {$arrayElemAt: ['$initial.opponent.members.id',0]}}},
{$match: {$or: [
  {player_id: pokemon_id, opponent_id: opponent_id},
  {player_id: opponent_id, opponent_id: pokemon_id}
]}},
// Side/outcome derivation and summary/rows facets omitted.`},
  history:{title:'View MongoDB · Battle history',database:'MongoDB',operation:'find',changes:'No',
    data:'battles',techniques:'Trainer filter, projection, descending sort, limit',
    explanation:'Reads the latest 50 battles for the selected trainer, including active ones. Projection returns list fields without downloading the full turn log; opening Review or Resume loads the selected battle.',
    source:'backend/analytics/service.py · history',query:`battles.find({trainer_id}, {
  projection: {_id: 1, difficulty: 1, status: 1, turn_count: 1,
    started_at: 1, ended_at: 1, team_id: 1, team_name: 1, reward: 1}
}).sort({started_at: -1}).limit(50);`}
};
const FEATURE_HELP = {
  catalogue:{title:'About the catalogue and move data',items:[
    ['Catalogue versus collection','The Pokédex lists all 151 supported species. Your collection contains only the individual copies you own; win battles to obtain more. Browsing a species does not add it to your collection.'],
    ['Project data','Cached PokéAPI data provides species, stats, types and damaging moves. The project uses all 18 types and move references across game versions; it does not reproduce the original Generation I rules.'],
    ['Base stats and battle stats','Base stats describe a species. In battle, HP is 2 × base HP + 60; Attack, Defense, Special Attack, Special Defense and Speed are their base values + 5.'],
    ['Move terms','Power contributes to damage. Accuracy is the chance an attempted move hits; PP is its remaining number of uses. Null accuracy bypasses the accuracy check. A hit can still cause zero damage against an immune target.'],
    ['Reward tiers and shiny copies','Common, uncommon, rare and legendary/mythical are project reward tiers, not a ranking of battle strength. Shiny copies look different but have the same combat stats. The ★ symbol marks an approved project-specific move-pool addition.']
  ]},
  teams:{title:'How collection copies and saved teams work',items:[
    ['Species number versus Owned #','The Pokédex number identifies a species. Owned # identifies one individual copy in your collection; two copies of the same species have different Owned # values. A copy can be used in different teams, but only once in the same team.'],
    ['Draft versus saved team','Adding, removing, reordering or changing moves edits the draft on this page. Click Save team to persist it. Team analysis and new battles use the saved version. Removing a member does not delete its collection copy; deleting a team also preserves your collection and earlier battle history.'],
    ['Team requirements','Draft teams may be saved empty. A battle requires 1–6 members, four distinct eligible moves per member and a total cost of at most 30 points. Each legendary species may appear only once per team across normal/shiny variants.'],
    ['Budget example','A member’s cost is the sum of its six base stats divided by 100, rounded up. Squirtle has 314 total base stats, so it costs 4 points. A team budget is the sum of its members’ costs.'],
    ['Growing your collection','One starter is available per trainer. Wins award additional copies. Non-legendary species allow six normal and six shiny copies separately; legendary collection copies are unlimited, while the team limit still applies.']
  ]},
  analysis:{title:'How to read team analysis',items:[
    ['Statistics and types','Totals and averages use the saved team’s species base stats. Type distribution counts both types of a dual-type member, so its counts can add up to more than the team size.'],
    ['Defensive matchups','Each row is an incoming attack type. Weak means a combined multiplier above 1, resistant means above 0 and below 1, and immune means 0. Dual defensive types multiply together; a 4× weakness still counts as one weak member.'],
    ['Offensive coverage','Coverage uses the moves saved on your team. A 2× multiplier is super effective, 1× is neutral, 0.5× is resisted and 0× is immune. The panel considers each single defending type separately; it is not a forecast of an actual battle.']
  ]},
  recommendations:{title:'What Exposure, Coverage and recommendations mean',items:[
    ['Eligible partners','Only unused copies already in this trainer’s collection are considered. A team below six members gets addition plans; a full team gets replacement plans. Budget and legendary-species limits apply.'],
    ['Exposure: lower is better','For each incoming type, add only weakness above neutral damage: 2× adds 1, 4× adds 3, and neutral/resisted/immune matchups add 0. Average across members, then sum across all 18 incoming types. This is a weakness score, not a percentage or a win probability.'],
    ['Coverage: higher is better','The number of single defending types that at least one move hits super effectively, out of 18. Before uses your saved moves. After keeps retained members’ moves and gives the proposed partner its suggested default moves.'],
    ['Ranking and arrows','Each arrow compares the current team with the proposed team. MySQL prioritises lower exposure, then higher coverage and lower candidate cost, returning up to three distinct species. Suggestions do not edit the team; use Review this team, make the change and save.'],
    ['No eligible improvement','This can mean there are no unused owned copies, no affordable/legal plans, or none that lower exposure or improve coverage without worsening exposure. A larger collection can provide more options; every reward does not guarantee a recommendation.'],
    ['W / L / D on a card','Wins, losses and draws from this trainer’s completed non-forfeit battles under the current rules containing that species, once per species per battle. Other team sizes and difficulties may be included. These MongoDB counts give context and do not determine the SQL recommendation ranking.']
  ]},
  difficulty:{title:'What Easy, Medium and Hard change',items:[
    ['Equal team size','The opponent always starts with the same number of Pokémon as your saved team. Strength here means the sum of all six species base stats across a team, not a measured win probability.'],
    ['Strength targets','From 100 generated candidate teams, Easy targets 85% of your strength, Medium 100% and Hard 115%. Available candidates may miss that target; Opponent matching shows the actual selected strength. Type matchups also influence selection.'],
    ['Opponent move choice','Easy chooses random usable moves. Medium chooses randomly half the time and otherwise uses expected damage. Hard chooses the highest expected damage, considering accuracy and type immunity.'],
    ['Rules versus difficulty','Rules version determines damage mechanics. Difficulty changes opponent generation, move choice and reward odds; it does not change the saved rules version or guarantee a win/loss.']
  ]},
  analytics:{title:'How to interpret these results',items:[
    ['Which data is counted','The overview, difficulty table, most-used moves and species performance cover this trainer’s completed battles across all saved rules versions and difficulties, including forfeits. The filters further down apply only to Battle strategy evidence and 1v1 matchups.'],
    ['Sample and duration','A sample is a count of recorded battles or move attempts, as labelled. The strategy and 1v1 sections warn when fewer than 10 battles are available; reaching 10 does not establish statistical reliability. Duration includes time spent thinking and time away from the battle.'],
    ['Damage and hit rates','A move attempt is an executed player attack, including a miss. Damage is actual damage dealt, limited by remaining HP. Hits against immune targets count as hits with zero damage. Observed hit rates can differ from listed move accuracy.'],
    ['Repetition and predictions','High repetition means one move accounts for at least 75% of player attacks in a battle with at least five attempts. Groups separate difficulty and team size, but team composition and choices can still differ. Patterns are associations, not proof that a strategy causes wins.'],
    ['1v1 perspective','Both starting teams must contain exactly one member. The chosen species can be on your side or the AI side; wins/losses are counted from that species’ perspective. Larger-team battles and forfeits are excluded.'],
    ['Battle history','History includes active and completed battles, newest 50 first, regardless of the strategy filters. Review opens the saved battle; Resume continues an active one.']
  ]},
  prediction:{title:'How the starting prediction is defined',items:[
    ['Method: move-pressure-1','This saved heuristic compares each side’s best accuracy-adjusted damage as a share of opposing maximum HP, averaged over starting member pairings. It does not simulate the whole battle.'],
    ['Prediction labels','Favoured means your attack-pressure score is more than 1.10 times the opponent’s. Disadvantaged means the opponent’s is more than 1.10 times yours. Otherwise the label is evenly matched. These thresholds compare scores, not win probabilities.'],
    ['Saved at the start','The prediction remains unchanged as turns resolve. The displayed prior-battle counts match this trainer’s rules, difficulty and starting team size, excluding forfeits; they need not involve the same species.'],
    ['Correct directional calls','Favoured + win and disadvantaged + loss count as correct. The denominator includes decisive wins/losses for those directional labels; draws and evenly matched labels are assessed separately.']
  ]},
  persistence:{title:'What is saved when you play or review a battle',items:[
    ['Saved snapshots and events','MongoDB stores the initial teams, changing HP/PP and turn events. Editing a saved SQL team later does not rewrite an earlier battle snapshot.'],
    ['Revision','Revision is the saved battle’s update counter, not its turn count. The server accepts an action only against the matching active revision, so two stale requests cannot both resolve it.'],
    ['Manual versus Auto Battle','Manual and Auto use the same rules. Auto chooses the attack with the best estimated accuracy-adjusted damage and healthy replacements. Leaving the page, hiding the tab or reloading pauses Auto; an action already sent can finish.'],
    ['Winning rewards','The battle outcome and reward roll are saved before the case animation. SQL records the awarded owned copy using the battle UUID as a unique reference. SQL delivery and MongoDB confirmation are separate operations; a pending delivery can be retried by reopening the battle. Reopening an already delivered reward keeps the same copy.']
  ]}
};
function featureHelp(name) {
  const help=FEATURE_HELP[name];
  return `<details class="feature-help spacer"><summary>${esc(help.title)}</summary><dl>${help.items.map(([label,description])=>`<div><dt>${esc(label)}</dt><dd>${esc(description)}</dd></div>`).join('')}</dl></details>`;
}
function rulesLabel(version) {
  if(version==='prototype-1')return 'V1 · original damage (prototype-1)';
  if(version==='prototype-2')return 'V2 · 40% damage cap (prototype-2)';
  return `Other saved version (${version || 'not recorded'})`;
}
function rulesDescription(version) {
  if(version==='prototype-1')return 'Original saved battles use the damage formula without a per-hit maximum-HP cap.';
  if(version==='prototype-2')return 'Each hit is capped at 40% of the defender’s maximum HP, rounded down (minimum 1 for a non-immune hit). The cap applies to both sides; a weakened target can still faint.';
  return 'This saved version is not described by the V1/V2 guide. Its results remain separate under its stored rules identifier.';
}
function analyticsRulesGuide(version) {
  return `<div class="rules-filter-note" role="note"><p><strong>Selected rules: ${esc(rulesLabel(version))}.</strong> ${esc(rulesDescription(version))}</p><p><strong>Filter scope:</strong> these choices affect Battle strategy evidence and 1v1 matchups only. Difficulty controls the opponent and reward odds; rules version controls damage mechanics. Applying filters selects saved records and does not change any battle.</p><details class="feature-help"><summary>Why keep V1 and V2 separate?</summary><p>V1 (<code>prototype-1</code>) is the original uncapped damage formula. V2 (<code>prototype-2</code>) adds the 40% maximum-HP damage cap to reduce immediate knockouts. New battles use V2; earlier records keep their original rules. A V1 option appears only when this trainer has V1 records. Compare results within the same rules version and difficulty because mechanics and opponents affect outcomes.</p></details></div>`;
}
function savedBattleReference(battle) {
  const reward=battle.reward;
  return `<section class="saved-battle-reference" aria-label="Saved battle and reward references"><h3>Saved battle and reward references</h3><dl><div><dt>Battle UUID</dt><dd><code>${esc(battle._id)}</code></dd></div><div><dt>Rules version</dt><dd>${esc(rulesLabel(battle.rules_version))}</dd></div><div><dt>Saved revision</dt><dd>${esc(battle.revision ?? 'Not recorded')}</dd></div>${reward?`<div><dt>Awarded copy</dt><dd>${reward.delivered&&reward.owned_id!=null?`Owned #${esc(reward.owned_id)}`:'Delivery pending'}</dd></div>`:''}</dl><p class="note">The battle UUID identifies the MongoDB battle. For a delivered reward, SQL <code>battle_rewards.battle_id</code> uses the same UUID and <code>owned_id</code> points to the collection’s Owned #. These are saved references for checking the linked records.</p></section>`;
}
const pokemonCost = p => Math.ceil(stats.reduce((sum,s)=>sum+p[s],0)/100);
const draftCost = () => state.draft.members.reduce((sum,m)=>sum+pokemonCost(m.pokemon),0);
const moveHitChance = move => move.id===0||move.accuracy===null?100:
  typeof move.accuracy==='number'&&move.accuracy>=0&&move.accuracy<=100?move.accuracy:null;
const moveMissLabel = move => moveHitChance(move)===null?'Unknown':`${100-moveHitChance(move)}%`;
const moveChanceText = move => moveHitChance(move)===null?'Accuracy unavailable':`Hit ${moveHitChance(move)}% · Miss ${moveMissLabel(move)}`;
const REWARD_COLORS = {common:'#a9bbd0',uncommon:'#65ca8c',rare:'#b794ff',legendary:'#ffd447'};
const REWARD_ODDS = JSON.parse(document.querySelector('#reward-odds').textContent);
const percent = value => `${Math.round(value*100)}%`;
const rewardOddsText = odds => `Common ${percent(odds.rarities.common)} · Uncommon ${percent(odds.rarities.uncommon)} · Rare ${percent(odds.rarities.rare)} · Legendary/Mythical ${percent(odds.rarities.legendary)}. Shiny: ${percent(odds.shiny_chance)}, independent of rarity.`;
const revealedRewards = new Set();
let rewardSpin = null;
let autoBattle = null;
let battleRequestPending = false;

function updateBattleControls() {
  const active=state.battle?.status==='active',automatic=autoBattle!==null;
  const start=document.querySelector('[data-action="auto-battle"]'),pause=document.querySelector('[data-action="pause-auto"]');
  if(start){start.hidden=automatic;start.disabled=!active||battleRequestPending;}
  if(pause){pause.hidden=!automatic;pause.disabled=false;}
  const status=document.querySelector('#auto-status');
  if(status)status.textContent=automatic?'Auto Battle is running':battleRequestPending?'Finishing the current turn…':'Manual control';
  document.querySelectorAll('[data-battle-action]').forEach(control=>{
    control.disabled=automatic||battleRequestPending||control.dataset.unavailable==='true';
  });
}
function stopAutoBattle() {
  if(autoBattle){clearTimeout(autoBattle.timer);autoBattle=null;}
  updateBattleControls();
}
function startAutoBattle() {
  if(autoBattle||battleRequestPending||state.view!=='battle'||state.battle?.status!=='active'||document.hidden)return;
  const session={battleId:state.battle._id,trainerId:state.trainer.id,timer:null};autoBattle=session;
  updateBattleControls();
  const schedule=()=>{session.timer=setTimeout(async()=>{
    if(autoBattle!==session)return;
    if(state.view!=='battle'||state.battle?._id!==session.battleId||state.trainer?.id!==session.trainerId||document.hidden||state.battle.status!=='active'){
      stopAutoBattle();return;
    }
    if(state.busy){schedule();return;}
    try {await submitBattleAction({kind:'auto'});}
    catch(error){stopAutoBattle();notice(error.message);return;}
    if(autoBattle===session&&state.battle.status==='active')schedule();
    else if(autoBattle===session)stopAutoBattle();
  },700);};
  schedule();
}
async function submitBattleAction(action) {
  if(battleRequestPending||state.battle?.status!=='active')return;
  const previous=state.battle,trainerId=state.trainer?.id;
  const sameBattle=()=>state.battle?._id===previous._id&&state.trainer?.id===trainerId;
  battleRequestPending=true;updateBattleControls();
  try {
    const next=await api(`/battles/${previous._id}/actions`,'POST',{revision:previous.revision,action});
    if(!sameBattle())return;
    state.battle=next;
    if(state.view==='battle')await window.battleEffects.play(previous,next,{
      renderFighter:(side,snapshot)=>fighter(snapshot,side==='player'?'YOUR PARTNER':'OPPONENT',side==='player'),
      colorForType:typeColor,effectivenessText,eventText
    });
  } catch(error) {
    stopAutoBattle();
    // A response may fail after a turn committed. Read back instead of retrying it.
    try {const saved=await api(`/battles/${previous._id}`);if(sameBattle())state.battle=saved;} catch { /* A later refresh can recover. */ }
    throw error;
  } finally {
    battleRequestPending=false;
    if(sameBattle()&&state.view==='battle')drawBattle();
  }
}

function rewardKey(battle) {return `pokedb:reward:${battle.trainer_id}:${battle._id}`;}
function rewardWasRevealed(battle) {
  const key=rewardKey(battle);
  try {return revealedRewards.has(key)||localStorage.getItem(key)==='revealed';}
  catch {return revealedRewards.has(key);}
}
function cancelRewardSpin() {
  const spin=rewardSpin;rewardSpin=null;
  if(spin?.animation)spin.animation.cancel();
}
function rewardCase(battle) {
  const reward=battle.reward,revealed=rewardWasRevealed(battle);
  return `<section class="reward-case ${reward.is_shiny?'is-shiny':''}" data-battle="${esc(battle._id)}" style="--reward-color:${REWARD_COLORS[reward.rarity]||REWARD_COLORS.common}">
    <span class="eyebrow">VICTORY DROP</span>
    <div class="case-sealed" ${revealed?'hidden':''}><div class="case-ball" aria-hidden="true"></div><h3>A new partner is inside.</h3><p>One victory. One Pokémon. Open your reward case.</p>${button('Open reward case','open-reward','','primary')}</div>
    <div class="case-opening" hidden><h3>Revealing your saved reward…</h3><div class="case-window" aria-hidden="true"><div class="case-reel"></div><span class="case-pointer"></span></div><p class="case-status" role="status">Opening your case…</p>${button('Skip animation','skip-reward','','case-skip')}</div>
    <div class="case-revealed" ${revealed?'':'hidden'}><div class="case-burst" aria-hidden="true">✦ <span>✧</span> ✦</div>${shinyBadge(reward)}<span class="case-rarity">${esc(reward.rarity)} partner</span><div class="reward">${img({id:reward.pokemon_id,name:reward.name,is_shiny:reward.is_shiny})}<div><h3 class="reward-name" tabindex="-1">${reward.is_shiny?'Shiny ':''}${esc(title(reward.name))}</h3><p class="case-delivery">${reward.delivered?'Added to your collection.':'Reward delivery pending; reopen this battle from history to retry.'}</p>${reward.selection_note?`<p class="case-delivery">${esc(reward.selection_note)}</p>`:''}</div></div></div>
    <p class="case-odds">This animation reveals the reward saved for this win. Reopening a delivered reward does not roll a new one.<br>Base reward odds: ${rewardOddsText(reward.odds||REWARD_ODDS.easy)} Full variants are rerolled during delivery; tiers adjust if a tier is full.</p>
  </section>`;
}
function finishRewardCase() {
  const spin=rewardSpin;if(!spin)return;
  rewardSpin=null;
  spin.animation?.cancel();
  if(!spin.element.isConnected)return;
  revealedRewards.add(rewardKey(spin.battle));
  try {localStorage.setItem(rewardKey(spin.battle),'revealed');} catch { /* In-memory reveal still works. */ }
  spin.element.querySelector('.case-sealed').hidden=true;
  spin.element.querySelector('.case-opening').hidden=true;
  const revealed=spin.element.querySelector('.case-revealed');revealed.hidden=false;
  revealed.setAttribute('role','status');
  revealed.querySelector('.reward-name').focus({preventScroll:true});
}
async function openRewardCase() {
  const battle=state.battle,element=document.querySelector('.reward-case');
  if(!element||battle?.status!=='win'||!battle.reward||rewardSpin||rewardWasRevealed(battle))return;
  const spin={battle,element,animation:null};rewardSpin=spin;
  element.querySelector('.case-sealed').hidden=true;
  element.querySelector('.case-opening').hidden=false;
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){finishRewardCase();return;}
  let pool=[];
  try {pool=(await api('/pokemon')).pokemon;} catch { /* Reveal still works when catalogue loading fails. */ }
  if(rewardSpin!==spin||!element.isConnected)return;
  const reel=element.querySelector('.case-reel'),viewport=element.querySelector('.case-window');
  const winnerIndex=28;
  const cards=Array.from({length:34},()=>pool.length?pool[Math.floor(Math.random()*pool.length)]:null);
  // The winner always comes from the persisted server reward. Other cards are decorative.
  cards[winnerIndex]={id:battle.reward.pokemon_id,name:battle.reward.name,rarity:battle.reward.rarity,is_shiny:battle.reward.is_shiny};
  reel.innerHTML=cards.map((p,i)=>`<div class="case-card ${p?.is_shiny?'is-shiny':''}" ${i===winnerIndex?'data-winner="true"':''} style="--card-color:${REWARD_COLORS[p?.rarity]||REWARD_COLORS.common}">${p?img(p):'<span class="ball" aria-hidden="true"></span>'}<strong>${p?esc(title(p.name)):'Mystery partner'}</strong><small>${p?`${p.is_shiny?'✦ Shiny · ':''}${esc(p.rarity)}`:'Pokémon'}</small></div>`).join('');
  // Make later sprites load before entering the viewport during the animation.
  reel.querySelectorAll('img').forEach(image=>{image.loading='eager';});
  const winner=reel.children[winnerIndex];
  const start=viewport.clientWidth/2-reel.children[0].offsetWidth/2;
  const end=viewport.clientWidth/2-winner.offsetLeft-winner.offsetWidth/2;
  if(typeof reel.animate!=='function'){finishRewardCase();return;}
  spin.animation=reel.animate([{transform:`translateX(${start}px)`},{transform:`translateX(${end}px)`}],
    {duration:4600,easing:'cubic-bezier(.12,.72,.12,1)',fill:'forwards'});
  spin.animation.finished.then(()=>{if(rewardSpin===spin)finishRewardCase();}).catch(()=>{});
  element.querySelector('[data-action="skip-reward"]').focus({preventScroll:true});
}

// The reference catalogue is shared by profiles and fixed for this app session.
// Keep mutable teams, collections and battle evidence live on every request.
const catalogueResponses = new Map();
async function api(path, method='GET', body) {
  const cacheable=method==='GET' && /^\/pokemon(?:\/\d+)?(?:\?.*)?$/.test(path);
  if(cacheable && catalogueResponses.has(path))return catalogueResponses.get(path);
  const response = await fetch(`/api${path}`, {method, headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf}, body:body===undefined?undefined:JSON.stringify(body)});
  const contentType=(response.headers.get('Content-Type')||'').split(';')[0].trim().toLowerCase();
  if(contentType!=='application/json'&&!contentType.endsWith('+json')) {
    const next=response.status===404?'Restart the Python app to load the latest routes, then refresh this page.':'Check the app terminal for the server error, then refresh this page.';
    throw new Error(`API /api${path.split('?')[0]} returned a non-JSON response (HTTP ${response.status}). ${next}`);
  }
  let result;
  try {result=await response.json();}
  catch {throw new Error(`API /api${path.split('?')[0]} returned invalid JSON (HTTP ${response.status}). Check the app terminal for details.`);}
  if (!response.ok) throw new Error(result?.error || `Request failed (${response.status})`);
  if(cacheable){
    catalogueResponses.set(path,result);
    if(catalogueResponses.size>20)catalogueResponses.delete(catalogueResponses.keys().next().value);
  }
  return result;
}
function notice(message='') {const box=document.querySelector('#notice');box.textContent=message;box.hidden=!message;}
async function run(work) {
  if(state.busy) return;
  state.busy=true;main.setAttribute('aria-busy','true');main.classList.add('loading');dialog.classList.add('loading');notice();
  try {await work();} catch(error) {notice(error.message);}
  finally {state.busy=false;main.removeAttribute('aria-busy');main.classList.remove('loading');dialog.classList.remove('loading');}
}
function modal(content) {document.querySelector('#dialog-content').innerHTML=content;if(!dialog.open)dialog.showModal();}
async function refreshSession() {
  const result=await api('/session');Object.assign(state,result);
  document.querySelector('#profile-button').textContent=state.trainer ? `${state.trainer.name} ↗` : 'Choose trainer ↗';
}
function profilesModal() {
  modal(`<span class="eyebrow">YOUR TRAINER PROFILE</span><h2 id="dialog-title">Choose your trainer</h2><p class="note">Trainer profiles select a collection and battle history; they are not password-protected accounts. Profiles and data are shared by applications connected to the same databases. Choose your own demonstration profile and edit only its records.</p>
    <div class="profile-options">${state.profiles.map(p=>button(p.name,'select-profile',p.id)).join('')}</div>
    <form id="profile-form" class="form-row"><label>New trainer name<input name="name" maxlength="40" required autocomplete="nickname"></label><button class="primary">Create trainer</button></form>`);
}
function startersModal() {
  const starters=[{id:1,name:'bulbasaur',types:['grass','poison']},{id:4,name:'charmander',types:['fire']},{id:7,name:'squirtle',types:['water']}];
  modal(`<span class="eyebrow">EVERY ADVENTURE STARTS SOMEWHERE</span><h2 id="dialog-title">Choose your first partner.</h2><p class="note">One starter per trainer. Win battles to grow your collection.</p>
    <div class="starter-grid">${starters.map(p=>`<button class="poke-card" style="--type-color:${typeColor(p.types[0])}" data-action="starter" data-value="${p.id}">${img(p)}<h3>${p.name}</h3>${tags(p.types)}<small class="spacer">Choose ${p.name}</small></button>`).join('')}</div>`);
}
function needTrainer() {
  if(!state.trainer){main.innerHTML=heading('YOUR ADVENTURE','Start your Pokémon adventure.','Choose a trainer profile to build teams and battle.')+button('Choose trainer','profiles','','primary');return true;}
  if(!state.trainer.starter_chosen){main.innerHTML=heading('YOUR FIRST PARTNER','A new adventure awaits.','Choose your starter to unlock teams and battles.')+button('Choose a starter','starters','','primary');return true;}
  return false;
}
async function navigate(view) {
  stopAutoBattle();window.battleEffects.cancel();
  cancelRewardSpin();
  state.view=view;location.hash=view;
  document.querySelectorAll('[data-nav]').forEach(b=>{b.classList.toggle('active',b.dataset.nav===view);b.setAttribute('aria-current',b.dataset.nav===view?'page':'false');});
  if(view!=='pokedex' && needTrainer())return;
  const render={pokedex:renderPokedex,teams:renderTeams,analysis:renderAnalysis,battle:renderBattle,analytics:renderAnalytics}[view] || renderPokedex;
  await render();
}
async function renderPokedex(q='',type='') {
  const data=await api(`/pokemon?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type)}`);
  main.innerHTML=`<section class="hero"><div><span class="eyebrow">THE ORIGINAL 151 · A WORLD TO DISCOVER</span><h1>Know your Pokémon.<br>Find your next partner.</h1><p>Explore Kanto's first generation, discover their strengths, and build a team that's yours.</p></div><div class="hero-art">${img({id:4,name:'Charmander'})}${img({id:25,name:'Pikachu'})}${img({id:7,name:'Squirtle'})}<small>CHOOSE YOUR NEXT PARTNER</small></div></section>
    <p class="note">The Pokédex shows all supported species. Your collection contains only copies you own. Choose a trainer, select a starter and win battles to grow that collection.</p>${featureHelp('catalogue')}
    <form id="search-form" class="toolbar"><input aria-label="Search Pokémon" name="q" placeholder="Search by name or Pokédex number…" value="${esc(q)}"><select name="type" aria-label="Filter by type"><option value="">All types</option>${data.types.map(t=>`<option value="${esc(t.name)}" ${t.name===type?'selected':''}>${esc(title(t.name))}</option>`).join('')}</select><button class="quiet">Search</button><span class="count">${data.pokemon.length} Pokémon to discover</span></form>${databaseEvidence(DB_EVIDENCE.pokedex)}
    ${data.pokemon.length?`<section class="grid">${data.pokemon.map(p=>`<button class="poke-card" style="--type-color:${typeColor(p.types[0])}" data-action="pokemon" data-value="${p.id}"><span class="number">#${String(p.id).padStart(3,'0')}</span>${img(p)}<h3>${esc(title(p.name))}</h3>${tags(p.types)}</button>`).join('')}</section>`:empty('No Pokémon match your search.')}`;
}
async function pokemonModal(id) {
  const p=await api(`/pokemon/${id}`);
  modal(`<span class="eyebrow">POKÉDEX / #${String(p.id).padStart(3,'0')}</span>${img(p).replace('<img','<img class="sprite"')}<h2 id="dialog-title">${esc(title(p.name))}</h2>${tags(p.types)}<p>${esc(p.description)}</p><span class="badge">${p.rarity} reward tier</span>
    <h3 class="spacer">Base stats</h3><p class="note">Species base stats, before battle scaling: battle HP = 2 × base HP + 60; the other combat stats = base stat + 5. Reward tier describes the project’s drop category, not combat strength. Shiny appearance changes no stats.</p>${stats.map(s=>`<div class="stat-line"><span>${statLabel(s)}</span><strong>${p[s]}</strong><span class="bar"><i style="width:${Math.min(p[s]/255*100,100)}%"></i></span></div>`).join('')}
    <details class="rules spacer"><summary>Fixed move pool · ${p.moves.length} moves</summary><p class="note">Miss chance is based on move accuracy. An attack can hit but deal zero damage to an immune target. All supported moves use simplified single-hit damage. Status and secondary effects are omitted. ★ marks an approved project-specific move-pool exception.</p>${table(['Move','Type','Power','Hit chance','Miss chance','PP'],p.moves.map(m=>[`${esc(title(m.name))}${m.source==='project_override'?' ★':''}`,tags([m.type]),m.power,moveHitChance(m)===null?'Unknown':moveHitChance(m)+'%',moveMissLabel(m),m.pp]))}</details>`);
}
async function loadTeams() {
  const [owned,list]=await Promise.all([api('/collection'),api('/teams')]);state.collection=owned.pokemon;state.teams=list.teams;
}
async function renderTeams() {
  await loadTeams();
  if(!state.draft && state.teams.length)state.draft=await api(`/teams/${state.teams[0].id}`);
  if(!state.draft)state.draft={name:'My team',members:[]};
  drawTeams();
}
function drawTeams() {
  const draft=state.draft;
  const cost=draftCost();
  main.innerHTML=heading('BUILD SOMETHING YOURS','Collection & teams','Choose up to six partners, then pick four moves for each.')+
    `<section class="card spacer" aria-live="polite"><strong class="${cost>30?'weak':''}">Team budget: ${cost} / 30 points · ${30-cost} remaining</strong><p class="note">Each Pokémon costs its total base stats divided by 100, rounded up. ${cost>30?'Remove or replace a member before saving or starting a new battle.':'Save your team to apply changes.'}</p></section>`+featureHelp('teams')+databaseEvidence(DB_EVIDENCE.teams)+
    `<div class="toolbar"><label>Saved teams<select id="team-select"><option value="">New team</option>${state.teams.map(t=>`<option value="${t.id}" ${draft.id===t.id?'selected':''}>${esc(t.name)} · ${t.size}/6</option>`).join('')}</select></label>${button('New team','new-team')}${draft.id?button('Delete team','delete-team',draft.id,'danger'):''}<span class="count">${state.collection.length} Pokémon in your collection</span></div>
    <div class="two-col collection-layout"><section><form id="team-form"><div class="form-row card"><label>Team name<input id="team-name" value="${esc(draft.name)}" maxlength="60" required></label><button class="primary">Save team</button></div><div class="section-title"><h3>Active roster</h3><small>${draft.members.length} / 6 Pokémon</small></div>
    <div class="stack">${draft.members.length?draft.members.map((m,i)=>`<article class="member">${img(m.pokemon)}<div><div class="row between"><h3>${esc(title(m.pokemon.name))} ${shinyBadge(m.pokemon)} · ${pokemonCost(m.pokemon)} pts</h3><div>${i?button('↑','move-up',i,'quiet small'):''}${button('Remove','remove-member',i,'quiet small')}</div></div>${tags(m.pokemon.types)}<div class="move-picks">${[0,1,2,3].map(slot=>{const selected=m.pokemon.moves.find(move=>move.id===m.moves[slot]);return `<label>Move ${slot+1}<select data-member="${i}" data-slot="${slot}">${m.pokemon.moves.map(move=>`<option value="${move.id}" ${move.id===m.moves[slot]?'selected':''}>${esc(title(move.name))} · ${move.type} · ${move.power} power · ${moveMissLabel(move)} miss${move.source==='project_override'?' ★':''}</option>`).join('')}</select><small class="move-accuracy">${selected?moveChanceText(selected):'Choose a move'}</small></label>`;}).join('')}</div></div></article>`).join(''):empty('Add Pokémon from your collection to get started.')}</div></form><p class="note">Choose four distinct moves. Miss chance applies to each attack: 85% hit means 15% miss. ★ denotes a project-specific exception. Save your team before analysing it or starting a battle.</p></section>
    <aside class="card collection-panel"><h3>Your collection</h3><p class="note">Organised by Pokédex number, then normal/shiny variant. Non-legendary species allow six normal and six shiny copies each. Teams allow one of each legendary species, up to six members and 30 points.</p><div class="collection-list">${collectionGroups(cost)}</div></aside></div>`;
}
function collectionGroups(cost) {
  if(!state.collection.length)return '<p class="note collection-empty">Your collection is empty. Win battles to collect more partners.</p>';
  const groups=new Map();
  const sorted=state.collection.slice().sort((a,b)=>a.pokemon.id-b.pokemon.id||Number(Boolean(a.pokemon.is_shiny))-Number(Boolean(b.pokemon.is_shiny))||a.owned_id-b.owned_id);
  for(const owned of sorted){
    const id=owned.pokemon.id;if(!groups.has(id))groups.set(id,{pokemon:owned.pokemon,copies:[],normal:0,shiny:0});
    const group=groups.get(id);group.copies.push(owned);group[owned.pokemon.is_shiny?'shiny':'normal']++;
  }
  return [...groups.values()].map(group=>{
    const p=group.pokemon,limit=p.rarity==='legendary'?'':' / 6';
    return `<section class="collection-group" data-species-id="${p.id}"><div class="collection-group-heading"><h4>#${String(p.id).padStart(3,'0')} ${esc(title(p.name))}</h4><small>Normal ${group.normal}${limit} · Shiny ${group.shiny}${limit}${p.rarity==='legendary'?' · One per team':''}</small></div>${group.copies.map(o=>collectionCard(o,cost,o.pokemon.is_shiny?group.shiny:group.normal)).join('')}</section>`;
  }).join('');
}
function collectionCard(owned,cost,copies) {
  const p=owned.pokemon,inTeam=state.draft.members.some(m=>m.owned_id===owned.owned_id);
  const legendaryConflict=p.rarity==='legendary'&&state.draft.members.some(m=>m.pokemon.id===p.id);
  const full=state.draft.members.length>=6,overBudget=cost+pokemonCost(p)>30;
  const label=inTeam?'In team':legendaryConflict?'Legendary limit':full?'Team full':overBudget?'Over budget':'Add to team';
  const reason=inTeam?'Already in this team':legendaryConflict?'Only one of this legendary species is allowed per team':full?'Remove a team member before adding another':overBudget?'This Pokémon would exceed the 30-point team budget':'Add this owned Pokémon to the team';
  return `<article class="owned ${p.is_shiny?'is-shiny':''}" data-owned-id="${owned.owned_id}" style="--type-color:${typeColor(p.types[0])}">${img(p)}<div class="meta"><h4>${esc(title(p.name))} ${shinyBadge(p)}</h4>${tags(p.types)}<div class="owned-details"><span class="badge">${esc(p.rarity)}</span><strong>${pokemonCost(p)} pts</strong></div><small class="copy-count">${p.is_shiny?'Shiny':'Normal'} ${copies}${p.rarity==='legendary'?' owned':' / 6 copies'}</small></div><div class="owned-footer"><small>Owned #${owned.owned_id} · ${owned.source==='starter'?'Starter':'Reward'}</small><button class="quiet small" data-action="add-member" data-value="${owned.owned_id}" aria-label="${esc(`${label}: ${p.is_shiny?'Shiny ':''}${title(p.name)}, owned ${owned.owned_id}`)}" title="${esc(reason)}" ${inTeam||legendaryConflict||full||overBudget?'disabled':''}>${label}</button></div></article>`;
}
function rememberName(){const input=document.querySelector('#team-name');if(input&&state.draft)state.draft.name=input.value;}
function teamOptions(chosen) {return state.teams.map(t=>`<option value="${t.id}" ${t.id===Number(chosen)?'selected':''}>${esc(t.name)} · ${t.size}/6</option>`).join('');}
async function renderAnalysis(teamId) {
  state.teams=(await api('/teams')).teams;
  if(!state.teams.length){main.innerHTML=heading('KNOW YOUR STRENGTHS','Team analysis','Save a team to see its strengths and weaknesses.')+button('Build a team','go-teams','','primary');return;}
  teamId=teamId || state.teams[0].id;
  // Recommendations can finish independently; their failure should not hide analysis.
  const recommendation=api(`/teams/${teamId}/recommendations`).then(data=>({data}),error=>({error}));
  const a=await api(`/teams/${teamId}/analysis`);
  main.innerHTML=heading('KNOW YOUR STRENGTHS','Team analysis','Understand your roster before stepping into the arena.')+`<div class="toolbar"><label>Team<select id="analysis-team">${teamOptions(teamId)}</select></label></div>${databaseEvidence(DB_EVIDENCE.analysis)}
    <div class="metric-grid">${metric('Team size',a.stats.size)}${metric('Total base stats',stats.reduce((sum,s)=>sum+a.stats['total_'+s],0))}${metric('Average Speed',a.stats.average_speed.toFixed(1))}${metric('Types represented',a.distribution.length)}</div>
    ${featureHelp('analysis')}
    <div class="two-col"><section class="card"><h3>Defensive matchups</h3><p class="note">Number of members weak, resistant or immune to each attacking type. Both defensive types are combined.</p>${table(['Attacking type','Weak','Resistant','Immune'],a.matchups.map(r=>[tags([r.type]),`<span class="${r.weak?'weak':''}">${r.weak}</span>`,r.resistant,r.immune]))}${databaseEvidence(SECTION_EVIDENCE.defense)}</section>
    <div class="stack"><section class="card"><h3>Team statistics</h3>${table(['Stat','Total','Average'],stats.map(s=>[statLabel(s),a.stats['total_'+s],a.stats['average_'+s].toFixed(1)]))}${databaseEvidence(SECTION_EVIDENCE.statistics)}</section><section class="card"><h3>Type distribution</h3>${a.distribution.length?table(['Type','Members'],a.distribution.map(t=>[tags([t.name]),t.count])):'No members yet.'}${databaseEvidence(SECTION_EVIDENCE.distribution)}</section></div></div>
    <section class="card spacer"><h3>Offensive coverage</h3><p class="note">Best multiplier available from your selected moves against each single defending type. This is coverage, not a prediction of victory.</p><div class="tags">${a.coverage.map(c=>`<span class="type ${c.best_multiplier>1?'grass':''}">${c.type} · ${c.best_multiplier}×</span>`).join('')}</div>${databaseEvidence(SECTION_EVIDENCE.coverage)}</section>
    <section class="card spacer" id="recommendations" aria-busy="true"><h3>Recommended partners</h3><p role="status">Finding partners for this team…</p>${databaseEvidence(SECTION_EVIDENCE.recommendations)}</section>`;
  const panel=document.querySelector('#recommendations');
  recommendation.then(({data,error})=>{
    // An earlier response must never overwrite another team's screen.
    if(document.querySelector('#recommendations')!==panel)return;
    panel.setAttribute('aria-busy','false');
    panel.innerHTML=error?`<h3>Recommended partners</h3><p class="note">${esc(error.message)}</p>${databaseEvidence(SECTION_EVIDENCE.recommendations)}`:recommendationsContent(a,data,teamId);
  });
}
function recommendationsContent(a,r,teamId) {
  const score=value=>value===null||value===undefined?'New team':Number(value).toFixed(2);
  return `<div class="row between"><div><h3>Recommended partners</h3><p class="note">MySQL ranks eligible owned Pokémon by lower exposure, better coverage and cost.</p></div><span class="badge">Budget ${a.budget.total} / ${a.budget.limit}</span></div>
    <div class="recommendation-grid">${r.suggestions.length?r.suggestions.map(s=>{
      const h=r.history.find(h=>h._id===s.pokemon_id);
      const improved=Object.keys(s.before.weaknesses||{}).filter(type=>(s.after.weaknesses[type]??Infinity)<s.before.weaknesses[type]-1e-9);
      const added=(s.after.covered_types||[]).filter(type=>!(s.before.covered_types||[]).includes(type));
      const action=s.replace_owned_id?`Replace ${esc(title(s.replace_name))} with`:'Add';
      return `<article class="recommendation-card" style="--type-color:${typeColor(s.types?.[0]||s.suggested_moves[0]?.type)}"><div class="row between"><h4>${action} ${esc(title(s.name))}</h4><span class="badge">Owned #${s.owned_id}</span></div>${tags(s.types||[])}
        <div class="recommendation-scores"><span>Exposure<strong>${score(s.before.exposure)} → ${score(s.after.exposure)}</strong></span><span>Coverage<strong>${s.before.coverage} → ${s.after.coverage} / 18</strong></span><span>Team cost<strong>${s.budget.total} / ${s.budget.limit}</strong></span></div>
        ${improved.length?`<div class="recommendation-types"><b>Less weak to</b>${tags(improved)}</div>`:''}
        ${added.length?`<div class="recommendation-types"><b>New coverage</b>${tags(added)}</div>`:''}
        <div class="recommendation-moves"><b>Moves</b>${s.suggested_moves.map(m=>`<span class="recommendation-move"><span class="type ${esc(m.type)}">${esc(title(m.type))}</span>${esc(title(m.name))}</span>`).join('')}</div>
        <p class="note recommendation-history">${h?`${h.battles} matching species appearances · ${h.wins}W ${h.losses}L ${h.draws}D`:'No matching battle history yet.'}</p></article>`;
    }).join(''):'<p>No eligible improvement is available from this collection. Suggestions need an unused owned copy that fits the budget and species limits and improves the score. Win battles to collect more options, or adjust the saved team and check again.</p>'}</div>
    <p class="note">Exposure is a weakness score: lower is better. Coverage counts super-effective options out of 18 types: higher is better. Arrows compare the current and proposed teams. Suggestions use default moves and never edit the team automatically.</p>${button('Review this team','edit-team',teamId)}${featureHelp('recommendations')}${databaseEvidence(SECTION_EVIDENCE.recommendations)}`;
}
function predictionPanel(b) {
  const p=b.prediction;
  if(!p)return '<section class="card"><h3>Pre-battle prediction</h3><p class="note">This older battle has no saved prediction.</p></section>';
  const h=p.history;
  return `<section class="card" id="prediction"><h3>Pre-battle prediction: ${esc(title(p.label))}</h3><p class="note">Saved before the first turn; this assessment stays fixed.</p><ul>${p.reasons.map(reason=>`<li>${esc(reason)}</li>`).join('')}</ul><p class="note">${esc(p.note)}</p><p>${h.battles} prior comparable battles: ${h.wins} wins, ${h.losses} losses, ${h.draws} draws.</p><p class="note">${esc(h.note)} ${h.battles<10?'Historical evidence is limited.':''}</p>${b.budget?`<p class="note">Starting team cost: ${b.budget.total} / ${b.budget.limit} points.</p>`:''}</section>`;
}
const rules = (version='prototype-2') => `<details class="feature-help spacer"><summary>How this battle works</summary><p><strong>${esc(rulesLabel(version))}.</strong> ${esc(rulesDescription(version))} These are simplified project mechanics.</p><dl>
  <div><dt>Stats and damage</dt><dd>Battle HP = 2 × base HP + 60; other combat stats = base stat + 5. Physical moves use Attack/Defense; special moves use Special Attack/Special Defense. A move matching the attacker’s type gets a 1.5× same-type attack bonus (STAB). Defender type multipliers combine, then a random factor from 0.85 to 1.0 applies.</dd></div>
  <div><dt>Damage formula</dt><dd><code>floor((22 × power × attack / defense / 50 + 2) × STAB × type factor × random factor)</code>. Immunity causes zero damage; other hits cause at least 1. V2 then applies its maximum-HP cap; actual damage cannot exceed the target’s remaining HP.</dd></div>
  <div><dt>Turns, accuracy and PP</dt><dd>Move priority acts first, then Speed, with a random tie break. Accuracy is checked for each attempted move; PP (remaining uses) decreases even on a miss. A fainted Pokémon loses its queued action. When all move PP is exhausted, Fallback Strike is a neutral 50-power physical attack with recoil equal to one quarter of damage dealt, minimum 1.</dd></div>
  <div><dt>Switching and results</dt><dd>Voluntary switching uses your turn and happens before the opponent attacks. Replacing a fainted member is free. Defeating every opponent wins; losing all your members loses. Simultaneous defeat or 200 completed turns is a draw. Forfeiting counts as a loss. Only wins grant rewards; HP/PP reset for each new battle.</dd></div>
  <div><dt>Simplifications</dt><dd>Supported moves are single-target, single-hit attacks. Status effects, secondary effects, abilities, items and critical hits are omitted. The opponent chooses its move without seeing your next action. Auto Battle uses these same rules.</dd></div>
  </dl>${featureHelp('difficulty')}</details>`;
async function renderBattle() {
  if(state.battle){state.battle=await api(`/battles/${state.battle._id}`);drawBattle();return;}
  const history=await api('/battles');const active=history.battles.find(b=>b.status==='active');
  if(active){state.battle=await api(`/battles/${active._id}`);drawBattle();return;}
  await loadTeams();
  const lastTeam=history.battles.find(b=>state.teams.some(t=>t.id===b.team_id&&t.size>0))?.team_id;
  const chosenTeam=lastTeam??state.teams.find(t=>t.size>0)?.id;
  main.innerHTML=heading('PUT YOUR STRATEGY TO WORK','Battle arena','A new opponent, matched to your team. One decision at a time.')+
    `<section class="card"><h2>Ready your team.</h2><form id="battle-form"><label>Choose a saved team<select name="team_id" required><option value="">Select a team</option>${teamOptions(chosenTeam)}</select></label><div class="difficulty-options">${[['easy','A gentler challenge'],['medium','Test your balance'],['hard','Make every move count']].map(([d,t])=>`<label><span><input type="radio" name="difficulty" value="${d}" ${d==='medium'?'checked':''}> ${title(d)}</span><small>${t}<br>${percent(REWARD_ODDS[d].shiny_chance)} shiny · ${percent(REWARD_ODDS[d].rarities.legendary)} legendary</small></label>`).join('')}</div><button class="primary" ${state.teams.some(t=>t.size>0)?'':'disabled'}>Start battle →</button></form><p class="note">Opponents match your team size. Difficulty adjusts target strength, matchups and move choices; it does not guarantee an outcome.</p>${rules()}</section>${databaseEvidence(DB_EVIDENCE.battle)}
    <section class="card spacer"><h3>A new partner with every win.</h3>${table(['Difficulty','Common','Uncommon','Rare','Legendary / Mythical','Shiny'],Object.entries(REWARD_ODDS).map(([difficulty,odds])=>[title(difficulty),...['common','uncommon','rare','legendary'].map(tier=>percent(odds.rarities[tier])),percent(odds.shiny_chance)]))}<p class="note">Base rarity odds sum to 100% per difficulty. Shiny is a separate, independent roll. Non-legendary species allow six normal and six shiny copies each; full variants are rerolled and rarity odds adjust if a tier is full. Rewards enter your collection automatically.</p></section>`;
}
function fighter(side,label,back) {const p=side.members[side.active];return `<div class="fighter ${p.is_shiny?'is-shiny':''} ${p.hp<=0?'is-fainted':''}" data-side="${back?'player':'opponent'}" data-slot="${side.active}"><div class="sprite-stage"><span class="fighter-shadow" aria-hidden="true"></span><img class="battle-sprite" src="${sprite(p.id,back,p.is_shiny)}" alt="${p.is_shiny?'Shiny ':''}${esc(title(p.name))}" loading="eager"></div><div class="fighter-info"><span class="eyebrow">${label}</span><h3>${esc(title(p.name))} ${shinyBadge(p)}</h3>${tags(p.types)}<div class="hp" role="progressbar" aria-label="${esc(title(p.name))} HP" aria-valuenow="${p.hp}" aria-valuemin="0" aria-valuemax="${p.max_hp}"><i style="width:${p.hp/p.max_hp*100}%"></i></div><small class="hp-text">${p.hp} / ${p.max_hp} HP</small><div class="team-dots" aria-label="${side.members.filter(m=>m.hp>0).length} healthy Pokémon">${side.members.map(m=>m.hp>0?'●':'○').join(' ')}</div></div></div>`;}
function eventText(e) {
  const side=e.side==='player'?'Your':'Opponent’s';
  if(e.kind==='move')return `${side} ${title(e.name)} used ${title(e.move)}. ${e.hit?`${e.damage} damage.${effectivenessText(e)?' '+effectivenessText(e):''}`:'It missed.'}${e.recoil?` ${e.recoil} recoil damage.`:''}`;
  if(e.kind==='switch')return `${side} ${title(e.name)} entered the battle.`;
  if(e.kind==='faint')return `${side} ${title(e.name)} fainted.`;
  return 'You forfeited the battle.';
}
function effectivenessText(event) {
  if(!event.hit||typeof event.effectiveness!=='number')return '';
  if(event.effectiveness===0)return 'No effect.';
  if(event.effectiveness>1)return 'Super effective!';
  if(event.effectiveness<1)return 'Not very effective.';
  return '';
}
function drawBattle() {
  cancelRewardSpin();
  const b=state.battle,p=b.player.members[b.player.active],active=b.status==='active';
  if(!active)stopAutoBattle();
  const lastEvent=b.turns.at(-1)?.events.at(-1);
  const exhausted=p.moves.every(m=>m.remaining_pp===0);
  const choices=exhausted?[{id:0,name:'fallback-strike',type:'neutral',remaining_pp:'∞',power:50,accuracy:null}]:p.moves;
  main.innerHTML=heading('THE BATTLE IS YOURS','Battle arena',`${title(b.difficulty)} difficulty · ${b.team_name}`)+
    `<div class="battle-layout ${active?'':'battle-finished'}"><section class="battle-stage"><div class="arena"><div class="arena-header"><span>${b.status==='active'?'LIVE BATTLE':b.status.toUpperCase()}</span><span>${b.rules_version==='prototype-1'?'V1':'V2'} · TURN ${b.turn_count}</span></div><div class="fighters">${fighter(b.player,'YOUR PARTNER',true)}<div class="versus">VS</div>${fighter(b.opponent,'OPPONENT',false)}</div><div class="battle-effects" aria-hidden="true"></div></div><p class="battle-message" role="status" aria-live="polite" aria-atomic="true" data-kind="${esc(lastEvent?.kind||'ready')}">${lastEvent?esc(eventText(lastEvent)):'Choose a move or Auto Battle to begin.'}</p></section>
    ${active?'<aside class="battle-controls card" aria-label="Battle controls">':''}
    ${active?`<section class="auto-controls"><div class="row between"><div><span class="eyebrow">BATTLE CONTROL</span><h3 id="auto-status" aria-live="polite">Manual control</h3></div><div class="row">${button('Auto Battle','auto-battle','','primary')}${button('Pause Auto Battle','pause-auto')}</div></div><p class="note">Auto Battle chooses attacks and healthy replacements. Pause to take over. Leaving this screen, hiding this tab or reloading pauses automation; a turn already submitted will finish.</p></section>`:''}
    ${active?`<h3 class="spacer">${p.hp<=0?'Choose a healthy replacement.':'What will you do?'}</h3><div class="actions">${choices.map(m=>`<button class="move-button" style="--type-color:${typeColor(m.type)}" data-action="attack" data-value="${m.id}" ${p.hp<=0||m.remaining_pp===0?'disabled':''}><strong>${esc(title(m.name))}</strong><div class="row">${tags([m.type])}<small>${m.power} power · ${m.remaining_pp} PP</small></div><span class="move-accuracy">${moveChanceText(m)}</span></button>`).join('')}</div><div class="section-title"><h4>Switch Pokémon</h4><small>${p.hp<=0?'Free replacement':'Uses your turn'}</small></div><div class="row">${b.player.members.map((m,i)=>`<button class="quiet small" data-action="switch" data-value="${i}" ${m.hp<=0||i===b.player.active?'disabled':''}>${m.is_shiny?'Shiny ':''}${esc(title(m.name))} · ${m.hp} HP</button>`).join('')}</div><div class="spacer">${button('Forfeit battle','forfeit','','danger small')}</div></aside>`:
    `<section class="result"><h2>${b.status==='win'?'Victory. A new partner awaits!':b.status==='loss'?'A lesson for the next battle.':'An evenly matched battle.'}</h2>${b.status==='win'&&b.reward?rewardCase(b):`<p class="note">${b.turn_count} turns played. Adjust your team or try another difficulty.</p>`}${savedBattleReference(b)}<div class="row spacer">${button('Battle again','new-battle','','primary')}${button('View collection','go-teams')}</div></section>`}</div><div class="section-title"><h2>Battle analysis</h2></div>
    <section class="battle-analysis" aria-label="Battle analysis">${predictionPanel(b)}<section class="card"><h3>Battle log</h3><ol class="battle-log">${b.turns.length?b.turns.slice().reverse().map(t=>`<li><span class="turn-label">${t.kind==='turn'?'TURN '+t.number:title(t.kind).toUpperCase()} · ${t.controller==='auto'?'AUTO':'MANUAL'}</span>${t.decision?`<p class="auto-reason">${esc(t.decision)}</p>`:'<br>'}${t.events.map(e=>esc(eventText(e))).join('<br>')}</li>`).join(''):'<li>Your opponent is ready. Choose your first move.</li>'}</ol></section><section class="card"><h4>Opponent matching</h4><p class="note">Your strength: ${b.generation.player_strength}<br>Target: ${Math.round(b.generation.target_strength)}<br>Opponent strength: ${b.generation.actual_strength}</p><small>Strength = total base stats across the team.</small></section></section>${databaseEvidence(DB_EVIDENCE.battle)}${rules(b.rules_version)}`;
  main.insertAdjacentHTML('beforeend',featureHelp('prediction')+featureHelp('persistence'));
  document.querySelectorAll('[data-action="attack"],[data-action="switch"],[data-action="forfeit"]').forEach(control=>{
    control.dataset.battleAction='true';control.dataset.unavailable=String(control.disabled);
  });
  updateBattleControls();
}
async function renderAnalytics(rulesVersion='',difficulty='') {
  const previousMatchup=document.querySelector('#matchup-form');
  const matchupIds=previousMatchup?new FormData(previousMatchup):null;
  const filters=new URLSearchParams({difficulty});if(rulesVersion)filters.set('rules_version',rulesVersion);
  const [a,h,strategy]=await Promise.all([api('/analytics'),api('/battles'),api(`/analytics/strategy?${filters}`)]);const s=a.summary;
  main.innerHTML=heading('EVERY BATTLE TELLS A STORY','Battle analytics','Look back, find patterns, and make your next team stronger.')+databaseEvidence(DB_EVIDENCE.analytics)+
    `<p class="note"><strong>Overview scope:</strong> these totals and the difficulty, move and species tables cover all completed battles for this trainer, across rules versions and difficulties. The filters below apply only to Battle strategy evidence and 1v1 matchups.</p>${featureHelp('analytics')}`+
    `<div class="metric-grid">${metric('Completed battles',s.battles)}${metric('Win rate',s.battles?(s.wins/s.battles*100).toFixed(1)+'%':'—')}${metric('Average turns',Number(s.average_turns||0).toFixed(1))}${metric('Average duration',Math.round(s.average_seconds||0)+'s')}</div>
    <p class="note">Win rate = wins ÷ all completed battles, including draws and forfeits. Duration includes thinking time. Active battles are excluded.</p>${databaseEvidence(SECTION_EVIDENCE.summary)}
    <div class="two-col"><section class="card"><h3>Results by difficulty</h3>${a.difficulty.length?table(['Difficulty','Wins','Losses','Draws','Battles'],a.difficulty.map(d=>[esc(d._id),d.wins,d.losses,d.draws,d.battles])):empty('Finish your first battle to see results.')}${databaseEvidence(SECTION_EVIDENCE.difficulty)}</section><section class="card"><h3>Most-used moves</h3>${a.moves.length?table(['Move','Uses'],a.moves.map(m=>[esc(title(m.name)),m.uses])):'<p class="note">Your executed moves will appear here, including misses.</p>'}${databaseEvidence(SECTION_EVIDENCE.moves)}</section></div>
    <section class="card spacer"><h3>Pokémon performance</h3><p class="note">Appearances count completed battles containing the species, once per battle. Win rate describes the team result, not individual knockouts.</p>${a.pokemon.length?table(['Pokémon','Appearances','Wins','Win rate'],a.pokemon.map(p=>[esc(title(p.name)),p.appearances,p.wins,(p.wins/p.appearances*100).toFixed(1)+'%'])):empty('No completed battles yet.')}${databaseEvidence(SECTION_EVIDENCE.performance)}</section>
    <section class="card spacer" id="strategy-evidence"><h3>Battle strategy evidence</h3>
    <form id="strategy-form" class="toolbar"><label>Battle rules version<select name="rules_version">${strategy.rules_versions.map(v=>`<option value="${esc(v)}" ${v===strategy.rules_version?'selected':''}>${esc(rulesLabel(v))}</option>`).join('')}</select></label><label>Difficulty<select name="difficulty"><option value="">All difficulties</option>${['easy','medium','hard'].map(d=>`<option value="${d}" ${d===strategy.difficulty?'selected':''}>${title(d)}</option>`).join('')}</select></label><button class="quiet">Apply filters</button></form>${analyticsRulesGuide(strategy.rules_version)}
    <p><strong>${strategy.battles} completed battles</strong> under these filters. ${strategy.battles<10?'Small sample: treat patterns cautiously.':''}</p><p class="note">${esc(strategy.note)}</p>
    <h4>Damage per attempted move</h4><p class="note">Observed miss rate is misses divided by attempted attacks in these filtered battles; it can differ from a move's listed miss chance. Hits against immune targets count as hits.</p>${strategy.moves.length?table(['Move','Attempts','Hit rate','Miss rate','Total damage','Damage / attempt'],strategy.moves.map(m=>[esc(title(m.name)),m.attempts,(m.hit_rate*100).toFixed(1)+'%',((1-m.hit_rate)*100).toFixed(1)+'%',m.damage,m.damage_per_attempt.toFixed(1)])):'<p class="note">No player attacks in the selected battles yet.</p>'}
    ${databaseEvidence(SECTION_EVIDENCE.damage)}<h4 class="spacer">Does repeating one move correlate with wins?</h4><p class="note">Only battles with at least ${strategy.min_attempts} player attacks. High repetition means one move accounts for at least ${strategy.dominant_share*100}% of attacks. Compare rows within the same difficulty and team size; the battle count is the sample size.</p>
    ${strategy.repetition.length?table(['Difficulty','Team size','Pattern','Battles','Wins / losses / draws','Win rate','Average top-move share'],strategy.repetition.map(r=>[esc(r._id.difficulty),r._id.team_size,esc(r._id.pattern),`${r.battles}${r.battles<10?' (small sample)':''}`,`${r.wins} / ${r.losses} / ${r.draws}`,(r.wins/r.battles*100).toFixed(1)+'%',(r.average_top_share*100).toFixed(1)+'%'])):'<p class="note">No battles with enough attempted moves under these filters.</p>'}
    ${databaseEvidence(SECTION_EVIDENCE.repetition)}<div class="spacer" id="prediction-results"><h4>Predictions and actual outcomes</h4><p class="note">Same rules/difficulty filters as above; forfeits and missing predictions excluded. Favoured + win and disadvantaged + loss count as correct directional calls. Draws and evenly matched labels are shown separately. These results do not establish a calibrated win probability.</p>${predictionResults(strategy.predictions.map(r=>({...r,_id:{...r._id,rules:strategy.rules_version}})))}${featureHelp('prediction')}${databaseEvidence(SECTION_EVIDENCE.predictions)}</div></section>
    <section class="card spacer" id="matchup-evidence"><h3>1v1 matchups from your battles</h3><p>Loading your battle matchups…</p></section>
    <section class="card spacer"><h3>Battle history</h3><p class="note">Your latest 50 battles, including active battles, across all rules and difficulties. The strategy filters do not change this list. Review shows saved results and rewards; Resume continues an active battle.</p>${h.battles.length?table(['Team','Difficulty','Result','Turns','Started',''],h.battles.map(b=>[esc(b.team_name),esc(b.difficulty),`<span class="badge">${b.status}</span>`,b.turn_count,esc(new Date(b.started_at).toLocaleString()),button(b.status==='active'?'Resume':'Review','review-battle',b._id,'quiet small')])):empty('Your first battle starts a new chapter.')}${databaseEvidence(SECTION_EVIDENCE.history)}</section>`;
  await renderMatchups(matchupIds?.get('pokemon_id')||4,matchupIds?.get('opponent_id')||7);
}
async function renderMatchups(pokemonId=4,opponentId=7) {
  const target=document.querySelector('#matchup-evidence');if(!target)return;
  const filters=new FormData(document.querySelector('#strategy-form'));
  const params=new URLSearchParams({pokemon_id:pokemonId,opponent_id:opponentId,rules_version:filters.get('rules_version'),difficulty:filters.get('difficulty')});
  const h=await api(`/analytics/matchups?${params}`),summary=h.summary;
  const options=selected=>h.pokemon.map(p=>`<option value="${p.id}" ${p.id===Number(selected)?'selected':''}>${esc(title(p.name))}</option>`).join('');
  const selected=h.pokemon.find(p=>p.id===h.pokemon_id);
  target.innerHTML=`<h3>1v1 matchups from your battles</h3><p class="note">Source: your saved simulator battles in MongoDB. Uses the battle rules and difficulty filters above.</p>
    <form id="matchup-form" class="toolbar"><label>Selected species<select name="pokemon_id">${options(h.pokemon_id)}</select></label><label>Other species<select name="opponent_id">${options(h.opponent_id)}</select></label><button class="quiet">Compare matchup</button></form>
    <p class="note">${esc(h.note)}</p>
    ${summary.battles?`<p><strong>${summary.battles} completed 1v1 battles</strong> &middot; ${summary.wins} wins / ${summary.losses} losses / ${summary.draws} draws &middot; ${(summary.win_rate*100).toFixed(1)}% observed win rate for ${esc(title(selected?.name||h.pokemon_id))}.</p>${summary.battles<10?'<p class="note">Small sample: treat these results cautiously.</p>':''}
    ${table(['Difficulty','Selected Pokemon side','Battles','Wins','Losses','Draws','Observed win rate','Average turns'],h.rows.map(r=>[esc(title(r.difficulty)),r.selected_side==='player'?'Your team':'AI opponent',r.battles,r.wins,r.losses,r.draws,(r.win_rate*100).toFixed(1)+'%',Number(r.average_turns||0).toFixed(1)]))}`:
    '<p>No completed 1v1 battles for this matchup under these filters. Save a team with one Pokemon, finish battles, then return here. Larger team battles do not count as 1v1 results.</p>'}${databaseEvidence(SECTION_EVIDENCE.matchups)}`;
}
function predictionResults(rows) {
  if(!rows.length)return '<p>No completed battles with predictions yet.</p>';
  return table(['Method / rules','Prediction','Wins','Losses','Draws','Sample','Correct directional calls'],Object.values(rows.reduce((groups,r)=>{
    const key=JSON.stringify([r._id.method,r._id.rules,r._id.label]);
    const g=groups[key] ||= {method:r._id.method,rules:r._id.rules,label:r._id.label,win:0,loss:0,draw:0};
    g[r._id.outcome]+=r.battles;return groups;
  },{})).map(g=>[esc(g.method+' / '+g.rules),esc(g.label),g.win,g.loss,g.draw,g.win+g.loss+g.draw,g.label==='evenly matched'?'Assessed separately':`${g.label==='favoured'?g.win:g.loss} / ${g.win+g.loss} decisive battles`]));
}
async function perform(action,value) {
  if(action==='auto-battle')startAutoBattle();
  else if(action==='open-reward')await openRewardCase();
  else if(action==='skip-reward')finishRewardCase();
  else if(action==='profiles'){await refreshSession();profilesModal();}
  else if(action==='close-dialog')dialog.close();
  else if(action==='starters')startersModal();
  else if(action==='select-profile'){await api('/profiles/select','POST',{id:Number(value)});state.draft=null;state.battle=null;await refreshSession();dialog.close();await navigate(state.view);if(!state.trainer.starter_chosen)startersModal();}
  else if(action==='starter'){await api('/starter','POST',{pokemon_id:Number(value)});await refreshSession();dialog.close();state.draft=null;await navigate('teams');}
  else if(action==='pokemon')await pokemonModal(value);
  else if(action==='go-teams'){state.draft=null;await navigate('teams');}
  else if(action==='edit-team'){state.draft=await api(`/teams/${value}`);await navigate('teams');}
  else if(action==='new-team'){state.draft={name:'My new team',members:[]};drawTeams();}
  else if(action==='delete-team'){if(confirm('Delete this saved team? Your collection and battle history will remain.')){await api(`/teams/${value}`,'DELETE');state.draft=null;await renderTeams();}}
  else if(action==='add-member'){
    rememberName();const o=state.collection.find(p=>p.owned_id===Number(value));
    if(!o||state.draft.members.length>=6||state.draft.members.some(m=>m.owned_id===o.owned_id))return;
    if(draftCost()+pokemonCost(o.pokemon)>30)return;
    if(o.pokemon.rarity==='legendary'&&state.draft.members.some(m=>m.pokemon.id===o.pokemon.id))return;
    const sorted=o.pokemon.moves.slice().sort((a,b)=>Number(!o.pokemon.types.includes(a.type))-Number(!o.pokemon.types.includes(b.type))||Math.abs(a.power-70)-Math.abs(b.power-70)||a.id-b.id);
    state.draft.members.push({owned_id:o.owned_id,pokemon:o.pokemon,moves:sorted.slice(0,4).map(m=>m.id)});drawTeams();
  }
  else if(action==='remove-member'){rememberName();state.draft.members.splice(Number(value),1);drawTeams();}
  else if(action==='move-up'){rememberName();const i=Number(value);[state.draft.members[i-1],state.draft.members[i]]=[state.draft.members[i],state.draft.members[i-1]];drawTeams();}
  else if(['attack','switch','forfeit'].includes(action)){
    if(autoBattle||battleRequestPending)return;
    if(action==='forfeit'&&!confirm('Forfeit this battle? It will be recorded as a loss.'))return;
    const chosen=action==='attack'?{kind:'move',move_id:Number(value)}:action==='switch'?{kind:'switch',slot:Number(value)}:{kind:'forfeit'};
    await submitBattleAction(chosen);
  }
  else if(action==='new-battle'){state.battle=null;await renderBattle();}
  else if(action==='review-battle'){state.battle=await api(`/battles/${value}`);await navigate('battle');}
}
document.addEventListener('click',event=>{
  const requested=event.target.closest('[data-action]');
  if(requested?.dataset.action==='pause-auto'){
    stopAutoBattle();window.battleEffects.cancel();return;
  }
  if(requested&&!['auto-battle','attack','switch','forfeit'].includes(requested.dataset.action)){
    stopAutoBattle();window.battleEffects.cancel();
  }
  const nav=event.target.closest('[data-nav]');if(nav){run(()=>navigate(nav.dataset.nav));return;}
  const action=event.target.closest('[data-action]');if(action&&!action.disabled)run(()=>perform(action.dataset.action,action.dataset.value));
});
document.addEventListener('change',event=>{
  const target=event.target;
  if(target.matches('[data-member]')){
    const member=state.draft.members[Number(target.dataset.member)];member.moves[Number(target.dataset.slot)]=Number(target.value);
    const move=member.pokemon.moves.find(m=>m.id===Number(target.value));
    target.closest('label').querySelector('.move-accuracy').textContent=move?moveChanceText(move):'Choose a move';
  }
  if(target.id==='team-select')run(async()=>{state.draft=target.value?await api(`/teams/${target.value}`):{name:'My new team',members:[]};drawTeams();});
  if(target.id==='analysis-team')run(()=>renderAnalysis(Number(target.value)));
});
document.addEventListener('submit',event=>{
  event.preventDefault();const form=event.target;
  run(async()=>{
    const data=new FormData(form);
    if(form.id==='profile-form'){await api('/profiles','POST',{name:data.get('name')});state.draft=null;state.battle=null;await refreshSession();startersModal();}
    if(form.id==='search-form')await renderPokedex(data.get('q'),data.get('type'));
    if(form.id==='strategy-form')await renderAnalytics(data.get('rules_version'),data.get('difficulty'));
    if(form.id==='matchup-form')await renderMatchups(data.get('pokemon_id'),data.get('opponent_id'));
    if(form.id==='team-form'){rememberName();const d=state.draft;const saved=await api(d.id?`/teams/${d.id}`:'/teams',d.id?'PUT':'POST',{name:d.name,members:d.members.map(m=>({owned_id:m.owned_id,moves:m.moves}))});state.draft=await api(`/teams/${saved.id}`);await renderTeams();notice('Team saved. Ready when you are.');}
    if(form.id==='battle-form'){state.battle=await api('/battles','POST',{team_id:Number(data.get('team_id')),difficulty:data.get('difficulty')});drawBattle();}
  });
});
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(view!==state.view)run(()=>navigate(view));});
document.addEventListener('visibilitychange',()=>{if(document.hidden){stopAutoBattle();window.battleEffects.cancel();}});
window.addEventListener('pagehide',()=>{stopAutoBattle();window.battleEffects.cancel();});
run(async()=>{await refreshSession();await navigate(location.hash.slice(1)||'pokedex');});
