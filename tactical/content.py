"""Small curated pool. Rules use effect identifiers, never parsed English."""
COLORS = 'WUBRG'
KEYWORDS = {
    'Flash': 'You may cast this card whenever you have priority. Its activated abilities retain their printed speed.',
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
    creature('w_recruit', 'Citadel Recruit', 'W', 1, 1, 3, text='No special abilities.'),
    creature('w_patrol', 'Dawn Patrol', 'W', 2, 2, 2, ['Guard']),
    creature('w_medic', 'Dawn Medic', 'W', 3, 2, 3, ['Lifesteal']),
    creature('w_captain', 'Formation Captain', 'W', 4, 2, 4, effect='formation', text='While this is on your battlefield, your other creatures have +1 attack.'),
    spell('w_muster', 'Muster', 'W', 2, 'tokens', 'Create two Recruit creature tokens, each with 1 attack and 1 health.', amount=2),
    spell('w_shield', 'Hold Formation', 'W', 1, 'protect', 'Prevent all damage to a creature you control until the end of this turn.', 'friendly', True),
    spell('w_exile', 'Equal Judgment', 'W', 4, 'exile', 'Remove a creature with at least 3 attack from the battlefield without killing it. It does not go to the graveyard. A commander returns to its command zone instead.', 'large', True),
    spell('w_rally', 'United Front', 'W', 3, 'team_buff', 'Each creature you currently control gains +1 attack and +1 health until your next turn.', amount=1),
    creature('u_apprentice', 'Tide Apprentice', 'U', 1, 1, 2),
    creature('u_glider', 'Mist Glider', 'U', 2, 1, 3, ['Flying']),
    creature('u_scholar', 'Tide Scholar', 'U', 3, 1, 3, effect='draw', text='When this enters your battlefield, draw 1 card.'),
    creature('u_echo', 'Echo Savant', 'U', 4, 2, 4, effect='spell_draw', text='While this is on your battlefield, casting your second noncreature spell in a turn makes you draw 1 card.'),
    spell('u_return', 'Turn Aside', 'U', 2, 'bounce', 'Return a targeted creature to its owner\'s hand. A commander returns to its command zone instead.', 'creature', True),
    spell('u_counter', 'Null Sigil', 'U', 2, 'counter', 'Cancel a targeted pending spell or ability. Its effect does not happen; costs already paid are not refunded.', 'stack', True),
    spell('u_insight', 'Measured Insight', 'U', 2, 'filter', 'Draw three cards, then choose one to discard.', amount=3),
    spell('u_ready', 'Second Wind', 'U', 1, 'ready', 'Ready a creature you control. It can attack or use exhaust abilities again, unless it just entered without Haste.', 'friendly', True),
    creature('b_shambler', 'Crypt Shambler', 'B', 1, 1, 2, effect='death_drain', text='When this dies, deal 1 damage to each opponent and heal yourself for 1.'),
    creature('b_broker', 'Bone Broker', 'B', 2, 2, 2, effect='sacrifice', text='Pay 1 mana, exhaust this creature, and sacrifice another creature you control to draw 1 card. These costs are paid even if the ability is cancelled.'),
    creature('b_collector', 'Soul Collector', 'B', 3, 2, 3, ['Lifesteal'], 'death_ping', 'Whenever another friendly creature dies, deal 1 damage to each opponent.'),
    creature('b_heir', 'Grave Heir', 'B', 4, 3, 4, effect='death_grow', text='Whenever another creature you control dies, this creature permanently gains +1 attack and +1 health.'),
    spell('b_recall', 'Grave Recall', 'B', 2, 'recall', 'Return a creature from your graveyard to hand.', 'grave'),
    spell('b_kill', 'Cruel Exchange', 'B', 3, 'destroy', 'Pay 2 health as a cost. Destroy a creature.', 'creature', True),
    spell('b_bargain', 'Dark Bargain', 'B', 1, 'bargain', 'Pay 2 health as a cost. Draw two cards.', amount=2),
    spell('b_revive', 'Unearth', 'B', 4, 'revive', 'Put a creature with mana cost 3 or less from your graveyard onto your battlefield. Its entry abilities trigger. It must wait to attack unless it has Haste.', 'small_grave'),
    creature('r_duelist', 'Ember Duelist', 'R', 1, 2, 1, ['Haste']),
    creature('r_raider', 'Cinder Raider', 'R', 2, 3, 1, ['Haste']),
    creature('r_weaver', 'Spellweaver', 'R', 3, 2, 2, effect='spell_damage', text='Whenever you cast a noncreature spell, deal 1 damage to each opponent.'),
    creature('r_charger', 'Ash Charger', 'R', 4, 5, 2, ['Haste', 'Trample']),
    spell('r_bolt', 'Magma Bolt', 'R', 2, 'damage', 'Deal 3 damage to a creature or player.', 'any', True, 3),
    spell('r_loot', 'Reckless Study', 'R', 1, 'draw', 'Discard a card as a cost. Draw two cards.', amount=2),
    spell('r_wipe', 'Cinder Rain', 'R', 4, 'wipe', 'Deal 3 damage to every creature.', amount=3),
    spell('r_anthem', 'Uneven Fury', 'R', 3, 'anthem', 'This stays on your battlefield as an engine. All creatures, including enemy creatures, have Haste. Each gains attack equal to its printed attack minus its printed health, with a minimum bonus of 0.'),
    creature('g_seed', 'Grove Tender', 'G', 1, 1, 3, ['Reach']),
    creature('g_sprite', 'Grove Sprite', 'G', 2, 1, 3, effect='mana', text='Exhaust this creature to add 1 ready green mana. This does not increase your permanent mana capacity.'),
    creature('g_sentinel', 'Thorn Sentinel', 'G', 3, 3, 4, ['Reach']),
    creature('g_beast', 'Ancient Beast', 'G', 6, 6, 7, ['Trample', 'Ward']),
    spell('g_ramp', 'Cultivate', 'G', 2, 'ramp', 'Add 1 permanent green mana capacity and 1 ready green mana. Total permanent capacity cannot exceed 10.'),
    spell('g_growth', 'Verdant Surge', 'G', 1, 'buff', 'A creature you control gains +2 attack and +2 health until your next turn.', 'friendly', True, 2),
    spell('g_fight', 'Predator’s Challenge', 'G', 3, 'fight', 'Your ready creature with the highest attack and a targeted enemy creature deal damage to each other equal to their attack. If you have no ready creature, nothing happens.', 'enemy'),
    spell('g_insight', 'Canopy Counsel', 'G', 3, 'draw', 'Draw two cards.', amount=2),
    spell('r_goad', 'Wild Provocation', 'R', 3, 'goad', "All creatures currently on the battlefield must attack if able through the end of their controller's next turn. They must attack a player other than you if possible."),
]
# Neutral utility participates in every identity; the prototype is intentionally >40
# to exercise shared support rather than create five isolated eight-card decks.
CARDS += [
    creature('c_sentry', 'Prism Sentry', 'C', 2, 1, 3, ['Reach']),
    spell('c_break', 'Disrupt Engine', 'C', 3, 'remove_engine', "Put a targeted noncreature engine into its owner's graveyard. This cannot remove equipment.", 'engine', True),
    spell('c_chart', 'Chart a Course', 'C', 3, 'draw', 'Draw two cards.', amount=2),
    spell('c_relay', 'Reclamation Relay', 'C', 5, 'relay', 'This stays on your battlefield as an engine. Whenever a token you control dies, ready all your creatures and add 1 temporary mana that can pay generic costs (numbers), not colored symbols.'),
    spell('c_nest', 'Recruit Foundry', 'C', 4, 'foundry', 'This stays on your battlefield as an engine. When it enters, create a 1/1 Recruit token. Whenever a token you control dies, create another 1/1 Recruit token.'),
]
from .items import NEW_CARDS, GEAR
CARDS += NEW_CARDS
CARD_MAP = {c['id']: c for c in CARDS}
CARD_MAP.update({x['id']: x['card'] for x in GEAR})

