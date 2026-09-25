"""Idempotently add the second, 100-card expansion and rebuild its catalog."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
path = ROOT / 'data/cards.json'
data = json.loads(path.read_text())
creatures = {
'Token': [
 ('Sunlit Cadet',1,1,1,'enter','tokens',1), ('Oathbound Herald',3,2,3,'enter','tokens',2),
 ('Dawn Procession Leader',5,3,4,'enter','tokens',3), ('Silverwing Chaplain',2,1,3,'attack','heal',2),
 ('Banner Scribe',3,1,4,'ally_enters','draw',1), ('Shieldwall Captain',4,3,3,'attack','team_buff',1),
 ('Radiant Quartermaster',3,2,3,'spell_cast','tokens',1), ('Lastwatch Veteran',2,2,2,'dies','tokens',2),
 ('Sunforge Architect',4,2,4,'land','tokens',1), ('Seraph of the Muster',6,4,5,'attack','tokens',3)],
'Blink': [
 ('Rift Apprentice',1,1,1,'enter','draw',1), ('Moonlit Savant',4,2,3,'enter','draw',2),
 ('Prism Navigator',4,3,3,'attack','copy',1), ('Echo Attendant',2,1,3,'ally_enters','heal',2),
 ('Tideglass Oracle',4,2,4,'spell_cast','draw',1), ('Departing Scholar',2,2,1,'dies','draw',1),
 ('Mistveil Envoy',3,2,3,'enter','heal',4), ('Planar Surveyor',3,1,4,'enter','land',1),
 ('Memory Diver',3,2,3,'enter','recall',1), ('Astral Cartographer',5,3,5,'attack','draw',2)],
'Graveyard': [
 ('Dusk Acolyte',1,1,1,'dies','drain',2), ('Funeral Chronicler',3,1,4,'ally_dies','draw',1),
 ('Ossuary Warden',4,3,4,'enemy_dies','heal',2), ('Bloodwake Rider',3,3,2,'attack','drain',2),
 ('Gravebell Keeper',3,2,3,'dies','recall',1), ('Revenant Archivist',5,3,4,'enter','recall',2),
 ('Bone Lantern Bearer',2,1,3,'ally_dies','heal',2), ('Ashen Mourner',4,2,4,'enemy_dies','draw',1),
 ('Crypt Broodmother',5,3,5,'dies','tokens',3), ('Nightfall Harvester',6,4,5,'attack','drain',3)],
'Spells': [
 ('Kindle Apprentice',1,1,1,'enter','damage',1), ('Flare Duelist',2,2,2,'attack','damage',1),
 ('Runespark Defender',3,1,4,'spell_cast','heal',2), ('Emberquill Scholar',4,2,3,'enter','draw',2),
 ('Cinderheart Adept',3,2,3,'spell_cast','self_buff',1), ('Volcanic Herald',5,3,4,'enter','damage',4),
 ('Ashburst Familiar',2,2,1,'dies','damage',2), ('Blazewing Commander',5,3,4,'spell_cast','team_buff',1),
 ('Wildfire Summoner',5,2,5,'spell_cast','tokens',2), ('Inferno Oracle',6,4,4,'attack','damage',4)],
'Ramp': [
 ('Seedling Pilgrim',1,1,1,'enter','search',1), ('Mossheart Healer',2,1,4,'land','heal',3),
 ('Verdant Wayfinder',4,2,4,'enter','land',2), ('Barkhide Guardian',4,3,5,'land','self_buff',2),
 ('Canopy Archivist',3,2,3,'enter','draw',1), ('Wildroot Matriarch',5,3,5,'land','team_buff',1),
 ('Thicket Nestkeeper',4,2,4,'land','tokens',2), ('Forestwake Colossus',6,5,6,'attack','land',2),
 ('Autumn Reclaimer',4,3,4,'dies','recall',1), ('Worldseed Ancient',7,5,7,'land','draw',2)]}
# Spell tuple: name, mana cost, target (None/friendly/enemy/any), effects.
def e(effect, amount=0, **extra): return dict(effect=effect, amount=amount, **extra)
spells={
'Token': [
 ('Call the Watch',2,None,[e('tokens',3)]), ('Citadel Assembly',4,None,[e('tokens',5)]),
 ('Shared Resolve',2,None,[e('team_buff',1)]), ('Dawnward Blessing',3,None,[e('team_buff',2)]),
 ('Sheltering Light',1,'friendly',[e('buff',3,power=0),e('heal',2)]),
 ('Recruitment Orders',3,None,[e('tokens',2),e('draw',1)]), ('Sanctuary Bells',2,None,[e('tokens',1),e('heal',4)]),
 ('Raise the Ramparts',3,None,[e('tokens',2),e('armor',3)]), ('United Charge',4,None,[e('tokens',2),e('team_buff',1)]),
 ('Last Light Rally',5,None,[e('tokens',4),e('heal',5)])],
'Blink': [
 ('Fleeting Reflection',1,'friendly',[e('blink')]), ('Slip Through Mist',2,'friendly',[e('blink'),e('draw',1)]),
 ('Return to Stillwater',2,'enemy',[e('bounce')]), ('Rift Rejection',3,'enemy',[e('bounce'),e('draw',1)]),
 ('Deepwater Study',2,None,[e('draw',2)]), ('Memory Cascade',4,None,[e('draw',3)]),
 ('Sheltered Passage',2,'friendly',[e('blink'),e('heal',4)]), ('Borrowed Memories',3,None,[e('recall',1),e('draw',1)]),
 ('Temporal Shelter',2,'friendly',[e('buff',4,power=0),e('draw',1)]), ('Prismatic Journey',4,'friendly',[e('blink'),e('draw',2)])],
'Graveyard': [
 ('Whisper from Below',1,None,[e('recall',1)]), ('Ossuary Expedition',3,None,[e('recall',2)]),
 ('Blood Tithe',2,None,[e('drain',3)]), ('Midnight Feast',4,None,[e('drain',5)]),
 ('Grave Sentence',3,'enemy',[e('destroy')]), ('Soul Reclamation',5,'enemy',[e('destroy'),e('recall',1)]),
 ('Funeral Offering',2,None,[e('recall',1),e('heal',3)]), ('Dark Testament',3,None,[e('draw',2),e('drain',1)]),
 ('Bonewall Pact',3,None,[e('tokens',2),e('armor',2)]), ('Gravesong Renewal',5,None,[e('recall',3),e('heal',3)])],
'Spells': [
 ('Searing Needle',1,'any',[e('damage',2)]), ('Scorching Arc',2,'any',[e('damage',4)]),
 ('Phoenix Flare',4,'any',[e('damage',6)]), ('Rain of Embers',3,None,[e('area_damage',2)]),
 ('Volcanic Reckoning',5,None,[e('area_damage',4)]), ('Inspired Ignition',2,None,[e('damage',2),e('draw',1)]),
 ('Runefire Study',3,None,[e('draw',2),e('damage',1)]), ('Cinder Reinforcements',3,None,[e('tokens',2),e('damage',2)]),
 ('Overheated Edge',2,'friendly',[e('buff',1,power=4)]), ('Final Conflagration',6,None,[e('area_damage',3),e('damage',4)])],
'Ramp': [
 ('Trail of Seeds',1,None,[e('search',2)]), ('Rootway Expedition',2,None,[e('ramp',1)]),
 ('Awaken the Grove',4,None,[e('ramp',2)]), ('Canopy Insight',3,None,[e('ramp',1),e('draw',1)]),
 ('Titanic Mantle',3,'friendly',[e('buff',5,power=5)]), ('Barkskin Veil',1,'friendly',[e('buff',4,power=0)]),
 ('Wildwood Communion',3,None,[e('draw',2),e('heal',3)]), ('Seedborn Reinforcements',4,None,[e('ramp',1),e('tokens',2)]),
 ('Overgrowth March',5,None,[e('team_buff',3)]), ('Worldroot Renewal',6,None,[e('ramp',3),e('heal',6)])]}
events={'attack':'When this attacks','enter':'When this enters','ally_enters':'Whenever another nontoken creature enters under your control','ally_dies':'Whenever another friendly creature dies','enemy_dies':'Whenever an enemy creature dies','dies':'When this dies','spell_cast':'Whenever you cast a noncreature spell','land':'Whenever you play a land'}
def describe(effect):
 n=effect['amount']; kind=effect['effect']
 return {'copy':'choose another friendly nontoken creature; create a token copy tapped and attacking, then exile it at turn end',
 'tokens':f'create {n} 1/1 Recruit token(s)', 'heal':f'heal your hero for {n}', 'draw':f'draw {n} card(s)',
 'damage':f'deal {n} damage', 'drain':f'the enemy hero loses {n} life and you gain {n}',
 'recall':f'return {n} highest-cost creature(s) from your discard to hand',
 'land':f'search your deck for {n} land(s) and put them into play tapped',
 'ramp':f'search your deck for {n} land(s) and put them into play tapped',
 'search':f'search your deck for {n} land(s) and put them into your hand',
 'team_buff':f'your creatures get +{n}/+{n} until end of turn', 'self_buff':f'this gets +{n}/+{n} permanently',
 'armor':f'gain {n} armor', 'area_damage':f'deal {n} damage to each enemy creature',
 'buff':f'that creature gets +{effect.get("power",0)}/+{n} until end of turn',
 'blink':'blink that friendly creature', 'bounce':"return that enemy creature to its owner's hand",
 'destroy':'destroy that enemy creature'}[kind]
new=[]
for archetype,color in zip(creatures,'WUBRG'):
 for name,cost,atk,hp,event,effect,amount in creatures[archetype]:
  trigger=dict(event=event,effect=effect,amount=amount)
  text=events[event]+', '+describe(trigger)+(' to the enemy hero' if effect=='damage' else '')+'.'
  new.append(dict(name=name,type='Cyber Fighter',color=color,cost=cost,atk=atk,hp=hp,archetype=archetype,text=text,trigger=trigger))
 for name,cost,target,effects in spells[archetype]:
  prefix={'friendly':'Choose a friendly creature. ','enemy':'Choose an enemy creature. ','any':'Choose any creature or hero. ',None:''}[target]
  texts=[describe(effect)+(' to that target' if target=='any' else ' to the enemy hero') if effect['effect']=='damage' else describe(effect) for effect in effects]
  new.append(dict(name=name,type='Instant Spell',color=color,cost=cost,atk=0,hp=0,archetype=archetype,text=prefix+'. '.join(t[0].upper()+t[1:] for t in texts)+'.',spell=dict(target=target,effects=effects)))
names={c['name'] for c in new}
data['expansion_cards']=[c for c in data['expansion_cards'] if c['name'] not in names]+new
from refine_cards import apply_identities, catalog
apply_identities(data)
path.write_text(json.dumps(data,indent=2)+'\n')
(ROOT/'CARD_CATALOG.md').write_text(catalog(data))
print(f'{len(new)} expansion cards; curated identities retained.')
