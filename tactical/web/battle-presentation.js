/* Presentation review: public events only, interruptible motion, independent audio buses. */
(() => {
  const fx = window.SpireFX;
  const base = {consume:fx.consume, capture:fx.capture, setTarget:fx.setTarget, configure:fx.configure, clear:fx.clear};
  const palette = {W:'#ffeeb6',U:'#68d5ff',B:'#b577e5',R:'#ff6838',G:'#72ec9c',C:'#dac398'};
  const settings = {...fx.settings, intensity:1, effectsVolume:.3, ambienceVolume:.12, musicVolume:0};
  const pending = new Map(), points = new Map(), captures = new Map(), origins = new Map();
  const removers = new Set(), numberSlots = new Map();
  const stateAnimations = new Set(), localAnimations = new Map();
  let lastImpactSound=0;
  let battle, seen=0, identity='', selection, canvas, ctx, overlay, weather, environment;
  let frame=0, cursor={x:0,y:0}, trails=[], generation=0, audio, controlsInstalled=false;
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
      this.ambience.gain.setTargetAtTime(battle?settings.ambienceVolume*(performance.now()<this.duckUntil?.3:1):0,t,.1);
      this.music.gain.setTargetAtTime(battle?settings.musicVolume:0,t,.1);
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
      if(kind==='counter'){
        [1870,2630,3490,4670].forEach((frequency,i)=>{const at=this.ctx.currentTime+i*.025,o=this.ctx.createOscillator(),g=this.ctx.createGain();o.frequency.setValueAtTime(frequency,at);o.frequency.exponentialRampToValueAtTime(frequency*.85,at+.18);g.gain.setValueAtTime(.0001,at);g.gain.exponentialRampToValueAtTime(.06,at+.003);g.gain.exponentialRampToValueAtTime(.0001,at+.18);o.connect(g).connect(this.effects);o.start(at);o.stop(at+.2);o.onended=()=>{o.disconnect();g.disconnect()}});
      }
      if(['socket','tick','treasure','rare'].includes(kind)){
        const notes=kind==='socket'?[880,1320]:kind==='tick'?[920]:kind==='rare'?[330,440,660,880,1320]:[330,440,660];
        notes.forEach((frequency,i)=>{const at=this.ctx.currentTime+i*.085,o=this.ctx.createOscillator(),g=this.ctx.createGain();o.type=kind==='tick'?'triangle':'sine';o.frequency.value=frequency;g.gain.setValueAtTime(.0001,at);g.gain.exponentialRampToValueAtTime(kind==='tick'?.035:.12,at+.008);g.gain.exponentialRampToValueAtTime(.0001,at+(kind==='tick'?.045:.42));o.connect(g).connect(this.effects);o.start(at);o.stop(at+(kind==='tick'?.05:.45));o.onended=()=>{o.disconnect();g.disconnect()}});return;
      }
      const t=this.ctx.currentTime,gain=this.ctx.createGain();gain.connect(this.effects);
      if(kind==='combat'&&performance.now()-lastImpactSound<65)return;
      if(kind==='combat')lastImpactSound=performance.now();
      const heavy=['meteor','fire'].includes(kind),length=kind==='counter'?.32:kind==='departure'?.14:kind==='combat'?.09:heavy?.45:.25;
      gain.gain.setValueAtTime(0,t);gain.gain.linearRampToValueAtTime(heavy?.22:.09,t+.012);
      gain.gain.exponentialRampToValueAtTime(.0001,t+length);
      if(['card','combat','meteor','fire','counter','departure'].includes(kind)) {
        const buffer=this.ctx.createBuffer(1,this.ctx.sampleRate*length,this.ctx.sampleRate),data=buffer.getChannelData(0);
        for(let i=0;i<data.length;i++)data[i]=(Math.random()*2-1)*Math.exp(-i/data.length*3);
        const source=this.ctx.createBufferSource(),filter=this.ctx.createBiquadFilter();
        source.buffer=buffer;filter.type='lowpass';filter.frequency.value=kind==='meteor'?380:kind==='counter'?6500:kind==='departure'?3800:kind==='card'?1800:1200;
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
  function updateEnvironment(){if(overlay)overlay.style.opacity=String(Math.min(1,settings.intensity));if(environment)environment.hidden=!battle||settings.reduced||settings.intensity===0;document.body.classList.toggle('presentation-reduced',settings.reduced);document.body.classList.toggle('presentation-off',settings.intensity===0)}
  function node(uid){return document.querySelector(`.board [data-uid="${CSS.escape(uid||'')}"]`)||document.querySelector(`.hand [data-uid="${CSS.escape(uid||'')}"]`)||document.querySelector(`.players [data-uid="${CSS.escape(uid||'')}"]`)}
  function center(element){const r=element.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}}
  function point(uid,owner){const n=uid?.startsWith('p:')?document.querySelector(`[data-health-orb="${uid}"]`)||document.querySelector(`[data-player="${uid}"] .player-label`)||document.querySelector(`[data-player="${uid}"] .player-summary`):node(uid)||document.querySelector(`[data-stack="${CSS.escape(uid||'')}"]`);if(n){const raw=center(n);if(!n.getClientRects().length||raw.y<0||raw.y>innerHeight||raw.x<0||raw.x>innerWidth){const summary=document.querySelector(`[data-player="p:${owner}"] .player-summary,[data-player="p:${owner}"] .player-label`);if(summary){const r=center(summary);return {x:Math.max(24,Math.min(innerWidth-24,r.x)),y:Math.max(64,Math.min(innerHeight-160,r.y))}}}const p={x:Math.max(24,Math.min(innerWidth-24,raw.x)),y:Math.max(24,Math.min(innerHeight-40,raw.y))};points.set(uid,p);return p}return points.get(uid)||publicHand(owner)}
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
  function family(e){if(e.kind==='creature')return 'arrival';if(e.effect==='damage')return e.color==='R'?'fireball':'strike';return {wipe:'meteor',protect:'shield',draw:'wisdom',filter:'wisdom',loot:'wisdom',bounce:'wave',revive:'portal',recall:'portal',buff:'growth',permanent_buff:'growth',ramp:'roots',mana:'roots',destroy:'shadow',remove_engine:'shatter',team_buff:'rally',anthem:'rally',goad:'provocation',fight:'clash',ready:'wind',bargain:'sacrifice'}[e.effect]||e.effect||'sigil'}
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

  function chargeGlyph(kind){
 const glyphs={strike:'M15 75L85 25M35 80L90 45M10 55L60 10',shield:'M50 12L80 25Q84 65 50 86Q16 65 20 25Z M35 40L50 55 68 33',wisdom:'M50 30Q30 15 15 25V70Q35 60 50 76Q65 60 85 70V25Q65 15 50 30V76',growth:'M50 90Q30 40 50 10M47 50Q5 50 22 20Q47 20 47 50M50 65Q92 60 80 35Q52 38 50 65',roots:'M50 10V40Q20 50 15 90M50 40Q80 50 85 90M50 40V92',wave:'M10 60Q30 10 48 48T90 30M10 75Q30 25 48 63T90 45',wind:'M10 35Q85 10 85 35T35 55M10 70Q70 40 90 65',counter:'M50 10L90 50 50 90 10 50Z M30 30L70 70M70 30L30 70',shatter:'M50 10L85 32 78 75 50 92 22 75 15 32Z M50 10V92M15 32L78 75M85 32L22 75',rally:'M25 85V15L80 30 25 50M50 85V55',provocation:'M15 70L75 15 50 48 85 35 25 85',clash:'M15 70L85 20M15 50L70 10M35 85L90 40',portal:'M50 10C95 10 95 90 50 90C5 90 5 10 50 10M50 25C75 25 75 75 50 75C25 75 25 25 50 25',drain:'M20 80Q90 60 30 15M50 85Q10 55 80 20',shadow:'M20 80Q90 60 30 15M50 85Q10 55 80 20',sacrifice:'M50 10L88 76H12Z M35 40L65 70M65 40L35 70',heal:'M50 15V85M15 50H85',banish:'M50 10V90M10 50H90M22 22L78 78M78 22L22 78'};
 return '<svg viewBox="0 0 100 100"><circle class="sigil-orbit" cx="50" cy="50" r="44"/><path d="'+(glyphs[kind]||glyphs.counter)+'"/><circle class="sigil-core" cx="50" cy="50" r="4"/></svg>';
 }
 function spellCharge(e,origin){
    const stack=document.querySelector(`[data-stack="${CSS.escape(e.action_uid)}"]`),at=stack?{x:stack.getBoundingClientRect().left-35,y:center(stack).y}:{x:innerWidth*.84,y:innerHeight*.3};
    const n=document.createElement('div');const kind=family(e);n.className=kind==='fireball'?'fx-pending-flame':'fx-pending-sigil';n.dataset.family=kind;n.style.setProperty('--charge-color',palette[e.color]||palette.C);if(kind!=='fireball')n.innerHTML=chargeGlyph(kind);n.style.left=at.x+'px';n.style.top=at.y+'px';overlay.append(n);
    if(!settings.reduced)n.animate([{translate:'0 8px',opacity:.5},{translate:'0 0',opacity:1}],{duration:100,easing:'ease-out'});
    return n;
  }
  function syncPending(b) {
    for(const s of b.stack) {
      let p=pending.get(s.uid);
      const e={...s,color:s.color||s.public_card?.color,action_uid:s.uid};
      if(!p){p={...e,family:family(e),origin:origins.get(s.uid)||publicHand(s.owner)};pending.set(s.uid,p);if(!settings.reduced&&settings.intensity!==0){if(p.family==='arrival')p.actor=incoming(e,p.origin);else if(p.family!=='meteor')p.actor=spellCharge(e,p.origin)}}
      p.next=s.uid===b.stack.at(-1)?.uid;if(!p.actor&&!settings.reduced&&settings.intensity!==0){if(p.family==='arrival')p.actor=incoming(e,p.origin);else if(p.family!=='meteor')p.actor=spellCharge(e,p.origin)}
      const stack=document.querySelector(`[data-stack="${CSS.escape(s.uid)}"]`);
      p.position=stack?{x:stack.getBoundingClientRect().left-22,y:center(stack).y}:p.position||{x:innerWidth*.84,y:innerHeight*.27};
      if(p.actor&&p.family!=='arrival'){p.actor.style.left=p.position.x+'px';p.actor.style.top=p.position.y+'px';p.actor.hidden=settings.intensity===0||settings.reduced}stack?.classList.toggle('fx-resolves-next',p.next);
    }
    for(const [uid,p] of pending)if(!b.stack.some(s=>s.uid===uid)){p.actor?.remove();pending.delete(uid)}
    updateWeather();audio?.syncCharge();if(pending.size||selection)wake();
  }
  function updateWeather(){if(!weather)return;weather.classList.toggle('gathering',!!(selection?.family==='meteor'||[...pending.values()].some(p=>p.family==='meteor'))&&!settings.reduced&&settings.intensity!==0)}
  function applyBurn(card) {
    document.querySelectorAll('.fx-art-fire,.fx-art-aura').forEach(n=>n.remove());
    if(!card||settings.reduced||settings.intensity===0)return;
    const n=node(card.uid),img=n?.querySelector('.illustration');if(!img)return;
    const r=n.getBoundingClientRect(),a=img.getBoundingClientRect(),fire=document.createElement('span');fire.className='fx-art-fire';
    Object.assign(fire.style,{left:(a.left-r.left)+'px',top:(a.top-r.top)+'px',width:a.width+'px',height:a.height+'px'});n.append(fire);
  }
  function setTarget(card,s) {
    base.setTarget(card,s);
    selection=s&&['cast','ability'].includes(s.action)?{...s,family:family({kind:card?.kind,effect:card?.abilities?.[s.ability]?.effect||card?.effect,color:card?.color}),owner:card?.owner}:null;
    document.querySelectorAll('.fx-art-fire,.fx-art-aura').forEach(n=>n.remove());
    if(!selection)trails=[];
    setup();updateWeather();audio?.syncCharge();if(selection||pending.size)wake();
  }
  // Keep server labels current; decorate outcomes without rewriting authoritative state.
  function local(n,frames,duration,easing='linear') {
    if(!n||settings.intensity===0)return;
    localAnimations.get(n)?.cancel();
    const animation=n.animate(settings.reduced?[{outline:'2px solid #e8d9ac'},{outline:'2px solid transparent'}]:frames,{duration:settings.reduced?120:duration,easing});
    localAnimations.set(n,animation);stateAnimations.add(animation);
    const done=()=>{stateAnimations.delete(animation);if(localAnimations.get(n)===animation)localAnimations.delete(n)};
    animation.finished.then(done,done);
  }
  function recipient(uid){return uid?.startsWith('p:')?document.querySelector('[data-health-orb="'+uid+'"]'):node(uid)}
  function cueAt(text,at,color='#ffe8a4',heal=false){
    if(settings.intensity===0)return;
    const n=document.createElement('span');n.className='fx-state-number';n.textContent=text;n.style.color=color;
    n.style.left=at.x+'px';n.style.top=at.y+'px';overlay.append(n);
    const remove=()=>{n.remove();removers.delete(remove)};removers.add(remove);setTimeout(remove,450);
    n.animate(settings.reduced||heal?[{opacity:1,transform:'translate(-50%,-100%)'},{opacity:0,transform:'translate(-50%,-100%)'}]:
      [{opacity:0,transform:'translate(-50%,-100%) scale(.8)'},{opacity:1,transform:'translate(-50%,-100%) scale(1.12)',offset:40/450},{opacity:0,transform:'translate(-50%,-100%) scale(1)'}],{duration:450}).finished.then(remove,remove);return remove;
  }
  function numberAt(uid,text,color,heal=false,actor=null){const n=actor||recipient(uid),at=point(uid);if(n){const r=n.getBoundingClientRect();at.x=r.right-12;at.y=r.top+18}numberSlots.get(uid)?.();const cleanup=cueAt(text,at,color,heal);numberSlots.set(uid,cleanup);while(numberSlots.size>96){const key=numberSlots.keys().next().value;numberSlots.get(key)?.();numberSlots.delete(key)}return cleanup}
  function edge(n,color='#ffe8a4',duration=180){local(n,[{boxShadow:'inset 0 0 0 2px '+color},{boxShadow:'inset 0 0 0 0 transparent'}],duration)}
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
    setTimeout(()=>{if(token!==generation){g.cleanup();return}g.n.classList.add(settings.reduced?'fx-depart-static':'fx-depart-'+reason);audio?.play('departure');setTimeout(g.cleanup,settings.reduced?120:220)},settings.reduced?0:delay);
  }
  function arrival(uid,e) {
    const n=node(uid);if(!n)return;
    fx.stats.arrivals++;if(e.commander)fx.stats.commanderArrivals++;
    n.dataset.arrival=e.commander?'commander':e.color||'C';n.classList.add('fx-materializing');n.style.setProperty('--arrival-color',palette[e.color]||palette.C);
    const duration=220,from=origins.get(e.action_uid)||publicHand(e.owner),to=center(n);
    if(!settings.reduced)local(n,[{opacity:.6,translate:(from.x-to.x)+'px '+(from.y-to.y)+'px',easing:'ease-out'},
      {opacity:1,translate:'0 0',offset:160/220},{opacity:1,translate:'0 0'}],duration);
    const origin=pending.get(e.action_uid)?.actor;
    origin?.remove();audio?.play(e.commander?'commander':'summon');
    const token=generation;setTimeout(()=>{if(token===generation)edge(n,palette[e.color]||palette.C,60)},settings.reduced?0:160);setTimeout(()=>n.classList.remove('fx-materializing'),duration);
  }
  function shake() {
    if(settings.reduced||settings.intensity===0)return;
    local(document.querySelector('.temple-table')||document.querySelector('.players'),[{translate:'0 0'},{translate:'3px 0'},{translate:'-2px 0'},{translate:'0 0'}],100);
  }
  function hit(uid,e,detail=null,actor=null) {
    const n=actor||recipient(uid),before=e.results?.before.cards[uid],after=e.results?.after.cards[uid];
    const amount=detail?.dealt??(before&&after?Math.max(0,after.damage-before.damage):0);
    const prevented=detail?detail.attempted>detail.dealt:before?.protected&&['damage','wipe','fight'].includes(e.effect);
    let cleanup;
    if(prevented){edge(n,'#fff7c6');if(!amount)cleanup=numberAt(uid,'Blocked','#fff7c6');audio?.play('shield')}
    if(amount>0){
      cleanup=numberAt(uid,'−'+amount,'#ffb09a',false,n);
      const lethal=detail?amount>=detail.remaining:(e.results?.departures||[]).includes(uid);
      const heavy=!lethal&&amount>=(detail?.remaining??Math.max(1,(before?.health||1)-(before?.damage||0)))*.5;
      const distance=(heavy?6:5)*Math.min(1,settings.intensity);
      local(n,[{translate:'0 0',outline:'2px solid transparent'},{translate:distance+'px 0',outline:heavy?'3px solid #ffe1b8':'2px solid #eed5b2',offset:.2},{translate:-distance*.6+'px 0',offset:.5},{translate:distance*.2+'px 0',offset:.8},{translate:'0 0'}],120);
      audio?.play(lethal?'departure':'combat');
    }
    return cleanup;
  }
  function combat(e,b) {
    fx.stats.combatSequences++;
    const attacks=e.attacks||[],departed=new Map(),scheduledDeaths=new Set();
    for(const uid of e.results?.departures||[])departed.set(uid,ghost(uid));
    const stagger=attacks.length>1?Math.min(80,270/(attacks.length-1)):0,token=generation,started=performance.now(),cleanups=new Set(),animations=new Set();
    const later=(f,delay)=>setTimeout(()=>{if(token!==generation||performance.now()-started>=900)return;const existing=new Set(stateAnimations);f();for(const a of stateAnimations)if(!existing.has(a))animations.add(a)},settings.reduced?0:delay);
    setTimeout(()=>{for(const cleanup of cleanups)cleanup?.();for(const g of departed.values())g?.cleanup();for(const a of animations)a.cancel()},900);
    attacks.forEach((a,i)=>{
      const contacts=(e.hits||[]).filter(h=>h.source===a.uid||a.blockers.includes(h.source)&&h.target===a.uid);
      const target=a.blockers[0]||'p:'+a.defender,from=point(a.uid,e.owner),to=point(target,a.defender);
      const attacker=node(a.uid)||departed.get(a.uid)?.n;
      later(()=>{
        if(!settings.reduced){let dx=to.x-from.x,dy=to.y-from.y;
          // Leading edges collide; the attacking card must not cover the defender's stats.
          const ar=attacker?.getBoundingClientRect(),tr=recipient(target)?.getBoundingClientRect()||captures.get(target);
          if(ar&&tr){const fraction=Math.max(0,Math.abs(dx)>0?1-(ar.width+tr.width)/2/Math.abs(dx):0,Math.abs(dy)>0?1-(ar.height+tr.height)/2/Math.abs(dy):0);dx*=fraction;dy*=fraction;}

          local(attacker,[{translate:'0 0',easing:'ease-out'},{translate:-dx*.04+'px '+-dy*.04+'px',offset:70/365,easing:'cubic-bezier(.55,0,1,1)'},{translate:dx+'px '+dy+'px',offset:180/365},{translate:dx+'px '+dy+'px',offset:225/365,easing:'ease-out'},{translate:'0 0'}],365);}
      },i*stagger);
      later(()=>{
        const grouped=new Map();for(const h of contacts){const prev=grouped.get(h.target);if(prev){prev.dealt+=h.dealt;prev.attempted+=h.attempted}else grouped.set(h.target,{...h})}
        for(const [uid,h] of grouped){cleanups.add(hit(uid,e,h,uid===a.uid?(attacker?.querySelector('.illustration')||attacker):departed.get(uid)?.n));
          if(departed.has(uid)&&!scheduledDeaths.has(uid)){scheduledDeaths.add(uid);departure(uid,e,0,departed.get(uid));}}
      },180+i*stagger);
    });
    for(const [uid,g] of departed)later(()=>{if(!scheduledDeaths.has(uid)){scheduledDeaths.add(uid);departure(uid,e,0,g)}},180+Math.max(0,attacks.length-1)*stagger);
    const major=Object.entries(e.results?.before.health||{}).some(([id,hp])=>hp-e.results.after.health[id]>=5||e.results.after.health[id]<=0);
    if(major)later(shake,180);
    for(const [id,hp] of Object.entries(e.results?.before.health||{}))if(e.results.after.health[id]>hp)later(()=>cleanups.add(numberAt('p:'+id,'+'+(e.results.after.health[id]-hp),'#86ffc5',true)),180);
  }
  function resultCues(e,only=null){
    const before=e.results?.before,after=e.results?.after;if(!before||!after)return;
    for(const [uid,c] of Object.entries(before.cards)){
      if(only&&uid!==only)continue;
      const a=after.cards[uid];if(a&&a.damage>c.damage)hit(uid,e,{dealt:a.damage-c.damage,attempted:a.damage-c.damage,remaining:c.health-c.damage});
      else if(c.protected&&uid===e.target&&['damage','wipe','fight'].includes(e.effect))hit(uid,e);
      if(a&&(a.attack!==c.attack||a.health!==c.health||a.protected!==c.protected))edge(node(uid),'#e7f0ae',250);
    }
    for(const [id,hp] of Object.entries(before.health)){
      if(only&&only!=='p:'+id||e.delegated_health?.includes(id))continue;
      const change=after.health[id]-hp;if(change)numberAt('p:'+id,(change>0?'+':'−')+Math.abs(change),change>0?'#86ffc5':'#ffb09a',change>0);
      if(change>0)local(recipient('p:'+id),[{boxShadow:'inset 0 0 18px #86ffc550'},{boxShadow:'inset 0 0 0 2px #86ffc5'},{boxShadow:'inset 0 0 0 0 transparent'}],180);
      if(change<0)edge(recipient('p:'+id),'#ffb09a',120);
    }
    if(e.effect==='heal'&&after.health[String(e.owner)]===before.health[String(e.owner)])numberAt('p:'+e.owner,'+0','#86ffc5',true);
  }
  function counter(e,p){
    const at=p?.position||point(e.action_uid,e.owner),reduced=e.outcome!=='countered'||settings.reduced||settings.intensity<1;
    cueAt(e.outcome==='countered'?'Countered':'Fizzled',{x:at.x,y:at.y-25},'#d6eaff',true);
    const seal=document.createElement('div');seal.className='fx-counter-seal';seal.innerHTML=chargeGlyph('counter');seal.style.left=at.x+'px';seal.style.top=at.y+'px';overlay.append(seal);
    const cleanup=()=>{seal.remove();removers.delete(cleanup)};removers.add(cleanup);
    seal.animate(reduced?[{opacity:1,scale:'1'},{opacity:0,scale:settings.reduced?'1':'.3'}]:[{opacity:1,scale:'1'},{opacity:0,scale:'1.4'}],{duration:reduced?120:180}).finished.then(cleanup,cleanup);
    if(!reduced)for(let i=0;i<12;i++){const shard=document.createElement('i');shard.className='fx-counter-shard';shard.style.left=at.x+'px';shard.style.top=at.y+'px';overlay.append(shard);
      const remove=()=>{shard.remove();removers.delete(remove)};removers.add(remove);const angle=i*Math.PI/6,reach=30+i%3*12;
      shard.animate([{opacity:1,translate:'0 0',rotate:'0deg'},{opacity:0,translate:Math.cos(angle)*reach+'px '+Math.sin(angle)*reach+'px',rotate:i*35+'deg'}],{duration:320,easing:'ease-out'}).finished.then(remove,remove);}
    audio?.play(e.outcome==='countered'?'counter':'fizzle');p?.actor?.remove();
  }
  function connectCue(source,target,duration=180,count=1,owner=0){
    if(settings.intensity===0)return;
    const n=recipient(source)||document.querySelector('[data-relic-uid="'+CSS.escape(source||'')+'"]'),dest=recipient(target);
    edge(n);const from=n?.getClientRects().length?center(n):point('p:'+owner,owner),to=point(target,owner);
    if(count>1)cueAt('×'+count,from);
    if(settings.reduced){edge(dest);return}
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('fx-connection');svg.setAttribute('viewBox','0 0 '+innerWidth+' '+innerHeight);
    const line=document.createElementNS(svg.namespaceURI,'path');line.setAttribute('d','M'+from.x+' '+from.y+' Q'+(from.x+to.x)/2+' '+(Math.min(from.y,to.y)-25)+' '+to.x+' '+to.y);svg.append(line);overlay.append(svg);
    const remove=()=>{svg.remove();removers.delete(remove)};removers.add(remove);const length=line.getTotalLength();line.style.strokeDasharray=length;line.animate([{strokeDashoffset:length},{strokeDashoffset:0}],{duration,easing:'ease-out'});
    const token=generation;setTimeout(()=>{remove();if(token===generation)edge(dest,'#fff0b5',250)},duration);
  }
  function perform(e,b) {
    const token=generation;
    const later=(callback,delay)=>setTimeout(()=>{if(token===generation)callback()},delay);
    const p=pending.get(e.action_uid);
    if(e.outcome!=='resolved') {fx.stats.counters++;fx.stats.fizzles++;if(settings.intensity!==0)counter(e,p);else audio?.play('counter');return 450}
    if(settings.intensity===0){audio?.play(e.stage==='combat'?'combat':family(e)==='fireball'?'fire':family(e));return 0;}
    if(e.stage==='combat'){combat(e,b);return 900}
    const type=family(e),duration=settings.reduced?50:settings.fast?300:type==='meteor'?1150:type==='fireball'?670:750;
    if(type==='arrival') {
      for(const uid of e.results?.entries||[e.source_uid])arrival(uid,e);
      return 220;
    }
    const departed=new Map((e.results?.departures||[]).map(uid=>[uid,ghost(uid)])),impacted=new Set();
    const feedback=uid=>{
      if(token!==generation||type==='meteor'&&!uid)return;
      const key=type==='meteor'?uid:'all';if(impacted.has(key))return;impacted.add(key);
      if(!e.suppress_trigger_cue)resultCues(e.cue_results?{...e,results:e.cue_results}:e,type==='meteor'?uid:null);
      for(const [id,g] of departed)if(type!=='meteor'||id===uid)departure(id,e,0,g);
    };
    if(e.effect==='attach'||e.relic_uid){
      const duration=e.effect==='attach'?160:180;
      if(!e.suppress_trigger_cue)connectCue(e.relic_uid||e.source_uid,e.target||'p:'+e.owner,duration,e.trigger_count||1,e.owner);
      later(()=>feedback(e.target),settings.reduced?0:duration);return duration+250;
    }
    base.consume({...b,visual_events:[{...e,onImpact:feedback}]});
    if(type==='meteor') {
      audio?.play('meteor');
      for(const uid of e.affected_uids||[])node(uid)?.classList.add('fx-simultaneous-hit');
      later(()=>document.querySelectorAll('.fx-simultaneous-hit').forEach(n=>n.classList.remove('fx-simultaneous-hit')),duration);
      // The core draws projectiles and impacts; synchronize local recoil and numbers with arrival.

    } else if(type==='fireball'){audio?.play('fire')}
    else if(type==='shield'){audio?.play('shield');node(e.target)?.classList.add('fx-shield-impact');later(()=>node(e.target)?.classList.remove('fx-shield-impact'),500)}
    if(!['meteor','fireball','shield'].includes(type))audio?.play(type);

    for(const uid of e.results?.entries||[])arrival(uid,{...e,color:e.effect==='tokens'?'W':e.color});
    return duration;
  }
  function finish() {
    generation++;
    for(const animation of stateAnimations)animation.cancel();stateAnimations.clear();localAnimations.clear();numberSlots.clear();
    for(const remove of [...removers])remove();
    document.querySelectorAll('.fx-simultaneous-hit,.fx-materializing').forEach(n=>n.classList.remove('fx-simultaneous-hit','fx-materializing'));
  }
  function consume(b,opts={}) {
    if(!b)return;setup();installControls();
    const key=b.players.map(p=>p.name+':'+p.commander).join('|'),events=b.visual_events||[];
    if(opts.initial||opts.reset||key!==identity||(events.at(-1)?.seq||0)<seen) {
      finish();pending.forEach(p=>p.actor?.remove());pending.clear();origins.clear();selection=null;
      seen=events.at(-1)?.seq||0;identity=key;battle=b;updateEnvironment();audio?.update();base.consume(b,{initial:true});capture(b);syncPending(b);return;
    }
    battle=b;updateEnvironment();
    const fresh=events.filter(e=>e.seq>seen),groups=new Map();
    for(const e of fresh)if(e.stage!=='cast'&&e.relic_uid&&e.outcome==='resolved'){
      const key=[e.relic_uid,e.target,e.effect].join('|'),list=groups.get(key)||[];list.push(e);groups.set(key,list);
    }
    for(const list of groups.values()){
      const first=list[0].results,last=list.at(-1).results;
      list.forEach((e,i)=>{e={...e};e.trigger_count=list.length;e.suppress_trigger_cue=i>0;
        if(!i&&first&&last)e.cue_results={...last,before:first.before};list[i]=e});
    }
    const cues=new Map([...groups.values()].flat().map(e=>[e.seq,e]));
    for(const original of fresh) {
      const e=cues.get(original.seq)||original;
      seen=e.seq;
      if(e.stage==='cast'){origins.set(e.action_uid,points.get(e.source_uid)||publicHand(e.owner));base.consume({...b,visual_events:[e]});audio?.play('card')}
      else {perform(e,b)}
    }
    // New outcomes start immediately; local animation channels replace older decoration.
    syncPending(b);capture(b);while(origins.size>128)origins.delete(origins.keys().next().value);
  }
  function configure(options) {
    if(options.volume!==undefined)options={...options,effectsVolume:options.volume};
    Object.assign(settings,options);base.configure({sound:false,reduced:settings.reduced,fast:settings.fast,intensity:settings.intensity});
    audio?.update();audio?.syncCharge();updateEnvironment();updateWeather();if(settings.reduced||settings.intensity===0){finish();pending.forEach(p=>{p.actor?.remove();p.actor=null});document.querySelectorAll('.fx-art-fire,.fx-art-aura').forEach(n=>n.remove())}else if(battle)syncPending(battle);installControls();
    document.dispatchEvent(new Event('spire-effects-change'));
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
    frame=0;ctx.clearRect(0,0,innerWidth,innerHeight);if(document.hidden||settings.reduced||settings.intensity===0)return;
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
  function clear(){document.querySelectorAll('.fx-art-fire,.fx-art-aura').forEach(n=>n.remove());finish();pending.forEach(p=>p.actor?.remove());pending.clear();selection=null;trails=[];battle=null;base.clear();audio?.stopCharge();audio?.update();updateEnvironment();updateWeather();ctx?.clearRect(0,0,innerWidth,innerHeight)}
  function playCue(kind){audio?.play(kind)}
  function animateState(n,frames,duration=450,delay=0){if(!n||settings.intensity===0)return;const animation=n.animate(settings.reduced?[{filter:'brightness(1.15)'},{filter:'brightness(1)'}]:frames,{duration:settings.reduced?140:settings.fast?duration*.5:duration,delay:settings.reduced?0:settings.fast?delay*.5:delay,easing:'ease-out'});stateAnimations.add(animation);animation.finished.then(()=>stateAnimations.delete(animation),()=>stateAnimations.delete(animation));return animation}
  function floating(text,n,color='#ffe8a4'){if(n)cueAt(text,center(n),color,true)}
  function presentState(previous,current){
    if(!current)return;
    if(!previous){if(current.phase==='opening'){document.querySelectorAll('.hand .card').forEach((n,i)=>{const deck=document.querySelector('.own-deck')?.getBoundingClientRect(),r=n.getBoundingClientRect();animateState(n,[{opacity:0,translate:deck?`${deck.left-r.left}px ${deck.top-r.top}px`:'0 20px'},{opacity:1,translate:'0 0'}],180,i*50)});document.querySelectorAll('.opponent-hand .card-back').forEach((n,i)=>animateState(n,[{opacity:.3,translate:'30px -15px'},{opacity:1,translate:'0 0'}],180,i*50));playCue('card')}return}
    if(previous.phase!==current.phase||previous.active!==current.active){animateState(document.querySelector('.temple-turn'),[{filter:'brightness(1.7)',transform:'scale(1.02)'},{filter:'brightness(1)',transform:'scale(1)'}]);playCue('turn')}
    for(const p of current.players){const old=previous.players.find(x=>x.id===p.id);if(!old)continue;
      const fresh=(current.visual_events||[]).filter(e=>e.seq>(previous.visual_events?.at(-1)?.seq||0));
      const hasHealthEvent=fresh.some(e=>e.results&&e.results.before.health[String(p.id)]!==e.results.after.health[String(p.id)]);
      if(p.hp!==old.hp&&!hasHealthEvent){const heal=p.hp>old.hp,n=recipient('p:'+p.id);edge(n,heal?'#86ffc5':'#ff997b');numberAt('p:'+p.id,(heal?'+':'−')+Math.abs(p.hp-old.hp),heal?'#86ffc5':'#ff997b',heal)}
      const own=!!document.querySelector(`.own-player[data-player="p:${p.id}"]`),manaChanged=JSON.stringify(p.mana)!==JSON.stringify(old.mana)||JSON.stringify(p.capacity)!==JSON.stringify(old.capacity)||p.temporary!==old.temporary;
      if(manaChanged){const mana=own?document.querySelector('.central-mana'):document.querySelector(`[data-player="p:${p.id}"] .mana-track`);mana?.querySelectorAll('.mana-artifact').forEach(n=>animateState(n,[{filter:'brightness(2)',transform:'scale(.8)'},{filter:'brightness(1.3)',transform:'scale(1.15)',offset:.5},{filter:'none',transform:'scale(1)'}],650));playCue('mana')}
      const newCards=own?p.hand.filter(c=>!old.hand.some(x=>x.uid===c.uid)):[],draws=own?newCards.length:Math.max(0,p.hand_count-old.hand_count);
      if(draws){playCue('card');if(own){const deck=document.querySelector('.own-deck')?.getBoundingClientRect();for(const [i,c] of newCards.entries()){const n=document.querySelector(`.hand [data-uid="${CSS.escape(c.uid)}"]`);if(!n)continue;const r=n.getBoundingClientRect();animateState(n,[{opacity:.25,translate:deck?`${deck.left-r.left}px ${deck.top-r.top}px`:'0 20px',filter:'brightness(1.6)'},{opacity:1,translate:'0 0',filter:'none'}],180,i*50)}}else document.querySelectorAll('.opponent-hand .card-back').forEach((n,i)=>animateState(n,[{opacity:.4,translate:'30px -15px'},{opacity:1,translate:'0 0'}],180,i*50))}
    }
  }
  function presentInventory(previous,current){
    if(!previous||!current||!['build','retry'].includes(current.stage))return;
    setup();
    for(const item of current.inventory||[]){
      const old=previous.inventory?.find(x=>x.uid===item.uid);if(!old)continue;
      const escaped=CSS.escape(item.uid),result=document.querySelector('[data-item-result="'+escaped+'"]');
      for(const [gem,tier] of Object.entries(item.gems||{})){
        if(old.gems?.[gem]===tier)continue;
        const socket=document.querySelector('[data-socket-item="'+escaped+'"][data-gem="'+CSS.escape(gem)+'"]');
        if(!socket)continue;
        playCue('socket');
        if(settings.intensity===0)continue;
        if(settings.reduced){edge(socket);edge(result,'#d6f4c3',250);continue}
        local(socket.querySelector('i'),[{translate:'0 -16px',opacity:0},{translate:'0 0',opacity:1}],140,'cubic-bezier(.2,.8,.3,1)');
        const token=generation;setTimeout(()=>{if(token!==generation)return;edge(socket,'#fff3bb',80);setTimeout(()=>{if(token!==generation||!socket.isConnected)return;connectElements(socket,result,180)},80)},140);
      }
      if(item.tier!==old.tier){edge(result||document.querySelector('.upgrade-preview'),'#d6f4c3',250);playCue('socket')}
    }
    (current.me?.equipped||[]).forEach((uid,slot)=>{
      if(!uid||previous.me?.equipped?.[slot]===uid)return;
      const source=document.querySelector('[data-action="inventoryItem:'+CSS.escape(uid)+'"]'),target=document.querySelector('[data-loadout-slot="'+slot+'"]');
      connectElements(source,target,160);playCue('card');
    });
    for(const [design,tier] of Object.entries(current.me?.card_upgrades||{}))if(previous.me?.card_upgrades?.[design]!==tier)edge(document.querySelector('.upgrade-preview'),'#d6f4c3',250);
  }
  function connectElements(source,target,duration){
    if(!source||!target||settings.intensity===0)return;edge(source);
    if(settings.reduced){edge(target,'#d6f4c3',250);return}
    const from=center(source),to=center(target),pulse=document.createElement('i');pulse.className='fx-item-pulse';pulse.style.left=from.x+'px';pulse.style.top=from.y+'px';overlay.append(pulse);
    const remove=()=>{pulse.remove();removers.delete(remove)};removers.add(remove);const token=generation;
    pulse.animate([{translate:'0 0'},{translate:(to.x-from.x)+'px '+(to.y-from.y)+'px'}],{duration,easing:'ease-out'}).finished.then(()=>{remove();if(token===generation)edge(target,'#d6f4c3',250)},remove);
  }
  function presentOutcome(stage,previous,seat){
    const won=previous.survivor===seat;
    playCue(won?'treasure':'counter');floating(won?(stage==='victory'?'Campaign complete':'Victory · Rewards earned'):'Defeat',document.querySelector('main'),won?'#ffe68a':'#e9a2ae');
    animateState(document.querySelector('.treasure-rewards')||document.querySelector('main'),[{filter:'brightness(1.7)'},{filter:'brightness(1)'}],750);
  }
  Object.assign(fx,{consume,capture,setTarget,configure,clear,finish,settings,playCue,presentState,presentInventory,presentOutcome});
  Object.defineProperty(fx,'activeCrackle',{get:()=>!!audio?.charge});
  Object.defineProperty(fx,'debug',{get:()=>({audio:audio?.ctx.state,family:selection?.family,weather:weather?.classList.contains('gathering'),pending:pending.size,queued:0,controlsInstalled,reduced:settings.reduced,sound:settings.sound})});
  document.addEventListener('pointermove',e=>{cursor={x:e.clientX,y:e.clientY};if(selection?.family==='fireball'){trails.push({...cursor,time:performance.now()});if(trails.length>30)trails.shift();wake()}});
  document.addEventListener('pointerdown',e=>{if(!settings.sound)return;try{audio??=new Mixer();audio.resume().catch(()=>{})}catch{}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clear();audio?.ctx.suspend().catch(()=>{})}});
  window.addEventListener('resize',()=>{finish();resize()});
})();
