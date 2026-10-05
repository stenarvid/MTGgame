/* Presentation review: public events only, interruptible motion, independent audio buses. */
(() => {
  const fx = window.SpireFX;
  const base = {consume:fx.consume, capture:fx.capture, setTarget:fx.setTarget, configure:fx.configure, clear:fx.clear};
  const palette = {W:'#ffeeb6',U:'#68d5ff',B:'#b577e5',R:'#ff6838',G:'#72ec9c',C:'#dac398'};
  const settings = {...fx.settings, intensity:1, effectsVolume:.3, ambienceVolume:.12, musicVolume:0};
  const pending = new Map(), points = new Map(), captures = new Map(), origins = new Map();
  const jobs = [], restores = new Map(), removers = new Set();
  let battle, seen=0, identity='', selection, canvas, ctx, overlay, weather, environment;
  let frame=0, cursor={x:0,y:0}, trails=[], activeJob, jobTimer, generation=0, audio, controlsInstalled=false;
  Object.assign(fx.stats,{arrivals:0,commanderArrivals:0,combatSequences:0,departures:0,counters:0});
  base.configure({sound:false,managedPresentation:true});

  class Mixer {
    constructor() {
      this.ctx = new (window.AudioContext||window.webkitAudioContext)();
      this.master=this.ctx.createGain();
      const limiter=this.ctx.createDynamicsCompressor();
      limiter.threshold.value=-18; limiter.ratio.value=8;
      this.master.connect(limiter).connect(this.ctx.destination);
      for(const name of ['effects','ambience','music']) {
        this[name]=this.ctx.createGain();this[name].connect(this.master);
      }
      this.charge=null;this.ambienceSource=null;this.musicSources=[];this.duckUntil=0;
      this.update();
    }
    update() {
      const t=this.ctx.currentTime;
      this.master.gain.setTargetAtTime(settings.sound?1:0,t,.025);
      this.effects.gain.setTargetAtTime(settings.effectsVolume,t,.025);
      this.ambience.gain.setTargetAtTime(settings.ambienceVolume*(performance.now()<this.duckUntil?.3:1),t,.1);
      this.music.gain.setTargetAtTime(settings.musicVolume,t,.1);
      if(!settings.sound)this.stopCharge();
    }
    async resume() {
      await this.ctx.resume();
      if(document.hidden)return;
      if(!this.ambienceSource) {
        const buffer=this.ctx.createBuffer(1,this.ctx.sampleRate*8,this.ctx.sampleRate),data=buffer.getChannelData(0);
        let wind=0;
        for(let i=0;i<data.length;i++){wind=(wind+(Math.random()*2-1)*.04)/1.025;data[i]=wind*Math.min(1,i/2000,(data.length-i)/2000)}
        const source=this.ctx.createBufferSource(),filter=this.ctx.createBiquadFilter();
        source.buffer=buffer;source.loop=true;filter.type='lowpass';filter.frequency.value=800;
        source.connect(filter).connect(this.ambience);source.start();this.ambienceSource=source;
        // Optional quiet harmonic bed. Music starts muted; no song is forced on players.
        for(const frequency of [110,164.81,220]) {
          const oscillator=this.ctx.createOscillator(),gain=this.ctx.createGain();
          oscillator.frequency.value=frequency;gain.gain.value=.008;
          oscillator.connect(gain).connect(this.music);oscillator.start();this.musicSources.push(oscillator);
        }
      }
      this.syncCharge();this.update();
    }
    syncCharge() {
      const targeting=selection?.family==='fireball';
      const charged=[...pending.values()].some(p=>p.family==='fireball');
      if(!settings.sound||(!targeting&&!charged)||document.hidden){this.stopCharge();return}
      if(this.ctx.state!=='running')return;
      if(!this.charge) {
        const buffer=this.ctx.createBuffer(1,this.ctx.sampleRate*5,this.ctx.sampleRate),data=buffer.getChannelData(0);
        let brown=0,pop=0;
        for(let i=0;i<data.length;i++) {
          const noise=Math.random()*2-1;brown=(brown+.04*noise)/1.02;
          if(Math.random()<1/(this.ctx.sampleRate*.14))pop=.4+Math.random()*.6;
          pop*=Math.exp(-1/(this.ctx.sampleRate*.014));
          data[i]=(brown*.8+noise*.06+noise*pop*.7)*Math.min(1,i/1500,(data.length-i)/1500);
        }
        const source=this.ctx.createBufferSource(),filter=this.ctx.createBiquadFilter(),gain=this.ctx.createGain();
        source.buffer=buffer;source.loop=true;filter.type='lowpass';filter.frequency.value=2600;
        source.connect(filter).connect(gain).connect(this.effects);source.start();this.charge={source,filter,gain};
      }
      this.charge.gain.gain.setTargetAtTime(targeting?.48:.13,this.ctx.currentTime,.08);
    }
    stopCharge(){if(this.charge){try{this.charge.source.stop()}catch{}this.charge.source.disconnect();this.charge.filter.disconnect();this.charge.gain.disconnect();this.charge=null}}
    play(kind) {
      if(!settings.sound||this.ctx.state!=='running'||document.hidden)return;
      const t=this.ctx.currentTime,gain=this.ctx.createGain();gain.connect(this.effects);
      const heavy=['meteor','combat','fire'].includes(kind),length=heavy?.45:.25;
      gain.gain.setValueAtTime(0,t);gain.gain.linearRampToValueAtTime(heavy?.22:.09,t+.012);
      gain.gain.exponentialRampToValueAtTime(.0001,t+length);
      if(['card','combat','meteor','fire','counter','departure'].includes(kind)) {
        const buffer=this.ctx.createBuffer(1,this.ctx.sampleRate*length,this.ctx.sampleRate),data=buffer.getChannelData(0);
        for(let i=0;i<data.length;i++)data[i]=(Math.random()*2-1)*Math.exp(-i/data.length*3);
        const source=this.ctx.createBufferSource(),filter=this.ctx.createBiquadFilter();
        source.buffer=buffer;filter.type='lowpass';filter.frequency.value=kind==='meteor'?380:kind==='card'?1800:1200;
        source.connect(filter).connect(gain);source.start();source.onended=()=>{source.disconnect();filter.disconnect();gain.disconnect()};
      } else {
        const oscillator=this.ctx.createOscillator();oscillator.type=kind==='shadow'?'triangle':'sine';
        oscillator.frequency.setValueAtTime(kind==='shield'?660:330,t);
        oscillator.frequency.exponentialRampToValueAtTime(kind==='shield'?990:500,t+length);
        oscillator.connect(gain);oscillator.start();oscillator.stop(t+length+.02);
        oscillator.onended=()=>{oscillator.disconnect();gain.disconnect()};
      }
      if(heavy){this.duckUntil=performance.now()+850;this.update();setTimeout(()=>this.update(),900)}
    }
  }
  function setup() {
    if(overlay)return;
    overlay=document.createElement('div');overlay.id='presentation-layer';overlay.setAttribute('aria-hidden','true');
    canvas=document.createElement('canvas');overlay.append(canvas);document.body.append(overlay);ctx=canvas.getContext('2d');resize();
    weather=document.createElement('div');weather.className='fx-weather';weather.setAttribute('aria-hidden','true');document.body.append(weather);
    environment=document.createElement('div');environment.className='fx-environment';environment.setAttribute('aria-hidden','true');
    environment.innerHTML='<div class="fx-rune-breath"></div>'+Array.from({length:8},(_,i)=>`<i style="--x:${18+i*9}%;--delay:${i*.9}s;--duration:${7+i%3}s"></i>`).join('');document.body.append(environment);
    updateEnvironment();
  }
  function resize(){if(!canvas)return;const dpr=Math.min(devicePixelRatio||1,1.5);canvas.width=innerWidth*dpr;canvas.height=innerHeight*dpr;canvas.style.width=innerWidth+'px';canvas.style.height=innerHeight+'px';ctx.setTransform(dpr,0,0,dpr,0,0)}
  function updateEnvironment(){if(environment)environment.hidden=settings.reduced||settings.intensity===0;document.body.classList.toggle('presentation-reduced',settings.reduced)}
  function node(uid){return document.querySelector(`.board [data-uid="${CSS.escape(uid||'')}"]`)||document.querySelector(`.hand [data-uid="${CSS.escape(uid||'')}"]`)}
  function center(element){const r=element.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}}
  function point(uid,owner){const n=uid?.startsWith('p:')?document.querySelector(`[data-player="${uid}"] .player-label`)||document.querySelector(`[data-player="${uid}"] .player-summary`):node(uid)||document.querySelector(`[data-stack="${CSS.escape(uid||'')}"]`);if(n){const p=center(n);points.set(uid,p);return p}return points.get(uid)||publicHand(owner)}
  function publicHand(owner){const own=document.querySelector(`.player.own[data-player="p:${owner}"],.player.own-player[data-player="p:${owner}"]`);const n=own?document.querySelector('.hand'):document.querySelector('.opponent-hand');return n?center(n):{x:innerWidth*.5,y:owner===0?innerHeight*.85:innerHeight*.15}}
  function capture(b) {
    base.capture(b);if(!b)return;
    for(const p of b.players) {
      point('p:'+p.id,p.id);
      for(const c of [...p.board,...p.hand]) {
        const n=node(c.uid);if(!n)continue;
        points.set(c.uid,center(n));const r=n.getBoundingClientRect();
        captures.set(c.uid,{node:n.cloneNode(true),x:r.left,y:r.top,width:r.width,height:r.height});
      }
    }
    for(const s of b.stack)point(s.uid,s.owner);
    while(captures.size>96)captures.delete(captures.keys().next().value);
    while(points.size>512)points.delete(points.keys().next().value);
  }
  function family(e){return e.kind==='creature'?'arrival':e.effect==='wipe'?'meteor':e.effect==='damage'&&e.color==='R'?'fireball':e.effect==='protect'?'shield':e.effect}
  function artwork(card,e){const key=card.commander?'commander_'+e.commander_id:card.token?'token_recruit':card.id;return window.cardArtURL?window.cardArtURL(key):'/art/'+encodeURIComponent(key)}
  function arrivalSlot(owner){const board=document.querySelector(`[data-player="p:${owner}"] .board`);if(!board)return point('p:'+owner,owner);const r=board.getBoundingClientRect(),last=board.querySelector('.card-slot:last-child,.card:last-child');const lr=last?.getBoundingClientRect();return {x:Math.min(innerWidth*.79,lr?lr.right+Math.min(lr.width,150)/2+12:r.left+r.width/2),y:r.top+Math.min(140,r.height)/2}}
  function incoming(e,origin) {
    const card=e.public_card;if(!card?.id)return null;
    const slot=arrivalSlot(e.owner),n=document.createElement('div');n.className='fx-arrival-card';
    n.style.setProperty('--arrival-color',palette[e.color]||palette.C);n.style.left=slot.x+'px';n.style.top=slot.y+'px';
    const title=document.createElement('strong');title.textContent=card.name;
    const img=document.createElement('img');img.src=artwork(card,e);img.alt='';
    const stats=document.createElement('span');stats.textContent=card.attack+' / '+card.health;
    const status=document.createElement('small');status.textContent=card.commander?'Commander · pending':'Pending · can respond';
    n.append(title,img,stats,status);overlay.append(n);
    if(!settings.reduced)n.animate([{transform:`translate(calc(-50% + ${origin.x-slot.x}px),calc(-50% + ${origin.y-slot.y}px)) scale(.7)`,opacity:.1},{transform:'translate(-50%,-50%) scale(1)',opacity:.75}],{duration:settings.fast?150:340,easing:'ease-out'});
    return n;
  }

  function spellCharge(e,origin){
    const stack=document.querySelector(`[data-stack="${CSS.escape(e.action_uid)}"]`),at=stack?{x:stack.getBoundingClientRect().left-35,y:center(stack).y}:{x:innerWidth*.84,y:innerHeight*.3};
    const n=document.createElement('div');n.className='fx-pending-flame';n.style.left=at.x+'px';n.style.top=at.y+'px';overlay.append(n);
    if(!settings.reduced)n.animate([{transform:`translate(${origin.x-at.x}px,${origin.y-at.y}px) scale(.5)`,opacity:1},{transform:'translate(0,0) scale(1)',opacity:1}],{duration:500,easing:'ease-out'});
    return n;
  }
  function syncPending(b) {
    for(const s of b.stack) {
      let p=pending.get(s.uid);
      const e={...s,color:s.color||s.public_card?.color,action_uid:s.uid};
      if(!p){p={...e,family:family(e),origin:origins.get(s.uid)||publicHand(s.owner)};pending.set(s.uid,p);if(p.family==='arrival')p.actor=incoming(e,p.origin);else if(p.family==='fireball')p.actor=spellCharge(e,p.origin)}
      p.next=s.uid===b.stack.at(-1)?.uid;
      const stack=document.querySelector(`[data-stack="${CSS.escape(s.uid)}"]`);
      p.position=stack?{x:stack.getBoundingClientRect().left-22,y:center(stack).y}:p.position||{x:innerWidth*.84,y:innerHeight*.27};
      stack?.classList.toggle('fx-resolves-next',p.next);
    }
    for(const [uid,p] of pending)if(!b.stack.some(s=>s.uid===uid)){p.actor?.remove();pending.delete(uid)}
    updateWeather();audio?.syncCharge();if(pending.size||selection)wake();
  }
  function updateWeather(){if(!weather)return;weather.classList.toggle('gathering',!!(selection?.family==='meteor'||[...pending.values()].some(p=>p.family==='meteor'))&&!settings.reduced)}
  function applyBurn(card) {
    document.querySelectorAll('.fx-art-fire').forEach(n=>n.remove());
    if(!card||settings.reduced||settings.intensity===0)return;
    const n=node(card.uid),img=n?.querySelector('.illustration');if(!img)return;
    const r=n.getBoundingClientRect(),a=img.getBoundingClientRect(),fire=document.createElement('span');fire.className='fx-art-fire';
    Object.assign(fire.style,{left:(a.left-r.left)+'px',top:(a.top-r.top)+'px',width:a.width+'px',height:a.height+'px'});n.append(fire);
  }
  function setTarget(card,s) {
    base.setTarget(card,s);
    selection=s&&['cast','ability'].includes(s.action)?{...s,family:family({kind:card?.kind,effect:card?.abilities?.[s.ability]?.effect||card?.effect,color:card?.color}),owner:card?.owner}:null;
    if(selection?.family==='fireball')applyBurn(card);else document.querySelectorAll('.fx-art-fire').forEach(n=>n.remove());
    if(!selection)trails=[];
    setup();updateWeather();audio?.syncCharge();if(selection||pending.size)wake();
  }
  function restore(uid){for(const f of restores.get(uid)||[])f();restores.delete(uid)}
  function hold(e) {
    if(settings.reduced||!e.results)return;
    const before=e.results.before,after=e.results.after;
    for(const [uid,c] of Object.entries(before.cards)) {
      const a=after.cards[uid],n=node(uid);if(!n||!a||c.damage===a.damage&&c.health===a.health)continue;
      const label=n.querySelector('.stats>span:first-child'),badge=n.querySelector('.damage-badge');
      const list=[];
      if(label){const text=label.textContent;label.textContent=`${c.attack} / ${c.health-c.damage}`;list.push(()=>{if(label.isConnected)label.textContent=text})}
      if(badge){badge.style.visibility='hidden';list.push(()=>badge.style.visibility='')}
      restores.set(uid,list);
    }
    for(const [id,hp] of Object.entries(before.health)) {
      if(hp===after.health[id])continue;
      const label=document.querySelector(`[data-player="p:${id}"] .player-label b`)||document.querySelector(`[data-player="p:${id}"] .player-summary b`);
      if(label){const text=label.textContent;label.textContent=label.closest('.player-label')?String(hp):hp+' health';restores.set('p:'+id,[()=>{if(label.isConnected)label.textContent=text}])}
    }
  }
  function ghost(uid) {
    const s=captures.get(uid);if(!s)return null;
    const n=document.createElement('div');n.className='board fx-departing-card';
    Object.assign(n.style,{left:s.x+'px',top:s.y+'px',width:s.width+'px',height:s.height+'px'});
    const c=s.node.cloneNode(true);c.removeAttribute('data-uid');c.querySelectorAll('button,select').forEach(x=>x.remove());
    Object.assign(c.style,{position:'relative',width:'100%',height:'100%',transform:'none'});n.append(c);overlay.append(n);
    const cleanup=()=>{n.remove();removers.delete(cleanup)};removers.add(cleanup);return {n,cleanup};
  }
  function departure(uid,e,delay=0,existing=null) {
    const g=existing||ghost(uid);if(!g)return;
    const reason=e.effect==='bounce'?'retreat':e.effect==='exile'?'exile':e.effect==='combat'||e.effect==='fight'?'fracture':e.color==='R'||e.effect==='wipe'?'burn':'shadow';
    fx.stats.departures++;g.n.dataset.departure=reason;
    const token=generation;
    setTimeout(()=>{if(token!==generation){g.cleanup();return}restore(uid);g.n.classList.add('fx-depart-'+reason);audio?.play('departure');setTimeout(g.cleanup,settings.fast?180:420)},settings.reduced?0:delay);
  }
  function arrival(uid,e) {
    const n=node(uid);if(!n)return;
    fx.stats.arrivals++;if(e.commander)fx.stats.commanderArrivals++;
    n.dataset.arrival=e.commander?'commander':e.color||'C';n.classList.add('fx-materializing');n.style.setProperty('--arrival-color',palette[e.color]||palette.C);
    const img=n.querySelector('.illustration'),duration=settings.fast?200:e.commander?650:420;
    if(img&&!settings.reduced)img.animate([{opacity:0,filter:'brightness(2.8) blur(5px)',transform:'scale(.94)'},{opacity:1,filter:'none',transform:'none'}],{duration,easing:'ease-out'});
    const origin=pending.get(e.action_uid)?.actor;
    origin?.remove();audio?.play(e.commander?'commander':'summon');
    setTimeout(()=>n.classList.remove('fx-materializing'),duration+80);
  }
  function shake(strength) {
    if(settings.reduced||settings.intensity===0)return;
    const amount=Math.min(5,strength)*settings.intensity;
    document.querySelectorAll('.player .board').forEach(n=>n.animate([{translate:'0 0'},{translate:`${amount}px ${amount*.4}px`},{translate:`${-amount}px ${-amount*.3}px`},{translate:'0 0'}],{duration:settings.fast?120:230}));
  }
  function hit(uid,e) {
    restore(uid);const n=node(uid);if(!n)return;
    const state=e.results?.after.cards[uid];
    if(state?.protected){n.classList.add('fx-shield-impact');audio?.play('shield');setTimeout(()=>n.classList.remove('fx-shield-impact'),400)}
    else if(!settings.reduced)n.animate([{translate:'0 0',filter:'brightness(1)'},{translate:`${3*settings.intensity}px 2px`,filter:'brightness(1.6)'},{translate:'0 0',filter:'none'}],{duration:220});
  }
  function combat(e,b) {
    fx.stats.combatSequences++;hold(e);audio?.play('combat');const departed=new Map();for(const uid of e.results?.departures||[])departed.set(uid,ghost(uid));
    for(const a of e.attacks||[]) {
      const target=a.blockers[0]||'p:'+a.defender,from=point(a.uid,e.owner),to=point(target,a.defender),n=node(a.uid)||departed.get(a.uid)?.n;
      if(n&&!settings.reduced){const dx=(to.x-from.x)*.3,dy=(to.y-from.y)*.3;n.animate([{translate:'0 0'},{translate:`${dx}px ${dy}px`,offset:.4},{translate:`${dx*.8}px ${dy*.8}px`,offset:.6},{translate:'0 0'}],{duration:settings.fast?180:470,easing:'ease-in-out'})}
      setTimeout(()=>{hit(target,e);hit(a.uid,e)},settings.fast?70:190);
    }
    for(const uid of e.results?.departures||[])departure(uid,e,settings.fast?70:200,departed.get(uid));
    shake(1.5);
  }
  function perform(e,b) {
    const p=pending.get(e.action_uid);hold(e);
    if(e.outcome!=='resolved') {
      fx.stats.counters++;p?.actor?.classList.add('fx-countered-arrival');
      const at=p?.position||point(e.action_uid,e.owner),smoke=document.createElement('div');smoke.className='fx-counter-smoke';smoke.style.left=at.x+'px';smoke.style.top=at.y+'px';overlay.append(smoke);setTimeout(()=>smoke.remove(),500);
      audio?.play('counter');base.consume({...b,visual_events:[e]});return 250;
    }
    if(e.stage==='combat'){combat(e,b);return settings.fast?220:520}
    const type=family(e),duration=settings.reduced?50:settings.fast?300:type==='meteor'?1150:type==='fireball'?670:350;
    if(type==='arrival') {
      for(const uid of e.results?.entries||[e.source_uid])arrival(uid,e);
      base.consume({...b,visual_events:[{...e,target:e.source_uid}]});return settings.fast?250:550;
    }
    base.consume({...b,visual_events:[e]});
    if(type==='meteor') {
      audio?.play('meteor');shake(4);
      for(const uid of e.affected_uids||[])node(uid)?.classList.add('fx-simultaneous-hit');
      setTimeout(()=>document.querySelectorAll('.fx-simultaneous-hit').forEach(n=>n.classList.remove('fx-simultaneous-hit')),duration);
      // The core draws projectiles and impacts; synchronize local recoil and numbers with arrival.
      for(const uid of e.affected_uids||[])setTimeout(()=>hit(uid,e),settings.fast?200:650);
    } else if(type==='fireball'){audio?.play('fire');setTimeout(()=>hit(e.target,e),settings.fast?250:650)}
    else if(type==='shield'){audio?.play('shield');node(e.target)?.classList.add('fx-shield-impact');setTimeout(()=>node(e.target)?.classList.remove('fx-shield-impact'),500)}
    for(const uid of e.results?.departures||[])departure(uid,e,type==='meteor'?650:type==='fireball'?650:100);
    for(const uid of e.results?.entries||[])arrival(uid,{...e,color:e.effect==='tokens'?'W':e.color});
    return duration;
  }
  function nextJob() {
    if(activeJob||!jobs.length)return;
    activeJob=jobs.shift();const duration=perform(activeJob.e,activeJob.b),token=generation;
    jobTimer=setTimeout(()=>{if(token!==generation)return;for(const uid of [...restores.keys()])restore(uid);activeJob=null;nextJob()},duration);
  }
  function finish() {
    generation++;clearTimeout(jobTimer);jobs.length=0;activeJob=null;
    for(const uid of [...restores.keys()])restore(uid);
    for(const remove of [...removers])remove();
    document.querySelectorAll('.fx-simultaneous-hit,.fx-materializing').forEach(n=>n.classList.remove('fx-simultaneous-hit','fx-materializing'));
  }
  function consume(b,opts={}) {
    if(!b)return;setup();installControls();
    const key=b.players.map(p=>p.name+':'+p.commander).join('|'),events=b.visual_events||[];
    if(opts.initial||opts.reset||key!==identity||(events.at(-1)?.seq||0)<seen) {
      finish();pending.forEach(p=>p.actor?.remove());pending.clear();origins.clear();selection=null;
      seen=events.at(-1)?.seq||0;identity=key;battle=b;base.consume(b,{initial:true});capture(b);syncPending(b);return;
    }
    battle=b;
    for(const e of events.filter(e=>e.seq>seen)) {
      seen=e.seq;
      if(e.stage==='cast'){origins.set(e.action_uid,points.get(e.source_uid)||publicHand(e.owner));base.consume({...b,visual_events:[e]});audio?.play('card')}
      else {jobs.push({e,b});if(jobs.length>6)finish()}
    }
    // Keep a cancelled charge until its smoke begins, even though the authoritative stack has advanced.
    nextJob();syncPending(b);capture(b);
  }
  function configure(options) {
    if(options.volume!==undefined)options={...options,effectsVolume:options.volume};
    Object.assign(settings,options);base.configure({sound:false,reduced:settings.reduced,fast:settings.fast});
    audio?.update();audio?.syncCharge();updateEnvironment();if(settings.reduced)finish();installControls();
  }
  function installControls() {
    const host=document.querySelector('#motion-controls')||document.querySelector('.fx-settings');if(!host||host.querySelector('.presentation-controls'))return;
    const group=document.createElement('div');group.className='presentation-controls';
    group.innerHTML='<label>Ambience <input data-mix="ambienceVolume" type="range" min="0" max="1" step=".05" value=".12"></label><label>Music <input data-mix="musicVolume" type="range" min="0" max="1" step=".05" value="0"></label><label>Effect intensity <select id="fx-intensity"><option value="0">Off</option><option value=".5">Subtle</option><option value="1" selected>Normal</option><option value="1.4">Strong</option></select></label>';
    host.append(group);group.querySelectorAll('[data-mix]').forEach(n=>n.oninput=()=>configure({[n.dataset.mix]:Number(n.value)}));group.querySelector('#fx-intensity').onchange=e=>configure({intensity:Number(e.target.value)});
    const volume=host.querySelector('#fx-volume');if(volume?.parentElement)volume.parentElement.firstChild.textContent='Effects ';
    controlsInstalled=true;
  }
  function wake(){setup();if(!frame)frame=requestAnimationFrame(draw)}
  function glow(at,size,alpha=1) {
    ctx.save();ctx.globalAlpha=alpha;const g=ctx.createRadialGradient(at.x,at.y,1,at.x,at.y,size);
    g.addColorStop(0,'#fff0b4');g.addColorStop(.25,'#ffb148');g.addColorStop(.6,'#ff4824');g.addColorStop(1,'#970d1300');ctx.fillStyle=g;ctx.fillRect(at.x-size,at.y-size,size*2,size*2);ctx.restore();
  }
  function draw(now) {
    frame=0;ctx.clearRect(0,0,innerWidth,innerHeight);if(document.hidden||settings.reduced)return;
    if(selection?.family==='fireball') {
      trails=trails.filter(p=>now-p.time<320);
      for(let i=1;i<trails.length;i++){const a=trails[i-1],b=trails[i],age=(now-b.time)/320;ctx.strokeStyle=`rgba(255,${Math.round(80+age*60)},35,${(1-age)*.6})`;ctx.lineWidth=(1-age)*8;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.quadraticCurveTo((a.x+b.x)/2+Math.sin(now*.01+i)*6,(a.y+b.y)/2-8,b.x,b.y);ctx.stroke()}
    }
    for(const p of [...pending.values()].slice(-6)) {
      if(p.family==='fireball') {
        glow(p.position,30+Math.sin(now*.006)*5,p.next?.95:.5);
        if(p.target){const to=point(p.target,p.owner);ctx.save();ctx.globalAlpha=p.next?.3:.12;ctx.strokeStyle='#ff9959';ctx.setLineDash([5,8]);ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(p.position.x,p.position.y);ctx.quadraticCurveTo((p.position.x+to.x)/2,to.y-35,to.x,to.y);ctx.stroke();ctx.restore()}
      }
    }
    if(selection?.family==='meteor'||[...pending.values()].some(p=>p.family==='meteor')) {
      for(let i=0;i<6;i++){const x=innerWidth*(.23+i*.105),y=35+Math.sin(now*.001+i)*7;glow({x,y},16,.5);ctx.fillStyle='#392520';ctx.beginPath();ctx.moveTo(x-7,y-8);ctx.lineTo(x+9,y-5);ctx.lineTo(x+7,y+7);ctx.lineTo(x-8,y+10);ctx.closePath();ctx.fill()}
    }
    if(selection||pending.size)frame=requestAnimationFrame(draw);
  }
  function clear(){finish();pending.forEach(p=>p.actor?.remove());pending.clear();selection=null;trails=[];base.clear();audio?.stopCharge();updateWeather();ctx?.clearRect(0,0,innerWidth,innerHeight)}
  Object.assign(fx,{consume,capture,setTarget,configure,clear,finish,settings});
  Object.defineProperty(fx,'activeCrackle',{get:()=>!!audio?.charge});
  Object.defineProperty(fx,'debug',{get:()=>({audio:audio?.ctx.state,family:selection?.family,weather:weather?.classList.contains('gathering'),pending:pending.size,queued:jobs.length,controlsInstalled,reduced:settings.reduced,sound:settings.sound})});
  document.addEventListener('pointermove',e=>{cursor={x:e.clientX,y:e.clientY};if(selection?.family==='fireball'){trails.push({...cursor,time:performance.now()});if(trails.length>30)trails.shift();wake()}});
  document.addEventListener('pointerdown',e=>{if(!settings.sound)return;try{audio??=new Mixer();audio.resume().catch(()=>{})}catch{}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clear();audio?.ctx.suspend().catch(()=>{})}});
  window.addEventListener('resize',()=>{finish();resize()});
})();
