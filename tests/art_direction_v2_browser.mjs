import fs from 'node:fs/promises';
const [url,port,version='v2']=process.argv.slice(2);
const target=await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`,{method:'PUT'})).json();
const ws=new WebSocket(target.webSocketDebuggerUrl.replace('localhost','127.0.0.1'));
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
let serial=0;const pending=new Map();
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}});
function call(method,params={}){return new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})}
async function evaluate(code){const r=await call('Runtime.evaluate',{expression:`(async()=>{${code}})()`,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
try{
    await call('Page.enable');await call('Runtime.enable');
    await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
    await call('Page.navigate',{url});
    for(let n=0;n<100;n++){if(await evaluate(`return document.querySelectorAll('.sample').length===${version==='v3'?7:6};`))break;await new Promise(r=>setTimeout(r,100))}
    await evaluate(`await Promise.all([...document.images].map(img=>img.decode()));if(new Set([...document.images].map(img=>img.src)).size!==${version==='v3'?7:6})throw Error('Need six unique illustrations');if(document.documentElement.scrollWidth>innerWidth)throw Error('Desktop overflow');`);
    let r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
    await fs.writeFile(`artifacts/art-direction-${version}-desktop.png`,Buffer.from(r.data,'base64'));
    await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await evaluate(`if(document.documentElement.scrollWidth>innerWidth)throw Error('Mobile overflow');`);
    r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
    await fs.writeFile(`artifacts/art-direction-${version}-mobile.png`,Buffer.from(r.data,'base64'));
    console.log('Art direction review passed: all images decoded; desktop and mobile fit.');
}finally{try{await call('Browser.close')}catch{}ws.close()}
