'use strict';
const state = {csrf: '', trainer: null, profiles: [], view: 'pokedex', collection: [], teams: [], draft: null, battle: null, busy: false};
const main = document.querySelector('#main');
const dialog = document.querySelector('#dialog');
const stats = ['hp','attack','defense','special_attack','special_defense','speed'];
const TYPE_COLORS = {normal:'#929aa4',fire:'#f08135',water:'#3d93db',electric:'#e5b821',grass:'#6ca944',ice:'#67bcc1',fighting:'#c75842',poison:'#9d62bd',ground:'#caa559',flying:'#839bd7',psychic:'#e1648e',bug:'#91a73a',rock:'#a59359',ghost:'#74629f',dragon:'#6479c9',dark:'#665c6b',steel:'#7898ac',fairy:'#d97eb4'};
const typeColor = name => TYPE_COLORS[name] || '#7c8caa';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const title = value => String(value).replaceAll('-', ' ').replaceAll('_', ' ');
const sprite = (id, back=false) => `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${back?'back/':''}${Number(id)}.png`;
const img = (p, back=false) => `<img src="${sprite(p.id,back)}" alt="${esc(title(p.name))}" loading="lazy">`;
const tags = types => `<div class="tags">${types.map(t=>`<span class="type ${esc(t)}">${esc(t)}</span>`).join('')}</div>`;
const statLabel = s => ({hp:'HP',attack:'Attack',defense:'Defense',special_attack:'Sp. Attack',special_defense:'Sp. Defense',speed:'Speed'}[s]);
const button = (text, action, value='', cls='quiet') => `<button type="button" class="${cls}" data-action="${action}" data-value="${esc(value)}">${esc(text)}</button>`;
const table = (headers, rows) => `<div class="table-scroll"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const heading = (eyebrow, name, text) => `<div class="page-heading"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(name)}</h1><p>${esc(text)}</p></div></div>`;
const empty = text => `<div class="card empty">${esc(text)}</div>`;
const metric = (name,value) => `<div class="metric"><span>${esc(name)}</span><strong>${esc(value)}</strong></div>`;

async function api(path, method='GET', body) {
  const response = await fetch(`/api${path}`, {method, headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf}, body:body===undefined?undefined:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
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
  state.view=view;location.hash=view;
  document.querySelectorAll('[data-nav]').forEach(b=>{b.classList.toggle('active',b.dataset.nav===view);b.setAttribute('aria-current',b.dataset.nav===view?'page':'false');});
  if(view!=='pokedex' && needTrainer())return;
  const render={pokedex:renderPokedex,teams:renderTeams,analysis:renderAnalysis,battle:renderBattle,analytics:renderAnalytics}[view] || renderPokedex;
  await render();
}
async function renderPokedex(q='',type='') {
  const data=await api(`/pokemon?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type)}`);
  main.innerHTML=`<section class="hero"><div><span class="eyebrow">THE ORIGINAL 151 · A WORLD TO DISCOVER</span><h1>Know your Pokémon.<br>Find your next partner.</h1><p>Explore Kanto's first generation, discover their strengths, and build a team that's yours.</p></div><div class="hero-art">${img({id:4,name:'Charmander'})}${img({id:25,name:'Pikachu'})}${img({id:7,name:'Squirtle'})}<small>CHOOSE YOUR NEXT PARTNER</small></div></section>
    <form id="search-form" class="toolbar"><input aria-label="Search Pokémon" name="q" placeholder="Search by name or Pokédex number…" value="${esc(q)}"><select name="type" aria-label="Filter by type"><option value="">All types</option>${data.types.map(t=>`<option value="${esc(t.name)}" ${t.name===type?'selected':''}>${esc(title(t.name))}</option>`).join('')}</select><button class="quiet">Search</button><span class="count">${data.pokemon.length} Pokémon to discover</span></form>
    ${data.pokemon.length?`<section class="grid">${data.pokemon.map(p=>`<button class="poke-card" style="--type-color:${typeColor(p.types[0])}" data-action="pokemon" data-value="${p.id}"><span class="number">#${String(p.id).padStart(3,'0')}</span>${img(p)}<h3>${esc(title(p.name))}</h3>${tags(p.types)}</button>`).join('')}</section>`:empty('No Pokémon match your search.')}`;
}
async function pokemonModal(id) {
  const p=await api(`/pokemon/${id}`);
  modal(`<span class="eyebrow">POKÉDEX / #${String(p.id).padStart(3,'0')}</span>${img(p).replace('<img','<img class="sprite"')}<h2 id="dialog-title">${esc(title(p.name))}</h2>${tags(p.types)}<p>${esc(p.description)}</p><span class="badge">${p.rarity} reward tier</span>
    <h3 class="spacer">Base stats</h3>${stats.map(s=>`<div class="stat-line"><span>${statLabel(s)}</span><strong>${p[s]}</strong><span class="bar"><i style="width:${Math.min(p[s]/255*100,100)}%"></i></span></div>`).join('')}
    <details class="rules spacer"><summary>Fixed move pool · ${p.moves.length} moves</summary><p class="note">All supported moves use simplified single-hit damage. Status and secondary effects are omitted. ★ marks an approved project-specific move-pool exception.</p>${table(['Move','Type','Power','Accuracy','PP'],p.moves.map(m=>[`${esc(title(m.name))}${m.source==='project_override'?' ★':''}`,tags([m.type]),m.power,m.accuracy===null?'Always':m.accuracy+'%',m.pp]))}</details>`);
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
  main.innerHTML=heading('BUILD SOMETHING YOURS','Collection & teams','Choose up to six partners, then pick four moves for each.')+
    `<div class="toolbar"><label>Saved teams<select id="team-select"><option value="">New team</option>${state.teams.map(t=>`<option value="${t.id}" ${draft.id===t.id?'selected':''}>${esc(t.name)} · ${t.size}/6</option>`).join('')}</select></label>${button('New team','new-team')}${draft.id?button('Delete team','delete-team',draft.id,'danger'):''}<span class="count">${state.collection.length} Pokémon in your collection</span></div>
    <div class="two-col"><section><form id="team-form"><div class="form-row card"><label>Team name<input id="team-name" value="${esc(draft.name)}" maxlength="60" required></label><button class="primary">Save team</button></div><div class="section-title"><h3>Active roster</h3><small>${draft.members.length} / 6 Pokémon</small></div>
    <div class="stack">${draft.members.length?draft.members.map((m,i)=>`<article class="member">${img(m.pokemon)}<div><div class="row between"><h3>${esc(title(m.pokemon.name))}</h3><div>${i?button('↑','move-up',i,'quiet small'):''}${button('Remove','remove-member',i,'quiet small')}</div></div>${tags(m.pokemon.types)}<div class="move-picks">${[0,1,2,3].map(slot=>`<label>Move ${slot+1}<select data-member="${i}" data-slot="${slot}">${m.pokemon.moves.map(move=>`<option value="${move.id}" ${move.id===m.moves[slot]?'selected':''}>${esc(title(move.name))} · ${move.type} · ${move.power} power${move.source==='project_override'?' ★':''}</option>`).join('')}</select></label>`).join('')}</div></div></article>`).join(''):empty('Add Pokémon from your collection to get started.')}</div></form><p class="note">Choose four distinct moves. ★ denotes a project-specific exception. Save your team before analysing it or starting a battle.</p></section>
    <aside class="card"><h3>Your collection</h3><p class="note">Win battles to meet new partners. Duplicate species are separate owned Pokémon.</p><div class="collection-list">${state.collection.map(o=>`<div class="owned">${img(o.pokemon)}<div class="meta"><h4>${esc(title(o.pokemon.name))}</h4><small>#${o.owned_id} · ${o.pokemon.rarity}</small></div><button class="quiet small" data-action="add-member" data-value="${o.owned_id}" ${draft.members.some(m=>m.owned_id===o.owned_id)||draft.members.length>=6?'disabled':''}>Add</button></div>`).join('')}</div></aside></div>`;
}
function rememberName(){const input=document.querySelector('#team-name');if(input&&state.draft)state.draft.name=input.value;}
function teamOptions(chosen) {return state.teams.map(t=>`<option value="${t.id}" ${t.id===Number(chosen)?'selected':''}>${esc(t.name)} · ${t.size}/6</option>`).join('');}
async function renderAnalysis(teamId) {
  await loadTeams();
  if(!state.teams.length){main.innerHTML=heading('KNOW YOUR STRENGTHS','Team analysis','Save a team to see its strengths and weaknesses.')+button('Build a team','go-teams','','primary');return;}
  teamId=teamId || state.teams[0].id;
  const a=await api(`/teams/${teamId}/analysis`);
  main.innerHTML=heading('KNOW YOUR STRENGTHS','Team analysis','Understand your roster before stepping into the arena.')+`<div class="toolbar"><label>Team<select id="analysis-team">${teamOptions(teamId)}</select></label></div>
    <div class="metric-grid">${metric('Team size',a.stats.size)}${metric('Total base stats',stats.reduce((sum,s)=>sum+a.stats['total_'+s],0))}${metric('Average Speed',a.stats.average_speed.toFixed(1))}${metric('Types represented',a.distribution.length)}</div>
    <div class="two-col"><section class="card"><h3>Defensive matchups</h3><p class="note">Number of members weak, resistant or immune to each attacking type. Both defensive types are combined.</p>${table(['Attacking type','Weak','Resistant','Immune'],a.matchups.map(r=>[tags([r.type]),`<span class="${r.weak?'weak':''}">${r.weak}</span>`,r.resistant,r.immune]))}</section>
    <div class="stack"><section class="card"><h3>Team statistics</h3>${table(['Stat','Total','Average'],stats.map(s=>[statLabel(s),a.stats['total_'+s],a.stats['average_'+s].toFixed(1)]))}</section><section class="card"><h3>Type distribution</h3>${a.distribution.length?table(['Type','Members'],a.distribution.map(t=>[tags([t.name]),t.count])):'No members yet.'}</section></div></div>
    <section class="card spacer"><h3>Offensive coverage</h3><p class="note">Best multiplier available from your selected moves against each single defending type. This is coverage, not a prediction of victory.</p><div class="tags">${a.coverage.map(c=>`<span class="type ${c.best_multiplier>1?'grass':''}">${c.type} · ${c.best_multiplier}×</span>`).join('')}</div></section>`;
}
const rules = (version='prototype-2') => `<details class="rules spacer"><summary>How this battle works</summary><p>Choose a move each turn. Priority and Speed determine which attack happens first. Each move uses PP; when all PP runs out, Fallback Strike deals neutral damage and causes recoil. Switching uses a turn, while replacing a fainted Pokémon is free.</p><p>All moves use simplified single-hit damage. No status effects, abilities, items or critical hits. HP and PP reset each battle. ${version==='prototype-1'?'This saved battle uses the original uncapped damage rules.':'Each hit deals at most 40% of the target’s maximum HP, giving healthy Pokémon time to respond. Already weakened Pokémon can still faint.'} A draw occurs after 200 turns. Your opponent never sees your next selected action.</p></details>`;
async function renderBattle() {
  if(state.battle){state.battle=await api(`/battles/${state.battle._id}`);drawBattle();return;}
  const history=await api('/battles');const active=history.battles.find(b=>b.status==='active');
  if(active){state.battle=await api(`/battles/${active._id}`);drawBattle();return;}
  await loadTeams();
  main.innerHTML=heading('PUT YOUR STRATEGY TO WORK','Battle arena','A new opponent, matched to your team. One decision at a time.')+
    `<section class="card"><h2>Ready your team.</h2><form id="battle-form"><label>Choose a saved team<select name="team_id" required><option value="">Select a team</option>${teamOptions()}</select></label><div class="difficulty-options">${[['easy','A gentler challenge'],['medium','Test your balance'],['hard','Make every move count']].map(([d,t])=>`<label><span><input type="radio" name="difficulty" value="${d}" ${d==='medium'?'checked':''}> ${title(d)}</span><small>${t}</small></label>`).join('')}</div><button class="primary" ${state.teams.some(t=>t.size>0)?'':'disabled'}>Start battle →</button></form><p class="note">Opponents match your team size. Difficulty adjusts target strength, matchups and move choices; it does not guarantee an outcome.</p>${rules()}</section>
    <section class="card spacer"><h3>A new partner with every win.</h3><p class="note">Reward odds: Common 60% · Uncommon 25% · Rare 12% · Legendary/Mythical 3%. Rewards enter your collection, not your active team. Duplicates are possible.</p></section>`;
}
function fighter(side,label,back) {const p=side.members[side.active];return `<div class="fighter"><span class="eyebrow">${label}</span>${img(p,back)}<h3>${esc(title(p.name))}</h3>${tags(p.types)}<div class="hp"><i style="width:${p.hp/p.max_hp*100}%"></i></div><small>${p.hp} / ${p.max_hp} HP</small><div class="team-dots" aria-label="${side.members.filter(m=>m.hp>0).length} healthy Pokémon">${side.members.map(m=>m.hp>0?'●':'○').join(' ')}</div></div>`;}
function eventText(e) {
  const side=e.side==='player'?'Your':'Opponent’s';
  if(e.kind==='move')return `${side} ${title(e.name)} used ${title(e.move)}. ${e.hit?`${e.damage} damage${e.effectiveness===0?' — immune':''}.`:'It missed.'}${e.recoil?` ${e.recoil} recoil damage.`:''}`;
  if(e.kind==='switch')return `${side} ${title(e.name)} entered the battle.`;
  if(e.kind==='faint')return `${side} ${title(e.name)} fainted.`;
  return 'You forfeited the battle.';
}
function drawBattle() {
  const b=state.battle,p=b.player.members[b.player.active],active=b.status==='active';
  const exhausted=p.moves.every(m=>m.remaining_pp===0);
  const choices=exhausted?[{id:0,name:'fallback-strike',type:'neutral',remaining_pp:'∞',power:50}]:p.moves;
  main.innerHTML=heading('THE BATTLE IS YOURS','Battle arena',`${title(b.difficulty)} difficulty · ${b.team_name}`)+
    `<div class="two-col"><section><div class="arena"><div class="arena-header"><span>${b.status==='active'?'LIVE BATTLE':b.status.toUpperCase()}</span><span>${b.rules_version==='prototype-1'?'V1':'V2'} · TURN ${b.turn_count}</span></div><div class="fighters">${fighter(b.player,'YOUR PARTNER',true)}<div class="versus">VS</div>${fighter(b.opponent,'OPPONENT',false)}</div></div>
    ${active?`<h3 class="spacer">${p.hp<=0?'Choose a healthy replacement.':'What will you do?'}</h3><div class="actions">${choices.map(m=>`<button class="move-button" style="--type-color:${typeColor(m.type)}" data-action="attack" data-value="${m.id}" ${p.hp<=0||m.remaining_pp===0?'disabled':''}><strong>${esc(title(m.name))}</strong><div class="row">${tags([m.type])}<small>${m.power} power · ${m.remaining_pp} PP</small></div></button>`).join('')}</div><div class="section-title"><h4>Switch Pokémon</h4><small>${p.hp<=0?'Free replacement':'Uses your turn'}</small></div><div class="row">${b.player.members.map((m,i)=>`<button class="quiet small" data-action="switch" data-value="${i}" ${m.hp<=0||i===b.player.active?'disabled':''}>${esc(title(m.name))} · ${m.hp} HP</button>`).join('')}</div><div class="spacer">${button('Forfeit battle','forfeit','','danger small')}</div>`:
    `<section class="result"><h2>${b.status==='win'?'Victory. A new partner awaits!':b.status==='loss'?'A lesson for the next battle.':'An evenly matched battle.'}</h2>${b.reward?`<div class="reward">${img({id:b.reward.pokemon_id,name:b.reward.name})}<div><span class="badge">${b.reward.rarity}</span><h3>${esc(title(b.reward.name))}</h3><small>${b.reward.delivered?'Added to your collection.':'Reward delivery pending; reopen this battle to retry.'}</small></div></div>`:`<p class="note">${b.turn_count} turns played. Adjust your team or try another difficulty.</p>`}<div class="row spacer">${button('Battle again','new-battle','','primary')}${button('View collection','go-teams')}</div></section>`}${rules(b.rules_version)}</section>
    <aside class="stack"><section class="card"><h3>Battle log</h3><ol class="battle-log">${b.turns.length?b.turns.slice().reverse().map(t=>`<li><span class="turn-label">${t.kind==='turn'?'TURN '+t.number:title(t.kind).toUpperCase()}</span><br>${t.events.map(e=>esc(eventText(e))).join('<br>')}</li>`).join(''):'<li>Your opponent is ready. Choose your first move.</li>'}</ol></section><section class="card"><h4>Opponent matching</h4><p class="note">Your strength: ${b.generation.player_strength}<br>Target: ${Math.round(b.generation.target_strength)}<br>Opponent strength: ${b.generation.actual_strength}</p><small>Strength = total base stats across the team.</small></section></aside></div>`;
}
async function renderAnalytics() {
  const [a,h]=await Promise.all([api('/analytics'),api('/battles')]);const s=a.summary;
  main.innerHTML=heading('EVERY BATTLE TELLS A STORY','Battle analytics','Look back, find patterns, and make your next team stronger.')+
    `<div class="metric-grid">${metric('Completed battles',s.battles)}${metric('Win rate',s.battles?(s.wins/s.battles*100).toFixed(1)+'%':'—')}${metric('Average turns',Number(s.average_turns||0).toFixed(1))}${metric('Average duration',Math.round(s.average_seconds||0)+'s')}</div>
    <p class="note">Win rate = wins ÷ all completed battles, including draws and forfeits. Duration includes thinking time. Active battles are excluded.</p>
    <div class="two-col"><section class="card"><h3>Results by difficulty</h3>${a.difficulty.length?table(['Difficulty','Wins','Losses','Draws','Battles'],a.difficulty.map(d=>[esc(d._id),d.wins,d.losses,d.draws,d.battles])):empty('Finish your first battle to see results.')}</section><section class="card"><h3>Most-used moves</h3>${a.moves.length?table(['Move','Uses'],a.moves.map(m=>[esc(title(m.name)),m.uses])):'<p class="note">Your executed moves will appear here, including misses.</p>'}</section></div>
    <section class="card spacer"><h3>Pokémon performance</h3><p class="note">Appearances count completed battles containing the species, once per battle. Win rate describes the team result, not individual knockouts.</p>${a.pokemon.length?table(['Pokémon','Appearances','Wins','Win rate'],a.pokemon.map(p=>[esc(title(p.name)),p.appearances,p.wins,(p.wins/p.appearances*100).toFixed(1)+'%'])):empty('No completed battles yet.')}</section>
    <section class="card spacer"><h3>Battle history</h3><p class="note">Your latest 50 battles. Open an active battle to resume it.</p>${h.battles.length?table(['Team','Difficulty','Result','Turns','Started',''],h.battles.map(b=>[esc(b.team_name),esc(b.difficulty),`<span class="badge">${b.status}</span>`,b.turn_count,esc(new Date(b.started_at).toLocaleString()),button(b.status==='active'?'Resume':'Review','review-battle',b._id,'quiet small')])):empty('Your first battle starts a new chapter.')}</section>`;
}
async function perform(action,value) {
  if(action==='profiles'){await refreshSession();profilesModal();}
  else if(action==='close-dialog')dialog.close();
  else if(action==='starters')startersModal();
  else if(action==='select-profile'){await api('/profiles/select','POST',{id:Number(value)});state.draft=null;state.battle=null;await refreshSession();dialog.close();await navigate(state.view);if(!state.trainer.starter_chosen)startersModal();}
  else if(action==='starter'){await api('/starter','POST',{pokemon_id:Number(value)});await refreshSession();dialog.close();state.draft=null;await navigate('teams');}
  else if(action==='pokemon')await pokemonModal(value);
  else if(action==='go-teams'){state.draft=null;await navigate('teams');}
  else if(action==='new-team'){state.draft={name:'My new team',members:[]};drawTeams();}
  else if(action==='delete-team'){if(confirm('Delete this saved team? Your collection and battle history will remain.')){await api(`/teams/${value}`,'DELETE');state.draft=null;await renderTeams();}}
  else if(action==='add-member'){
    rememberName();const o=state.collection.find(p=>p.owned_id===Number(value));
    if(!o||state.draft.members.length>=6||state.draft.members.some(m=>m.owned_id===o.owned_id))return;
    const sorted=o.pokemon.moves.slice().sort((a,b)=>Number(!o.pokemon.types.includes(a.type))-Number(!o.pokemon.types.includes(b.type))||Math.abs(a.power-70)-Math.abs(b.power-70)||a.id-b.id);
    state.draft.members.push({owned_id:o.owned_id,pokemon:o.pokemon,moves:sorted.slice(0,4).map(m=>m.id)});drawTeams();
  }
  else if(action==='remove-member'){rememberName();state.draft.members.splice(Number(value),1);drawTeams();}
  else if(action==='move-up'){rememberName();const i=Number(value);[state.draft.members[i-1],state.draft.members[i]]=[state.draft.members[i],state.draft.members[i-1]];drawTeams();}
  else if(['attack','switch','forfeit'].includes(action)){
    if(action==='forfeit'&&!confirm('Forfeit this battle? It will be recorded as a loss.'))return;
    const chosen=action==='attack'?{kind:'move',move_id:Number(value)}:action==='switch'?{kind:'switch',slot:Number(value)}:{kind:'forfeit'};
    state.battle=await api(`/battles/${state.battle._id}/actions`,'POST',{revision:state.battle.revision,action:chosen});drawBattle();
  }
  else if(action==='new-battle'){state.battle=null;await renderBattle();}
  else if(action==='review-battle'){state.battle=await api(`/battles/${value}`);await navigate('battle');}
}
document.addEventListener('click',event=>{
  const nav=event.target.closest('[data-nav]');if(nav){run(()=>navigate(nav.dataset.nav));return;}
  const action=event.target.closest('[data-action]');if(action&&!action.disabled)run(()=>perform(action.dataset.action,action.dataset.value));
});
document.addEventListener('change',event=>{
  const target=event.target;
  if(target.matches('[data-member]'))state.draft.members[Number(target.dataset.member)].moves[Number(target.dataset.slot)]=Number(target.value);
  if(target.id==='team-select')run(async()=>{state.draft=target.value?await api(`/teams/${target.value}`):{name:'My new team',members:[]};drawTeams();});
  if(target.id==='analysis-team')run(()=>renderAnalysis(Number(target.value)));
});
document.addEventListener('submit',event=>{
  event.preventDefault();const form=event.target;
  run(async()=>{
    const data=new FormData(form);
    if(form.id==='profile-form'){await api('/profiles','POST',{name:data.get('name')});state.draft=null;state.battle=null;await refreshSession();startersModal();}
    if(form.id==='search-form')await renderPokedex(data.get('q'),data.get('type'));
    if(form.id==='team-form'){rememberName();const d=state.draft;const saved=await api(d.id?`/teams/${d.id}`:'/teams',d.id?'PUT':'POST',{name:d.name,members:d.members.map(m=>({owned_id:m.owned_id,moves:m.moves}))});state.draft=await api(`/teams/${saved.id}`);await renderTeams();notice('Team saved. Ready when you are.');}
    if(form.id==='battle-form'){state.battle=await api('/battles','POST',{team_id:Number(data.get('team_id')),difficulty:data.get('difficulty')});drawBattle();}
  });
});
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(view!==state.view)run(()=>navigate(view));});
run(async()=>{await refreshSession();await navigate(location.hash.slice(1)||'pokedex');});
