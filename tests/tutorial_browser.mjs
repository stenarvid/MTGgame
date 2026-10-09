// Chromium DevTools smoke coverage without a third-party browser dependency.
import fs from 'node:fs/promises';
const [base,port]=process.argv.slice(2);
const target=await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(base)}`,{method:'PUT'})).json();
const ws=new WebSocket(target.webSocketDebuggerUrl.replace('localhost','127.0.0.1'));
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',e=>reject(Error(e.message||String(e.error))),{once:true})});
let serial=0;const pending=new Map(),errors=[];
ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text+' '+(m.params.exceptionDetails.exception?.description||''));});
ws.addEventListener('close',event=>{for(const p of pending.values())p.reject(Error('Debugger closed: '+event.code+' '+event.reason));pending.clear()});
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(Error('Debugger timeout: '+method+' '+JSON.stringify(params).slice(0,240)))},10000);pending.set(id,{resolve:r=>{clearTimeout(timer);resolve(r)},reject:e=>{clearTimeout(timer);reject(e)}});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(expression){const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;let body;try{new AsyncFunction('return ('+expression+');');body='return ('+expression+');'}catch{body=expression}const result=await call('Runtime.evaluate',{expression:'(async()=>{'+body+'})()',awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value}
async function wait(expression){for(let n=0;n<120;n++){if(await evaluate("typeof state !== 'undefined' && ("+expression+")"))return;await new Promise(r=>setTimeout(r,100))}throw Error('Timed out: '+expression)}
async function click(action){await evaluate(`document.querySelector('[data-action="${action}"]').click()`)}
async function screenshot(name,full=true){await evaluate(`await Promise.all([...document.images].filter(img=>img.getClientRects().length).map(img=>{img.loading='eager';return img.decode().catch(()=>{})}))`);await new Promise(r=>setTimeout(r,250));const result=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:full});await fs.writeFile('artifacts/tactical-'+name+'.png',Buffer.from(result.data,'base64'))}
async function mobileStage(name){
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await evaluate(`if(state&&!home)render();if(document.documentElement.scrollWidth>innerWidth+1)throw Error('Mobile ${name} overflows');const manaPrompt=document.querySelector('.mandatory-mana');if(manaPrompt){const r=manaPrompt.getBoundingClientRect();if(r.top<0||r.bottom>innerHeight)throw Error('Mobile mana prompt is offscreen');}if([...document.querySelectorAll('.card')].some(c=>!c.querySelector('.frame-ornament')))throw Error('Missing identity frame');`);
    await screenshot('mobile-'+name);await screenshot('mobile-'+name+'-viewport',false);
    await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
    await evaluate('if(state&&!home)render()');
}

try{
await call('Runtime.enable');await call('Page.enable');await call('Page.addScriptToEvaluateOnNewDocument',{source:'window.confirm=()=>true'});await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:base});await wait(`!!document.querySelector('[data-action="createTutorial"]')`);await click('createTutorial');await wait(`state?.lesson?.step==='stats'`);await evaluate(`await act('respond')`);await screenshot('tutorial-stats');
await evaluate(`const orbs=[...document.querySelectorAll('.portrait-orb')];if(orbs.length!==2||orbs.some(o=>!o.querySelector('img').complete))throw Error('Missing commander portrait orbs');for(const p of state.battle.players){if(document.querySelector('[data-health-orb="p:'+p.id+'"] .orb-health').textContent!==String(p.hp))throw Error('Orb health mismatch');}const own=document.querySelector('.own-orb').getBoundingClientRect(),enemy=document.querySelector('.enemy-orb').getBoundingClientRect();if(enemy.left>=own.left||enemy.top>=own.top)throw Error('Health orbs are not mirrored');`);
await evaluate(`home=true;await new Promise(r=>setTimeout(r,300));globalThis.realTrainingState=structuredClone(state);const sample=state.battle.players[0].hand[0];state.battle.phase='combat';state.battle.priority=0;for(const p of state.battle.players){p.board=Array.from({length:p.id===0?12:8},(_,i)=>({...sample,uid:'layout-'+p.id+'-'+i,owner:p.id,sick:false,keywords:['Guard']}));}state.battle.players[0].engines=[{...state.cards.find(c=>c.id==='c_nest'),uid:'layout-engine',owner:0}];home=false;render();home=true;`);
await screenshot('temple-crowded');
await evaluate(`if(document.querySelectorAll('.own-player>.board:not(.engine-row)>.card').length!==12)throw Error('Crowded fixture was replaced');const enemy=document.querySelector('.player:not(.own-player)>.board').getBoundingClientRect(),own=document.querySelector('.own-player>.board').getBoundingClientRect(),mana=document.querySelector('.central-mana').getBoundingClientRect();if(enemy.bottom>own.top||own.bottom>mana.top)throw Error('Crowded temple rows overlap');`);
await mobileStage('temple-crowded');
await evaluate('state=realTrainingState;home=false;signature="";render()');await click('tutorial_next');
const visited=new Set();let captured=false,targetTested=false,manaCaptured=false;
for(let n=0;n<1300;n++){
await wait('!busy');await evaluate(`await poll();if(state.stage==='battle'&&!state.battle.choice&&!['opening','grow'].includes(state.battle.phase)&&!state.priority_flow.hold)await act('hold_priority',{enabled:true});`);
const info=await evaluate(`({step:state.lesson.step,stage:state.stage,priority:state.battle.priority,phase:state.battle.phase})`);visited.add(info.step);
if(info.step==='complete')break;
if(info.phase==='grow'&&info.priority===0&&!manaCaptured){await screenshot('main-mana');await mobileStage('main-mana');manaCaptured=true;}
if(info.step==='duel'&&!targetTested&&await evaluate("state.battle.priority===0&&state.battle.players[0].hand.some(c=>c.id==='u_return'&&!castReason(c))")){
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await evaluate('render();templeHandExpanded=true;render()');
 await evaluate(`globalThis.targetCard=state.battle.players[0].hand.find(c=>c.id==='u_return');globalThis.targetUnit=state.battle.players[0].board[0];globalThis.savedMana=JSON.stringify(state.battle.players[0].mana);document.querySelector('[data-action="cast:'+targetCard.uid+'"]').click();if(templeHandExpanded)throw Error('Targeting must fold mobile hand');if(document.documentElement.scrollWidth>innerWidth+1)throw Error('Mobile temple overflows');document.querySelector('.own-player .board [data-action="target:'+targetUnit.uid+'"]').click();if(JSON.stringify(state.battle.players[0].mana)!==savedMana||!selected.target)throw Error('First target tap spent mana');`);
 await screenshot('temple-target-mobile');
 await click('cancel');
 await evaluate(`if(selected)throw Error('Cancel retained target');document.querySelector('[data-action="templeHand"]').click();document.querySelector('[data-action="cast:'+targetCard.uid+'"]').click();document.querySelector('.own-player .board [data-action="target:'+targetUnit.uid+'"]').click();document.querySelector('.own-player .board [data-action="target:'+targetUnit.uid+'"]').click();`);
 await wait('!busy');await evaluate(`if(!state.battle.stack.some(s=>s.effect==='bounce'))throw Error('Second target tap did not cast');`);
 await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});await evaluate('render()');targetTested=true;
}

if(info.step==='card_upgrade'&&!captured){await click('inventoryCard:w_recruit');await screenshot('tutorial-inventory');await mobileStage('tutorial-inventory');captured=true;}
const did=await evaluate(`
const s=state,m=s.me,b=s.battle,p=b.players[m.seat],step=s.lesson.step;let move=null;
if(s.stage==='build'){
 if(m.reward_left){const index=m.reward.findIndex(id=>legal(id));move={action:'pick',index};}
 else if(step==='card_upgrade')move={action:'upgrade_card',design:'w_recruit'};
 else if(step==='shop')move={action:'buy_item',index:0};
 else if(step==='equipment'){const uid=s.tutorial.purchased;const slot=m.equipped.includes(uid)?m.equipped.indexOf(uid):1;move={action:s.tutorial.unequipped?'equip':'unequip',uid,slot};}
 else if(step==='item_upgrade')move={action:'upgrade_item',uid:s.tutorial.purchased};
 else if(step==='boss_ready')move={action:'ready'};
 else if(m.relic_options.length)move={action:'relic',relic:m.relic_options[0]};
}else if(b.phase==='opening'){
 if(!p.kept)move={action:'keep'};else if(p.bottom_remaining)move={action:'bottom',uid:p.hand[0].uid};
}else if(b.priority===m.seat){
 if(b.phase==='grow')move={action:'color',color:state.lesson.step==='opening'?'W':((p.capacity.U||0)<2?'U':'W')};
 else if(b.choice)move={action:'choose_discard',uid:p.hand[0].uid};
 else if(b.phase==='blocks'){const a=b.attacks.find(a=>a.defender===m.seat),c=p.board.find(c=>!c.tapped);move={action:'block',blocks:a&&c?{[a.uid]:[c.uid]}:{}};}
 else if(b.phase==='combat'&&!b.stack.length)move={action:'attack',attacks:p.board.filter(c=>!c.tapped&&(!c.sick||c.keywords.includes('Haste'))).map(c=>({uid:c.uid,defender:1}))};
 else if(['main','main2'].includes(b.phase)&&!b.stack.length){const c=p.hand.find(c=>['w_recruit','u_apprentice','u_scholar'].includes(c.id)&&!castReason(c));move=c?{action:'cast',uid:c.uid}:{action:'pass'};}
 else move={action:'pass'};
}
if(move){const {action,...data}=move;
 if(['upgrade_card','buy_item','equip','unequip','upgrade_item'].includes(action)){
  if(action==='upgrade_item'||action==='equip')handleInventoryAction('inventoryItem',data.uid);
  const key=action==='upgrade_card'?action+':'+data.design:action==='buy_item'?action+':'+data.index:action==='equip'?action+':'+data.uid+':'+data.slot:action==='unequip'?action+':'+data.slot:action+':'+data.uid;
  const el=document.querySelector('[data-action="'+key+'"]');if(!el||el.disabled)throw Error('Missing enabled tutorial control '+key);
  el.click();while(busy)await new Promise(r=>setTimeout(r,40));
  if(document.querySelector('#error').style.display!=='none')throw Error(document.querySelector('#error').textContent);
 }else if(action==='attack'&&data.attacks.length){
  for(const a of data.attacks){handleTempleCombat('combatSelect',a.uid);document.querySelector('.portrait-orb[data-action="combatAssign:p:'+a.defender+'"]').click();}
  drawTempleArrows();if(!document.querySelector('.combat-arrows g path'))throw Error('Missing attacker assignment arrows');
  document.querySelector('[data-action="attack"]').click();while(busy)await new Promise(r=>setTimeout(r,40));
 }else if(action==='block'&&Object.keys(data.blocks).length){
  for(const [attacker,blockers] of Object.entries(data.blocks))for(const uid of blockers){handleTempleCombat('combatSelect',uid);document.querySelector('[data-action="combatAssign:'+attacker+'"]').click();}
  drawTempleArrows();if(!document.querySelector('.combat-arrows g path'))throw Error('Missing blocker assignment arrows');
  document.querySelector('[data-action="block"]').click();while(busy)await new Promise(r=>setTimeout(r,40));
 }else if(action==='color'){
  window.scrollTo(0,document.documentElement.scrollHeight);const prompt=document.querySelector('.mandatory-mana');if(!prompt)throw Error('Missing mandatory mana prompt');const bounds=prompt.getBoundingClientRect();if(bounds.top<0||bounds.bottom>innerHeight)throw Error('Mana prompt is offscreen');const choice=prompt.querySelector('.gem-choices [data-action="color:'+data.color+'"]');if(!choice?.querySelector('.mana-artifact'))throw Error('Missing mana gem choice');choice.click();while(busy)await new Promise(r=>setTimeout(r,40));
 }else if(action==='cast'&&!data.target){
  document.querySelector('.hand [data-action="cast:'+data.uid+'"]').click();while(busy)await new Promise(r=>setTimeout(r,40));
 }else await request('/api/action',{code:credentials.code,action,...data});
 signature='';await poll();return true;
}return false;
`);
if(!did)await new Promise(r=>setTimeout(r,150));
}
if(!targetTested)throw Error('Target interaction was not exercised');await wait(`state.lesson.step==='complete'`);await screenshot('tutorial-complete');
for(const step of ['block','mana','card_upgrade','shop','equipment','item_upgrade','boss','boss_rewards','complete'])if(!visited.has(step))throw Error('Skipped tutorial lesson '+step);
await click('tutorial_restart');await wait(`state.lesson.step==='stats'&&state.me.essence===0`);
await call('Page.reload');await wait(`state?.lesson?.step==='stats'`);
if(errors.length)throw Error(errors.join('\n'));
console.log('Playable tutorial browser passed: production combat, mana, blockers, rewards, inventory, design and item upgrades, shop, boss, mobile inventory, restart and reload.');
}finally{try{await call('Browser.close')}catch{}ws.close()}



