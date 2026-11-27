const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function fixture() {
  const calls=[];
  let fail=false;
  const context=vm.createContext({state:{csrf:'test'}, fetch:async(path,options)=>{
    calls.push({path,options});
    return {headers:{get:()=> 'application/json'},ok:!fail,status:fail?503:200,
      json:async()=>fail?{error:'Temporary failure'}:{request:calls.length}};
  }});
  const source=fs.readFileSync('frontend/static/app.js','utf8');
  vm.runInContext(source.slice(source.indexOf('const catalogueResponses'),source.indexOf('function notice(')),context);
  return {context,calls,setFailure:value=>{fail=value;}};
}

test('revisiting a catalogue page avoids refetching and filters stay distinct',async()=>{
  const f=fixture();
  const original=await f.context.api('/pokemon?q=&type=');
  await f.context.api('/pokemon?q=pika&type=');
  assert.equal(await f.context.api('/pokemon?q=&type='),original);
  assert.equal(f.calls.length,2);
});

test('teams, collection, session and battle data always request current data',async()=>{
  const f=fixture();
  for(const path of ['/teams','/collection','/session','/battles','/analytics']){
    const first=await f.context.api(path),second=await f.context.api(path);
    assert.notEqual(first.request,second.request);
  }
  assert.equal(f.calls.length,10);
});

test('a failed catalogue request can be retried and a fresh browser starts empty',async()=>{
  const f=fixture();
  f.setFailure(true);
  await assert.rejects(f.context.api('/pokemon/25'),/Temporary failure/);
  f.setFailure(false);
  await f.context.api('/pokemon/25');
  await f.context.api('/pokemon/25');
  assert.equal(f.calls.length,2);
  const refreshed=fixture();
  await refreshed.context.api('/pokemon/25');
  assert.equal(refreshed.calls.length,1);
});

test('catalogue cache is bounded when many searches are entered',async()=>{
  const f=fixture();
  for(let index=0;index<21;index++)await f.context.api('/pokemon?q='+index);
  await f.context.api('/pokemon?q=0');
  assert.equal(f.calls.length,22);
});
