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
async function wait(expression){for(let n=0;n<120;n++){if(await evaluate("typeof state !== 'undefined' && ("+expression+")"))return;await new Promise(r=>setTimeout(r,100))}throw Error('Timed out: '+expression+' '+JSON.stringify(await evaluate(`({phase:state?.battle?.phase,priority:state?.battle?.priority,kept:state?.battle?.players.map(p=>p.kept),error:document.querySelector('#error')?.textContent,connection:connection.textContent})`))+' '+errors.join('; '))}
async function click(action){await evaluate(`document.querySelector('[data-action="${action}"]').click()`)}
async function screenshot(name,full=true){await evaluate(`await Promise.all([...document.images].filter(img=>img.getClientRects().length).map(img=>{img.loading='eager';return img.decode().catch(()=>{})}))`);await new Promise(r=>setTimeout(r,250));const result=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:full});await fs.writeFile('artifacts/tactical-'+name+'.png',Buffer.from(result.data,'base64'))}
async function mobileStage(name){
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await evaluate(`if(state&&!home)render();if(document.documentElement.scrollWidth>innerWidth+1)throw Error('Mobile ${name} overflows');if([...document.querySelectorAll('.card')].some(c=>!c.querySelector('.frame-ornament')))throw Error('Missing identity frame');`);
    await screenshot('mobile-'+name);await screenshot('mobile-'+name+'-viewport',false);
    await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
    await evaluate('if(state&&!home)render()');
}
try{
await call('Runtime.enable');await call('Page.enable');await call('Page.addScriptToEvaluateOnNewDocument',{source:'window.confirm=()=>true'});await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:base});await wait(`!!document.querySelector('[data-action="createSolo"]')`);await screenshot('rooms');await mobileStage('rooms');
await click('createSolo');await wait(`state?.stage==='lobby'`);await evaluate(`if(state.size!==2||document.querySelector('[data-action="add_bot"]'))throw Error('Solo lobby must be 1v1');`);await click('start');await wait(`state?.stage==='commanders'`);await screenshot('commanders');await mobileStage('commanders');
// Commander and package are separate, uncommitted choices until confirmation.
await evaluate(`if(document.querySelectorAll('[data-action^="pickCommander:"]').length!==3)throw Error('Expected three commanders');if(document.querySelector('[data-action^="pickPackage:"]'))throw Error('Packages visible before commander choice');document.querySelector('[data-action^="pickCommander:"]').click()`);
await wait(`!!document.querySelector('[data-action^="pickPackage:"]')`);
await evaluate(`if(state.me.commander!==null)throw Error('Commander committed too early');if(document.querySelectorAll('[data-action^="pickPackage:"]').length!==2)throw Error('Expected exactly two packages');if(!document.querySelector('[data-action="confirmCommander"]').disabled)throw Error('Confirmation must require a package')`);
await screenshot('commander-packages');await mobileStage('commander-packages');
await click('pickPackage:1');
await call('Page.reload');await wait(`commanderDraft?.package===1`);
await click('backCommander');await wait(`!!document.querySelector('[data-action^="pickCommander:"]')`);
await evaluate(`document.querySelector('[data-action^="pickCommander:"]').click()`);
await click('pickPackage:0');await click('confirmCommander');await wait(`state?.stage==='draft'`);await screenshot('draft');await mobileStage('draft');
await evaluate(`document.querySelector('[data-action^="inspect:"]').click()`);
await wait(`document.querySelector('#artInspector')?.open`);
await evaluate(`const art=document.querySelector('#artInspector .inspector-body img');if(!art||(!art.src.includes('/art/')&&!art.src.startsWith('data:image/svg+xml')))throw Error('Inspector has no artwork');await art.decode();if(!art.naturalWidth)throw Error('Inspector artwork did not load');document.querySelector('#closeInspector').click()`);
for(let n=0;n<15;n++){
    await wait(`!busy&&state?.stage==='draft'`);
    await evaluate(`document.querySelector('[data-action^="pick:"]').click()`);
    await wait(`!busy`);
}
await wait(`state?.stage==='build'`);
await evaluate(`document.querySelector('[data-action^="relic:"]').click()`);await wait(`!busy&&state.me.relic_options.length===0`);
await screenshot('build');await mobileStage('build');await click('ready');await wait(`state?.stage==='battle'`);await screenshot('mulligan');
await click('mulligan');await wait(`!busy&&state.battle.players[0].mulligan`);await click('keep');await wait(`!busy&&state.battle.players[0].kept`);
// Either seat may start. Pass human response windows during the rival's first turn.
for(let n=0;n<100;n++){if(await evaluate(`!!document.querySelector('.mandatory-mana')`))break;await evaluate(`if(!busy&&state?.battle?.priority===state.me.seat&&state.battle.active!==state.me.seat)await act('pass')`);await new Promise(r=>setTimeout(r,100))}
await wait(`!!document.querySelector('.mandatory-mana')`);await evaluate(`document.querySelector('[data-action^="color:"]').click()`);await wait(`state?.battle?.phase==='main'`);await screenshot('battle');
// Persisted seat survives a page reload, with the same hidden hand.
const hand=await evaluate(`state.battle.players[0].hand.map(c=>c.uid)`);
await call('Page.reload');await wait(`state?.stage==='battle'`);
const restored=await evaluate(`state.battle.players[0].hand.map(c=>c.uid)`);
if(JSON.stringify(hand)!==JSON.stringify(restored))throw Error('Reload changed the hand');
await evaluate(`if(state.battle.players.length!==2)throw Error('Solo battle must be 1v1')`);
const privateHands=await evaluate(`state.battle.players.slice(1).every(p=>p.hand.length===0)`);
if(!privateHands)throw Error('An opponent hand leaked');
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await evaluate(`render();if(document.documentElement.scrollWidth>innerWidth+1)throw Error('Mobile page overflows horizontally');if(getComputedStyle(document.querySelector('.decision-panel')).position!=='fixed')throw Error('Mobile decisions are not fixed');if(document.querySelectorAll('.player:not(.own-player)').length!==1)throw Error('Expected one focused battlefield')`);
await screenshot('mobile');
await call('Emulation.setDeviceMetricsOverride',{width:1500,height:1100,deviceScaleFactor:1,mobile:false});
// Two genuine bearer seats share a draft and battle; neither can read the other hand.
await evaluate(`seat(await request('/api/create',{mode:'human',name:'Host',size:2,target:5}))`);
await wait(`state?.stage==='lobby'&&state.mode==='human'`);
await evaluate(`globalThis.friend=await request('/api/join',{code:credentials.code,name:'Friend'});globalThis.friendAction=async function(action,data={}){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+friend.token},body:JSON.stringify({code:friend.code,action,...data})});const result=await r.json();if(!r.ok)throw Error(result.error)};globalThis.friendState=async function(){return (await fetch('/api/state?code='+friend.code,{headers:{Authorization:'Bearer '+friend.token}})).json()}`);
await click('start');await wait(`state?.stage==='commanders'`);
await evaluate(`document.querySelector('[data-action^="pickCommander:"]').click()`);await click('pickPackage:0');await click('confirmCommander');
await wait(`!!state.me.commander`);
await evaluate(`if(document.querySelector('[data-action^="pickCommander:"]'))throw Error('Confirmed player can still pick');const f=await friendState();await friendAction('commander',{commander:f.me.offers[0],package:1});await poll()`);
await wait(`state?.stage==='draft'`);await screenshot('human-draft');
for(let n=0;n<45;n++)await evaluate(`await act('pick',{index:0});await friendAction('pick',{index:0});await poll()`);
await wait(`state?.stage==='build'`);
await evaluate(`await act('relic',{relic:state.me.relic_options[0]});const f=await friendState();await friendAction('relic',{relic:f.me.relic_options[0]});await friendAction('ready');await act('ready')`);
await wait(`state?.stage==='battle'`);
await evaluate(`await act('respond');await friendAction('respond');await act('keep');await friendAction('keep');await poll();for(let n=0;n<20&&state.battle.phase==='draw';n++){if(state.battle.priority===state.me.seat)await act('pass');else await friendAction('pass');await poll()}if(state.battle.active===state.me.seat)await act('color',{color:commander(state.me.commander).colors[0]});else{const f=await friendState();await friendAction('color',{color:f.commanders.find(c=>c.id===f.me.commander).colors[0]});await poll()}`);
await wait(`state?.battle?.phase==='main'`);
await evaluate(`const f=await friendState();if(f.battle.players[state.me.seat].hand.length||state.battle.players[f.me.seat].hand.length)throw Error('Cross-seat hand leak');if(f.battle.players[f.me.seat].hand.length<5)throw Error('Friend hand missing');if(state.battle.priority===state.me.seat){await act('pass');await friendAction('pass')}else{await friendAction('pass');await act('pass')}await poll()`);
await wait(`state?.battle?.phase==='precombat'`);
await screenshot('human-battle');
await evaluate(`if(!document.querySelector('#timer'))throw Error('Decision timer missing');const cards=[...document.querySelectorAll('.hand .card')];if(!cards.every(c=>c.querySelector('.action-hint')))throw Error('Hand guidance missing');const unavailable=cards.find(c=>c.getAttribute('aria-disabled')==='true');if(unavailable){const size=state.battle.stack.length;unavailable.click();if(state.battle.stack.length!==size||busy)throw Error('Unavailable card submitted an action');unavailable.querySelector('.art-inspect').click();if(!document.querySelector('#artInspector').open)throw Error('Unavailable card cannot be inspected');document.querySelector('#closeInspector').click()}`);
// End the isolated duel through the genuine concession route and review winner rewards.
await evaluate(`for(let n=0;n<20;n++){const f=await friendState();if(f.battle.priority===f.me.seat){await friendAction('concede');break}const b=state.battle;if(b.phase==='combat'&&!b.stack.length)await act('attack',{attacks:[]});else if(b.phase==='blocks')await act('block',{blocks:{}});else if(b.phase==='grow')await act('color',{color:commander(state.me.commander).colors[0]});else await act('pass');}await poll()`);
await wait(`state?.stage==='build'&&state.me.reward_left===2`);
await evaluate(`if(getComputedStyle(document.querySelector('#error')).display!=='none')throw Error('Stale battle error persisted into rewards')`);await screenshot('rewards');await mobileStage('rewards');
await evaluate(`if(!document.querySelector('.build-actions [data-action="ready"]').disabled)throw Error('Rewards can be skipped');for(let n=0;n<2;n++)await act('pick',{index:state.me.reward.findIndex(legal)});if(state.me.reward_left||document.querySelector('.build-actions [data-action="ready"]').disabled)throw Error('Reward completion did not unlock battle');SpireFX.configure({reduced:true});if(!document.body.classList.contains('presentation-reduced'))throw Error('Reduced motion ignored');`);

