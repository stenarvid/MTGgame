// Presentation only: the server owns passing, deadlines and phase transitions.
let priorityClockOffset=0;
let triggerOrder = [], triggerOrderKey = '', repeatPhaseStops = false;
function phaseGroup(phase){return phase==='grow'?'main':['precombat','attack_response','blocks','damage_response','combat_end'].includes(phase)?'combat':phase}
function priorityBarHTML(){
 const b=state.battle,m=state.me,f=state.priority_flow||{auto:m.auto},own=b.priority===m.seat&&!b.finished;
 const mandatory=!!b.choice||['opening','grow'].includes(b.phase),manualMain=own&&!b.stack.length&&['main','main2','combat_end'].includes(b.phase);
 let label='Pass',action='pass',disabled=!own||mandatory;
 if(!own){label='\u231b Waiting';disabled=true}
 else if(b.phase==='combat'&&!b.stack.length){label=Object.values(attackChoices).some(v=>v!=null)?'Confirm Attacks':'Skip Combat';action='attack'}
 else if(b.phase==='blocks'){label='Confirm Blockers';action='block'}
 else if(manualMain){label={main:'Enter Combat',main2:'End Turn',combat_end:'End Combat'}[b.phase];action={main:'enter_combat',main2:'end_turn',combat_end:'end_combat'}[b.phase]}
 else if(b.stack.length){label=f.auto?'\u231b Resolving':'Resolve';action=f.auto?'pass':'pass_once'}
 else if(!f.auto){action='pass_once'}
 if(mandatory){label=b.phase==='grow'?'Choose Mana':b.phase==='opening'?'Opening Hand':b.choice?.kind==='trigger_order'?'Order Triggers':'Required Choice';disabled=true}
 if(f.auto&&own&&!mandatory&&!manualMain&&!['combat','blocks'].includes(b.phase)){disabled=true;label=b.stack.length?'\u231b Resolving':'\u231b Auto-pass'}
 const names={draw:'Draw',main:'Main 1',combat:'Combat',main2:'Main 2',end:'End'};
 const track=side=>`<div class="priority-phase-row"><span>${side==='own'?'Your turn':'Opponent'}</span>${Object.entries(names).map(([phase,name])=>{const stop=(f.stops||[]).find(s=>s.phase===phase&&s.side===side),active=phaseGroup(b.phase)===phase&&(b.active===m.seat)===(side==='own');return `<button class="phase-marker ${active?'active':''} ${stop?'stop':''}" data-action="phaseStop:${side}:${phase}" aria-label="${side==='own'?'Your':'Opponent'} ${name}: ${stop?'remove '+(stop.repeat?'repeating':'one-use')+' stop':'set stop'}" aria-pressed="${!!stop}" ${active?'aria-current="step"':''}>${active?'<svg class="phase-flame" aria-hidden="true" viewBox="0 0 16 20"><path fill="currentColor" d="M8 0C12 7 15 8 15 13a7 7 0 1 1-14 0c0-3 2-5 4-7-1 4 1 5 2 6C10 8 7 5 8 0z"/></svg>':''}${name}${stop?`<small>${stop.repeat?'\u21bb':'\u25cf'}</small>`:''}</button>`}).join('')}</div>`;
 return `<section class="priority-bar" aria-label="Turn and priority controls"><div class="priority-timeline">${track('own')}${track('opponent')}</div><div class="priority-actions"><span class="priority-mode">${f.auto?'Auto-pass on':'Auto-pass paused'}<small>${({precombat:'Before attackers',attack_response:'Before blockers',damage_response:'Before damage',draw:'After draw',end:'End step'})[b.phase]||''}</small></span>${button(label,action,disabled,'priority-pill')}${!f.auto?button('Resume Auto-pass','resume_auto',b.finished,'smallbtn'):button('Respond','respond',b.finished,'smallbtn')}<button class="priority-fast ${f.auto?'enabled':''}" data-action="toggleAuto" aria-pressed="${!!f.auto}" title="Toggle Auto-Pass Priority" aria-label="Auto-Pass Priority">&gt;&gt;</button></div><div class="priority-secondary"><span id="response-countdown" role="timer"></span>${button(f.hold?'Hold Priority: On':'Hold Priority','toggleHold',b.finished||mandatory,'smallbtn')}${own&&!f.auto&&!manualMain&&!mandatory&&!['combat','blocks'].includes(b.phase)?button('Pass Once','pass_once',false,'smallbtn'):''}<details data-panel="priority-settings"><summary>Turn settings</summary><label><input data-priority-setting="auto_advance" type="checkbox" ${f.auto_advance?'checked':''}> Auto-advance my turn</label><label><input data-priority-setting="auto_order" type="checkbox" ${f.auto_order!==false?'checked':''}> Auto-Order Triggers</label><label><input id="repeatPhaseStops" type="checkbox" ${repeatPhaseStops?'checked':''}> Repeat every turn for new stops</label><p>Click a phase to add or remove a stop. Every stop pauses auto-pass. Hold is cleared by Resume.</p></details></div></section>`;
}
function priorityChoiceHTML(){
 const choice=state.battle.choice;if(choice?.kind!=='trigger_order'||choice.owner!==state.me.seat)return '';
 const key=choice.uids.join(',');if(key!==triggerOrderKey){triggerOrderKey=key;triggerOrder=[...choice.uids]}
 return `<h3>Choose your trigger resolution order</h3><p>First in this list resolves first.</p><ol>${triggerOrder.map((uid,n)=>`<li>${esc(state.battle.stack.find(s=>s.uid===uid)?.name||uid)} ${button('Earlier','triggerEarlier:'+uid,n===0,'smallbtn')} ${button('Later','triggerLater:'+uid,n===triggerOrder.length-1,'smallbtn')}</li>`).join('')}</ol>${button('Confirm Order','confirmTriggerOrder',false,'primary')}`;
}
function handlePriorityAction(action,arg){
 if(action==='explicitAbility'){const [uid,index]=arg.split(':');selectExplicitAbility(uid,Number(index));return true}
 if(action==='toggleAuto'){act(state.priority_flow?.auto?'respond':'resume_auto');return true}
 if(action==='toggleHold'){act('hold_priority',{enabled:!state.priority_flow?.hold});return true}
 if(action==='phaseStop'){const [side,phase]=arg.split(':');act('phase_stop',{side,phase,repeat:repeatPhaseStops});return true}
 if(action==='confirmTriggerOrder'){act('order_triggers',{order:triggerOrder});return true}
 if(['triggerEarlier','triggerLater'].includes(action)){const n=triggerOrder.indexOf(arg),next=n+(action==='triggerEarlier'?-1:1);if(next>=0&&next<triggerOrder.length)[triggerOrder[n],triggerOrder[next]]=[triggerOrder[next],triggerOrder[n]];render();return true}
 return false;
}
function updateResponseCountdown(){const el=document.querySelector('#response-countdown'),deadline=state?.priority_flow?.deadline;if(el)el.textContent=deadline?`Auto-pass in ${Math.max(0,Math.ceil(deadline-(Date.now()/1000-priorityClockOffset)))}s`:''}
setInterval(updateResponseCountdown,100);
document.addEventListener('change',event=>{if(event.target.dataset.prioritySetting)act('priority_settings',{[event.target.dataset.prioritySetting]:event.target.checked});if(event.target.id==='repeatPhaseStops')repeatPhaseStops=event.target.checked});

function selectExplicitAbility(uid,index){
 const c=state.battle.players[state.me.seat].board.find(c=>c.uid===uid),spec=c?.abilities?.find(a=>a.index===index);
 if(!spec?.available){error(spec?.reason||'Ability is unavailable.');return}
 combatSelection=null;selected={action:'ability',uid,ability:index,name:spec.name,explicit:true,spec,costs:{},pendingCosts:['sacrifice','discard'].filter(field=>spec[field])};
 advanceExplicitSelection(selected);
}
function advanceExplicitSelection(s){
 const me=state.battle.players[state.me.seat],field=s.pendingCosts[0];s.target=null;
 if(field){templeHandExpanded=field==='discard'&&matchMedia('(max-width:850px)').matches;s.costChoice=true;s.costField=field;s.targetKind=null;s.targets=(field==='discard'?me.hand:me.board.filter(c=>c.uid!==s.uid)).map(c=>c.uid);render()}
 else if(s.spec.target){templeHandExpanded=false;s.costChoice=false;s.targetKind=s.spec.target;s.targets=state.battle.targets[s.spec.target]||[];render()}
 else act('ability',{uid:s.uid,ability:s.ability,...s.costs});
}
