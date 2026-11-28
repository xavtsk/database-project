const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('frontend/static/app.js', 'utf8');
const win = (id='saved-win', trainer=1) => ({
  _id:id, trainer_id:trainer, status:'win',
  reward:{pokemon_id:7, name:'squirtle', rarity:'common', delivered:true, owned_id:42}
});

function fixture(battle=win(), storageBlocked=false) {
  const calls=[], storage=new Map();
  let rendered;
  const context=vm.createContext({
    state:{battle:null}, esc:String, title:String, img:()=>'', shinyBadge:()=>'',
    rewardOddsText:()=>'', REWARD_COLORS:{common:'#777'}, REWARD_ODDS:{easy:{}},
    button:(label,action)=>`<button data-action="${action}">${label}</button>`,
    localStorage:{
      getItem(key){if(storageBlocked)throw Error('Storage blocked');return storage.get(key);},
      setItem(key,value){if(storageBlocked)throw Error('Storage blocked');storage.set(key,value);}
    },
    document:{querySelector:()=>({})},
    api:async(path,method='GET')=>{calls.push({path,method});return structuredClone(battle);},
    navigate:async view=>{assert.equal(view,'battle');rendered=context.rewardCase(context.state.battle);}
  });
  vm.runInContext('const revealedRewards=new Set(); let rewardSpin=null;',context);
  vm.runInContext(source.slice(source.indexOf('function rewardKey('),source.indexOf('// The reference catalogue')),context);
  vm.runInContext(source.slice(source.indexOf('async function perform('),source.indexOf("document.addEventListener('click'")),context);
  return {context,calls,storage,html:()=>rendered};
}

function assertRevealed(html) {
  assert.match(html, /class="case-sealed" hidden/);
  assert.match(html, /class="case-revealed" >/);
  assert.match(html, /squirtle/);
}

for(const blocked of [false,true]) {
  test(`history win shows its saved reward without a spin, storage ${blocked?'blocked':'empty'}`,async()=>{
    const f=fixture(win(),blocked);
    await f.context.perform('review-battle','saved-win');
    assertRevealed(f.html());
    assert.equal(f.context.state.battle.reward.owned_id,42);
    assert.deepEqual(f.calls,[{path:'/battles/saved-win',method:'GET'}]);
    // A stale/programmatic Open click must not start a reel or fetch another reward.
    await f.context.openRewardCase();
    assert.equal(f.calls.length,1);
    assert.equal(vm.runInContext('rewardSpin',f.context),null);
    assertRevealed(f.context.rewardCase(f.context.state.battle));
  });
}

test('resuming an active battle keeps its first victory reveal available',async()=>{
  const f=fixture({...win(),status:'active',reward:null});
  f.context.navigate=async()=>{};
  await f.context.perform('review-battle','saved-win');
  const completed=win();
  assert.equal(f.context.rewardWasRevealed(completed),false);
  const html=f.context.rewardCase(completed);
  assert.match(html,/class="case-sealed" >/);
  assert.match(html,/class="case-revealed" hidden/);
  assert.equal(f.storage.size,0);
});

test('reviewing one reward does not suppress another battle or trainer reward',async()=>{
  const f=fixture();
  await f.context.perform('review-battle','saved-win');
  assert.equal(f.context.rewardWasRevealed(win('new-win')),false);
  assert.equal(f.context.rewardWasRevealed(win('saved-win',2)),false);
  assert.equal(f.context.rewardWasRevealed(win()),true);
});

test('pending delivery review shows its saved status without offering another spin',async()=>{
  const battle=win();battle.reward.delivered=false;
  const f=fixture(battle);
  await f.context.perform('review-battle','saved-win');
  assertRevealed(f.html());
  assert.match(f.html(),/Reward delivery pending/);
  assert.equal(f.calls.length,1);
});
