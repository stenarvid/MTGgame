"""Explicit RPG item templates and socket composition; never parse rules text."""
import copy


def card(id, name, color, cost, effect, text, kind='response', **fields):
    return dict(id=id, name=name, color=color, cost=cost, effect=effect, text=text,
                kind=kind, pips={} if color == 'C' else {color: 1}, keywords=[],
                type_line={'equipment':'Artifact — Equipment', 'response':'Instant', 'enchantment':'Enchantment', 'creature':'Creature', 'consumable':'Consumable'}.get(kind, kind),
                art_style='sigil', **fields)


NEW_CARDS = [
    card('w_spire_recruit', 'Spire Recruit', 'W', 2, 'equipped_recruit',
         'As long as Spire Recruit is equipped, it gets +1/+1 and has vigilance.', 'creature', attack=2, health=2),
    card('w_stand_together', 'Stand Together', 'W', 2, 'stand_together',
         'Target creature gets +2/+2 until end of turn. You gain 2 life.', target='creature'),
    card('u_artificer_study', "Artificer’s Study", 'U', 3, 'equipment_study',
         'Whenever you cast an Equipment spell, draw a card.', 'enchantment'),
    card('u_disrupt_ritual', 'Disrupt the Ritual', 'U', 2, 'soft_counter',
         'Counter target noncreature spell unless its controller pays {3}.', target='noncreature_spell'),
    card('b_graveward_squire', 'Graveward Squire', 'B', 3, 'equipment_death',
         'Whenever an equipped creature you control dies, you may pay {1}. If you do, draw a card and lose 1 life.',
         'creature', attack=2, health=3),
    card('b_cut_weak', 'Cut Down the Weak', 'B', 2, 'destroy_small',
         'Destroy target creature with mana value 3 or less.', target='small_creature'),
    card('r_forgefire_raider', 'Forgefire Raider', 'R', 3, 'equipment_attack_loot',
         'Whenever Forgefire Raider attacks, if it’s equipped, you may discard a card. If you do, draw a card.',
         'creature', attack=3, health=2),
    card('r_cinder_strike', 'Cinder Strike', 'R', 2, 'damage',
         'Cinder Strike deals 3 damage to target creature.', target='creature', amount=3),
    card('g_wildsteel_tender', 'Wildsteel Tender', 'G', 2, 'equipment_cast_counter',
         'Whenever you cast an Equipment spell, put a +1/+1 counter on target creature you control.',
         'creature', attack=2, health=2),
    card('g_break_armory', 'Break the Armory', 'G', 2, 'destroy_artifact',
         'Destroy target artifact.', target='artifact'),
]

for c in NEW_CARDS:
    if c['kind'] == 'creature':
        c['type_line'] = 'Creature — '+{
            'w_spire_recruit':'Human Soldier', 'b_graveward_squire':'Human Soldier',
            'r_forgefire_raider':'Human Warrior', 'g_wildsteel_tender':'Elf Artificer'}[c['id']]


def gear(id, name, color, cost, attack, health, equip, keyword=None):
    text = f'Equipped creature gets +{attack}/+{health}'
    text += f' and has {keyword.lower()}.' if keyword else '.'
    c = card(id, name, color, cost, 'equipment', text+f'\nEquip {{{equip}}}', 'equipment',
             gear_attack=attack, gear_health=health, equip_cost=equip,
             granted_keywords=[keyword] if keyword else [], attachment=None)
    return dict(id=id, name=name, category='equipment', effect='equipment', text=c['text'], card=c, art_style='sigil')


GEAR = [gear('spiresteel_blade', 'Spiresteel Blade', 'C', 1, 1, 0, 1),
        gear('dawnward_shield', 'Dawnward Shield', 'W', 2, 0, 2, 2, 'Vigilance'),
        gear('embercleave_axe', 'Embercleave Axe', 'R', 2, 2, 0, 2),
        gear('gravebound_fang', 'Gravebound Fang', 'B', 2, 1, 0, 2, 'Lifelink'),
        gear('rootbreaker_maul', 'Rootbreaker Maul', 'G', 3, 2, 2, 3, 'Trample')]
NEW_RELICS = [dict(id=id, name=name, category='relic', effect='socket_relic',
                   condition=condition, attack=0, health=1, text=text, art_style='sigil')
              for id, name, condition, text in [
                  ('smith_insignia', "Smith’s Insignia", 'equipped', 'Equipped creatures you control get +0/+1.'),
                  ('muster_standard', 'Muster Standard', 'nontoken', 'Nontoken creatures you control get +0/+1.'),
                  ('sovereign_crest', "Sovereign’s Crest", 'legendary', 'Legendary creatures you control get +0/+1.')]]
ITEM_MAP = {x['id']: x for x in GEAR+NEW_RELICS}
GEM_FAMILIES = [dict(id=id, name=name, role=role) for id, name, role in [
    ('might', 'Might', 'bonus'), ('brood', 'Brood', 'condition'), ('vitality', 'Vitality', 'trigger'),
    ('binding', 'Binding', 'trigger'), ('guardian', 'Guardian', 'bonus'), ('bastion', 'Bastion', 'bonus')]]
