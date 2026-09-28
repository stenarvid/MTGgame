"""Idempotently expand every faction to 50 mechanically distinct cards."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / 'data' / 'cards.json'

NAMES = {
    'Token': ['Gilded Standard','Dawnline Captain','Oathhall Squire','Procession Angel','Bastion Choir','Sunwall Tactician','Bannerwing Scout','Citadel Matron','Radiant Twin','Lastlight Marshal','Muster the Meek','March of Shields','Oath of Fellowship','Dawnfront Formation','Call the Seraphs','Hold the Line','Shared Triumph','Sanctuary Muster','Banner of Resolve','Final Procession'],
    'Blink': ['Riftglass Seer','Mistway Courier','Echo Chamberlain','Tidefold Adept','Vanishing Oracle','Aether Cartographer','Moonwake Familiar','Loopbound Scholar','Stillwater Guide','Chronicle Diver','Momentary Passage','Fold into Mist','Echoed Arrival','Riftglass Denial','Borrowed Tomorrow','Tidal Repetition','Memory Loop','Aether Evacuation','Second Arrival','Endless Corridor'],
    'Graveyard': ['Ossuary Ferryman','Gravesoil Tender','Bloodledger Adept','Mourning Revenant','Cryptwake Seer','Bone Taxer','Last-Breath Scribe','Dusk Reclaimer','Ashen Celebrant','Sepulcher Regent','Feed the Crypt','Price of Memory','Requiem Bargain','Open the Ossuary','Blood for Knowledge','Graveborn Host','Final Testament','Harvest the Fallen','Debt to the Dead','Midnight Resurrection'],
    'Spells': ['Runespark Prodigy','Cinderchain Mage','Emberline Savant','Flarewing Adept','Ashstorm Caller','Voltaic Duelist','Pyre Archivist','Spellscar Phoenix','Inferno Conductor','Lastspark Oracle','Kindle the Chain','Forked Cinder','Runic Detonation','Storm of Embers','Reckless Research','Flashfire Volley','Arc of Ruin','Pyromancer’s Encore','Combustive Insight','Worldfire Equation'],
    'Ramp': ['Seedpath Initiate','Rootmap Druid','Canopy Grazer','Loamheart Sage','Wildland Envoy','Barkcrown Warden','Trailborn Giant','Verdant Behemoth','Worldroot Keeper','Primeval Wayfinder','Open the Trail','Season of Plenty','Canopy’s Gift','Roots Remember','Titanic Emergence','Verdant Stampede','Living Landscape','Ancient Provisions','Worldseed Awakening','Endless Wilds'],
    'Morph': ['Prismatic Mite','Memory-Skin Adept','Chorus Familiar','Cinder Mimic','Rootglass Larva','Mourning Chrysalis','Welcoming Doppel','Adaptive Witness','Mosaic Shepherd','Rewritten Guardian','Prismwake Oracle','Formless Attendant','Blooming Replica','Echo-Skin Savant','Manyfold Keeper','Transfigured Herald','Living Palimpsest','Perfected Mimic','Mosaic Sovereign','Borrowed Shape','Prismatic Graft','Memory Imprint','Chorus Rewrite','Cinder Mutation','Rooted Mutation','Mourning Mutation','Welcoming Mutation','Hostile Reflection','Selective Evolution','Mosaic Cascade','Blink the Many','Rewrite the Fallen','Shape the Future','Prismatic Rebirth','Convergent Bloom','Unmake Identity','Shared Adaptation','Grand Metamorphosis','Perfect Reassembly']
}

COLORS = {'Token':'W','Blink':'U','Graveyard':'B','Spells':'R','Ramp':'G','Morph':'P'}
EVENTS = ['enter','attack','ally_enters','spell_cast','land','dies','ally_dies','enemy_dies']
EVENT_TEXT = {'enter':'When this enters','attack':'When this attacks',
              'ally_enters':'Whenever another nontoken creature enters under your control',
              'spell_cast':'Whenever you cast a noncreature spell','land':'Whenever you play a land',
              'dies':'When this dies','ally_dies':'Whenever another friendly creature dies',
              'enemy_dies':'Whenever an enemy creature dies'}
CONDITION_TEXT = {'wide_board':'if you control at least four creatures',
                  'six_lands':'if you control at least six lands',
                  'second_spell':'if this is your second noncreature spell this turn',
                  'graveyard_full':'if your graveyard contains at least three creatures',
                  'empty_hand':'if you have one or fewer cards in hand'}

def e(kind, amount=0, **kw):
    return dict(effect=kind, amount=amount, **kw)

CREATURE_EFFECTS = {
    'Token': [e('tokens',1),e('custom_tokens',1,token={'name':'Dawn Shieldbearer','color':'W','attack':0,'health':3,'keywords':['guard']}),e('heal',2),e('buff_group',1,selection='tokens',permanent=True),e('armor',2),e('draw',1),e('grant_keyword',keyword='vigilance',selection='tokens'),e('tokens',2),e('buff_group',1,selection='all'),e('custom_tokens',1,token={'name':'Sunlit Spirit','color':'W','attack':1,'health':1,'keywords':['haste']})],
    'Blink': [e('draw',1),e('loot',2),e('freeze',1),e('recover_spell',1),e('armor',2),e('untap_lands',1),e('draw',1),e('heal',3),e('draw',2),e('self_buff',1)],
    'Graveyard': [e('mill',2),e('recall',1),e('drain',1),e('armor',2),e('reanimate',1,max_cost=2),e('loot',2),e('custom_tokens',1,token={'name':'Bone Thrall','color':'B','attack':2,'health':1}),e('recover_spell',1),e('draw',1),e('drain',2)],
    'Spells': [e('damage',1),e('loot',1),e('custom_tokens',1,token={'name':'Cinder Spark','color':'R','attack':1,'health':1,'keywords':['haste']}),e('self_buff',1),e('draw',1),e('armor',2),e('recover_spell',1),e('damage',2),e('buff_group',1,selection='attacking'),e('power_damage',0)],
    'Ramp': [e('search',1),e('self_buff',1),e('draw',1),e('heal',2),e('custom_tokens',1,token={'name':'Wildseed Plant','color':'G','attack':0,'health':2}),e('untap_lands',1),e('grant_keyword',keyword='trample',selection='all'),e('buff_group',1,selection='all',permanent=True),e('armor',3),e('custom_tokens',1,token={'name':'Thicket Beast','color':'G','attack':3,'health':3,'keywords':['trample']})],
}

SPELL_EFFECTS = {
    'Token': [(e('tokens',2),),(e('custom_tokens',1,token={'name':'Dawn Shieldbearer','color':'W','attack':0,'health':3,'keywords':['guard']}),),(e('tokens',1),e('draw',1)),(e('buff_group',1,selection='tokens',permanent=True),e('armor',1)),(e('custom_tokens',2,token={'name':'Sunlit Spirit','color':'W','attack':1,'health':1,'keywords':['haste']}),),(e('armor',4),e('tokens',1)),(e('grant_keyword',keyword='guard',selection='all'),),(e('heal',2,scale='tokens',cap=5),),(e('buff_group',2,selection='attacking'),),(e('tokens',3),e('buff_group',1,selection='tokens'))],
    'Blink': [(e('blink'),),(e('blink'),e('draw',1)),(e('bounce'),),(e('freeze',2),),(e('loot',3),),(e('recover_spell',1),e('draw',1)),(e('blink'),e('armor',3)),(e('bounce'),e('draw',1)),(e('untap_lands',3),e('draw',1)),(e('blink_board',1),)],
    'Graveyard': [(e('mill',3),e('recall',1)),(e('sacrifice'),e('draw',2)),(e('drain',2,scale='graveyard',cap=3),),(e('reanimate',1,max_cost=3),),(e('destroy'),e('mill',2)),(e('pay_life',2),e('draw',3)),(e('custom_tokens',2,token={'name':'Bone Thrall','color':'B','attack':2,'health':1}),),(e('recover_spell',2),),(e('sacrifice'),e('reanimate',1,max_cost=4)),(e('reanimate',2,max_cost=3),e('pay_life',3))],
    'Spells': [(e('damage',2),),(e('damage',1),e('draw',1)),(e('area_damage',2),),(e('damage',3,scale='spells',cap=3),),(e('loot',2),e('damage',2)),(e('custom_tokens',2,token={'name':'Cinder Spark','color':'R','attack':1,'health':1,'keywords':['haste']}),),(e('buff',0,power=5),e('grant_keyword',keyword='haste')),(e('damage',2),e('recover_spell',1)),(e('draw',2),e('damage',2,condition='second_spell')),(e('area_damage',3),e('damage',4))],
    'Ramp': [(e('search',1),),(e('search',1),e('untap_lands',1)),(e('draw',1,scale='lands',cap=3),),(e('buff',4,power=4),e('grant_keyword',keyword='trample')),(e('custom_tokens',1,token={'name':'Thicket Beast','color':'G','attack':3,'health':3,'keywords':['trample']}),),(e('buff_group',2,selection='all'),),(e('search',2),e('heal',2)),(e('grant_keyword',keyword='vigilance',selection='all'),e('untap_lands',2)),(e('custom_tokens',2,token={'name':'Wildseed Plant','color':'G','attack':0,'health':2}),e('draw',1)),(e('search',3),e('buff_group',1,selection='all',permanent=True))],
}

MUTATIONS = ['insight','chorus','hospitality','spellflame','landgrowth','mourning','death_curse']

def target_for(effects):
    kinds = {x['effect'] for x in effects}
    if kinds & {'blink','buff','sacrifice'}: return 'friendly'
    if kinds & {'bounce','destroy'}: return 'enemy'
    if 'damage' in kinds: return 'any'
    return None

def describe_effect(x):
    kind=x['effect']; n=x.get('amount',0)
    mutation={'death_curse':'Death Curse','landgrowth':'Rootgrowth','spellflame':'Spellflame',
              'hospitality':'Welcoming','insight':'Insight','chorus':'Chorus',
              'mourning':'Mourning'}.get(x.get('mutation',''),x.get('mutation',''))
    cards='card' if n==1 else 'cards'; creatures='creature' if n==1 else 'creatures'
    lands='land' if n==1 else 'lands'; tokens='token' if n==1 else 'tokens'
    groups={'all':'creatures','tokens':'tokens','attacking':'attacking creatures','nontokens':'nontoken creatures'}
    return {
        'tokens':f'create {n} 1/1 Recruit {tokens}', 'custom_tokens':f"create {n} {x.get('token',{}).get('name','special')} {tokens}",
        'heal':f'gain {n} life', 'armor':f'gain {n} armor', 'draw':f'draw {n} {cards}', 'loot':f'draw {n} {cards}, then discard your highest-cost card',
        'damage':f'deal {n} damage', 'area_damage':f'deal {n} damage to each enemy creature', 'drain':f'drain {n} life from the enemy hero',
        'mill':f'put the top {n} {cards} of your deck into your graveyard', 'recall':f'return {n} {creatures} from your graveyard to hand', 'recover_spell':f"return {n} {'spell' if n==1 else 'spells'} from your graveyard to hand",
        'reanimate':f"return {n} {creatures} costing {x.get('max_cost',3)} or less from your graveyard to play", 'pay_life':f'lose {n} life',
        'search':f'play {n} additional {lands} from your reserve this turn', 'untap_lands':f'untap {n} {lands}', 'self_buff':f'this gets +{n}/+{n} permanently',
        'buff_group':f"your {groups.get(x.get('selection','all'), 'creatures')} get +{n}/+{n}" + (' permanently' if x.get('permanent') else ' this turn'),
        'grant_keyword':f"grant {x.get('keyword')} permanently", 'freeze':f'tap {n} enemy {creatures}; they skip their next untap', 'copy':'create a copy of another creature',
        'power_damage':"deal this creature's power to the enemy hero", 'blink':'blink a friendly creature', 'blink_board':'blink all friendly nontoken creatures',
        'bounce':'return an enemy creature to its owner’s hand', 'destroy':'destroy an enemy creature', 'sacrifice':'sacrifice a friendly creature',
        'buff':f"a friendly creature gets +{x.get('power',0)}/+{n} this turn", 'morph':f'Morph a friendly creature with {mutation}',
        'morph_board':f'Morph creatures across battlefield, deck, and graveyard with {mutation}', 'morph_self':f'this perpetually gains {mutation}'
    }[kind]

def regular_cards(faction):
    color=COLORS[faction]; names=NAMES[faction]; cards=[]
    stats=[(1,1,2),(2,2,2),(2,1,3),(3,3,2),(3,2,4),(4,4,3),(4,3,5),(5,5,4),(5,4,6),(6,6,6)]
    effects=CREATURE_EFFECTS[faction]
    for i,name in enumerate(names[:10]):
        cost,atk,hp=stats[i]; primary=effects[i]
        trigger=dict(event=EVENTS[i%len(EVENTS)], **primary)
        if i in (4,8): trigger['condition']='wide_board' if faction=='Token' else 'six_lands' if faction=='Ramp' else 'second_spell' if faction=='Spells' else 'graveyard_full' if faction=='Graveyard' else 'empty_hand'
        if i in (6,9): trigger['once_per_turn']=True
        clause=describe_effect(primary)
        if trigger.get('condition'): clause=CONDITION_TEXT[trigger['condition']]+', '+clause
        text=f"{EVENT_TEXT[trigger['event']]}, {clause}."
        for follow in trigger.get('then',[]): text+=' Then '+describe_effect(follow)+'.'
        if trigger.get('once_per_turn'): text+=' Triggers once each turn.'
        cards.append(dict(name=name,type='Cyber Fighter',color=color,cost=cost,atk=atk,hp=hp,archetype=faction,set='Convergence',trigger=trigger,text=text))
    for i,name in enumerate(names[10:]):
        effects=list(SPELL_EFFECTS[faction][i]); target=target_for(effects)
        prefix={'friendly':'Choose a friendly creature. ','enemy':'Choose an enemy creature. ','any':'Choose a creature or hero. ',None:''}[target]
        text=prefix+'. Then '.join(describe_effect(x).capitalize() for x in effects)+'.'
        cards.append(dict(name=name,type='Instant Spell',color=color,cost=1+i//2,atk=0,hp=0,archetype=faction,set='Convergence',spell=dict(target=target,effects=effects),text=text))
    return cards

def morph_cards():
    names=NAMES['Morph']; cards=[]
    stats=[(1,1,1),(2,1,3),(2,2,2),(3,3,2),(3,2,4),(3,1,5),(4,4,3),(4,3,5),(4,2,6),(5,5,4),(5,4,6),(2,2,3),(3,3,3),(4,3,4),(5,5,5),(2,1,4),(3,2,5),(5,4,5),(6,6,6)]
    for i,name in enumerate(names[:19]):
        mutation=MUTATIONS[i%len(MUTATIONS)]; primary=e('morph_self',1,mutation=mutation)
        trigger=dict(event=EVENTS[i%len(EVENTS)],**primary)
        if trigger['event'] == 'dies':
            trigger['event'] = 'ally_dies'
        if i>=7: trigger['then']=[e(('draw','heal','armor','self_buff')[i%4],1)]
        if i in (12,15,18): trigger['once_per_turn']=True
        cost,atk,hp=stats[i]
        text=f"{EVENT_TEXT[trigger['event']]}, {describe_effect(primary)}."
        for follow in trigger.get('then',[]): text+=' Then '+describe_effect(follow)+'.'
        if trigger.get('once_per_turn'): text+=' Triggers once each turn.'
        cards.append(dict(name=name,type='Cyber Fighter',color='P',cost=cost,atk=atk,hp=hp,archetype='Morph',set='Convergence',trigger=trigger,text=text))
    for i,name in enumerate(names[19:]):
        mutation=MUTATIONS[i%len(MUTATIONS)]
        if i in (8,13,18): effects=[e('morph_board',1,selection='friendly',mutation=mutation)]
        elif i in (7,15): effects=[e('morph_board',1,selection='enemy',mutation='death_curse')]
        elif i in (10,19): effects=[e('blink_board',1)]
        else:
            effects=[e('morph',1,mutation=mutation)]
            if i%3==0: effects.append(e('blink'))
            elif i%3==1: effects.append(e('draw',1))
            else: effects.append(e('heal',2))
        target='friendly' if any(x['effect'] in ('morph','blink') for x in effects) else None
        prefix='Choose a friendly creature. ' if target else ''
        text=prefix+'. Then '.join(describe_effect(x).capitalize() for x in effects)+'.'
        cards.append(dict(name=name,type='Instant Spell',color='P',cost=1+i//4,atk=0,hp=0,archetype='Morph',set='Convergence',spell=dict(target=target,effects=effects),text=text))
    return cards

def refresh_text(card):
    if card.get('trigger'):
        trigger=card['trigger']; clause=describe_effect(trigger)
        if trigger.get('condition'): clause=CONDITION_TEXT[trigger['condition']]+', '+clause
        text=f"{EVENT_TEXT[trigger['event']]}, {clause}."
        for follow in trigger.get('then',[]): text+=' Then '+describe_effect(follow)+'.'
        if trigger.get('once_per_turn'): text+=' Triggers once each turn.'
        card['text']=text
    elif card.get('spell'):
        spell=card['spell']; target=spell.get('target')
        prefix={'friendly':'Choose a friendly creature. ','enemy':'Choose an enemy creature. ',
                'any':'Choose a creature or hero. ',None:''}[target]
        card['text']=prefix+'. Then '.join(describe_effect(x).capitalize() for x in spell['effects'])+'.'

def main():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    additions=[]
    for faction in ('Token','Blink','Graveyard','Spells','Ramp'):
        additions.extend(regular_cards(faction))
    additions.extend(morph_cards())
    by_name={card['name']:card for card in additions}
    trigger_followups={
        'Canopy Grazer':e('heal',1), 'Mistway Courier':e('armor',1),
        'Flarewing Adept':e('damage',1), 'Seedpath Initiate':e('heal',1),
        'Barkcrown Warden':e('armor',2),
    }
    for name,follow in trigger_followups.items():
        by_name[name]['trigger'].setdefault('then',[]).append(follow)
    spell_followups={
        'Echoed Arrival':e('armor',2), 'Season of Plenty':e('armor',1),
        'Endless Corridor':e('draw',1), 'Mosaic Cascade':e('heal',2),
        'Perfect Reassembly':e('armor',3), 'Convergent Bloom':e('armor',2),
    }
    for name,follow in spell_followups.items():
        by_name[name]['spell']['effects'].append(follow)
    for card in additions: refresh_text(card)
    generated=set(sum(NAMES.values(),[]))
    # Remove cards written by an older Windows-console run that mojibaked curly
    # punctuation before the generator switched to explicit UTF-8.
    generated |= {name.encode('utf-8').decode('latin1') for name in list(generated)}
    def stale_generated(card):
        name=card['name']
        return (card.get('set') == 'Convergence' or name in generated or
                (name.startswith('Pyromancer') and name.endswith('s Encore')) or
                (name.startswith('Canopy') and name.endswith('s Gift')))
    data['expansion_cards']=[card for card in data.get('expansion_cards',[]) if not stale_generated(card)]
    data['expansion_cards'].extend(additions)
    PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Added {len(additions)} cards; every faction now has 50 unique cards.')

if __name__=='__main__': main()
