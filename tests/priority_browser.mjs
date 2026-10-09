// Real-server priority controls and desktop/mobile production layout.
import fs from 'node:fs/promises';
const [base,port,fixturePath]=process.argv.slice(2),fixtures=JSON.parse(await fs.readFile(fixturePath,'utf8'));
const target=await(await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(base)}`,{method:'PUT'})).json();
const ws=new WebSocket(target.webSocketDebuggerUrl.replace('localhost','127.0.0.1'));
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
let serial=0,checkNumber=0;const pending=new Map(),errors=[];
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text)});
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial,timer=setTimeout(()=>reject(Error('Debugger timeout: '+method)),15000);pending.set(id,{resolve:r=>{clearTimeout(timer);resolve(r)},reject:e=>{clearTimeout(timer);reject(e)}});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(code){const step=++checkNumber;let r;try{r=await call('Runtime.evaluate',{expression:`(async()=>{${code}})()`,awaitPromise:true,returnByValue:true,userGesture:true})}catch(e){throw Error('Priority evaluation '+step+': '+e.message)}if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
async function wait(expression){for(let n=0;n<120;n++){if(await evaluate(`return typeof state!=='undefined'&&${expression.includes('state')?'state&&':''}(${expression})`))return;await new Promise(r=>setTimeout(r,100))}throw Error('Timed out: '+expression+' '+await evaluate(`return JSON.stringify({phase:state?.battle?.phase,priority:state?.battle?.priority,stack:state?.battle?.stack.map(s=>s.name),choice:state?.battle?.choice,hold:state?.priority_flow?.hold,error:document.querySelector('#error')?.textContent})`))}
async function shot(name){await evaluate(`await Promise.all([...document.images].filter(i=>i.getClientRects().length).map(i=>{i.loading='eager';return i.decode().catch(()=>{})}))`);const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(`artifacts/tactical-priority-${name}.png`,Buffer.from(r.data,'base64'))}
try{
 await call('Runtime.enable');await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:base});await wait(`!!document.querySelector('[data-action="createSolo"]')`);
 await evaluate(`globalThis.fixtures=${JSON.stringify(fixtures)};seat(fixtures.battle)`);await wait(`state?.stage==='battle'&&!busy`);
 await evaluate(`if(!state.priority_flow.auto)throw Error('Auto-pass not default');if(document.querySelectorAll('.phase-marker').length!==10)throw Error('Missing own/opponent phases');if(document.querySelector('.priority-pill').textContent!=='Enter Combat')throw Error('Wrong main transition');const bar=document.querySelector('.priority-bar').getBoundingClientRect();if(bar.bottom>innerHeight+1||bar.left<0||bar.right>innerWidth+1)throw Error('Bar out of viewport');`);
 await shot('desktop');
 await evaluate(`document.querySelector('[data-action="phaseStop:own:combat"]').click()`);await wait(`!busy&&state.priority_flow.stops.length===1`);
 await evaluate(`await act('hold_priority',{enabled:true});if(!state.priority_flow.hold||state.priority_flow.auto)throw Error('Hold failed');const c=state.battle.players[0].hand[0];selectCast(c.uid);`);await wait(`state.battle.stack.length===1&&!busy`);
 await evaluate(`if(state.battle.priority!==0)throw Error('Hold lost priority');document.querySelector('[data-action="resume_auto"]').click()`);await wait(`!busy&&!state.priority_flow.hold&&state.priority_flow.auto`);
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await evaluate(`render();if(document.documentElement.scrollWidth>innerWidth+1)throw Error('Mobile horizontal overflow');const bar=document.querySelector('.priority-bar').getBoundingClientRect();if(bar.left<0||bar.right>innerWidth+1||bar.bottom>innerHeight+1)throw Error('Mobile bar outside viewport');templeHandExpanded=true;render();if(!document.querySelector('.hand-expanded'))throw Error('Hand tray failed');`);
 await shot('mobile');
 await evaluate(`const inspect=document.querySelector('.hand .art-inspect');if(inspect){inspect.click();if(!document.querySelector('#artInspector').open)throw Error('Inspection failed');document.querySelector('#artInspector').close()}`);
 await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
 await evaluate(`seat(fixtures.response)`);await wait(`!busy&&state?.battle?.priority===1`);
 await evaluate(`globalThis.friendAction=async(action,data={})=>{const auth=fixtures.response_friend;return request('/api/action',{code:auth.code,action,...data},auth)};globalThis.friendState=async()=>request('/api/state?code='+fixtures.response_friend.code,undefined,fixtures.response_friend);const f=await friendState();await friendAction('cast',{uid:f.battle.players[1].hand[0].uid,target:'p:0'});await poll();`);
 await wait(`state.battle.priority===0&&state.priority_flow.deadline&&!busy`);
 await evaluate(`globalThis.deadline=state.priority_flow.deadline;await poll();await poll();if(state.priority_flow.deadline!==deadline)throw Error('Polling reset countdown');document.querySelector('[data-action="respond"]').click()`);
 await wait(`!busy&&!state.priority_flow.auto`);
 await evaluate(`await new Promise(r=>setTimeout(r,3200));await poll();if(state.battle.priority!==0||!state.battle.stack.length)throw Error('Respond failed to pause');`);
 await shot('paused');
 await evaluate(`const counter=state.battle.players[0].hand[0];selectCast(counter.uid);const target=state.battle.stack[0].uid;document.querySelector('[data-action="target:'+target+'"]').click();app.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));if(selected)throw Error('Cancel failed');await act('resume_auto');`);
 await wait(`!busy&&state.priority_flow.auto&&state.battle.priority===1`);
 await evaluate(`const f=await friendState();await friendAction('cast',{uid:f.battle.players[1].hand[0].uid,target:'p:0'});await poll();`);
 await wait(`state.battle.priority===0&&state.priority_flow.deadline`);
 await evaluate(`globalThis.deadline=state.priority_flow.deadline`);await call('Page.reload');await wait(`state?.stage==='battle'&&state.battle.priority===0`);
 await wait(`state.battle.priority===1`);
 await evaluate(`if(state.battle.stack.length!==0)throw Error('Countdown did not resolve the passed action');if(state.battle.players[0].hp!==19)throw Error('Damage did not resolve one action at a time');`);
 await evaluate(`globalThis.fixtures=${JSON.stringify(fixtures)};seat(fixtures.transitions)`);await wait(`!busy&&state.battle.phase==='main'`);
 await evaluate(`document.querySelector('[data-action="enter_combat"]').click()`);await wait(`!busy&&state.battle.phase==='combat'`);
 await evaluate(`if(document.querySelector('.priority-pill').textContent!=='Skip Combat')throw Error('Empty combat label missing');document.querySelector('[data-action="attack"]').click()`);await wait(`!busy&&state.battle.phase==='combat_end'`);
 await evaluate(`document.querySelector('[data-action="end_combat"]').click()`);await wait(`!busy&&state.battle.phase==='main2'`);
 await evaluate(`document.querySelector('[data-action="phaseStop:own:end"]').click()`);await wait(`!busy&&state.priority_flow.stops.length===1`);
 await evaluate(`document.querySelector('[data-action="end_turn"]').click()`);await wait(`!busy&&state.battle.phase==='end'&&!state.priority_flow.auto`);
 await evaluate(`if(state.priority_flow.stops.length)throw Error('One-use stop retained');seat(fixtures.triggers)`);await wait(`!busy&&state.battle.choice?.kind==='trigger_order'`);
 await evaluate(`globalThis.expectedTriggerOrder=[...state.battle.choice.uids].reverse();document.querySelector('[data-action^="triggerLater:"]:not(:disabled)').click();if(JSON.stringify(triggerOrder)!==JSON.stringify(expectedTriggerOrder))throw Error('Order control failed');`);
 await shot('trigger-order');await evaluate(`document.querySelector('[data-action="confirmTriggerOrder"]').click()`);await wait(`!busy&&!state.battle.choice`);
 await evaluate(`if(JSON.stringify([...state.battle.stack].reverse().map(s=>s.uid))!==JSON.stringify(expectedTriggerOrder))throw Error('Server did not honor resolution order');`);
 if(errors.length)throw Error(errors.join('\n'));
 console.log('Priority browser passed: desktop/mobile action bar, phase markers, Hold, Respond, persistent countdown, immediate Resume, cancellation, hand inspection, phase progression, manual trigger ordering and one-action resolution.');
}finally{ws.close()}
