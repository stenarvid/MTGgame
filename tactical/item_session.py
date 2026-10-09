"""Owned gear, reusable gem unlocks, pouch spending and separate campaign drops."""
import copy
from .items import ITEM_MAP, GEM_MAP, CONSUMABLE_MAP, compose, validate_sockets, compatible
from .content import COMMANDER_MAP, CARD_MAP


class ItemSession:
    def loot_designs(self):
        from .progression import EQUIPMENT_MAP
        return [id for id in EQUIPMENT_MAP if id not in ITEM_MAP or ITEM_MAP[id].get('card', {}).get('color', 'C') in self.colors(0)+['C']]
    def socket_fits(self, item, gem, tier):
        proposed = copy.deepcopy(item)
        proposed['gems'] = dict(item.get('gems', {}), **{gem:tier})
        try:
            validate_sockets(proposed, {g:2 for g in GEM_MAP})
            return True
        except ValueError:
            return False
    def item_defaults(self, m):
        m.setdefault('gem_unlocks', {})
        m.setdefault('consumables', [])
        m.setdefault('pouch', [None, None])
        m.setdefault('supply_rewards', [])

    def item_card(self, m, ref):
        item = next((x for x in m.get('items', []) if ref == 'gear:'+x['uid'] and ITEM_MAP.get(x['design'], {}).get('category') == 'equipment'), None)
        return dict(compose(item), id=ref, base_design=item['design']) if item else None

    def card_identity(self, m, ref):
        card = self.item_card(m, ref)
        return card['base_design'] if card else ref

    def add_consumable(self, m, design):
        self.item_defaults(m)
        self.item_serial += 1
        item = dict(uid='supply'+str(self.item_serial), design=design)
        m['consumables'].append(item)
        return item

    def sync_consumables(self):
        if not self.battle: return
        for m in self.members:
            self.item_defaults(m)
            seat = m.get('seat', -1)
            if not 0 <= seat < len(self.battle.players): continue
            spent = set(self.battle.players[seat].get('spent_consumables', []))
            m['consumables'] = [x for x in m['consumables'] if x['uid'] not in spent]
            m['pouch'] = [None if uid in spent else uid for uid in m['pouch']]

    def supply_rewards(self, m):
        self.item_defaults(m)
        # Independent rolls never replace chest contents or the boss choice.
        if self.rng.random() < .20:
            eligible = [id for id, c in CONSUMABLE_MAP.items() if c['color'] in self.colors(m['id'])+['C']]
            item = self.add_consumable(m, self.rng.choice(eligible))
            m['supply_rewards'].append(dict(kind='consumable', name=CONSUMABLE_MAP[item['design']]['name']))
        if self.rng.random() < .10:
            locked = [id for id in GEM_MAP if id not in m['gem_unlocks']]
            if locked:
                gem = self.rng.choice(locked); m['gem_unlocks'][gem] = 0
                m['supply_rewards'].append(dict(kind='gem', name=GEM_MAP[gem]['name']))
            else:
                m['essence'] += 1
                m['supply_rewards'].append(dict(kind='essence', name='1 Essence'))

    def new_item_action(self, i, action, data):
        actions = ('socket_gem', 'preview_socket', 'clear_socket', 'upgrade_gem', 'buy_gem', 'buy_consumable', 'pouch')
        if action not in actions: return False
        from .battle import RuleError
        m = self.members[i]; self.item_defaults(m)
        if self.mode != 'solo' or i != 0 or self.stage not in ('build', 'retry') or m['ready']:
            raise RuleError('Change items between encounters before confirming your build.')
        if action == 'pouch':
            slot = data.get('slot'); uid = data.get('uid')
            if type(slot) is not int or not 0 <= slot < 2: raise RuleError('Choose pouch slot 1 or 2.')
            item = next((x for x in m['consumables'] if x['uid'] == uid), None)
            if uid is not None and not item: raise RuleError('Choose a consumable you own.')
            if item and CONSUMABLE_MAP[item['design']]['color'] not in self.colors(i)+['C']: raise RuleError('Outside your color identity.')
            if uid is not None and uid in m['pouch'] and m['pouch'][slot] != uid: raise RuleError('Each pouch slot needs a separate owned copy.')
            m['pouch'][slot] = uid
        elif action in ('buy_gem', 'buy_consumable'):
            if self.stage != 'build': raise RuleError('Shop purchases are unavailable during a retry.')
            design = data.get('design'); price = 2 if action == 'buy_gem' else 1
            if self.currency < price: raise RuleError(f'Need {price} shop currency.')
            if action == 'buy_gem':
                if design not in GEM_MAP or design in m['gem_unlocks']: raise RuleError('Choose a locked gem family.')
                m['gem_unlocks'][design] = 0
            else:
                if design not in CONSUMABLE_MAP or CONSUMABLE_MAP[design]['color'] not in self.colors(i)+['C']: raise RuleError('Choose a legal consumable.')
                self.add_consumable(m, design)
            self.currency -= price
        elif action == 'upgrade_gem':
            gem = data.get('gem'); tier = m['gem_unlocks'].get(gem, -1)
            if tier not in (0, 1): raise RuleError('Choose an unlocked gem below +2.')
            cost = (3, 6)[tier]
            if m['essence'] < cost: raise RuleError(f'Need {cost} Essence.')
            m['gem_unlocks'][gem] += 1; m['essence'] -= cost
        else:
            item = next((x for x in m['items'] if x['uid'] == data.get('uid')), None)
            if not item or item['design'] not in ITEM_MAP: raise RuleError('Choose a socketable item you own.')
            proposed = copy.deepcopy(item); proposed.setdefault('gems', {})
            if action == 'clear_socket': proposed['gems'].pop(data.get('gem'), None)
            else: proposed['gems'][data.get('gem')] = data.get('tier')
            try: validate_sockets(proposed, m['gem_unlocks'])
            except ValueError as exc: raise RuleError(str(exc)) from exc
            if action != 'preview_socket': item['gems'] = proposed['gems']
            return compose(proposed)
        return True

    def curated_items(self, m):
        act = self.encounter//4
        relic = dict(uid='enemy-relic', design='smith_insignia', tier=min(2, act), gems={})
        if act >= 1: relic['gems'] = {'might': min(1, act-1)}
        color = COMMANDER_MAP[m['commander']]['colors'][0]
        design = {'W':'dawnward_shield', 'U':'spiresteel_blade', 'B':'gravebound_fang', 'R':'embercleave_axe', 'G':'rootbreaker_maul'}[color]
        gear = dict(uid='enemy-gear', design=design, tier=min(2, act), gems={})
        if act >= 1: gear['gems'] = {'binding': 0}
        ref = 'gear:enemy-gear'
        deck = list(m['deck']); deck[-1] = ref
        supply = 'ember_flask' if color == 'R' else 'militia_beacon' if color == 'W' else 'healing_draught'
        return dict(deck=deck, equipment=[relic], gear_cards={ref:compose(gear)},
                    pouch=[dict(uid='enemy-supply', design=supply)])