COMMANDER_PASSIVES = {
    'wide': 'This commander has +1 attack for each other creature you control.',
    'second_draw': 'While this commander is on your battlefield, casting your second noncreature spell in a turn makes you draw 1 card.',
    'second_damage': 'While this commander is on your battlefield, casting your second noncreature spell in a turn deals 1 damage to each opponent.',
    'death_heal': 'While this commander is on your battlefield, whenever a creature you control dies (including this commander), heal yourself for 1.',
    'lifesteal': 'This commander has Lifesteal: damage it deals also heals you by that amount.',
    'flying': 'This commander has Flying: only creatures with Flying or Reach can block it.',
    'guard': 'This commander has Guard: attacking does not exhaust it.',
    'haste': 'This commander has Haste: it can attack and exhaust for abilities the turn it enters.',
    'ward': 'This commander has Ward: enemies pay 1 extra mana to target it.',
    'trample': 'This commander has Trample: attack damage left after killing its blockers hits the defending player.',
}
COMMANDER_ACTIVES = {
    'protect': 'prevent all damage to a creature you control until the end of this turn.',
    'token': 'create a Recruit token with 1 attack and 1 health.',
    'draw': 'draw 1 card.',
    'bounce': 'return a targeted creature to its owner\'s hand. A commander returns to its command zone instead.',
    'recall': 'return a creature from your graveyard to your hand.',
    'sacrifice': 'sacrifice another creature you control, then draw 2 cards.',
    'damage': 'deal 2 damage to a targeted creature or player.',
    'loot': 'discard 1 card, then draw 2 cards.',
    'ramp': 'add 1 permanent green mana capacity and 1 ready green mana (maximum 10 permanent capacity).',
    'buff': 'give a creature you control +2 attack and +2 health until your next turn.',
}

