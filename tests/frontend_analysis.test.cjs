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
    teamOptions:()=>'', tags:()=>'', button:()=>'', esc:String,
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

test('analysis renders before recommendations and skips the unused collection', async()=>{
  const f=fixture();
  await f.context.renderAnalysis(1);
  assert.match(f.main.html,/Team analysis/);
  assert.match(f.main.html,/Finding partners/);
  assert.deepEqual(f.calls,['/teams','/teams/1/recommendations','/teams/1/analysis']);
  f.pending.resolve({note:'Ranked in MySQL',suggestions:[],history:[]});
  await new Promise(setImmediate);
  assert.match(f.panel().innerHTML,/Ranked in MySQL/);
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
