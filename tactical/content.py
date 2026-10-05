"""Small curated pool. Rules use effect identifiers, never parsed English."""
COLORS = 'WUBRG'
KEYWORDS = {
    'Haste': 'May attack and exhaust for abilities immediately.',
    'Guard': 'Attacking does not exhaust this creature.',
    'Flying': 'Only creatures with Flying or Reach can block this.',
    'Reach': 'Can block Flying creatures.',
    'Trample': 'Excess damage after lethal blocker assignments reaches the defender.',
    'Lifesteal': 'Damage actually dealt also heals its controller.',
    'Ward': 'Opponents pay one additional generic mana to target this.',
    'Goad': 'Must attack if able, choosing someone other than the goader if possible.',
}

def creature(id, name, color, cost, attack, health, keywords=(), effect='', text=''):
    return dict(id=id, name=name, color=color, cost=cost, attack=attack, health=health,
                kind='creature', keywords=list(keywords), effect=effect, text=text,
                pips={color: 2 if cost >= 5 else 1} if color != 'C' else {})

def spell(id, name, color, cost, effect, text, target='', response=False, amount=0):
    return dict(id=id, name=name, color=color, cost=cost, kind='response' if response else 'spell',
                effect=effect, text=text, target=target, amount=amount, keywords=[],
                pips={color: 2 if cost >= 5 else 1} if color != 'C' else {})

