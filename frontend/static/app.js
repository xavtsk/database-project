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
function databaseEvidence({database,operation,data,techniques,changes,query}) {
  return `<details class="database-evidence spacer"><summary><span><b>Database evidence</b><small>${esc(database)} · ${esc(operation)}</small></span><span class="evidence-change ${changes==='No'?'read-only':'writes-data'}">Changes data: ${esc(changes)}</span></summary><div class="evidence-body"><dl><div><dt>Tables / collection</dt><dd>${esc(data)}</dd></div><div><dt>Techniques</dt><dd>${esc(techniques)}</dd></div></dl><h4>Representative query or pipeline</h4><pre><code>${esc(query)}</code></pre><p class="note">Shortened for explanation. <code>%s</code> values are bound by the backend; credentials and live values are never displayed.</p></div></details>`;
}
const DB_EVIDENCE = {
  pokedex:{database:'MySQL',operation:'SELECT · read-only',data:'pokemon, pokemon_types, types',techniques:'Parameterised search, nested type-membership query, JOIN',changes:'No',query:`SELECT p.id
FROM pokemon p
WHERE (p.name LIKE %s OR CAST(p.id AS CHAR)=%s)
  AND (%s='' OR p.id IN (
    SELECT pt.pokemon_id
    FROM pokemon_types pt JOIN types t ON t.id=pt.type_id
    WHERE t.name=%s
  ))
ORDER BY p.id;`},
  teams:{database:'MySQL',operation:'SELECT / INSERT / UPDATE / DELETE',data:'teams, team_members, owned_pokemon, team_member_moves',techniques:'LEFT JOIN, row lock, transaction, batch insert, rollback, cascades',changes:'Yes, when Save or Delete is clicked',query:`START TRANSACTION;
SELECT id FROM trainers WHERE id=%s FOR UPDATE;
UPDATE teams SET name=%s WHERE id=%s;
DELETE FROM team_members WHERE team_id=%s;
INSERT INTO team_members (...) VALUES (...);
INSERT INTO team_member_moves (...) VALUES (...);
COMMIT;`},
  analysis:{database:'MySQL',operation:'SELECT · read-only',data:'team/member/species/type/move tables and three SQL views',techniques:'JOIN, COUNT, SUM, AVG, GROUP BY, CTE, NOT EXISTS, ROW_NUMBER',changes:'No; recommendations are proposals only',query:`SELECT t.name, COUNT(*)
FROM team_members tm
JOIN owned_pokemon o ON o.id=tm.owned_id
JOIN pokemon_types pt ON pt.pokemon_id=o.pokemon_id
JOIN types t ON t.id=pt.type_id
WHERE tm.team_id=%s
GROUP BY t.id,t.name;

WITH roster AS (...), candidates AS (...), ranked AS (...)
SELECT * FROM ranked WHERE recommendation_rank <= 3;`},
  battle:{database:'MySQL → MongoDB',operation:'SELECT / INSERT, insert_one, replace_one',data:'SQL saved team/catalogue/rewards; MongoDB battles',techniques:'SQL roster JOIN and transaction; embedded snapshot; revision-checked replacement',changes:'Yes, when a battle starts, a turn resolves or a reward is delivered',query:`-- Read the owned SQL roster
SELECT ... FROM teams t
LEFT JOIN team_members tm ON tm.team_id=t.id
WHERE t.id=%s AND t.trainer_id=%s;

// Store/update the MongoDB battle
insertOne(battleSnapshot)
replaceOne({_id, trainer_id, revision, status:'active'}, updatedBattle)

-- On a win, deliver one SQL reward transaction
INSERT INTO owned_pokemon (...) VALUES (...);
INSERT INTO battle_rewards (...) VALUES (...);`},
  analytics:{database:'MongoDB',operation:'aggregate · read-only',data:'battles',techniques:'$match, $facet, $unwind, $group, $sort',changes:'No',query:`[
  {$match: {trainer_id, status: {$in: ['win','loss','draw']}}},
  {$facet: {
    summary: [{$group: {_id: null, battles: {$sum: 1}}}],
    moves: [{$unwind: '$turns'}, {$unwind: '$turns.events'},
            {$group: {_id: '$turns.events.move_id', uses: {$sum: 1}}}]
  }}
]`}
};
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
    <div class="case-opening" hidden><h3>Finding your next partner…</h3><div class="case-window" aria-hidden="true"><div class="case-reel"></div><span class="case-pointer"></span></div><p class="case-status" role="status">Opening your case…</p>${button('Skip animation','skip-reward','','case-skip')}</div>
    <div class="case-revealed" ${revealed?'':'hidden'}><div class="case-burst" aria-hidden="true">✦ <span>✧</span> ✦</div>${shinyBadge(reward)}<span class="case-rarity">${esc(reward.rarity)} partner</span><div class="reward">${img({id:reward.pokemon_id,name:reward.name,is_shiny:reward.is_shiny})}<div><h3 class="reward-name" tabindex="-1">${reward.is_shiny?'Shiny ':''}${esc(title(reward.name))}</h3><p class="case-delivery">${reward.delivered?'Added to your collection.':'Reward delivery pending; reopen this battle from history to retry.'}</p>${reward.selection_note?`<p class="case-delivery">${esc(reward.selection_note)}</p>`:''}</div></div></div>
    <p class="case-odds">Base reward odds: ${rewardOddsText(reward.odds||REWARD_ODDS.easy)} Full variants are rerolled; tiers adjust if a tier is full.</p>
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
  modal(`<span class="eyebrow">YOUR TRAINER PROFILE</span><h2 id="dialog-title">Choose your trainer</h2><p class="note">Local profiles share this computer. Choose yours or start a new adventure.</p>
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
    <form id="search-form" class="toolbar"><input aria-label="Search Pokémon" name="q" placeholder="Search by name or Pokédex number…" value="${esc(q)}"><select name="type" aria-label="Filter by type"><option value="">All types</option>${data.types.map(t=>`<option value="${esc(t.name)}" ${t.name===type?'selected':''}>${esc(title(t.name))}</option>`).join('')}</select><button class="quiet">Search</button><span class="count">${data.pokemon.length} Pokémon to discover</span></form>${databaseEvidence(DB_EVIDENCE.pokedex)}
    ${data.pokemon.length?`<section class="grid">${data.pokemon.map(p=>`<button class="poke-card" style="--type-color:${typeColor(p.types[0])}" data-action="pokemon" data-value="${p.id}"><span class="number">#${String(p.id).padStart(3,'0')}</span>${img(p)}<h3>${esc(title(p.name))}</h3>${tags(p.types)}</button>`).join('')}</section>`:empty('No Pokémon match your search.')}`;
}
async function pokemonModal(id) {
  const p=await api(`/pokemon/${id}`);
  modal(`<span class="eyebrow">POKÉDEX / #${String(p.id).padStart(3,'0')}</span>${img(p).replace('<img','<img class="sprite"')}<h2 id="dialog-title">${esc(title(p.name))}</h2>${tags(p.types)}<p>${esc(p.description)}</p><span class="badge">${p.rarity} reward tier</span>
    <h3 class="spacer">Base stats</h3>${stats.map(s=>`<div class="stat-line"><span>${statLabel(s)}</span><strong>${p[s]}</strong><span class="bar"><i style="width:${Math.min(p[s]/255*100,100)}%"></i></span></div>`).join('')}
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
    `<section class="card spacer" aria-live="polite"><strong class="${cost>30?'weak':''}">Team budget: ${cost} / 30 points · ${30-cost} remaining</strong><p class="note">Each Pokémon costs its total base stats divided by 100, rounded up. ${cost>30?'Remove or replace a member before saving or starting a new battle.':'Save your team to apply changes.'}</p></section>`+databaseEvidence(DB_EVIDENCE.teams)+
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
    <div class="two-col"><section class="card"><h3>Defensive matchups</h3><p class="note">Number of members weak, resistant or immune to each attacking type. Both defensive types are combined.</p>${table(['Attacking type','Weak','Resistant','Immune'],a.matchups.map(r=>[tags([r.type]),`<span class="${r.weak?'weak':''}">${r.weak}</span>`,r.resistant,r.immune]))}</section>
    <div class="stack"><section class="card"><h3>Team statistics</h3>${table(['Stat','Total','Average'],stats.map(s=>[statLabel(s),a.stats['total_'+s],a.stats['average_'+s].toFixed(1)]))}</section><section class="card"><h3>Type distribution</h3>${a.distribution.length?table(['Type','Members'],a.distribution.map(t=>[tags([t.name]),t.count])):'No members yet.'}</section></div></div>
    <section class="card spacer"><h3>Offensive coverage</h3><p class="note">Best multiplier available from your selected moves against each single defending type. This is coverage, not a prediction of victory.</p><div class="tags">${a.coverage.map(c=>`<span class="type ${c.best_multiplier>1?'grass':''}">${c.type} · ${c.best_multiplier}×</span>`).join('')}</div></section>
    <section class="card spacer" id="recommendations" aria-busy="true"><h3>Recommended partners</h3><p role="status">Finding partners for this team…</p></section>`;
  const panel=document.querySelector('#recommendations');
  recommendation.then(({data,error})=>{
    // An earlier response must never overwrite another team's screen.
    if(document.querySelector('#recommendations')!==panel)return;
    panel.setAttribute('aria-busy','false');
    panel.innerHTML=error?`<h3>Recommended partners</h3><p class="note">${esc(error.message)}</p>`:recommendationsContent(a,data,teamId);
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
    }).join(''):'<p>No eligible improvement is available from this collection.</p>'}</div>
    <p class="note">Suggestions use default moves and never edit the team automatically.</p>${button('Review this team','edit-team',teamId)}`;
}
function predictionPanel(b) {
  const p=b.prediction;
  if(!p)return '<section class="card"><h3>Pre-battle prediction</h3><p class="note">This older battle has no saved prediction.</p></section>';
  const h=p.history;
  return `<section class="card" id="prediction"><h3>Pre-battle prediction: ${esc(title(p.label))}</h3><p class="note">Saved before the first turn; this assessment stays fixed.</p><ul>${p.reasons.map(reason=>`<li>${esc(reason)}</li>`).join('')}</ul><p class="note">${esc(p.note)}</p><p>${h.battles} prior comparable battles: ${h.wins} wins, ${h.losses} losses, ${h.draws} draws.</p><p class="note">${esc(h.note)} ${h.battles<10?'Historical evidence is limited.':''}</p>${b.budget?`<p class="note">Starting team cost: ${b.budget.total} / ${b.budget.limit} points.</p>`:''}</section>`;
}
const rules = (version='prototype-2') => `<details class="rules spacer"><summary>How this battle works</summary><p>Choose a move each turn. Priority and Speed determine which attack happens first. Each move uses PP; when all PP runs out, Fallback Strike deals neutral damage and causes recoil. Switching uses a turn, while replacing a fainted Pokémon is free.</p><p>All moves use simplified single-hit damage. No status effects, abilities, items or critical hits. HP and PP reset each battle. ${version==='prototype-1'?'This saved battle uses the original uncapped damage rules.':'Each hit deals at most 40% of the target’s maximum HP, giving healthy Pokémon time to respond. Already weakened Pokémon can still faint.'} A draw occurs after 200 turns. Your opponent never sees your next selected action.</p></details>`;
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
    `<section class="result"><h2>${b.status==='win'?'Victory. A new partner awaits!':b.status==='loss'?'A lesson for the next battle.':'An evenly matched battle.'}</h2>${b.status==='win'&&b.reward?rewardCase(b):`<p class="note">${b.turn_count} turns played. Adjust your team or try another difficulty.</p>`}<div class="row spacer">${button('Battle again','new-battle','','primary')}${button('View collection','go-teams')}</div></section>`}</div><div class="section-title"><h2>Battle analysis</h2></div>
    <section class="battle-analysis" aria-label="Battle analysis">${predictionPanel(b)}<section class="card"><h3>Battle log</h3><ol class="battle-log">${b.turns.length?b.turns.slice().reverse().map(t=>`<li><span class="turn-label">${t.kind==='turn'?'TURN '+t.number:title(t.kind).toUpperCase()} · ${t.controller==='auto'?'AUTO':'MANUAL'}</span>${t.decision?`<p class="auto-reason">${esc(t.decision)}</p>`:'<br>'}${t.events.map(e=>esc(eventText(e))).join('<br>')}</li>`).join(''):'<li>Your opponent is ready. Choose your first move.</li>'}</ol></section><section class="card"><h4>Opponent matching</h4><p class="note">Your strength: ${b.generation.player_strength}<br>Target: ${Math.round(b.generation.target_strength)}<br>Opponent strength: ${b.generation.actual_strength}</p><small>Strength = total base stats across the team.</small></section></section>${databaseEvidence(DB_EVIDENCE.battle)}${rules(b.rules_version)}`;
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
    `<div class="metric-grid">${metric('Completed battles',s.battles)}${metric('Win rate',s.battles?(s.wins/s.battles*100).toFixed(1)+'%':'—')}${metric('Average turns',Number(s.average_turns||0).toFixed(1))}${metric('Average duration',Math.round(s.average_seconds||0)+'s')}</div>
    <p class="note">Win rate = wins ÷ all completed battles, including draws and forfeits. Duration includes thinking time. Active battles are excluded.</p>
    <div class="two-col"><section class="card"><h3>Results by difficulty</h3>${a.difficulty.length?table(['Difficulty','Wins','Losses','Draws','Battles'],a.difficulty.map(d=>[esc(d._id),d.wins,d.losses,d.draws,d.battles])):empty('Finish your first battle to see results.')}</section><section class="card"><h3>Most-used moves</h3>${a.moves.length?table(['Move','Uses'],a.moves.map(m=>[esc(title(m.name)),m.uses])):'<p class="note">Your executed moves will appear here, including misses.</p>'}</section></div>
    <section class="card spacer"><h3>Pokémon performance</h3><p class="note">Appearances count completed battles containing the species, once per battle. Win rate describes the team result, not individual knockouts.</p>${a.pokemon.length?table(['Pokémon','Appearances','Wins','Win rate'],a.pokemon.map(p=>[esc(title(p.name)),p.appearances,p.wins,(p.wins/p.appearances*100).toFixed(1)+'%'])):empty('No completed battles yet.')}</section>
    <section class="card spacer" id="strategy-evidence"><h3>Battle strategy evidence</h3>
    <form id="strategy-form" class="toolbar"><label>Battle rules<select name="rules_version">${strategy.rules_versions.map(v=>`<option value="${esc(v)}" ${v===strategy.rules_version?'selected':''}>${esc(v)}</option>`).join('')}</select></label><label>Difficulty<select name="difficulty"><option value="">All difficulties</option>${['easy','medium','hard'].map(d=>`<option value="${d}" ${d===strategy.difficulty?'selected':''}>${title(d)}</option>`).join('')}</select></label><button class="quiet">Apply filters</button></form>
    <p><strong>${strategy.battles} completed battles</strong> under these filters. ${strategy.battles<10?'Small sample: treat patterns cautiously.':''}</p><p class="note">${esc(strategy.note)}</p>
    <h4>Damage per attempted move</h4><p class="note">Observed miss rate is misses divided by attempted attacks in these filtered battles; it can differ from a move's listed miss chance. Hits against immune targets count as hits.</p>${strategy.moves.length?table(['Move','Attempts','Hit rate','Miss rate','Total damage','Damage / attempt'],strategy.moves.map(m=>[esc(title(m.name)),m.attempts,(m.hit_rate*100).toFixed(1)+'%',((1-m.hit_rate)*100).toFixed(1)+'%',m.damage,m.damage_per_attempt.toFixed(1)])):'<p class="note">No player attacks in the selected battles yet.</p>'}
    <h4 class="spacer">Does repeating one move correlate with wins?</h4><p class="note">Only battles with at least ${strategy.min_attempts} player attacks. High repetition means one move accounts for at least ${strategy.dominant_share*100}% of attacks. Compare rows within the same difficulty and team size; the battle count is the sample size.</p>
    ${strategy.repetition.length?table(['Difficulty','Team size','Pattern','Battles','Wins / losses / draws','Win rate','Average top-move share'],strategy.repetition.map(r=>[esc(r._id.difficulty),r._id.team_size,esc(r._id.pattern),`${r.battles}${r.battles<10?' (small sample)':''}`,`${r.wins} / ${r.losses} / ${r.draws}`,(r.wins/r.battles*100).toFixed(1)+'%',(r.average_top_share*100).toFixed(1)+'%'])):'<p class="note">No battles with enough attempted moves under these filters.</p>'}
    <div class="spacer" id="prediction-results"><h4>Predictions and actual outcomes</h4><p class="note">Same rules/difficulty filters as above; forfeits and missing predictions excluded. Favoured + win and disadvantaged + loss count as correct directional calls. Draws and evenly matched labels are shown separately. These results do not establish a calibrated win probability.</p>${predictionResults(strategy.predictions.map(r=>({...r,_id:{...r._id,rules:strategy.rules_version}})))}</div></section>
    <section class="card spacer" id="matchup-evidence"><h3>1v1 matchups from your battles</h3><p>Loading your battle matchups…</p></section>
    <section class="card spacer"><h3>Battle history</h3><p class="note">Your latest 50 battles. Open an active battle to resume it.</p>${h.battles.length?table(['Team','Difficulty','Result','Turns','Started',''],h.battles.map(b=>[esc(b.team_name),esc(b.difficulty),`<span class="badge">${b.status}</span>`,b.turn_count,esc(new Date(b.started_at).toLocaleString()),button(b.status==='active'?'Resume':'Review','review-battle',b._id,'quiet small')])):empty('Your first battle starts a new chapter.')}</section>`;
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
    <form id="matchup-form" class="toolbar"><label>Pok&eacute;mon<select name="pokemon_id">${options(h.pokemon_id)}</select></label><label>Opponent<select name="opponent_id">${options(h.opponent_id)}</select></label><button class="quiet">Compare matchup</button></form>
    <p class="note">${esc(h.note)}</p>
    ${summary.battles?`<p><strong>${summary.battles} completed 1v1 battles</strong> &middot; ${summary.wins} wins / ${summary.losses} losses / ${summary.draws} draws &middot; ${(summary.win_rate*100).toFixed(1)}% observed win rate for ${esc(title(selected?.name||h.pokemon_id))}.</p>${summary.battles<10?'<p class="note">Small sample: treat these results cautiously.</p>':''}
    ${table(['Difficulty','Selected Pokemon side','Battles','Wins','Losses','Draws','Observed win rate','Average turns'],h.rows.map(r=>[esc(title(r.difficulty)),r.selected_side==='player'?'Your team':'AI opponent',r.battles,r.wins,r.losses,r.draws,(r.win_rate*100).toFixed(1)+'%',Number(r.average_turns||0).toFixed(1)]))}`:
    '<p>No completed 1v1 battles for this matchup under these filters. Save a team with one Pokemon, finish battles, then return here. Larger team battles do not count as 1v1 results.</p>'}`;
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