// Every subject loads, retains distinct art, and is visible beside its rules for review.
await evaluate(`globalThis.artSubjects=[...state.cards.filter(c=>c.art_style!=='sigil').map(c=>({...c,key:c.id})),...state.commanders.map(c=>({...c,key:'commander_'+c.id,text:c.packages.map(p=>p.name+': '+p.description).join(' / ')})),...state.relics.map(c=>({...c,key:'relic_'+c.id}))];globalThis.artLoads=await Promise.all(artSubjects.map(async c=>{const img=new Image();img.src='/art/'+c.key;await img.decode();return img.naturalWidth>0}));if(!artLoads.every(Boolean))throw Error('Missing subject artwork');if(new Set(artSubjects.map(c=>c.key)).size!==62)throw Error('Expected 62 unique playable illustrations')`);
for(let group=0;group<4;group++){
    await evaluate(`app.innerHTML='<h2>Illustration review ${group+1}/4</h2><div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px">'+artSubjects.slice(${group*16},${group*16+16}).map(c=>'<article class="panel" style="margin:0;padding:12px"><img style="width:100%;height:250px;object-fit:contain;background:#0a1420" src="/art/'+c.key+'"><h3 style="font-size:18px">'+esc(c.name)+'</h3><p style="font-size:12px">'+esc(c.text|| (c.keywords||[]).join(', '))+'</p></article>').join('')+'</div>'`);
    await screenshot('art-review-'+(group+1));
}
if(errors.length)throw Error(errors.join('\n'));
console.log('Browser smoke passed: solo setup/battle/reload, mobile rendering, two-seat 45-pick human draft, relics, private hands, shared priority, full mobile journey, reward completion and contextual casting explanations.');
}finally{try{await call('Browser.close')}catch{}ws.close()}