CARDS = [
    creature('w_recruit', 'Citadel Recruit', 'W', 1, 1, 3, text='An early defensive body.'),
    creature('w_patrol', 'Dawn Patrol', 'W', 2, 2, 2, ['Guard']),
    creature('w_medic', 'Dawn Medic', 'W', 3, 2, 3, ['Lifesteal']),
    creature('w_captain', 'Formation Captain', 'W', 4, 2, 4, effect='formation', text='Your other creatures get +1 attack.'),
    spell('w_muster', 'Muster', 'W', 2, 'tokens', 'Create two 1/1 Recruits.', amount=2),
    spell('w_shield', 'Hold Formation', 'W', 1, 'protect', 'Prevent damage to a friendly creature this turn.', 'friendly', True),
    spell('w_exile', 'Equal Judgment', 'W', 4, 'exile', 'Exile a creature with attack 3 or greater.', 'large', True),
    spell('w_rally', 'United Front', 'W', 3, 'team_buff', 'Your creatures get +1/+1 until your next turn.', amount=1),
    creature('u_apprentice', 'Tide Apprentice', 'U', 1, 1, 2),
    creature('u_glider', 'Mist Glider', 'U', 2, 1, 3, ['Flying']),
    creature('u_scholar', 'Tide Scholar', 'U', 3, 1, 3, effect='draw', text='On entry, draw one card.'),
    creature('u_echo', 'Echo Savant', 'U', 4, 2, 4, effect='spell_draw', text='Your second noncreature spell each turn draws one card.'),
    spell('u_return', 'Turn Aside', 'U', 2, 'bounce', 'Return a creature to its owner’s hand.', 'creature', True),
    spell('u_counter', 'Null Sigil', 'U', 2, 'counter', 'Counter a pending spell or ability.', 'stack', True),
    spell('u_insight', 'Measured Insight', 'U', 2, 'filter', 'Draw three cards, then choose one to discard.', amount=3),
    spell('u_ready', 'Second Wind', 'U', 1, 'ready', 'Ready a friendly creature.', 'friendly', True),
    creature('b_shambler', 'Crypt Shambler', 'B', 1, 1, 2, effect='death_drain', text='On death, each opponent loses 1 health; you gain 1.'),
    creature('b_broker', 'Bone Broker', 'B', 2, 2, 2, effect='sacrifice', text='Exhaust, pay 1 mana and sacrifice another creature: draw one card.'),
    creature('b_collector', 'Soul Collector', 'B', 3, 2, 3, ['Lifesteal'], 'death_ping', 'Whenever another friendly creature dies, deal 1 damage to each opponent.'),
    creature('b_heir', 'Grave Heir', 'B', 4, 3, 4, effect='death_grow', text='Whenever another friendly creature dies, gain +1/+1.'),
    spell('b_recall', 'Grave Recall', 'B', 2, 'recall', 'Return a creature from your graveyard to hand.', 'grave'),
    spell('b_kill', 'Cruel Exchange', 'B', 3, 'destroy', 'Pay 2 health as a cost. Destroy a creature.', 'creature', True),
    spell('b_bargain', 'Dark Bargain', 'B', 1, 'bargain', 'Pay 2 health as a cost. Draw two cards.', amount=2),
    spell('b_revive', 'Unearth', 'B', 4, 'revive', 'Return a creature costing 3 or less from your graveyard to play.', 'small_grave'),
    creature('r_duelist', 'Ember Duelist', 'R', 1, 2, 1, ['Haste']),
    creature('r_raider', 'Cinder Raider', 'R', 2, 3, 1, ['Haste']),
    creature('r_weaver', 'Spellweaver', 'R', 3, 2, 2, effect='spell_damage', text='Whenever you cast a noncreature spell, deal 1 damage to each opponent.'),
    creature('r_charger', 'Ash Charger', 'R', 4, 5, 2, ['Haste', 'Trample']),
    spell('r_bolt', 'Magma Bolt', 'R', 2, 'damage', 'Deal 3 damage to a creature or player.', 'any', True, 3),
    spell('r_loot', 'Reckless Study', 'R', 1, 'draw', 'Discard a card as a cost. Draw two cards.', amount=2),
    spell('r_wipe', 'Cinder Rain', 'R', 4, 'wipe', 'Deal 3 damage to every creature.', amount=3),
    spell('r_anthem', 'Uneven Fury', 'R', 3, 'anthem', 'All creatures gain attack equal to max(0, printed attack − printed health). All have Haste while this is in play.'),
    creature('g_seed', 'Grove Tender', 'G', 1, 1, 3, ['Reach']),
    creature('g_sprite', 'Grove Sprite', 'G', 2, 1, 3, effect='mana', text='Exhaust: gain one temporary green mana.'),
    creature('g_sentinel', 'Thorn Sentinel', 'G', 3, 3, 4, ['Reach']),
    creature('g_beast', 'Ancient Beast', 'G', 6, 6, 7, ['Trample', 'Ward']),
    spell('g_ramp', 'Cultivate', 'G', 2, 'ramp', 'Gain one permanent green mana capacity, up to ten.'),
    spell('g_growth', 'Verdant Surge', 'G', 1, 'buff', 'A friendly creature gets +2/+2 until your next turn.', 'friendly', True, 2),
    spell('g_fight', 'Predator’s Challenge', 'G', 3, 'fight', 'Your strongest ready creature and a target creature deal their attack to each other.', 'enemy'),
    spell('g_insight', 'Canopy Counsel', 'G', 3, 'draw', 'Draw two cards.', amount=2),
    spell('r_goad', 'Wild Provocation', 'R', 3, 'goad', 'Goad every creature currently in play through its controller’s next turn.'),
]
# Neutral utility participates in every identity; the prototype is intentionally >40
# to exercise shared support rather than create five isolated eight-card decks.
CARDS += [
    creature('c_sentry', 'Prism Sentry', 'C', 2, 1, 3, ['Reach']),
    spell('c_break', 'Disrupt Engine', 'C', 3, 'remove_engine', 'Remove a noncreature engine (never a relic).', 'engine', True),
    spell('c_chart', 'Chart a Course', 'C', 3, 'draw', 'Draw two cards.', amount=2),
    spell('c_relay', 'Reclamation Relay', 'C', 5, 'relay', 'Whenever a friendly token dies, ready your creatures and gain 1 temporary mana.'),
    spell('c_nest', 'Recruit Foundry', 'C', 4, 'foundry', 'On entry, create a Recruit. Whenever a friendly token dies, create a Recruit.'),
]
CARD_MAP = {c['id']: c for c in CARDS}

def commander(id, name, colors, packages):
    return dict(id=id, name=name, colors=list(colors), packages=[
        dict(name=n, passive=p, active=a, description=d) for n,p,a,d in packages])

