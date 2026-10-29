const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve=yes; reject=no;});
  return {promise, resolve, reject};
}

function fixture() {
  const pending = deferred(), calls = [];
  let panel;
  const main = {set innerHTML(value) {this.html=value; panel={innerHTML:'', setAttribute(){}};}};
  const analysis = {stats:{size:1,average_speed:50},distribution:[],matchups:[],coverage:[],budget:{total:5,limit:30}};
  const context = vm.createContext({
    state:{teams:[]}, main, stats:[],
    document:{querySelector:()=>panel},
    heading:()=>'<h1>Team analysis</h1>', metric:()=>'', table:()=>'',
    teamOptions:()=>'', tags:values=>`<div class="tags">${values.map(value=>`<span class="type ${value}">${value}</span>`).join('')}</div>`,
    button:()=>'', esc:String, title:value=>String(value).replaceAll('-',' '), typeColor:()=> '#123456',
    databaseEvidence:()=>'<details>Database evidence</details>',DB_EVIDENCE:{analysis:{}},
    api:async path=>{
      calls.push(path);
      if(path==='/teams')return {teams:[{id:1}]};
      if(path.endsWith('/recommendations'))return pending.promise;
      if(path.endsWith('/analysis'))return analysis;
      throw Error('Unexpected request: '+path);
    }
  });
  const source=fs.readFileSync('frontend/static/app.js','utf8');
  vm.runInContext(source.slice(source.indexOf('async function renderAnalysis('),source.indexOf('function predictionPanel(')), context);
  return {context, main, pending, calls, panel:()=>panel, replacePanel:()=>{panel={innerHTML:'another team',setAttribute(){}};}};
}

test('database evidence stays collapsed, identifies writes and escapes query text',()=>{
  const source=fs.readFileSync('frontend/static/app.js','utf8');
  const context=vm.createContext({esc:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')});
  vm.runInContext(source.slice(source.indexOf('function databaseEvidence('),source.indexOf('const pokemonCost')),context);
  const html=context.databaseEvidence({database:'MySQL',operation:'INSERT',data:'teams',techniques:'transaction',changes:'Yes',query:'INSERT <private>'});
  assert.match(html,/^<details class="database-evidence spacer">/);
  assert.match(html,/Changes data: Yes/);
  assert.match(html,/INSERT &lt;private&gt;/);
  assert.doesNotMatch(html,/<private>/);
  assert.deepEqual(Array.from(vm.runInContext('Object.keys(DB_EVIDENCE)',context)),['pokedex','teams','analysis','battle','analytics']);
});

test('analysis renders before recommendations and skips the unused collection', async()=>{
  const f=fixture();
  await f.context.renderAnalysis(1);
  assert.match(f.main.html,/Team analysis/);
  assert.match(f.main.html,/Finding partners/);
  assert.deepEqual(f.calls,['/teams','/teams/1/recommendations','/teams/1/analysis']);
  f.pending.resolve({suggestions:[],history:[]});
  await new Promise(setImmediate);
  assert.match(f.panel().innerHTML,/MySQL ranks eligible owned Pokémon/);
  assert.match(f.panel().innerHTML,/No eligible improvement/);
});

test('recommendation cards are concise and colour-code affected and move types',()=>{
  const f=fixture();
  const response={history:[{_id:7,battles:4,wins:3,losses:1,draws:0}],suggestions:[{
    pokemon_id:7,owned_id:21,name:'squirtle',types:['water'],replace_owned_id:null,replace_name:null,
    before:{exposure:3.5,coverage:6,weaknesses:{fire:2,water:1},covered_types:['grass']},
    after:{exposure:2.5,coverage:7,weaknesses:{fire:1,water:1},covered_types:['grass','rock']},
    budget:{total:9,limit:30},suggested_moves:[{name:'water-gun',type:'water'}],
    reason:'This deliberately verbose backend explanation should not be rendered.'
  }]};
  const html=f.context.recommendationsContent(
    {budget:{total:5,limit:30}},response,1
  );
  assert.match(html,/Add squirtle/);
  assert.match(html,/Exposure<strong>3.50 → 2.50/);
  assert.match(html,/Less weak to/);
  assert.match(html,/class="type fire"/);
  assert.match(html,/class="type rock"/);
  assert.match(html,/class="type water"/);
  assert.doesNotMatch(html,/deliberately verbose/);
});

test('late recommendations cannot overwrite a different screen or team', async()=>{
  const f=fixture();
  await f.context.renderAnalysis(1);
  f.replacePanel();
  f.pending.resolve({note:'Old response',suggestions:[],history:[]});
  await new Promise(setImmediate);
  assert.equal(f.panel().innerHTML,'another team');
});

test('recommendation failure leaves the team analysis visible', async()=>{
  const f=fixture();
  await f.context.renderAnalysis(1);
  f.pending.reject(Error('Database unavailable'));
  await new Promise(setImmediate);
  assert.match(f.main.html,/Team analysis/);
  assert.match(f.panel().innerHTML,/Database unavailable/);
});
