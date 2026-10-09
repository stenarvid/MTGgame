const manaNames={W:'White',U:'Blue',B:'Black',R:'Red',G:'Green',C:'Generic'};
// New gameplay designs use distinct vector sigils until illustrated art is commissioned.
function sigilArt(c){
 const key=c.base_design||c.design||c.id,color=({W:'#f1df9a',U:'#73bded',B:'#ae86cb',R:'#f09266',G:'#8bd396',C:'#d4bb7c'})[c.color||'C'];
 const icons={spiresteel_blade:'M98 136 152 45 173 28 169 57 113 144ZM88 124 126 147M93 143 84 163',dawnward_shield:'M91 42 160 42 171 70Q170 125 126 158Q81 127 80 70Z',embercleave_axe:'M102 158 153 43M145 57Q193 30 197 87L160 100 139 77 112 66Z',gravebound_fang:'M96 150Q131 141 164 39Q182 95 135 141L117 157Z',rootbreaker_maul:'M112 157 143 78M117 40 173 52 166 90 109 78Z',smith_insignia:'M94 52 157 52 150 87 164 112 89 112 101 87ZM81 123 174 123',muster_standard:'M89 166 89 35 177 47 162 83 90 77',sovereign_crest:'M83 74 102 102 126 47 150 102 170 74 162 128 92 128Z'};
 const seed=[...key].reduce((a,v)=>(a*31+v.charCodeAt(0))>>>0,7),angle=seed%60;
 const icon=icons[key]|| (c.kind==='consumable'?'M108 43H143V66L161 97V141Q161 159 126 159Q91 159 91 141V97L108 66Z':c.kind==='creature'?'M108 44Q126 23 144 44V69L133 82 149 99 163 153H89L103 99 119 82 108 69Z':'M90 45H162V153H90ZM104 65H149M104 86H142M104 107H149');
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 252 192"><defs><radialGradient id="a"><stop stop-color="${color}" stop-opacity=".3"/><stop offset="1" stop-color="#101d25"/></radialGradient></defs><rect width="252" height="192" fill="url(#a)"/><g fill="none" stroke="${color}"><circle cx="126" cy="96" r="79" opacity=".4"/><path d="M126 11 205 96 126 181 47 96Z" transform="rotate(${angle} 126 96)" opacity=".5"/><path d="${icon}" fill="${color}" fill-opacity=".23" stroke-width="4" stroke-linejoin="round"/>${Array.from({length:5},(_,i)=>`<circle cx="${38+(seed*(i+1)%176)}" cy="${20+(seed*(i+3)%150)}" r="2"/>`).join('')}</g></svg>`;
 return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
function keywordHint(c,k){
 if(k==='Ward'&&c.ward_payments?.length)return (c.ward_cost?'Targeting also costs 1 additional mana. ':'')+'Each ward ability uses the stack: pay '+c.ward_payments.map(n=>'{'+n+'}').join(' and ')+' or the targeting spell or ability is countered.';
 return state.battle?.keywords[k]||({Vigilance:'Attacking does not tap this creature.',Lifelink:'Damage dealt by this creature also gains that much life.',Hexproof:'Cannot be targeted by spells or abilities your opponents control.'}[k])||k;
}
const manaShapes={W:'<circle cx="12" cy="12" r="5"/><path d="M11 1h2v4h-2zM11 19h2v4h-2zM1 11h4v2H1zM19 11h4v2h-4zM3 4l2-1 3 3-2 2zM17 17l2-2 3 4-2 1zM17 6l3-3 2 1-3 4zM3 20l-1-2 4-3 2 2z"/>',U:'<path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13z"/>',B:'<path d="M5 10a7 7 0 0 1 14 0v6l-3 1v4H8v-4l-3-1z"/><circle cx="9" cy="11" r="2" fill="var(--pip)"/><circle cx="15" cy="11" r="2" fill="var(--pip)"/>',R:'<path d="M13 2c3 7-3 7 1 11l3-5c8 11 0 15-5 15S1 18 5 11l3 3C6 8 12 8 13 2z"/>',G:'<path d="M12 1 5 9h3l-5 7h7v6h4v-6h7l-5-7h3z"/>'};
function manaPip(color,value=''){return `<span class="mana-pip ${color}" title="${manaNames[color]}${value!==''?' '+value:''}" aria-label="${manaNames[color]}${value!==''?' '+value:''}">${value!==''?value:`<svg viewBox="0 0 24 24" aria-hidden="true">${manaShapes[color]||''}</svg>`}</span>`}
// Vector ornament stays crisp at hand, battlefield, and inspection sizes.
function cardFrame(identity,commander=false){
    const motifs={
        W:'M0 30Q18 8 30 0M6 30Q20 20 30 6M9 22L14 10 19 16 24 5M12 26Q24 24 26 12',
        U:'M0 30C24 36 0 8 30 0M5 30C30 25 10 7 30 5M12 22Q28 28 22 12M9 15L15 9 21 15 15 21Z',
        B:'M0 30L8 20 4 10 16 15 20 8 30 0M8 30L16 23 12 18 23 16 30 8M18 29L24 24 29 18M12 12L18 6',
        R:'M0 30L8 13 13 22 18 4 23 12 30 0M8 30L19 25 16 18 30 8M20 30L24 20 30 16',
        G:'M0 30Q2 2 30 0M7 30Q10 10 30 7M5 21Q18 24 14 12Q1 10 5 21ZM17 8Q28 18 27 3Q16 0 17 8Z',
        C:'M0 30L0 12 12 0 30 0M7 30L7 16 16 7 30 7M14 26L14 19 19 14 26 14M11 11L19 3M3 19L11 11'};
    const left=identity[0]||'C',right=identity[1]||left;
    return `<div class="frame-ornament ${commander?'royal-frame':''}" aria-hidden="true">${[[left,'nw'],[right,'ne'],[left,'sw'],[right,'se']].map(([color,corner])=>`<svg class="frame-corner ${corner} ${color}" viewBox="0 0 36 36"><path class="ornament-shadow" d="${motifs[color]||motifs.C}"/><path d="${motifs[color]||motifs.C}"/><circle cx="4" cy="4" r="2.5"/><path class="frame-gem" d="M25 25L29 21 33 25 29 29Z"/></svg>`).join('')}<span class="frame-crest">${commander?'♛':'◆'}</span><span class="frame-footer">◇</span></div>`;
}
function cardHTML(c,action='',extra='',target=false){
    const artKey=c.art_style==='sigil'?(c.uid?'instance_'+c.uid:c.id):c.id==='commander'?'commander_'+state.battle.players[c.owner].commander:c.token?'token_recruit':c.id;
    inspectionCards.set(artKey,c);
    const attack=c.shown_attack??c.attack,health=(c.shown_health??c.health)-(c.damage||0);
    const identity=c.id==='commander'?(state.commanders?.find(x=>x.id===state.battle.players[c.owner].commander)?.colors||[c.color||'C']):Object.keys(c.pips||{}).filter(k=>k!=='C');
    if(!identity.length)identity.push(c.color||'C');
    const tones={W:'#eee0b4',U:'#70c5ef',B:'#af8ac5',R:'#ec8057',G:'#8bc88c',C:'#8f7353'};
    const dual=identity.length>=2;
    return `<div ${c.uid?`data-uid="${esc(c.uid)}"`:""} data-art-key="${esc(artKey)}" class="card ${esc(identity[0])} ${c.id==='commander'?'commander':''} ${c.tapped?'tapped':''} ${target?'target':''} ${dual?'dual':''}" ${dual?`style="--left:${tones[identity[0]]};--right:${tones[identity[1]]}"`:''} ${action?`data-action="${action}" tabindex="0" role="button"`:''}>${cardFrame(identity,c.id==='commander')}<div class="card-title"><strong>${esc(c.name)}</strong><span class="mana-cost">${manaCost(c)}</span></div><img class="illustration" style="object-position:center ${artKey==='r_wipe'?'75%':'25%'}" loading="lazy" alt="${esc(c.name)}" src="${c.art_style==='sigil'?sigilArt(c):window.cardArtURL?window.cardArtURL(artKey):'/art/'+esc(artKey)+'?v=anime-2'}"><div class="card-type">${c.id==='commander'?'Commander · ':''}${esc(c.type_line||c.kind)}${c.speed?' · '+esc(c.speed):''}</div><div class="card-rules"><small>${esc(c.text)}</small><div>${(c.keywords||[]).map(k=>`<span class="tag" title="${esc(keywordHint(c,k))}">${esc(k)}</span>`).join('')}</div></div>${c.kind==='creature'?`<div class="stats"><span>${attack} / ${health}</span><span class="card-state">${c.damage?c.damage+' damage ':''}${c.tapped?'Exhausted ':''}${c.sick&&c.shown_attack!==undefined?'New':''}</span></div>`:''}${extra?`<div class="card-controls">${extra}</div>`:''}<button class="art-inspect" data-action="inspect:${esc(artKey)}" aria-label="Inspect ${esc(c.name)} artwork and rules">Inspect</button></div>`
}
