"""Apply curated mechanical identities; also called by expand_cards.py."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def effect(kind, amount=0, **kw): return dict(effect=kind,amount=amount,**kw)
SHIELD=dict(name='Dawn Shieldbearer',color='W',attack=0,health=3,keywords=['guard'],text='Guard: takes 1 less blocking damage.')
SPIRIT=dict(name='Sunlit Spirit',color='W',attack=1,health=1,keywords=['haste'],text='Haste: can attack immediately.')
SPARK=dict(name='Cinder Spark',color='R',attack=1,health=1,keywords=['haste'],text='Haste: can attack immediately.')
BONE=dict(name='Bone Thrall',color='B',attack=2,health=1)
PLANT=dict(name='Wildseed Plant',color='G',attack=0,health=2)
BEAST=dict(name='Thicket Beast',color='G',attack=3,health=3,keywords=['trample'],text='Trample: excess combat damage hits the enemy hero.')
C={}
def creature(name,event,kind,amount=1,keywords=None,**kw):
 C[name]=dict(trigger=dict(event=event,**effect(kind,amount,**kw)))
 if keywords:C[name]['keywords']=keywords
creature('Astra, Echo Conduit','attack','copy')
creature('Dawn Musterer','attack','tokens',1)
creature('Sanctuary Keeper','ally_enters','heal',1)
creature('Banner Marshal','attack','buff_group',1,selection='tokens',permanent=True)
creature('Citadel Envoy','enter','custom_tokens',1,token=SHIELD)
creature('Sunlit Cadet','enter','tokens',1,condition='no_tokens')
creature('Oathbound Herald','enter','tokens',1,then=[effect('armor',2)])
creature('Dawn Procession Leader','enter','tokens',1,scale='tokens',cap=4)
creature('Silverwing Chaplain','attack','heal',0,scale='attackers',cap=5,keywords=['vigilance'])
creature('Banner Scribe','ally_enters','draw',1,once_per_turn=True)
creature('Shieldwall Captain','attack','grant_keyword',keyword='guard',selection='tokens')
creature('Radiant Quartermaster','spell_cast','custom_tokens',1,token=SHIELD,once_per_turn=True)
creature('Lastwatch Veteran','dies','tokens',2,then=[effect('heal',1)])
creature('Sunforge Architect','land','tokens',2,condition='outnumbered')
creature('Seraph of the Muster','attack','custom_tokens',2,token=SPIRIT)
creature('Mirror Pathfinder','attack','copy',copy_mode='small',then=[effect('draw',1)])
creature('Rift Archivist','ally_enters','draw',1)
creature('Mist Courier','attack','loot',2)
creature('Echo Adept','enter','draw',1,then=[effect('untap_lands',1)])
creature('Tidal Guardian','attack','freeze',1,keywords=['guard'])
creature('Rift Apprentice','enter','draw',1,condition='empty_hand')
creature('Moonlit Savant','enter','loot',3)
creature('Prism Navigator','attack','copy',copy_mode='permanent',then=[effect('pay_life',3)])
creature('Echo Attendant','ally_enters','heal',2,condition='low_life')
creature('Tideglass Oracle','spell_cast','draw',2,condition='second_spell',once_per_turn=True)
creature('Departing Scholar','dies','recover_spell',1)
creature('Mistveil Envoy','enter','heal',4,then=[effect('armor',1)])
creature('Planar Surveyor','enter','search',1,then=[effect('untap_lands',1)])
creature('Memory Diver','enter','recover_spell',1)
creature('Astral Cartographer','attack','draw',1,condition='six_lands',scale='attackers',cap=2)
creature('Grave Herald','attack','recall',1,condition='graveyard_full')
creature('Mourning Priest','ally_dies','drain',1)
creature('Crypt Scribe','dies','mill',2,then=[effect('draw',1)])
creature('Bone Gardener','enemy_dies','tokens',1,once_per_turn=True)
creature('Night Reclaimer','enter','reanimate',1,max_cost=2)
creature('Dusk Acolyte','dies','drain',2)
creature('Funeral Chronicler','ally_dies','loot',2,once_per_turn=True)
creature('Ossuary Warden','enemy_dies','armor',2)
creature('Bloodwake Rider','attack','drain',1,scale='graveyard',cap=3)
creature('Gravebell Keeper','dies','recall',1,then=[effect('pay_life',1)])
creature('Revenant Archivist','enter','recall',2,condition='graveyard_full')
creature('Bone Lantern Bearer','ally_dies','heal',2,once_per_turn=True,then=[effect('armor',1)])
creature('Ashen Mourner','enemy_dies','recover_spell',1,once_per_turn=True)
creature('Crypt Broodmother','dies','custom_tokens',3,token=BONE)
creature('Nightfall Harvester','attack','drain',1,scale='missing_life',cap=5,condition='low_life')
creature('Spark Savant','spell_cast','draw',1,once_per_turn=True)
creature('Flame Cantor','spell_cast','damage',1)
creature('Ember Captain','attack','damage',2,condition='solo_attack',keywords=['haste'])
creature('Cinder Artificer','spell_cast','custom_tokens',1,token=SPARK)
creature('Ashwing Raider','enter','damage',3,keywords=['haste'])
creature('Kindle Apprentice','enter','damage',1,then=[effect('recover_spell',1)])
creature('Flare Duelist','attack','damage',1,then=[effect('self_buff',1)])
creature('Runespark Defender','spell_cast','armor',2,condition='second_spell',once_per_turn=True)
creature('Emberquill Scholar','enter','draw',2,then=[effect('pay_life',2)])
creature('Cinderheart Adept','spell_cast','self_buff',1)
creature('Volcanic Herald','enter','damage',4,then=[effect('pay_life',2)])
creature('Ashburst Familiar','dies','damage',0,scale='source_power',cap=5)
creature('Blazewing Commander','spell_cast','buff_group',1,selection='attacking')
creature('Wildfire Summoner','spell_cast','tokens',2,condition='second_spell',once_per_turn=True)
creature('Inferno Oracle','attack','damage',2,scale='spells',cap=3)
creature('Rootbound Sage','land','draw',1,once_per_turn=True)
creature('Grove Tender','enter','land',1)
creature('Canopy Stalker','land','self_buff',1)
creature('Wildseed Keeper','land','custom_tokens',1,token=PLANT)
creature('Ancient Trailblazer','attack','land',1,keywords=['vigilance'])
creature('Seedling Pilgrim','enter','search',1)
creature('Mossheart Healer','land','heal',1,scale='lands',cap=4)
creature('Verdant Wayfinder','enter','land',1,then=[effect('draw',1,condition='six_lands')])
creature('Barkhide Guardian','land','self_buff',2,once_per_turn=True,keywords=['guard'])
creature('Canopy Archivist','enter','draw',1,condition='large_creature')
creature('Wildroot Matriarch','land','buff_group',1,selection='tokens',permanent=True)
creature('Thicket Nestkeeper','land','custom_tokens',1,token=BEAST,condition='six_lands')
creature('Forestwake Colossus','attack','land',2,condition='solo_attack',keywords=['trample'])
creature('Autumn Reclaimer','dies','recall',1,then=[effect('search',1)])
creature('Worldseed Ancient','land','draw',2,condition='wide_board',once_per_turn=True)
S={}
def spell(name,target,*effects): S[name]=dict(spell=dict(target=target,effects=list(effects)))
e=effect
spell('Call the Watch',None,e('tokens',2),e('tokens',1,condition='outnumbered'))
spell('Citadel Assembly',None,e('tokens',2),e('custom_tokens',1,token=SHIELD))
spell('Shared Resolve',None,e('buff_group',1,selection='tokens',permanent=True))
spell('Dawnward Blessing',None,e('buff_group',2,selection='nontokens'))
spell('Sheltering Light','friendly',e('buff',3,power=0),e('grant_keyword',keyword='guard'))
spell('Recruitment Orders',None,e('tokens',1),e('draw',1,condition='wide_board'))
spell('Sanctuary Bells',None,e('custom_tokens',1,token=SHIELD),e('heal',2,scale='tokens',cap=4))
spell('Raise the Ramparts',None,e('custom_tokens',2,token=SHIELD),e('armor',2))
spell('United Charge',None,e('custom_tokens',2,token=SPIRIT),e('buff_group',1,selection='attacking'))
spell('Last Light Rally',None,e('tokens',2),e('tokens',3,condition='low_life'),e('heal',3))
spell('Fleeting Reflection','friendly',e('blink'),e('freeze',1,condition='outnumbered'))
spell('Slip Through Mist','friendly',e('blink'),e('loot',2))
spell('Return to Stillwater','enemy',e('bounce'))
spell('Rift Rejection','enemy',e('bounce'),e('freeze',1))
spell('Deepwater Study',None,e('draw',1,condition='empty_hand'),e('draw',2))
spell('Memory Cascade',None,e('recover_spell',2),e('pay_life',2))
spell('Sheltered Passage','friendly',e('blink'),e('armor',4))
spell('Borrowed Memories',None,e('recover_spell',1),e('mill',2))
spell('Temporal Shelter','friendly',e('buff',4,power=0),e('untap_lands',1))
spell('Prismatic Journey','friendly',e('blink'),e('draw',1),e('untap_lands',2))
spell('Whisper from Below',None,e('mill',2),e('recall',1))
spell('Ossuary Expedition',None,e('recall',1),e('recall',1,condition='graveyard_full'))
spell('Blood Tithe','friendly',e('sacrifice'),e('drain',4))
spell('Midnight Feast',None,e('drain',2,scale='graveyard',cap=4))
spell('Grave Sentence','enemy',e('destroy'),e('pay_life',2))
spell('Soul Reclamation','enemy',e('destroy'),e('reanimate',1,max_cost=2))
spell('Funeral Offering','friendly',e('sacrifice'),e('draw',3))
spell('Dark Testament',None,e('pay_life',3),e('draw',3))
spell('Bonewall Pact',None,e('custom_tokens',2,token=BONE),e('armor',1,scale='graveyard',cap=3))
spell('Gravesong Renewal',None,e('reanimate',1,max_cost=5),e('pay_life',3))
spell('Searing Needle','any',e('damage',1),e('damage',2,condition='second_spell'))
spell('Scorching Arc','any',e('damage',4),e('pay_life',1))
spell('Phoenix Flare','any',e('damage',3,scale='spells',cap=4))
spell('Rain of Embers',None,e('area_damage',2),e('custom_tokens',1,token=SPARK))
spell('Volcanic Reckoning',None,e('area_damage',4),e('pay_life',3))
spell('Inspired Ignition',None,e('damage',2),e('loot',2))
spell('Runefire Study',None,e('draw',1),e('draw',2,condition='second_spell'))
spell('Cinder Reinforcements',None,e('custom_tokens',2,token=SPARK),e('damage',1))
spell('Overheated Edge','friendly',e('buff',0,power=4),e('grant_keyword',keyword='haste'))
spell('Final Conflagration',None,e('area_damage',2,scale='spells',cap=3),e('damage',3))
spell('Trail of Seeds',None,e('search',1),e('untap_lands',1))
spell('Rootway Expedition',None,e('ramp',1))
spell('Awaken the Grove',None,e('ramp',1),e('ramp',1,condition='large_creature'))
spell('Canopy Insight',None,e('ramp',1),e('draw',1,condition='six_lands'))
spell('Titanic Mantle','friendly',e('buff',5,power=5),e('grant_keyword',keyword='trample'))
spell('Barkskin Veil','friendly',e('buff',4,power=0),e('grant_keyword',keyword='vigilance'))
spell('Wildwood Communion',None,e('draw',1,scale='lands',cap=3),e('heal',2))
spell('Seedborn Reinforcements',None,e('ramp',1),e('custom_tokens',1,token=PLANT))
spell('Overgrowth March',None,e('buff_group',2,selection='tokens'),e('grant_keyword',keyword='trample',selection='tokens'))
spell('Worldroot Renewal',None,e('ramp',2),e('heal',0,scale='lands',cap=10))
CONDITIONS={'outnumbered':'you control fewer creatures than the enemy','low_life':'your hero is at half health or less','has_tokens':'you control a token','no_tokens':'you control no tokens','wide_board':'you control at least four creatures','large_creature':'you control a creature with 4+ attack','six_lands':'you control at least six lands','empty_hand':'you have at most one card in hand','graveyard_full':'your discard contains at least three creatures','solo_attack':'this attacks alone','second_spell':'you have cast at least two noncreature spells this turn'}
EVENTS={'attack':'When this attacks','enter':'When this enters','ally_enters':'Whenever another nontoken creature enters under your control','ally_dies':'Whenever another friendly creature dies','enemy_dies':'Whenever an enemy creature dies','dies':'When this dies','spell_cast':'Whenever you cast a noncreature spell','land':'Whenever you play a land'}
SELECTION={'tokens':'your tokens','nontokens':'your nontoken creatures','attacking':'your attacking creatures','all':'your creatures','small':'your creatures with 2 or less attack'}
SCALES={'tokens':'friendly token','lands':'land you control','graveyard':'creature in your discard','attackers':'friendly attacker','spells':'noncreature spell you cast this turn','missing_life':'HP missing from your hero','source_power':"point of this creature's attack"}
def describe(f, target=None):
 k=f['effect'];n=str(f.get('amount',0))
 if f.get('scale'):n+=f" + 1 per {SCALES[f['scale']]} (up to +{f.get('cap',3)})"
 t=f.get('token',{})
 texts={'tokens':f'create {n} 1/1 Recruits','custom_tokens':f"create {n} {t.get('attack',0)}/{t.get('health',0)} {t.get('name','')} token(s)"+(' with '+', '.join(t['keywords']) if t.get('keywords') else ''),
 'heal':f'heal your hero for {n}','draw':f'draw {n} card(s)','armor':f'gain {n} armor',
 'damage':f'deal {n} damage to '+('that target' if target=='any' else 'the enemy hero'),
 'area_damage':f'deal {n} damage to each enemy creature','drain':f'the enemy hero loses {n} life and you gain that much',
 'recall':f'return {n} highest-cost creature(s) from your discard to hand','recover_spell':f'return {n} highest-cost spell(s) from your discard to hand',
 'reanimate':f"return {n} highest-cost creature(s) costing at most {f.get('max_cost',3)} from your discard to play",
 'search':f'play {n} additional land(s) from your reserve this turn','land':f'play {n} additional land(s) from your reserve this turn','ramp':f'play {n} additional land(s) from your reserve this turn',
 'self_buff':f'this gets +{n}/+{n} permanently','team_buff':f'your creatures get +{n}/+{n} this turn',
 'buff_group':f"{SELECTION.get(f.get('selection','all'))} get +{f.get('power',n)}/+{n} "+('permanently' if f.get('permanent') else 'this turn'),
 'grant_keyword':('that creature' if target=='friendly' else SELECTION.get(f.get('selection','all')))+f" gains {f.get('keyword','')} permanently",
 'buff':f"that creature gets +{f.get('power',0)}/+{n} this turn",'blink':'blink that friendly creature','bounce':"return that enemy creature to its owner's hand",'destroy':'destroy that enemy creature',
 'freeze':f'tap the {n} strongest enemy creature(s); they skip their next untap',
 'loot':f'draw {n} card(s), then discard your highest-cost card','mill':f'put the top {n} cards of your deck into your discard',
 'pay_life':f'lose {n} life','untap_lands':f'untap {n} of your tapped lands','sacrifice':'sacrifice that creature','power_damage':"deal damage equal to that creature's attack to the enemy hero"}
 if k=='copy':
  texts[k]='choose another friendly nontoken creature; create a '+('1/1 ' if f.get('copy_mode')=='small' else '')+'token copy tapped and attacking'+('' if f.get('copy_mode')=='permanent' else '; exile it at turn end')
 text=texts[k]
 if f.get('scale'):
  text=text.replace('card(s)', 'cards').replace('creature(s)', 'creatures').replace('spell(s)', 'spells').replace('land(s)', 'lands').replace('token(s)', 'tokens')
 if f.get('condition'):text='if '+CONDITIONS[f['condition']]+', '+text
 if not f.get('scale'):
  amount=f.get('amount',0)
  if amount==1:
   text=text.replace('card(s)', 'card').replace('creature(s)', 'creature').replace('spell(s)', 'spell').replace('land(s)', 'land').replace('token(s)', 'token')
   text=text.replace('create 1 1/1 Recruits', 'create a 1/1 Recruit').replace('create 1 ', 'create a ')
  else:
   text=text.replace('card(s)', 'cards').replace('creature(s)', 'creatures').replace('spell(s)', 'spells').replace('land(s)', 'lands').replace('token(s)', 'tokens')
 return text

def apply_identities(data):
 for card in data['expansion_cards']:
  name=card['name']
  if name in C:
   card.update(C[name]);f=card['trigger']
   card['text']=(' / '.join(card.get('keywords',[])).title()+'. ' if card.get('keywords') else '')+EVENTS[f['event']]+', '+describe(f)+'.'
   for extra in f.get('then',[]):card['text']+=' Then '+describe(extra)+'.'
   if f.get('once_per_turn'):card['text']+=' Triggers once each turn.'
  if name in S:
   card.update(S[name]);spell=card['spell'];target=spell['target']
   prefix={'friendly':'Choose a friendly creature. ','enemy':'Choose an enemy creature. ','any':'Choose a creature or hero. ',None:''}[target]
   card['text']=prefix+'. '.join(describe(f,target).capitalize() for f in spell['effects'])+'.'
 # Gate early recursion / persistent-copy engines with appropriate mana costs.
 for card in data['expansion_cards']:
  if card['name']=='Kindle Apprentice':card['cost']=3
  if card['name']=='Prism Navigator':card['cost']=5
 return data

def catalog(data):
 cards=[dict(c,archetype=a) for a,cs in data['archetype_boosters'].items() for c in cs]+list(data['starter_cards'].values())+data['expansion_cards']
 lines=['# Card catalog','',f'{len(cards)} cards; 50 per faction. Expansion cards reuse the faction art library.','']
 for archetype in data['archetype_boosters']:
  lines += ['## '+archetype,'','| Card | Mana / color | Stats | Rules |','|---|---|---|---|']
  for c in cards:
   if c['archetype']==archetype:lines.append(f"| {c['name']} | {c['cost']} / {c['color']} | {str(c['atk'])+'/'+str(c['hp']) if c['hp'] else 'Spell'} | {c['text']} |")
  lines.append('')
 return '\n'.join(lines)
if __name__=='__main__':
 path=ROOT/'data/cards.json';data=apply_identities(json.loads(path.read_text()))
 path.write_text(json.dumps(data,indent=2)+'\n');(ROOT/'CARD_CATALOG.md').write_text(catalog(data))
 print('Refreshed curated card rules and the complete faction catalog.')
