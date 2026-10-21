'use strict';

// Presentation only: replay recorded events, then the caller renders saved state.
window.battleEffects=(()=>{
  let current=null;
  function cancel() {
    if(!current)return;
    current.cancelled=true;
    current.controller.abort();
    current.animations.forEach(animation=>animation.cancel());
    current.effects.forEach(element=>element.remove());
    current=null;
  }
  async function play(previous,next,{renderFighter,colorForType,effectivenessText,eventText}) {
    cancel();
    const arena=document.querySelector('.arena');
    if(!arena)return;
    const animated=!matchMedia('(prefers-reduced-motion: reduce)').matches&&typeof arena.animate==='function';
    const message=arena.closest('.battle-stage').querySelector('.battle-message');
    const playback={cancelled:false,animations:new Set(),effects:new Set(),controller:new AbortController()};current=playback;
    const sides={player:structuredClone(previous.player),opponent:structuredClone(previous.opponent)};
    const alive=()=>current===playback&&!playback.cancelled&&arena.isConnected;
    const sprite=side=>arena.querySelector(`[data-side="${side}"] .battle-sprite`);
    const member=side=>sides[side].members[sides[side].active];
    const render=side=>{
      if(!alive())return;
      const element=arena.querySelector(`[data-side="${side}"]`),p=member(side);
      if(Number(element.dataset.slot)!==sides[side].active){element.outerHTML=renderFighter(side,sides[side]);return;}
      element.classList.toggle('is-fainted',p.hp<=0);
      element.querySelector('.hp').setAttribute('aria-valuenow',p.hp);
      element.querySelector('.hp i').style.width=`${p.hp/p.max_hp*100}%`;
      element.querySelector('.hp-text').textContent=`${p.hp} / ${p.max_hp} HP`;
      const healthy=sides[side].members.filter(p=>p.hp>0).length;
      element.querySelector('.team-dots').textContent=sides[side].members.map(p=>p.hp>0?'●':'○').join(' ');
      element.querySelector('.team-dots').setAttribute('aria-label',`${healthy} healthy Pokémon`);
    };
    async function motion(element,frames,duration) {
      if(!animated||!alive()||!element)return;
      const animation=element.animate(frames,{duration,easing:'ease-out'});
      playback.animations.add(animation);
      try {await animation.finished;} catch { /* Navigation and pause can cancel playback. */ }
      finally {playback.animations.delete(animation);}
    }
    function wait(duration) {
      if(!alive()||duration<=0)return Promise.resolve();
      return new Promise(resolve=>{
        const signal=playback.controller.signal;
        const finish=()=>{clearTimeout(timer);signal.removeEventListener('abort',finish);resolve();};
        const timer=setTimeout(finish,duration);
        signal.addEventListener('abort',finish,{once:true});
      });
    }
    function effect(className,side,text='') {
      const element=document.createElement('span');element.className=className;element.textContent=text;
      const box=sprite(side).getBoundingClientRect(),bounds=arena.getBoundingClientRect();
      element.style.left=`${box.left-bounds.left+box.width/2}px`;
      element.style.top=`${box.top-bounds.top+box.height/2}px`;
      arena.querySelector('.battle-effects').append(element);playback.effects.add(element);
      return element;
    }
    function remove(element) {element.remove();playback.effects.delete(element);}
    try {
      for(const turn of next.turns.slice(previous.turns.length)) {
        for(const event of turn.events) {
          if(!alive())return;
          const started=performance.now();
          if(message){message.textContent=eventText(event);message.dataset.kind=event.kind;}
          const side=event.side,enemy=side==='player'?'opponent':'player';
          if(event.kind==='move') {
            const direction=side==='player'?1:-1;
            await motion(sprite(side),[{transform:'translateX(0)'},{transform:`translateX(${direction*20}px)`},{transform:'translateX(0)'}],220);
            if(!alive())return;
            const projectile=effect('battle-projectile',side);
            projectile.style.setProperty('--attack-color',colorForType(event.move_type||'normal'));
            const from=sprite(side).getBoundingClientRect(),to=sprite(enemy).getBoundingClientRect();
            const x=to.left+to.width/2-from.left-from.width/2,y=to.top+to.height/2-from.top-from.height/2;
            await motion(projectile,[{transform:'translate(-50%,-50%) scale(.5)',opacity:.3},
              {transform:`translate(calc(-50% + ${x}px),calc(-50% + ${y+(event.hit?0:-35)}px)) scale(1.2)`,opacity:1}],300);
            remove(projectile);if(!alive())return;
            member(enemy).hp=Math.max(0,member(enemy).hp-event.damage);
            member(side).hp=Math.max(0,member(side).hp-(event.recoil||0));
            render(enemy);render(side);
            const matchup=effectivenessText(event);
            const label=effect('battle-damage',enemy,!event.hit?'Miss':event.effectiveness===0?'No effect':`${matchup?matchup+'\n':''}−${event.damage} HP`);
            label.classList.toggle('battle-miss',!event.hit||event.effectiveness===0);
            label.classList.toggle('battle-type-message',Boolean(matchup));
            label.classList.toggle('battle-super-effective',event.hit&&event.effectiveness>1);
            label.classList.toggle('battle-resisted',event.hit&&event.effectiveness>0&&event.effectiveness<1);
            await Promise.all([
              motion(label,[{transform:'translate(-50%,-20%)',opacity:1},{transform:'translate(-50%,-130%)',opacity:0}],650),
              motion(sprite(enemy),event.hit&&event.damage>0?
                [{opacity:1,transform:'translateX(0)'},{opacity:.4,transform:`translateX(${direction*10}px)`},{opacity:1,transform:'translateX(0)'}]:
                [{transform:'translateY(0)'},{transform:'translateY(-12px)'},{transform:'translateY(0)'}],400)
            ]);
            remove(label);
            if(alive()&&event.recoil) {
              const recoil=effect('battle-damage',side,`−${event.recoil} recoil`);
              await motion(recoil,[{transform:'translate(-50%,-20%)',opacity:1},{transform:'translate(-50%,-130%)',opacity:0}],450);
              remove(recoil);
            }
          } else if(event.kind==='switch') {
            await motion(sprite(side),[{transform:'scale(1)',opacity:1},{transform:'scale(.2)',opacity:0}],180);
            if(!alive())return;
            const slot=event.slot??sides[side].members.findIndex(p=>p.name===event.name&&p.hp>0);
            if(slot>=0&&slot<sides[side].members.length)sides[side].active=slot;
            render(side);
            await motion(sprite(side),[{transform:'scale(.2)',opacity:0},{transform:'scale(1)',opacity:1}],250);
          } else if(event.kind==='faint') {
            await motion(sprite(side),[{transform:'translateY(0)',opacity:1},{transform:'translateY(20px)',opacity:.15}],300);
          }
          // Keep each event readable, including when reduced motion skips the effects.
          const readingTime=event.kind==='move'?1600:event.kind==='faint'?1200:1000;
          await wait(readingTime-(performance.now()-started));
        }
      }
    } finally {
      playback.effects.forEach(element=>element.remove());
      playback.animations.forEach(animation=>animation.cancel());
      if(current===playback)current=null;
    }
  }
  return {play,cancel};
})();
