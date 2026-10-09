// Targeted extensions to the existing inventory, targeting and temple controls.
function inventoryHTML(){return legacyInventoryHTML()+suppliesHTML()}
function inventoryPreview(){
 const x=inventorySelection?.kind==='item'&&state.inventory.find(x=>x.uid===inventorySelection.id);
 if(!x?.category)return legacyInventoryPreview();
 const options=state.socket_options?.[x.uid]||[],proposal=options[inventorySelection.proposal??-1]?.preview,cost=x.tier===0?3:6;
 const loadout=x.category==='relic'?`<div class="row">${state.me.equipped.map((uid,slot)=>button('Relic slot '+(slot+1),'equip:'+x.uid+':'+slot,state.me.equipped.includes(x.uid))).join('')}</div>`:`<p>${state.me.deck.includes('gear:'+x.uid)?'This copy is in your deck.':'Add this copy using the deck/reserve exchange below.'} Equipment is drawn and cast normally.</p>`;
 return `${itemArt(x)}<h3>${esc(x.name)}</h3><p class="item-rules" data-item-result="${esc(x.uid)}">${esc(x.text)}</p>${x.cost!==undefined?`<p>Cast: ${manaCost(x)}</p>`:''}${loadout}<p>Sockets: ${x.sockets.map(role=>{const gem=Object.entries(x.occupied).find(([,slots])=>slots.includes(role))?.[0];return `<span class="item-socket" data-socket-role="${esc(role)}" data-socket-item="${esc(x.uid)}" ${gem?`data-gem="${esc(gem)}"`:''}><i aria-hidden="true">${gem?'◆':'◇'}</i>${esc(role)}${gem?' ('+esc(gem)+')':''}</span>`}).join(' · ')}</p>${Object.keys(x.gems).map(g=>button('Remove '+g,'clearGem:'+x.uid+':'+g)).join(' ')}<label>Gem preview <select id="socketPreview" data-socket-preview><option value="-1">Choose a compatible gem</option>${options.map((o,j)=>`<option value="${j}" ${inventorySelection.proposal===j?'selected':''}>${esc(o.gem)} ${o.tier?'+'+o.tier:'base'}</option>`).join('')}</select></label>${proposal?`<section class="notice"><h4>After socketing</h4><p class="item-rules">${esc(proposal.text)}</p>${proposal.cost!==undefined?`<p>Cast: ${manaCost(proposal)}</p>`:''}<p>Occupied: ${Object.entries(proposal.occupied).map(([g,roles])=>`${g}: ${roles.join(', ')}`).join(' · ')}</p>${button('Apply gem · free','applyGem:'+x.uid,false,'primary')}</section>`:''}${x.tier<2?`<p>Upgrade unlocks: ${esc(x.next.sockets.at(-1))}. Printed effect stays unchanged.</p>${button('Unlock socket · '+cost+' Essence','upgrade_item:'+x.uid,state.me.essence<cost)}${state.me.essence<cost?`<p>Need ${cost-state.me.essence} more Essence.</p>`:''}`:'<p>All three sockets unlocked.</p>'}`;
}
function legalConsumable(c){return commander(state.me.commander).colors.includes(c.color)||c.color==='C'}
function suppliesHTML(){
 const m=state.me,stock=m.consumables||[],pouch=m.pouch||[null,null],catalog=state.consumable_catalog||[],gems=state.gems||[],unlocks=m.gem_unlocks||{},editable=!m.ready&&['build','retry'].includes(state.stage);
 const spec=item=>catalog.find(c=>c.id===item.design);
 return `<section class="panel supplies-inventory"><h3>Battle pouch · two slots</h3><p>Consumed permanently on activation, including defeats and retries. Change your pouch between battles.</p><div class="row">${pouch.map((uid,slot)=>{const item=stock.find(x=>x.uid===uid);return `<article><b>Slot ${slot+1}: ${esc(item?spec(item).name:'Empty')}</b>${item?button('Remove','pouchRemove:'+slot,!editable):''}</article>`}).join('')}</div><div class="grid">${stock.map(item=>{const c=spec(item);return `<article><h4>${esc(c.name)}</h4><span class="tag">${c.sorcery?'Sorcery':'Instant'}</span><p>${esc(c.text)}</p>${pouch.map((_,slot)=>button('Pouch slot '+(slot+1),'pouchItem:'+item.uid+':'+slot,!editable||pouch.includes(item.uid)||!legalConsumable(c))).join(' ')}</article>`}).join('')||'<p>No consumables owned.</p>'}</div><h3>Gem unlocks</h3><p>Reusable across compatible items. Higher tiers reserve more sockets; lower tiers remain available.</p><div class="grid">${gems.map(g=>{const tier=unlocks[g.id],cost=tier===0?3:6;return `<article><b>${esc(g.name)}</b><p>${tier===undefined?'Locked':`Unlocked through ${tier?'+'+tier:'base'}`}</p>${tier!==undefined&&tier<2?button('Upgrade · '+cost+' Essence','upgradeGem:'+g.id,!editable||m.essence<cost):''}</article>`}).join('')}</div>${state.stage==='build'?`<h3>Consumable & gem shop</h3><p>Separate from chest rewards. Consumables: 1 currency · gem unlocks: 2 currency.</p><div class="grid">${catalog.filter(legalConsumable).map(c=>`<article><b>${esc(c.name)}</b><span class="tag">${c.sorcery?'Sorcery':'Instant'}</span><p>${esc(c.text)}</p>${button('Buy · 1 currency','buyConsumable:'+c.id,m.ready||state.currency<1)}</article>`).join('')}${gems.filter(g=>unlocks[g.id]===undefined).map(g=>`<article><b>${esc(g.name)} gem</b><p>Reusable base-tier unlock.</p>${button('Unlock · 2 currency','buyGem:'+g.id,m.ready||state.currency<2)}</article>`).join('')}</div>`:''}${m.supply_rewards?.length?`<p>Separate supply rewards: ${m.supply_rewards.slice(-6).map(r=>esc(r.name)).join(' · ')}</p>`:''}</section>`;
}
function handleInventoryAction(action,arg){
 if(action==='applyGem'){const option=state.socket_options[arg]?.[inventorySelection?.proposal];if(option)act('socket_gem',{uid:arg,gem:option.gem,tier:option.tier});return true}
 if(action==='clearGem'){const [uid,gem]=arg.split(':');act('clear_socket',{uid,gem});return true}
 if(action==='upgradeGem'){act('upgrade_gem',{gem:arg});return true}
 if(action==='buyGem'){act('buy_gem',{design:arg});return true}
 if(action==='buyConsumable'){act('buy_consumable',{design:arg});return true}
 if(action==='pouchRemove'){act('pouch',{slot:Number(arg),uid:null});return true}
 if(action==='pouchItem'){const [uid,slot]=arg.split(':');act('pouch',{uid,slot:Number(slot)});return true}
 return legacyInventoryAction(action,arg);
}
document.addEventListener('change',e=>{if(e.target.matches('[data-socket-preview]')){inventorySelection.proposal=Number(e.target.value);render()}});
function battleItemControls(){
 const b=state.battle,me=b.players[state.me.seat],usable=b.priority===me.id&&!b.choice&&!['opening','grow','blocks'].includes(b.phase)&&!b.finished;
 return `<details class="battle-pouch" data-panel="pouch"><summary>Battle pouch · ${(me.pouch||[]).length}/2</summary>${(me.pouch||[]).map(c=>`<p><b>${esc(c.name)}</b><span class="tag">${c.sorcery?'Sorcery':'Instant'}</span><small>${esc(c.text)}</small>${button('Use · permanently spent','consumeItem:'+c.uid,!usable||(c.sorcery&&(b.active!==me.id||!['main','main2'].includes(b.phase)||b.stack.length))||!canPay(c.cost,c.pips,me),'smallbtn')}</p>`).join('')||'<p>Empty</p>'}</details>`;
}
function itemChoiceHTML(){
 const choice=state.battle.choice;if(!choice||choice.owner!==state.me.seat||choice.kind==='discard')return '';
 if(['attachment_target','counter_target'].includes(choice.kind))return `<h3>${esc(choice.name)} · choose a creature</h3>${state.battle.targets.friendly.map(uid=>button(targetLabel(uid),'itemTarget:'+uid)).join(' ')}`;
 if(['payment','optional_death_draw'].includes(choice.kind)){const cost=choice.cost??1,me=state.battle.players[state.me.seat];return `<h3>${esc(choice.name)}</h3><p>${cost} mana${choice.kind==='optional_death_draw'?' · draw a card and lose 1 life':''}</p>${button('Pay','itemPay:true',!canPay(cost,{},me))} ${button('Decline','itemPay:false')}`}
 return `<h3>${esc(choice.name)}</h3><p>Choose a hand card to discard, then draw a card.</p>${button('Decline','declineItem')}`;
}
function handleBattleItems(action,arg){
 if(action==='equipGear'||action==='consumeItem'){
  const me=state.battle.players[state.me.seat],source=(action==='equipGear'?me.gear:me.pouch).find(c=>c.uid===arg);if(!source)return true;
  const target=action==='equipGear'?'friendly':source.target,command=action==='equipGear'?'equip_gear':'consume';
  if(target){selected={uid:arg,name:source.name,targets:state.battle.targets[target],targetKind:target,action:command};render()}else act(command,{uid:arg});return true;
 }
 if(action==='itemTarget'){act('choose_item_target',{target:arg});return true}
 if(action==='itemPay'){act('choose_item_payment',{pay:arg==='true'});return true}
 if(action==='itemDiscard'){act('choose_item_discard',{uid:arg});return true}
 if(action==='declineItem'){act('decline_item_choice');return true}
 return false;
}
function gearCard(g,own){
 const b=state.battle,me=b.players[state.me.seat],disabled=b.priority!==me.id||(!me.instant_equip&&(b.active!==me.id||!['main','main2'].includes(b.phase)||!!b.stack.length))||['opening','grow','blocks'].includes(b.phase)||!!b.choice||!canPay(g.equip_cost,{},me)||!b.targets.friendly.length;
 return cardHTML(g,selected?.targets.includes(g.uid)?'target:'+g.uid:'',`<small>${g.attachment?'Attached to '+esc(targetLabel(g.attachment)):'Unattached'}</small>${own?button('Equip · '+(me.instant_equip?'Instant':'Sorcery')+' · '+g.equip_cost,'equipGear:'+g.uid,disabled,'smallbtn'):''}`);
}
