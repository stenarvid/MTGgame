import fs from 'node:fs/promises';
const [url,port]=process.argv.slice(2);
const target=await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`,{method:'PUT'})).json();
const ws=new WebSocket(target.webSocketDebuggerUrl.replace('localhost','127.0.0.1'));
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
let serial=0;const pending=new Map();
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}});
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(code){const r=await call('Runtime.evaluate',{expression:`(async()=>{${code}})()`,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
try{
    await call('Page.enable');await call('Runtime.enable');
    await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url});
    for(let n=0;n<100;n++){if(await evaluate(`return !!document.querySelector('.hand .card');`))break;await new Promise(r=>setTimeout(r,100))}
    await evaluate(`for(const option of document.querySelector('#sample').options){document.querySelector('#sample').value=option.value;render();await Promise.all([...document.images].map(img=>img.decode()));}document.querySelector('#sample').value='commander_wu';render();if(document.querySelector('.hand .card').getBoundingClientRect().width!==190||document.querySelector('.board .card').getBoundingClientRect().width!==135)throw Error('Incorrect card sizes');`);
    await evaluate(`if(document.querySelector('.hand .mana-cost').textContent.match(/[WUBRG]/))throw Error('Letter mana costs');if(document.querySelectorAll('.hand .mana-pip svg').length!==2)throw Error('Missing color symbols');if(getComputedStyle(document.querySelector('.board .card-rules')).display!=='none')throw Error('Battlefield is not compact');`);
    let clean=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile('artifacts/art-game-cards.png',Buffer.from(clean.data,'base64'));
    let box=await evaluate(`const r=document.querySelector('.board .card').getBoundingClientRect();return {x:r.x+40,y:r.y+80};`);
    await call('Input.dispatchMouseEvent',{type:'mouseMoved',...box});
    await new Promise(r=>setTimeout(r,600));
    await evaluate(`if(!document.querySelector('.card-inspection-shade'))throw Error('Missing black fade');if(getComputedStyle(document.querySelector('.card-hover-preview .card-rules')).display==='none')throw Error('Hover rules hidden');if(!document.querySelector('.card-hover-preview'))throw Error('Desktop hover did not enlarge');const r=document.querySelector('.card-hover-preview').getBoundingClientRect();if(r.left<0||r.right>innerWidth||r.top<0||r.bottom>innerHeight)throw Error('Hover outside viewport');`);
    let r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await fs.writeFile('artifacts/art-game-hover.png',Buffer.from(r.data,'base64'));
    await evaluate(`document.querySelector('.art-inspect').click();if(!document.querySelector('#artInspector').open)throw Error('Inspect failed');document.querySelector('#close').click();document.querySelector('#condition').value='damaged';render();if(!document.querySelector('.board .stats').textContent.includes('damage'))throw Error('Damage state missing');`);
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await evaluate(`if(document.documentElement.scrollWidth>innerWidth)throw Error('Mobile overflow');`);
    console.log('Game-art preview passed: all art, actual widths, hover bounds, Inspect, damage and mobile layout.');
}finally{try{await call('Browser.close')}catch{}ws.close()}