def commander(id, name, colors, packages):
    return dict(id=id, name=name, colors=list(colors), packages=[
        dict(name=n, passive=p, active=a, description=COMMANDER_PASSIVES[p] +
             ' Instant ability: while you have priority, pay 2 mana and exhaust this commander to ' +
             COMMANDER_ACTIVES[a] + (' Sacrifice is paid immediately, even if the ability is cancelled.' if a == 'sacrifice' else
                                    ' Discard is paid immediately, even if the ability is cancelled.' if a == 'loot' else ''))
        for n,p,a in packages])

COMMANDERS = [
    commander('dawn', 'Aurelia, Dawn Marshal', 'W', [('Shield Line', 'wide', 'protect'), ('Radiant Patrol', 'lifesteal', 'token')]),
    commander('tide', 'Neris, Tide Archivist', 'U', [('Patient Scholar', 'second_draw', 'draw'), ('Mist Captain', 'flying', 'bounce')]),
    commander('crypt', 'Veyra, Crypt Matron', 'B', [('Grave Court', 'death_heal', 'recall'), ('Blood Contract', 'lifesteal', 'sacrifice')]),
    commander('ember', 'Rakka, Ember Duelist', 'R', [('Flash Assault', 'haste', 'damage'), ('Spell Furnace', 'second_damage', 'loot')]),
    commander('grove', 'Orun, Grove Warden', 'G', [('Patient Growth', 'ward', 'ramp'), ('Beast March', 'trample', 'buff')]),
    commander('wu', 'Elya, Formation Weaver', 'WU', [('Sky Formation', 'flying', 'token'), ('Watchful Tide', 'guard', 'protect')]),
    commander('ub', 'Seth, Memory Broker', 'UB', [('Quiet Intrigue', 'second_draw', 'bounce'), ('Grave Circuit', 'death_heal', 'recall')]),
    commander('br', 'Kora, Ash Reclaimer', 'BR', [('Blood Rush', 'haste', 'sacrifice'), ('Ember Return', 'death_heal', 'recall')]),
    commander('rg', 'Tarn, Wildfire Herald', 'RG', [('Stampede', 'haste', 'token'), ('Mountain Heart', 'trample', 'ramp')]),
    commander('gw', 'Iona, Living Bastion', 'GW', [('Root Formation', 'wide', 'buff'), ('Enduring Oath', 'ward', 'protect')]),
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
    pool = [c for c in CARDS if c['color'] in colors and c not in NEW_CARDS]
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
    pack.extend(rng.sample([c['id'] for c in CARDS], 3))
    return pack

def personal_pack(rng, colors, size=5, minimum=2, legal_only=False):
    choices = [c['id'] for c in CARDS if legal(c['id'], colors)]
    pack = rng.sample(choices, minimum)
    remainder = [c for c in (choices if legal_only else [c['id'] for c in CARDS]) if c not in pack]
    needed = size-minimum
    pack += rng.sample(remainder,min(needed,len(remainder)))
    while len(pack) < size:
        pack.append(rng.choice(choices))
    rng.shuffle(pack)
    return pack