GEM_MAP = {x['id']: x for x in GEM_FAMILIES}
CONSUMABLES = [
    card('healing_draught', 'Healing Draught', 'C', 1, 'heal', '{1}, Consume Healing Draught: You gain 3 life.', 'consumable', amount=3),
    card('ember_flask', 'Ember Flask', 'R', 1, 'damage', '{R}, Consume Ember Flask: It deals 2 damage to target creature.', 'consumable', amount=2, target='creature'),
    card('mistveil_vial', 'Mistveil Vial', 'U', 1, 'hexproof', '{U}, Consume Mistveil Vial: Target creature you control gains hexproof until end of turn.', 'consumable', target='friendly'),
    card('barkskin_tonic', 'Barkskin Tonic', 'G', 1, 'barkskin', '{G}, Consume Barkskin Tonic: Target creature gets +1/+2 until end of turn.', 'consumable', target='creature'),
    card('militia_beacon', 'Militia Beacon', 'W', 2, 'soldier', '{1}{W}, Consume Militia Beacon: Create a 1/1 white Soldier creature token. Activate only as a sorcery.', 'consumable', sorcery=True),
]
CONSUMABLE_MAP = {x['id']: x for x in CONSUMABLES}
EXTRA_TARGETS = ('artifact', 'small_creature', 'noncreature_spell')


def roles(item):
    return (['bonus', 'trigger', 'condition'] if ITEM_MAP[item['design']]['category'] == 'equipment'
            else ['bonus', 'condition', 'trigger'])[:item['tier']+1]


def compatible(design, gem):
    spec = ITEM_MAP.get(design)
    if not spec:
        return False
    if gem == 'might':
        return spec['category'] == 'equipment' or design == 'smith_insignia'
    return gem in (('binding', 'guardian', 'bastion') if spec['category'] == 'equipment' else ('brood', 'vitality'))


def occupied(item, gem, tier):
    role = GEM_MAP[gem]['role']
    priority = ['condition', 'bonus', 'trigger'] if gem in ('might', 'guardian', 'bastion', 'binding') else ['bonus', 'condition', 'trigger']
    selected = [role] + [r for r in priority if r != role][:tier]
    if not set(selected) <= set(roles(item)):
        raise ValueError('This gem needs additional unlocked sockets.')
    return selected


def validate_sockets(item, unlocks):
    used = set()
    for gem, tier in item.get('gems', {}).items():
        if gem not in GEM_MAP or not compatible(item['design'], gem):
            raise ValueError('This gem is incompatible with this item.')
        if type(tier) is not int or not 0 <= tier <= unlocks.get(gem, -1):
            raise ValueError('Unlock this gem tier first.')
        slots = set(occupied(item, gem, tier))
        if used & slots:
            raise ValueError('Another gem already occupies a required socket.')
        used |= slots
    return sorted(used)


def compose(item):
    spec = ITEM_MAP[item['design']]
    gems = item.get('gems', {})
    out = copy.deepcopy(spec.get('card', spec))
    out.update(design=item['design'], item_uid=item.get('uid'), tier=item['tier'], gems=copy.deepcopy(gems),
               sockets=roles(item), occupied={g: occupied(item, g, t) for g, t in gems.items()})
    attack, health = (out.get('gear_attack', 0), out.get('gear_health', 0)) if spec['category'] == 'equipment' else (0, 1)
    condition = spec.get('condition')
    if 'might' in gems:
        attack, health = gems['might']+1, 0
    if 'brood' in gems:
        condition = 'token'
        if gems['brood']:
            attack, health = 0, gems['brood']+1
    if spec['category'] == 'relic':
        if 'vitality' in gems and gems['vitality']:
            attack, health = 0, gems['vitality']+1
        out.update(attack=attack, health=health, condition=condition, triggered='vitality' in gems)
        subject = {'equipped': 'equipped creature', 'token': 'creature token', 'nontoken': 'nontoken creature', 'legendary': 'legendary creature'}[condition]
        out['text'] = (f'Whenever a{ "n" if condition == "equipped" else ""} {subject} you control attacks, it gets +{attack}/+{health} until end of turn and you gain 1 life.'
                       if out['triggered'] else f'{subject.capitalize()}s you control get +{attack}/+{health}.')
    else:
        out.update(gear_attack=attack, gear_health=health)
        lines = []
        if 'guardian' in gems or 'bastion' in gems:
            out['gear_attack'] = out['gear_health'] = 0
            if 'guardian' in gems:
                out['bearer_ward'] = gems['guardian']+2
                lines.append(f'Equipped creature has ward {{{out["bearer_ward"]}}}.')
            else:
                out['ward'] = gems['bastion']+2
                lines.append('Ward {'+str(out['ward'])+'}')
        else:
            lines.append(f'Equipped creature gets +{attack}/+{health}.')
        if 'binding' in gems:
            out['auto_attach'] = True
            if gems['binding'] == 0:
                out['cost'] += 1
            if gems['binding'] == 2:
                out['granted_keywords'].append('Haste')
            lines.append('When this Equipment enters, attach it to target creature you control.')
        if out['granted_keywords']:
            lines.append('Equipped creature has '+ ' and '.join(k.lower() for k in out['granted_keywords'])+'.')
        lines.append(f'Equip {{{out["equip_cost"]}}}')
        out['text'] = '\n'.join(lines)
    out.update(category=spec['category'], art_style='sigil')
    return out


def item_view(item):
    out = compose(item)
    out.update(uid=item.get('uid', ''), name=out['name']+(f' +{item["tier"]}' if item['tier'] else ''))
    return out
