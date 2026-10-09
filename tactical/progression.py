"""Campaign equipment and curated design upgrades, independent of multiplayer relics."""
import copy
from .content import RELICS, CARD_MAP
from .items import ITEM_MAP, item_view

MAX_TIER = 2
SLOTS = 3
UPGRADE_COSTS = (3, 6)
EQUIPMENT = [dict(r, art='relic_'+r['id']) for r in RELICS] + [
    dict(id='panharmonicon', name='Panharmonicon', effect='entry', art='panharmonicon',
         text='Friendly creature and engine entry abilities trigger one additional time.')]
EQUIPMENT += list(ITEM_MAP.values())
EQUIPMENT_MAP = {item['id']: item for item in EQUIPMENT}


def item_description(item_id, tier=0):
    n = tier + 1
    return {
        'reserves': f'End your turn with at least 2 unspent mana: heal {n}.',
        'ashes': f'Your first friendly death each turn heals you {n}.',
        'chorus': f'Start your turn with at least four creatures: gain {n} temporary mana.',
        'edge': f'Your creatures get +{n} attack while you have 10 health or less.',
        'lens': f'After your third noncreature spell in a turn, draw {n} cards.',
        'roots': f'Whenever ramp adds capacity, heal {n}.',
        'panharmonicon': f'Friendly creature and engine entry abilities trigger {n} additional time(s). Extra triggers from equipped copies add together.'
    }[item_id]


def equipment_view(item):
    if item['design'] in ITEM_MAP:
        return item_view(item)
    spec = EQUIPMENT_MAP[item['design']]
    return dict(item, name=spec['name']+(f" +{item['tier']}" if item['tier'] else ''),
                text=item_description(item['design'], item['tier']), art=spec['art'])


def upgraded_card(design, tier=0):
    """Every upgrade has an explicit preview; identity pips and targets stay intact."""
    c = copy.deepcopy(CARD_MAP[design])
    if c.get('art_style') == 'sigil':
        # New designs retain their approved printed rules; item tiers use sockets.
        return dict(c, upgrade=0)
    c['upgrade'] = tier
    if not tier:
        return c
    c['name'] += f' +{tier}'
    detail = ''
    if c['kind'] == 'creature':
        c['attack'] += tier
        c['health'] += tier
        detail = f'+{tier}/+{tier} printed stats.'
        if c['effect'] == 'draw':
            c['amount'] = 1 + tier
            c['text'] = f'When this enters your battlefield, draw {1+tier} cards.'
    elif c['effect'] in ('damage', 'wipe', 'draw', 'filter', 'bargain', 'buff', 'team_buff', 'tokens'):
        c['amount'] += tier
        n = c['amount']
        c['text'] = {
            'damage': f'Deal {n} damage to a creature or player.',
            'wipe': f'Deal {n} damage to every creature.',
            'draw': ('Discard a card as a cost. ' if design == 'r_loot' else '') + f'Draw {n} cards.',
            'filter': f'Draw {n} cards, then choose one to discard.',
            'bargain': f'Pay 2 health as a cost. Draw {n} cards.',
            'buff': f'A creature you control gains +{n} attack and +{n} health until your next turn.',
            'team_buff': f'Each creature you currently control gains +{n} attack and +{n} health until your next turn.',
            'tokens': f'Create {n} 1/1 Recruits.'
        }[c['effect']]
    elif c['effect'] == 'ramp':
        c['amount'] = 1 + tier
        c['text'] = f'Add {1+tier} permanent green mana capacity and the same amount of ready green mana. Stop at 10 total permanent capacity.'
    elif c['effect'] == 'protect':
        c['upgrade_health'] = tier
        detail = f'Also grant +0/+{tier} until your next turn.'
    elif c['effect'] in ('foundry', 'relay', 'anthem'):
        c['engine_strength'] = 1 + tier
        c['text'] = ''
        detail = {'foundry': f'This stays on your battlefield as an engine. When it enters, or whenever a token you control dies, create {1+tier} Recruit tokens with 1 attack and 1 health each.',
                  'relay': f'Whenever a friendly token dies, ready your creatures and gain {1+tier} temporary mana.',
                  'anthem': CARD_MAP[design]['text'] + f' Your creatures also gain +{tier} attack while this engine remains.'}[c['effect']]
    else:
        floor = max(1, sum(c['pips'].values()))
        c['cost'] = max(floor, c['cost'] - tier)
        detail = f"Mana cost decreases to {c['cost']} without changing colored pips."
        if CARD_MAP[design]['cost']-tier < floor:
            c['upgrade_draw'] = 1
            detail += ' Draw one card when this spell resolves successfully.'
    c['text'] = (c['text']+' '+detail).strip()
    return c


def upgrade_preview(design, tier):
    return dict(design=design, tier=tier, cost=UPGRADE_COSTS[tier] if tier < MAX_TIER else None,
                current=upgraded_card(design,tier),
                next=upgraded_card(design,tier+1) if tier < MAX_TIER else None)
