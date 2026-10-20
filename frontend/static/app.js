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
const pokemonCost = p => Math.ceil(stats.reduce((sum,s)=>sum+p[s],0)/100);
const draftCost = () => state.draft.members.reduce((sum,m)=>sum+pokemonCost(m.pokemon),0);
const REWARD_COLORS = {common:'#a9bbd0',uncommon:'#65ca8c',rare:'#b794ff',legendary:'#ffd447'};
const revealedRewards = new Set();
let rewardSpin = null;

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
  return `<section class="reward-case" data-battle="${esc(battle._id)}" style="--reward-color:${REWARD_COLORS[reward.rarity]||REWARD_COLORS.common}">
    <span class="eyebrow">VICTORY DROP</span>
    <div class="case-sealed" ${revealed?'hidden':''}><div class="case-ball" aria-hidden="true"></div><h3>A new partner is inside.</h3><p>One victory. One Pokémon. Open your reward case.</p>${button('Open reward case','open-reward','','primary')}</div>
    <div class="case-opening" hidden><h3>Finding your next partner…</h3><div class="case-window" aria-hidden="true"><div class="case-reel"></div><span class="case-pointer"></span></div><p class="case-status" role="status">Opening your case…</p>${button('Skip animation','skip-reward','','case-skip')}</div>
    <div class="case-revealed" ${revealed?'':'hidden'}><div class="case-burst" aria-hidden="true">✦ <span>✧</span> ✦</div><span class="case-rarity">${esc(reward.rarity)} partner</span><div class="reward">${img({id:reward.pokemon_id,name:reward.name})}<div><h3 class="reward-name" tabindex="-1">${esc(title(reward.name))}</h3><p class="case-delivery">${reward.delivered?'Added to your collection.':'Reward delivery pending; reopen this battle from history to retry.'}</p></div></div></div>
    <p class="case-odds">Common 60% · Uncommon 25% · Rare 12% · Legendary/Mythical 3%</p>
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
  cards[winnerIndex]={id:battle.reward.pokemon_id,name:battle.reward.name,rarity:battle.reward.rarity};
  reel.innerHTML=cards.map((p,i)=>`<div class="case-card" ${i===winnerIndex?'data-winner="true"':''} style="--card-color:${REWARD_COLORS[p?.rarity]||REWARD_COLORS.common}">${p?img(p):'<span class="ball" aria-hidden="true"></span>'}<strong>${p?esc(title(p.name)):'Mystery partner'}</strong><small>${p?esc(p.rarity):'Pokémon'}</small></div>`).join('');
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

async function api(path, method='GET', body) {
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
  const cost=draftCost();
  main.innerHTML=heading('BUILD SOMETHING YOURS','Collection & teams','Choose up to six partners, then pick four moves for each.')+
    `<section class="card spacer" aria-live="polite"><strong class="${cost>30?'weak':''}">Team budget: ${cost} / 30 points · ${30-cost} remaining</strong><p class="note">Each Pokémon costs its total base stats divided by 100, rounded up. ${cost>30?'Remove or replace a member before saving or starting a new battle.':'Save your team to apply changes.'}</p></section>`+
    `<div class="toolbar"><label>Saved teams<select id="team-select"><option value="">New team</option>${state.teams.map(t=>`<option value="${t.id}" ${draft.id===t.id?'selected':''}>${esc(t.name)} · ${t.size}/6</option>`).join('')}</select></label>${button('New team','new-team')}${draft.id?button('Delete team','delete-team',draft.id,'danger'):''}<span class="count">${state.collection.length} Pokémon in your collection</span></div>
    <div class="two-col"><section><form id="team-form"><div class="form-row card"><label>Team name<input id="team-name" value="${esc(draft.name)}" maxlength="60" required></label><button class="primary">Save team</button></div><div class="section-title"><h3>Active roster</h3><small>${draft.members.length} / 6 Pokémon</small></div>
    <div class="stack">${draft.members.length?draft.members.map((m,i)=>`<article class="member">${img(m.pokemon)}<div><div class="row between"><h3>${esc(title(m.pokemon.name))} ? ${pokemonCost(m.pokemon)} pts</h3><div>${i?button('↑','move-up',i,'quiet small'):''}${button('Remove','remove-member',i,'quiet small')}</div></div>${tags(m.pokemon.types)}<div class="move-picks">${[0,1,2,3].map(slot=>`<label>Move ${slot+1}<select data-member="${i}" data-slot="${slot}">${m.pokemon.moves.map(move=>`<option value="${move.id}" ${move.id===m.moves[slot]?'selected':''}>${esc(title(move.name))} · ${move.type} · ${move.power} power${move.source==='project_override'?' ★':''}</option>`).join('')}</select></label>`).join('')}</div></div></article>`).join(''):empty('Add Pokémon from your collection to get started.')}</div></form><p class="note">Choose four distinct moves. ★ denotes a project-specific exception. Save your team before analysing it or starting a battle.</p></section>
    <aside class="card"><h3>Your collection</h3><p class="note">Win battles to meet new partners. Duplicate species are separate owned Pokémon. Costs are shown in points.</p><div class="collection-list">${state.collection.map(o=>`<div class="owned">${img(o.pokemon)}<div class="meta"><h4>${esc(title(o.pokemon.name))} · ${pokemonCost(o.pokemon)} pts</h4><small>#${o.owned_id} · ${o.pokemon.rarity}</small></div><button class="quiet small" data-action="add-member" data-value="${o.owned_id}" ${draft.members.some(m=>m.owned_id===o.owned_id)||draft.members.length>=6||cost+pokemonCost(o.pokemon)>30?'disabled':''}>Add</button></div>`).join('')}</div></aside></div>`;
}
function rememberName(){const input=document.querySelector('#team-name');if(input&&state.draft)state.draft.name=input.value;}
function teamOptions(chosen) {return state.teams.map(t=>`<option value="${t.id}" ${t.id===Number(chosen)?'selected':''}>${esc(t.name)} · ${t.size}/6</option>`).join('');}
async function renderAnalysis(teamId) {
  await loadTeams();
  if(!state.teams.length){main.innerHTML=heading('KNOW YOUR STRENGTHS','Team analysis','Save a team to see its strengths and weaknesses.')+button('Build a team','go-teams','','primary');return;}
  teamId=teamId || state.teams[0].id;
  const [a,r]=await Promise.all([api(`/teams/${teamId}/analysis`),api(`/teams/${teamId}/recommendations`)]);
  main.innerHTML=heading('KNOW YOUR STRENGTHS','Team analysis','Understand your roster before stepping into the arena.')+`<div class="toolbar"><label>Team<select id="analysis-team">${teamOptions(teamId)}</select></label></div>
    <div class="metric-grid">${metric('Team size',a.stats.size)}${metric('Total base stats',stats.reduce((sum,s)=>sum+a.stats['total_'+s],0))}${metric('Average Speed',a.stats.average_speed.toFixed(1))}${metric('Types represented',a.distribution.length)}</div>
    <div class="two-col"><section class="card"><h3>Defensive matchups</h3><p class="note">Number of members weak, resistant or immune to each attacking type. Both defensive types are combined.</p>${table(['Attacking type','Weak','Resistant','Immune'],a.matchups.map(r=>[tags([r.type]),`<span class="${r.weak?'weak':''}">${r.weak}</span>`,r.resistant,r.immune]))}</section>
    <div class="stack"><section class="card"><h3>Team statistics</h3>${table(['Stat','Total','Average'],stats.map(s=>[statLabel(s),a.stats['total_'+s],a.stats['average_'+s].toFixed(1)]))}</section><section class="card"><h3>Type distribution</h3>${a.distribution.length?table(['Type','Members'],a.distribution.map(t=>[tags([t.name]),t.count])):'No members yet.'}</section></div></div>
    <section class="card spacer"><h3>Offensive coverage</h3><p class="note">Best multiplier available from your selected moves against each single defending type. This is coverage, not a prediction of victory.</p><div class="tags">${a.coverage.map(c=>`<span class="type ${c.best_multiplier>1?'grass':''}">${c.type} · ${c.best_multiplier}×</span>`).join('')}</div></section>
    <section class="card spacer" id="recommendations"><h3>Recommended partners</h3><p>Team budget: ${a.budget.total} / ${a.budget.limit} points.</p><p class="note">${esc(r.note)} Defensive exposure averages weakness multipliers above 1 across members and all attacking types; lower is better.</p>
    ${r.suggestions.length?r.suggestions.map(s=>{const h=r.history.find(h=>h._id===s.pokemon_id);return `<article class="rules spacer"><h4>${s.replace_owned_id?`Replace ${esc(title(s.replace_name))} (#${s.replace_owned_id}) with`:'Consider adding'} ${esc(title(s.name))} (#${s.owned_id})</h4><p>${esc(s.reason)}</p><p class="note">Cost ${s.cost} points · proposed team ${s.budget.total} / ${s.budget.limit}. Suggested moves: ${s.suggested_moves.map(m=>esc(title(m.name))).join(', ')}.</p><p class="note">${h?`${h.battles} prior battles containing this species: ${h.wins} wins, ${h.losses} losses, ${h.draws} draws. Team results across different matchups; forfeits excluded.`:'No prior battle evidence for this species under the current rules.'}</p></article>`;}).join(''):'<p>No qualifying addition or replacement in your collection. Collect more Pokémon or review your selected moves.</p>'}
    ${button('Review this team','edit-team',teamId)}</section>`;
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
  cancelRewardSpin();
  const b=state.battle,p=b.player.members[b.player.active],active=b.status==='active';
  const exhausted=p.moves.every(m=>m.remaining_pp===0);
  const choices=exhausted?[{id:0,name:'fallback-strike',type:'neutral',remaining_pp:'∞',power:50}]:p.moves;
  main.innerHTML=heading('THE BATTLE IS YOURS','Battle arena',`${title(b.difficulty)} difficulty · ${b.team_name}`)+
    `<div class="two-col"><section><div class="arena"><div class="arena-header"><span>${b.status==='active'?'LIVE BATTLE':b.status.toUpperCase()}</span><span>${b.rules_version==='prototype-1'?'V1':'V2'} · TURN ${b.turn_count}</span></div><div class="fighters">${fighter(b.player,'YOUR PARTNER',true)}<div class="versus">VS</div>${fighter(b.opponent,'OPPONENT',false)}</div></div>
    ${active?`<h3 class="spacer">${p.hp<=0?'Choose a healthy replacement.':'What will you do?'}</h3><div class="actions">${choices.map(m=>`<button class="move-button" style="--type-color:${typeColor(m.type)}" data-action="attack" data-value="${m.id}" ${p.hp<=0||m.remaining_pp===0?'disabled':''}><strong>${esc(title(m.name))}</strong><div class="row">${tags([m.type])}<small>${m.power} power · ${m.remaining_pp} PP</small></div></button>`).join('')}</div><div class="section-title"><h4>Switch Pokémon</h4><small>${p.hp<=0?'Free replacement':'Uses your turn'}</small></div><div class="row">${b.player.members.map((m,i)=>`<button class="quiet small" data-action="switch" data-value="${i}" ${m.hp<=0||i===b.player.active?'disabled':''}>${esc(title(m.name))} · ${m.hp} HP</button>`).join('')}</div><div class="spacer">${button('Forfeit battle','forfeit','','danger small')}</div>`:
    `<section class="result"><h2>${b.status==='win'?'Victory. A new partner awaits!':b.status==='loss'?'A lesson for the next battle.':'An evenly matched battle.'}</h2>${b.status==='win'&&b.reward?rewardCase(b):`<p class="note">${b.turn_count} turns played. Adjust your team or try another difficulty.</p>`}<div class="row spacer">${button('Battle again','new-battle','','primary')}${button('View collection','go-teams')}</div></section>`}${rules(b.rules_version)}</section>
    <aside class="stack">${predictionPanel(b)}<section class="card"><h3>Battle log</h3><ol class="battle-log">${b.turns.length?b.turns.slice().reverse().map(t=>`<li><span class="turn-label">${t.kind==='turn'?'TURN '+t.number:title(t.kind).toUpperCase()}</span><br>${t.events.map(e=>esc(eventText(e))).join('<br>')}</li>`).join(''):'<li>Your opponent is ready. Choose your first move.</li>'}</ol></section><section class="card"><h4>Opponent matching</h4><p class="note">Your strength: ${b.generation.player_strength}<br>Target: ${Math.round(b.generation.target_strength)}<br>Opponent strength: ${b.generation.actual_strength}</p><small>Strength = total base stats across the team.</small></section></aside></div>`;
}
async function renderAnalytics(rulesVersion='',difficulty='') {
  const previousHistorical=document.querySelector('#historical-form');
  const historicalIds=previousHistorical?new FormData(previousHistorical):null;
  const filters=new URLSearchParams({difficulty});if(rulesVersion)filters.set('rules_version',rulesVersion);
  const [a,h,strategy]=await Promise.all([api('/analytics'),api('/battles'),api(`/analytics/strategy?${filters}`)]);const s=a.summary;
  main.innerHTML=heading('EVERY BATTLE TELLS A STORY','Battle analytics','Look back, find patterns, and make your next team stronger.')+
    `<div class="metric-grid">${metric('Completed battles',s.battles)}${metric('Win rate',s.battles?(s.wins/s.battles*100).toFixed(1)+'%':'—')}${metric('Average turns',Number(s.average_turns||0).toFixed(1))}${metric('Average duration',Math.round(s.average_seconds||0)+'s')}</div>
    <p class="note">Win rate = wins ÷ all completed battles, including draws and forfeits. Duration includes thinking time. Active battles are excluded.</p>
    <div class="two-col"><section class="card"><h3>Results by difficulty</h3>${a.difficulty.length?table(['Difficulty','Wins','Losses','Draws','Battles'],a.difficulty.map(d=>[esc(d._id),d.wins,d.losses,d.draws,d.battles])):empty('Finish your first battle to see results.')}</section><section class="card"><h3>Most-used moves</h3>${a.moves.length?table(['Move','Uses'],a.moves.map(m=>[esc(title(m.name)),m.uses])):'<p class="note">Your executed moves will appear here, including misses.</p>'}</section></div>
    <section class="card spacer"><h3>Pokémon performance</h3><p class="note">Appearances count completed battles containing the species, once per battle. Win rate describes the team result, not individual knockouts.</p>${a.pokemon.length?table(['Pokémon','Appearances','Wins','Win rate'],a.pokemon.map(p=>[esc(title(p.name)),p.appearances,p.wins,(p.wins/p.appearances*100).toFixed(1)+'%'])):empty('No completed battles yet.')}</section>
    <section class="card spacer" id="strategy-evidence"><h3>Battle strategy evidence</h3>
    <form id="strategy-form" class="toolbar"><label>Battle rules<select name="rules_version">${strategy.rules_versions.map(v=>`<option value="${esc(v)}" ${v===strategy.rules_version?'selected':''}>${esc(v)}</option>`).join('')}</select></label><label>Difficulty<select name="difficulty"><option value="">All difficulties</option>${['easy','medium','hard'].map(d=>`<option value="${d}" ${d===strategy.difficulty?'selected':''}>${title(d)}</option>`).join('')}</select></label><button class="quiet">Apply filters</button></form>
    <p><strong>${strategy.battles} completed battles</strong> under these filters. ${strategy.battles<10?'Small sample: treat patterns cautiously.':''}</p><p class="note">${esc(strategy.note)}</p>
    <h4>Damage per attempted move</h4>${strategy.moves.length?table(['Move','Attempts','Hit rate','Total damage','Damage / attempt'],strategy.moves.map(m=>[esc(title(m.name)),m.attempts,(m.hit_rate*100).toFixed(1)+'%',m.damage,m.damage_per_attempt.toFixed(1)])):'<p class="note">No player attacks in the selected battles yet.</p>'}
    <h4 class="spacer">Does repeating one move correlate with wins?</h4><p class="note">Only battles with at least ${strategy.min_attempts} player attacks. High repetition means one move accounts for at least ${strategy.dominant_share*100}% of attacks. Compare rows within the same difficulty and team size; the battle count is the sample size.</p>
    ${strategy.repetition.length?table(['Difficulty','Team size','Pattern','Battles','Wins / losses / draws','Win rate','Average top-move share'],strategy.repetition.map(r=>[esc(r._id.difficulty),r._id.team_size,esc(r._id.pattern),`${r.battles}${r.battles<10?' (small sample)':''}`,`${r.wins} / ${r.losses} / ${r.draws}`,(r.wins/r.battles*100).toFixed(1)+'%',(r.average_top_share*100).toFixed(1)+'%'])):'<p class="note">No battles with enough attempted moves under these filters.</p>'}
    <div class="spacer" id="prediction-results"><h4>Predictions and actual outcomes</h4><p class="note">Same rules/difficulty filters as above; forfeits and missing predictions excluded. Favoured + win and disadvantaged + loss count as correct directional calls. Draws and evenly matched labels are shown separately. These results do not establish a calibrated win probability.</p>${predictionResults(strategy.predictions.map(r=>({...r,_id:{...r._id,rules:strategy.rules_version}})))}</div></section>
    <section class="card spacer" id="historical-evidence"><h3>External 1v1 matchup evidence</h3><p>Loading historical matchups…</p></section>
    <section class="card spacer"><h3>Battle history</h3><p class="note">Your latest 50 battles. Open an active battle to resume it.</p>${h.battles.length?table(['Team','Difficulty','Result','Turns','Started',''],h.battles.map(b=>[esc(b.team_name),esc(b.difficulty),`<span class="badge">${b.status}</span>`,b.turn_count,esc(new Date(b.started_at).toLocaleString()),button(b.status==='active'?'Resume':'Review','review-battle',b._id,'quiet small')])):empty('Your first battle starts a new chapter.')}</section>`;
  await renderHistorical(historicalIds?.get('pokemon_id')||4,historicalIds?.get('opponent_id')||7);
}
async function renderHistorical(pokemonId=4,opponentId=7) {
  const target=document.querySelector('#historical-evidence');if(!target)return;
  const h=await api(`/analytics/historical?${new URLSearchParams({pokemon_id:pokemonId,opponent_id:opponentId})}`);
  const options=selected=>h.pokemon.map(p=>`<option value="${p.id}" ${p.id===Number(selected)?'selected':''}>${esc(title(p.name))}</option>`).join('');
  target.innerHTML=`<h3>External 1v1 matchup evidence</h3><p class="note">${esc(h.note)} Simulator rule/difficulty filters above apply to your own battles only.</p>
    <form id="historical-form" class="toolbar"><label>Pokémon<select name="pokemon_id">${options(h.pokemon_id)}</select></label><label>Opponent<select name="opponent_id">${options(h.opponent_id)}</select></label><button class="quiet">Compare matchup</button></form>
    ${h.installed?`<p class="note">Source: <a href="https://www.kaggle.com/terminus7/pokemon-challenge" target="_blank" rel="noopener noreferrer">Pokémon — Weedle's Cave</a> · ${esc(h.source.license)}. Version ${esc(h.source.manifest_sha256.slice(0,12))}.</p>
    ${h.rows.length?`<p>${h.battles} distinct source results. ${h.battles<10?'Small sample: treat these results cautiously.':''}</p>${table(['Selected Pokémon attacks','Results','Wins','Losses','Historical win rate'],h.rows.map(r=>[esc(r.attacker_role),`${r.battles}${r.battles<10?' (small sample)':''}`,r.wins,r.losses,(r.win_rate*100).toFixed(1)+'%']))}`:'<p>No historical evidence for this matchup in the approved mapped records.</p>'}`:'<p>The historical dataset has not been imported yet.</p>'}`;
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
  if(action==='open-reward')await openRewardCase();
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
    if(form.id==='strategy-form')await renderAnalytics(data.get('rules_version'),data.get('difficulty'));
    if(form.id==='historical-form')await renderHistorical(data.get('pokemon_id'),data.get('opponent_id'));
    if(form.id==='team-form'){rememberName();const d=state.draft;const saved=await api(d.id?`/teams/${d.id}`:'/teams',d.id?'PUT':'POST',{name:d.name,members:d.members.map(m=>({owned_id:m.owned_id,moves:m.moves}))});state.draft=await api(`/teams/${saved.id}`);await renderTeams();notice('Team saved. Ready when you are.');}
    if(form.id==='battle-form'){state.battle=await api('/battles','POST',{team_id:Number(data.get('team_id')),difficulty:data.get('difficulty')});drawBattle();}
  });
});
window.addEventListener('hashchange',()=>{const view=location.hash.slice(1);if(view!==state.view)run(()=>navigate(view));});
run(async()=>{await refreshSession();await navigate(location.hash.slice(1)||'pokedex');});