COMMANDERS = [
    commander('dawn', 'Aurelia, Dawn Marshal', 'W', [('Shield Line','wide','protect','Wide boards strengthen your commander; exhaust to protect an ally.'), ('Radiant Patrol','lifesteal','token','Commander has Lifesteal; exhaust to create a Recruit.')]),
    commander('tide', 'Neris, Tide Archivist', 'U', [('Patient Scholar','second_draw','draw','Your second spell each turn draws a card; exhaust to draw.'), ('Mist Captain','flying','bounce','Commander has Flying; exhaust to return a creature to hand.')]),
    commander('crypt', 'Veyra, Crypt Matron', 'B', [('Grave Court','death_heal','recall','Friendly deaths heal you; exhaust to recover a creature.'), ('Blood Contract','lifesteal','sacrifice','Commander has Lifesteal; exhaust and sacrifice an ally to draw two.')]),
    commander('ember', 'Rakka, Ember Duelist', 'R', [('Flash Assault','haste','damage','Commander has Haste; exhaust to deal two damage.'), ('Spell Furnace','second_damage','loot','Your second spell damages each opponent; exhaust and discard to draw two.')]),
    commander('grove', 'Orun, Grove Warden', 'G', [('Patient Growth','ward','ramp','Commander has Ward; exhaust to add green capacity.'), ('Beast March','trample','buff','Commander has Trample; exhaust to give an ally +2/+2.')]),
    commander('wu', 'Elya, Formation Weaver', 'WU', [('Sky Formation','flying','token','Flying commander and reinforcement support coordinated attacks.'), ('Watchful Tide','guard','protect','Guard commander and protection reward reserved defenses.')]),
    commander('ub', 'Seth, Memory Broker', 'UB', [('Quiet Intrigue','second_draw','bounce','Chain spells for cards; return opposing threats.'), ('Grave Circuit','death_heal','recall','Preserve health through sacrifice; recover lost pieces.')]),
    commander('br', 'Kora, Ash Reclaimer', 'BR', [('Blood Rush','haste','sacrifice','Haste pressure; sacrifice an ally to draw two.'), ('Ember Return','death_heal','recall','Friendly deaths heal you; recover attackers for another push.')]),
    commander('rg', 'Tarn, Wildfire Herald', 'RG', [('Stampede','haste','token','Haste commander; add attackers to a wide board.'), ('Mountain Heart','trample','ramp','Trample commander; ramp toward large threats.')]),
    commander('gw', 'Iona, Living Bastion', 'GW', [('Root Formation','wide','buff','Wide boards strengthen your commander; grow an ally.'), ('Enduring Oath','ward','protect','Ward commander; protect a key creature.')]),
]
COMMANDER_MAP = {c['id']: c for c in COMMANDERS}
PROTOTYPE_COMMANDERS = ['dawn', 'tide', 'crypt', 'br', 'rg']
RELICS = [
    dict(id='reserves', name='Patient Reserves', text='If you ended your turn with at least 2 unspent mana, heal 1.', effect='reserves'),
    dict(id='ashes', name='Ash Ledger', text='Your first friendly death each turn heals you 1.', effect='ashes'),
    dict(id='chorus', name='Chorus Stone', text='At your turn start, if you have at least four creatures, gain 1 temporary mana.', effect='chorus'),
    dict(id='edge', name='Risky Edge', text='Your creatures get +1 attack while you have 10 health or less.', effect='edge'),
    dict(id='lens', name='Focused Lens', text='After your third noncreature spell in a turn, draw one card.', effect='lens'),
    dict(id='roots', name='Root Pact', text='When you gain capacity through ramp, heal 1.', effect='roots'),
]
RELIC_MAP = {r['id']: r for r in RELICS}
BASICS = {'W':'w_recruit', 'U':'u_apprentice', 'B':'b_shambler', 'R':'r_duelist', 'G':'g_seed'}

def legal(card_id, colors):
    return CARD_MAP[card_id]['color'] in list(colors) + ['C']

def starter(colors):
    pool = [c for c in CARDS if c['color'] in colors]
    if len(colors) == 1:
        deck = [c['id'] for c in pool for _ in range(2)]
    else:
        deck = [c['id'] for c in pool]
        for color in colors:
            deck += [c['id'] for c in pool if c['color'] == color and c['kind'] == 'creature'][:2]
    deck += ['c_sentry','c_sentry','c_break','c_break','c_chart','c_chart']
    basics = [BASICS[c] for c in colors]
    while len(deck) < 30:
        deck.append(basics[len(deck) % len(basics)])
    return deck[:30]

def draft_pack(rng):
    pack = []
    for color in COLORS:
        pack.extend(rng.sample([c['id'] for c in CARDS if c['color'] == color], 2))
    pack.extend(rng.sample([c['id'] for c in CARDS if c['color'] == 'C'], 2))
    pack.extend(rng.sample(list(CARD_MAP), 3))
    return pack

def personal_pack(rng, colors, size=5, minimum=2):
    choices = [c['id'] for c in CARDS if legal(c['id'], colors)]
    pack = rng.sample(choices, minimum)
    remainder = [c for c in CARD_MAP if c not in pack]
    pack += rng.sample(remainder, size-minimum)
    rng.shuffle(pack)
    return pack
