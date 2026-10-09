"""Authoritative multiplayer battle rules, shared by browser players and AI."""
import copy
import random
import time
from .content import CARD_MAP, COMMANDER_MAP, RELIC_MAP, KEYWORDS
from .progression import upgraded_card, EQUIPMENT_MAP, equipment_view


class RuleError(ValueError):
    pass


from .battle_items import ItemBattle
from .items import ITEM_MAP, CONSUMABLE_MAP, EXTRA_TARGETS


from .priority import PriorityRules


class Battle(PriorityRules, ItemBattle):
    def __init__(self, builds, seed=0, starting=0, encounter=None):
        self.rng = random.Random(seed)
        self.serial = 0
        self.players = []
        self.gear_cards = {i:copy.deepcopy(build.get('gear_cards', {})) for i,build in enumerate(builds)}
        self.card_upgrades = {i:copy.deepcopy(build.get("card_upgrades",{})) for i,build in enumerate(builds)}
        self.stack = []
        self.log = []
        self.visual_events = []
        self.visual_serial = 0
        self.started_at = time.time()
        self.elapsed = 0
        self.active = starting
        self.priority = starting
        self.passes = 0
        self.phase = 'opening'
        self.round = 1
        self.attacks = []
        self.blocks = {}
        self.blocked = []
        self.defenders = []
        self.finished = False
        self.loop = None
        self.choice = None
        self.survivor = None
        self.encounter = encounter or {}
        for i, build in enumerate(builds):
            p = dict(id=i, name=build['name'], commander=build['commander'], package=build['package'],
                     relic=build['relic'], equipment=copy.deepcopy(build.get('equipment')), colors=COMMANDER_MAP[build['commander']]['colors'],
                     hp=25, alive=True, turns=0, completed_turn=False, mulligan=False, mulligan_count=0, bottom_remaining=0, kept=False, opening_color=None,
                     capacity={}, mana={}, temporary=0, fatigue=0, tax=0, commander_zone='command',
                     board=[], hand=[], deck=[], grave=[], exile=[], engines=[], gear=[],
                     pouch=copy.deepcopy(build.get('pouch', [])), spent_consumables=[], spells=0,
                     ashes_used=False, points=0, eliminator=None, eliminated_at=None, eliminated_elapsed=None, active_used=False)
            p['deck'] = [self.instance(c, i) for c in build['deck']]
            self.rng.shuffle(p['deck'])
            self.players.append(p)
            self.draw(i, 5)
        if 'head_start' in self.encounter.get('modifiers', []):
            for p in self.players[1:]:
                self.gain_capacity(p['id'], p['colors'][0])
        self.note('Keep your opening hand. Choose mana at the start of your main phase.')

    def instance(self, card_id, owner, commander=False):
        self.serial += 1
        if commander:
            spec = COMMANDER_MAP[card_id]
            c = dict(id='commander', name=spec['name'], color=spec['colors'][0], cost=4,
                     pips={color: 1 for color in spec['colors']}, attack=3, health=5,
                     kind='creature', keywords=[], effect='', text=self.package(owner)['description'], commander=True)
        else:
            c = copy.deepcopy(self.gear_cards.get(owner, {}).get(card_id)) or upgraded_card(card_id,self.card_upgrades.get(owner,{}).get(card_id,0))
        c.update(uid=str(self.serial), owner=owner, origin_owner=owner, printed_attack=c.get('attack',0), printed_health=c.get('health',0), damage=0, tapped=False, sick=True,
                 bonus_attack=0, bonus_health=0, protected=False, token=False, goad=None)
        return c

    def note(self, message):
        self.log.append(message)

    def living(self):
        return [p['id'] for p in self.players if p['alive']]

    def next_player(self, i):
        for offset in range(1, len(self.players)+1):
            j = (i+offset) % len(self.players)
            if self.players[j]['alive']:
                return j
        return i

    def package(self, i):
        p = self.players[i]
        return COMMANDER_MAP[p['commander']]['packages'][p['package']]

    def commander_present(self, i):
        return any(c.get('commander') for c in self.players[i]['board'])

    def protected_opening(self):
        return any(p['alive'] and not p['completed_turn'] for p in self.players)

    def find(self, uid):
        for p in self.players:
            for zone in ('board', 'hand', 'grave', 'engines', 'gear', 'exile'):
                for c in p[zone]:
                    if c['uid'] == str(uid):
                        return p, zone, c
        return None, None, None

    def keywords(self, c):
        result = set(c['keywords']) | self.item_keywords(c)
        owner = c['owner']
        if c.get('commander'):
            passive = self.package(owner)['passive']
            result.update({'haste':'Haste', 'guard':'Guard', 'flying':'Flying',
                       'ward':'Ward', 'trample':'Trample', 'lifesteal':'Lifesteal'}.get(passive, '').split())
        if any(e['effect'] == 'anthem' for p in self.players for e in p['engines']):
            result.add('Haste')
        if c['kind'] == 'creature' and self.timing_override(owner, 'creature_cast'):
            result.add('Flash')
        if c.get('goad'):
            result.add('Goad')
        return result

    def effect_strength(self, i, effect):
        p = self.players[i]
        if p.get('equipment') is not None:
            return sum(item.get('tier',0)+1 for item in p['equipment']
                       if item['design'] in EQUIPMENT_MAP and EQUIPMENT_MAP[item['design']]['effect'] == effect)
        return int(RELIC_MAP.get(p.get('relic'),{}).get('effect') == effect)

    def entry_triggers(self, i, card):
        if i == 0 and 'silent_entry' in self.encounter.get('modifiers', []):
            return
        repeats = 1 + self.effect_strength(i,'entry')
        effect = card['effect']
        if effect not in ('draw','foundry'):
            return
        for _ in range(repeats):
            self.push(i,'draw' if effect == 'draw' else 'tokens',
                      amount=(card.get('amount',1) or 1) if effect == 'draw' else card.get('engine_strength',1),
                      name=card['name']+' entry',source=card)

    def stats(self, c):
        p = self.players[c['owner']]
        item_attack, item_health = self.item_stats(c)
        attack = c.get('attack', 0) + c['bonus_attack'] + item_attack
        health = c.get('health', 0) + c['bonus_health'] + item_health
        attack += sum(1 for x in p['board'] if x['effect'] == 'formation' and x is not c)
        if p['hp'] <= 10:
            attack += self.effect_strength(p['id'],'edge')
        if c.get('commander') and self.package(p['id'])['passive'] == 'wide':
            attack += max(0, len(p['board'])-1)
        for other in self.players:
            for e in other['engines']:
                if e['effect'] == 'anthem':
                    attack += max(0, c['printed_attack']-c['printed_health'])
                    if other['id'] == c['owner']:
                        attack += e.get('engine_strength',1)-1
        if c['owner'] == 0 and 'weak_army' in self.encounter.get('modifiers', []):
            attack -= 1
        return max(0, attack), health

    def draw(self, i, count):
        p = self.players[i]
        for _ in range(count):
            if p['deck']:
                p['hand'].append(p['deck'].pop())
            else:
                p['fatigue'] += 1
                self.damage_player(i, p['fatigue'], None)
                self.note(f"{p['name']} takes {p['fatigue']} fatigue damage.")

    def damage_player(self, i, amount, source):
        p = self.players[i]
        if not p['alive']:
            return 0
        dealt = max(0, amount)
        if self.protected_opening():
            dealt = min(dealt, max(0, p['hp']-1))
        p['hp'] -= dealt
        if p['hp'] <= 0:
            p['eliminator'] = source
        return dealt

    def damage_creature(self, c, amount):
        dealt = 0 if c['protected'] else max(0, amount)
        c['damage'] += dealt
        return dealt

    def pay(self, i, cost, pips=None, commit=True):
        p = self.players[i]
        mana = p['mana'].copy()
        temp = p['temporary']
        pips = pips or {}
        for color, n in pips.items():
            if mana.get(color, 0) < n:
                return False
            mana[color] -= n
        generic = max(0, cost-sum(pips.values()))
        used = min(temp, generic)
        temp -= used
        generic -= used
        for color in sorted(mana, key=lambda k: -mana[k]):
            used = min(mana[color], generic)
            mana[color] -= used
            generic -= used
        if generic:
            return False
        if commit:
            p['mana'], p['temporary'] = mana, temp
        return True

    def gain_capacity(self, i, color, refresh=True):
        p = self.players[i]
        if sum(p['capacity'].values()) >= 10:
            return False
        p['capacity'][color] = p['capacity'].get(color, 0)+1
        if refresh:
            p['mana'][color] = p['mana'].get(color, 0)+1
        return True

    def targets(self, i, target_kind):
        result = self.item_targets(i, target_kind)
        for p in self.players:
            if not p['alive']:
                continue
            if target_kind == 'any':
                result.append(f"p:{p['id']}")
            if target_kind in ('grave', 'small_grave') and p['id'] == i:
                result += [c['uid'] for c in p['grave'] if c['kind'] == 'creature' and
                           (target_kind == 'grave' or c['cost'] <= 3)]
            for c in p['board']:
                if not self.item_target_allowed(i, c):
                    continue
                if target_kind in ('creature','any') or (target_kind == 'friendly' and p['id'] == i) or (target_kind == 'enemy' and p['id'] != i) or (target_kind == 'large' and self.stats(c)[0] >= 3):
                    result.append(c['uid'])
            if target_kind == 'engine':
                result += [c['uid'] for c in p['engines']]
        if target_kind == 'stack':
            result = [s['uid'] for s in self.stack]
        return result

    def cost_for(self, i, card, target=None):
        cost = card['cost'] + (self.players[i]['tax'] if card.get('commander') else 0)
        _, zone, c = self.find(target)
        if c and zone == 'board' and c['owner'] != i and ('Ward' in c['keywords'] or (c.get('commander') and self.package(c['owner'])['passive'] == 'ward')):
            cost += 1
        return cost

    def castable(self, i, card, target=None):
        if i == 0 and 'creatures_only' in self.encounter.get('modifiers', []) and card['kind'] != 'creature':
            return False
        if self.finished or i != self.priority or not self.players[i]['alive'] or self.phase in ('opening','grow','blocks'):
            return False
        if not self.instant_card(i, card) and (i != self.active or self.phase not in ('main','main2') or self.stack):
            return False
        if card.get('target') and target not in self.targets(i, card['target']):
            return False
        if card['effect'] in ('destroy','bargain') and self.players[i]['hp'] <= 2:
            return False
        if card['id'] == 'r_loot' and len(self.players[i]['hand']) < 2:
            return False
        return self.pay(i, self.cost_for(i, card, target), card['pips'], False)

    def presentation_state(self):
        # Public battlefield only; never include hands or deck order in presentation events.
        return dict(cards={c['uid']:dict(uid=c['uid'],owner=p['id'],card_id=c['id'],
                         attack=self.stats(c)[0],health=self.stats(c)[1],damage=c['damage'],
                         protected=c['protected'],commander=bool(c.get('commander')))
                         for p in self.players for c in p['board']},
                    health={str(p['id']):p['hp'] for p in self.players})

    def presentation_changes(self, before):
        after=self.presentation_state()
        removed=[uid for uid,c in before['cards'].items() if uid not in after['cards'] or
                 after['cards'][uid]['health'] <= after['cards'][uid]['damage']]
        return dict(before=before,after=after,departures=removed,
                    entries=[uid for uid in after['cards'] if uid not in before['cards']])

    def visual_event(self, stage, action, outcome='resolved'):
        self.visual_serial = getattr(self,'visual_serial',0)+1
        card = action.get('card') or {}
        source = self.find(action.get('source_uid'))[2] or {}
        relic_uid = action.get('relic_uid')
        relic_id = action.get('card_id', '') or ''
        if not relic_uid and relic_id.startswith('relic_'):
            design = relic_id[len('relic_'):]
            item = next((item for item in self.players[action['owner']].get('equipment') or []
                         if item['design'] == design), None)
            relic_uid = item['uid'] if item else f"legacy:{action['owner']}:{design}"
        event = dict(seq=self.visual_serial,stage=stage,outcome=outcome,
                     action_uid=action.get('uid'),card_id=card.get('id') or action.get('card_id') or source.get('id'),
                     source_uid=action.get('source_uid') or card.get('uid'),owner=action['owner'],
                     effect=action['effect'],kind=action.get('kind','ability'),name=action['name'],
                     color=card.get('color') or action.get('color') or source.get('color') or self.players[action['owner']]['colors'][0],
                     target=action.get('target'),amount=action.get('amount',0),
                     relic_uid=relic_uid,
                     commander=bool(card.get('commander') or source.get('commander')),
                     public_card={k:copy.deepcopy(card[k]) for k in ('uid','id','name','color','kind','cost','pips','attack','health','keywords','text','commander','art_style','base_design','design','gems','tier','type_line') if k in card},
                     commander_id=self.players[action['owner']]['commander'],
                     affected_uids=[c['uid'] for p in self.players for c in p['board']] if action['effect'] in ('wipe','goad','anthem') else [])
        self.visual_events = (getattr(self,'visual_events',[])+[event])[-128:]
        return event

    def push(self, i, effect, target=None, amount=0, card=None, kind='trigger', name=None, source=None):
        self.serial += 1
        s = dict(uid=f's{self.serial}', owner=i, effect=effect, target=target, amount=amount,
                 card=card, kind=kind, name=name or (card['name'] if card else effect),
                 lifesteal=bool(source and 'Lifesteal' in self.keywords(source)))
        s.update(card_id=(card or source or {}).get('id'),color=(card or source or {}).get('color'),source_uid=(source or card or {}).get('uid'))
        if not card and not source:
            item = next((item for item in self.players[i].get('equipment') or []
                         if equipment_view(item)['name'] == s['name']), None)
            if item:
                s['relic_uid'] = item['uid']
            relic = next((r for r in RELIC_MAP.values() if r['name'] == s['name']),None)
            if relic:
                s.update(card_id='relic_'+relic['id'],color='C')
                owned = next((item for item in self.players[i].get('equipment') or [] if item['design'] == relic['id']), None)
                if owned:
                    s['relic_uid'] = owned['uid']
        if source:
            s['source_category'] = 'equipment' if source['kind'] == 'equipment' else 'creature'
            s['source_order'] = source.get('attachment_order', 0) if source['kind'] == 'equipment' else source.get('entry_order', 10**9)
        self.stack.append(s)
        visual=self.visual_event('cast',s)
        s.update(public_card=visual['public_card'],commander=visual['commander'],commander_id=visual['commander_id'])
        self.passes = 0
        self.note(f"{self.players[i]['name']}: {s['name']} → pending")

    def triggers_cast(self, i, card):
        self.equipment_cast_triggers(i, card)
        if card['kind'] == 'creature':
            return
        p = self.players[i]
        p['spells'] += 1
        for c in list(p['board']):
            if c['effect'] == 'spell_damage':
                self.push(i, 'all_damage', amount=1, name=c['name'],source=c)
            if c['effect'] == 'spell_draw' and p['spells'] == 2:
                self.push(i, 'draw', amount=1, name=c['name'],source=c)
        if self.commander_present(i):
            passive = self.package(i)['passive']
            if p['spells'] == 2 and passive in ('second_draw','second_damage'):
                self.push(i, 'draw' if passive == 'second_draw' else 'all_damage', amount=1, name='Commander trigger',source=next(c for c in p['board'] if c.get('commander')))
        if p['spells'] == 3 and self.effect_strength(i,'lens'):
            self.push(i, 'draw', amount=self.effect_strength(i,'lens'), name='Focused Lens')

    def move_out(self, p, c, destination='grave'):
        self.detach(c)
        for zone in ('board','engines','gear'):
            if c in p[zone]:
                p[zone].remove(c)
        if c.get('commander'):
            p['commander_zone'] = 'command'
        elif not c.get('token'):
            c['tapped'], c['sick'] = False, True
            c['damage'] = c['bonus_attack'] = c['bonus_health'] = 0
            c['buffs'] = [x for x in c.get('buffs',[]) if x.get('duration') != 'Until your next turn']
            c['protected'], c['goad'] = False, None
            c['end_buffs'] = []
            c['owner'] = c.get('origin_owner', p['id'])
            self.players[c['owner']][destination].append(c)

    def death(self, p, c, watchers=None):
        watchers = list(p['board']) if watchers is None else watchers
        self.item_death_triggers(p, c, watchers)
        self.note(f"{c['name']} dies.")
        self.move_out(p, c)
        if c['effect'] == 'death_drain':
            self.push(p['id'], 'drain_all', amount=1, name=c['name'],source=c)
        for other in watchers:
            if other is c:
                continue
            if other['effect'] == 'death_grow':
                self.push(p['id'], 'permanent_buff', other['uid'], 1, name=other['name'],source=other)
            if other['effect'] == 'death_ping':
                self.push(p['id'], 'all_damage', amount=1, name=other['name'],source=other)
        if c.get('token'):
            for engine in p['engines']:
                if engine['effect'] == 'foundry':
                    self.push(p['id'], 'tokens', amount=engine.get('engine_strength',1), name=engine['name'],source=engine)
                if engine['effect'] == 'relay':
                    self.push(p['id'], 'relay_ready', amount=engine.get('engine_strength',1), name=engine['name'],source=engine)
        if any(w.get('commander') for w in watchers) and self.package(p['id'])['passive'] == 'death_heal':
            self.push(p['id'], 'heal', amount=1, name='Commander death trigger',source=next(w for w in watchers if w.get('commander')))
        if self.effect_strength(p['id'],'ashes') and not p['ashes_used']:
            p['ashes_used'] = True
            self.push(p['id'], 'heal', amount=self.effect_strength(p['id'],'ashes'), name='Ash Ledger')

    def check(self):
        if self.finished:
            return
        # Determine simultaneous victims before removing any controller or anthem.
        while True:
            victims = [p for p in self.players if p['alive'] and p['hp'] <= 0 and not self.protected_opening()]
            for p in victims:
                killer = p['eliminator']
                if killer is not None and killer != p['id']:
                    self.players[killer]['points'] += 1
                p['alive'] = False
                p['eliminated_at'] = time.time()
                p['eliminated_elapsed'] = self.elapsed
                self.note(f"{p['name']} is eliminated.")
            for p in victims:
                for zone in ('board','hand','deck','grave','exile','engines','gear'):
                    p[zone].clear()
                self.stack = [s for s in self.stack if s['owner'] != p['id']]
                self.attacks = [a for a in self.attacks if a['defender'] != p['id']]
                self.defenders = [i for i in self.defenders if i != p['id']]
            dead = [(p,c) for p in self.players if p['alive'] for c in p['board']
                    if self.stats(c)[1] <= c['damage']]
            watchers = {p['id']:list(p['board']) for p in self.players}
            for p,c in dead:
                self.death(p,c,watchers[p['id']])
            if not victims and not dead:
                break
        living = self.living()
        if self.choice and not self.players[self.choice['owner']]['alive']:
            self.choice = None
        if self.loop and not self.players[self.loop['owner']]['alive']:
            self.loop = None
        if len(living) <= 1:
            self.finished = True
            self.survivor = living[0] if living else None
            if living:
                self.players[living[0]]['points'] += 1
            self.phase = 'finished'
            self.note('Battle finished. Rewards and voting happen between battles.')
            self.loop = None
        elif not self.players[self.active]['alive'] and not self.stack:
            self.start_turn(self.next_player(self.active))
        elif not self.players[self.priority]['alive']:
            self.priority = self.next_player(self.priority)
            self.passes = 0
        if not self.finished and self.phase == 'blocks':
            self.defenders = [i for i in self.defenders if self.players[i]['alive']]
            if not self.defenders:
                self.phase = 'damage_response'
                self.priority = self.active
            else:
                self.priority = self.defenders[0]

    def resolve(self, s):
        i, effect, amount = s['owner'], s['effect'], s['amount']
        p = self.players[i]
        target = s['target']
        owner, zone, c = self.find(target)
        card = s['card']
        dealt = 0
        required = s.get('target_kind') or (card.get('target') if card else None)
        source = self.find(s.get('source_uid'))[2]
        invalid_source = s.get('requires_source') and (not source or self.find(s.get('source_uid'))[1] != 'board')
        invalid_target = required and target not in self.targets(i, required)
        before=self.presentation_state()
        visual=self.visual_event('resolve',s,'fizzle' if invalid_source or invalid_target else 'resolved')
        if s.get('requires_source') and (not source or self.find(s.get('source_uid'))[1] != 'board'):
            self.note(f"{s['name']} requires its source and has no effect.")
        elif required and target not in self.targets(i, required):
            self.note(f"{s['name']} has no legal target and fizzles.")
        elif self.item_resolve(s, c, zone, invalid_source or invalid_target):
            pass
        elif s['kind'] == 'creature':
            self.mark_entry(card)
            p['board'].append(card)
            if card.get('commander'):
                p['commander_zone'] = 'board'
            self.entry_triggers(i,card)
        elif effect == 'counter':
            pending = next((x for x in self.stack if x['uid'] == target), None)
            if pending:
                self.stack.remove(pending)
                self.visual_event('resolve',pending,'countered')
                self.finish_card(pending)
        elif effect == 'damage':
            if str(target).startswith('p:'):
                dealt = self.damage_player(int(target[2:]), amount, i)
            elif c and zone == 'board':
                dealt = self.damage_creature(c, amount)
        elif effect in ('all_damage','drain_all'):
            for other in self.players:
                if other['id'] != i:
                    dealt += self.damage_player(other['id'], amount, i)
            if effect == 'drain_all':
                p['hp'] += amount
        elif effect in ('draw','bargain','loot'):
            self.draw(i, amount or 1)
        elif effect == 'filter':
            self.draw(i,amount)
            if p['hand']:
                self.choice = dict(owner=i,kind='discard')
        elif effect == 'mana':
            p['temporary'] += amount
        elif effect == 'heal':
            p['hp'] += amount
        elif effect == 'tokens':
            for _ in range(amount):
                t = self.instance('w_recruit', i)
                t.update(name='Recruit', attack=1, health=1, printed_attack=1, printed_health=1, token=True, upgrade=0, text='A summoned 1/1 Recruit.')
                self.mark_entry(t)
                p['board'].append(t)
        elif effect == 'wipe':
            for other in self.players:
                for unit in other['board']:
                    self.damage_creature(unit, amount)
        elif effect in ('anthem','relay','foundry'):
            self.mark_entry(card)
            p['engines'].append(card)
            self.entry_triggers(i,card)
        elif effect == 'relay_ready':
            for unit in p['board']:
                unit['tapped'] = False
            p['temporary'] += amount or 1
        elif effect == 'goad':
            for other in self.players:
                for unit in other['board']:
                    unit['goad'] = dict(by=i, until=other['turns']+1)
        elif effect == 'ramp':
            for _ in range(amount or 1):
                if self.gain_capacity(i,'G'):
                    heal = self.effect_strength(i,'roots')
                    if heal:
                        self.push(i, 'heal', f'p:{i}', heal, name='Root Pact')
        elif effect == 'team_buff':
            for unit in p['board']:
                unit['bonus_attack'] += amount
                unit['bonus_health'] += amount
                self.record_buff(unit,s,'United strength',f'+{amount}/+{amount}', 'Until your next turn')
        elif c:
            if effect == 'destroy' and zone == 'board':
                self.death(owner,c)
            elif effect == 'exile' and zone == 'board':
                self.move_out(owner,c,'exile')
            elif effect == 'bounce' and zone == 'board':
                self.move_out(owner,c,'hand')
            elif effect == 'remove_engine' and zone == 'engines':
                self.move_out(owner,c)
            elif effect == 'protect' and zone == 'board':
                c['protected'] = True
                if card and card.get('upgrade_health'):
                    c['bonus_health'] += card['upgrade_health']
                    self.record_buff(c,s,'Fortified shield',f"+0/+{card['upgrade_health']}",'Until your next turn')
                self.record_buff(c,s,'Protection','Prevent damage', 'End of this turn')
            elif effect in ('buff','permanent_buff') and zone == 'board':
                if effect == 'permanent_buff':
                    c['attack'] += amount
                    c['health'] += amount
                else:
                    c['bonus_attack'] += amount
                    c['bonus_health'] += amount
                self.record_buff(c,s,'Strength',f'+{amount}/+{amount}', 'Permanent' if effect == 'permanent_buff' else 'Until your next turn')
            elif effect == 'ready' and zone == 'board':
                c['tapped'] = False
            elif effect in ('recall','revive') and zone == 'grave':
                owner['grave'].remove(c)
                owner['board' if effect == 'revive' else 'hand'].append(c)
                if effect == 'revive':
                    self.mark_entry(c)
                    c.update(sick=True,tapped=False,damage=0)
                    self.entry_triggers(i,c)
            elif effect == 'fight' and zone == 'board':
                fighters = [u for u in p['board'] if not u['tapped']]
                if fighters:
                    fighter = max(fighters, key=lambda u:self.stats(u)[0])
                    a,b = self.stats(fighter)[0], self.stats(c)[0]
                    hit_fighter = self.damage_creature(fighter,b)
                    hit_target = self.damage_creature(c,a)
                    if 'Lifesteal' in self.keywords(fighter):
                        p['hp'] += hit_target
                    if 'Lifesteal' in self.keywords(c):
                        owner['hp'] += hit_fighter
        if card and card.get('upgrade_draw') and not invalid_source and not invalid_target:
            self.draw(i,card['upgrade_draw'])
        if s.get('lifesteal'):
            p['hp'] += dealt
        self.note(f"Resolved: {s['name']}")
        self.finish_card(s)
        visual['results']=self.presentation_changes(before)

    def finish_card(self, s):
        c = s['card']
        if not c:
            return
        p = self.players[s['owner']]
        if c not in p['board'] and c not in p['engines'] and c not in p.get('gear', []):
            if c.get('commander'):
                p['commander_zone'] = 'command'
            elif c not in p['grave']:
                p['grave'].append(c)

    def finish_opening(self):
        if all(p['kept'] and not p.get('bottom_remaining',0) for p in self.players):
            self.start_turn(self.active)

    def start_turn(self, i):
        self.active = self.priority = i
        self.passes = 0
        p = self.players[i]
        p['turns'] += 1
        for other in self.players:
            other['spells'], other['ashes_used'] = 0, False
        for c in p['board']:
            c['tapped'] = c['sick'] = False
            c['damage'] = c['bonus_attack'] = c['bonus_health'] = 0
            c['buffs'] = [x for x in c.get('buffs',[]) if x.get('duration') != 'Until your next turn']
        p['mana'] = p['capacity'].copy()
        p['temporary'] = 0
        chorus = self.effect_strength(i, 'chorus') if len(p['board']) >= 4 else 0
        if chorus:
            self.push(i, 'mana', amount=chorus, name='Chorus Stone')
        p['active_used'] = False
        # 'grow' is the mandatory mana-choice substep of the first main phase.
        self.phase = 'draw'
        self.draw(i, 1)
        self.check()
        self.note(f"{p['name']} — turn {p['turns']}")
        if self.phase == 'main':
            self.begin_main()

    def begin_main(self):
        self.phase = 'main'
        self.check()
        # Special enemies are announced publicly, never secret stat multipliers.
        if not self.finished and self.active != 0 and self.encounter.get('rule') == 'reinforcements':
            self.push(self.active, 'tokens', amount=1, name='Elite reinforcements')
        if not self.finished and self.active != 0 and self.encounter.get('rule') == 'insight' and self.players[self.active]['turns'] % 2 == 0:
            self.push(self.active, 'draw', amount=1, name='Boss insight')

    def attack_ready(self, c):
        return not c['tapped'] and (not c['sick'] or 'Haste' in self.keywords(c))

    def record_buff(self, card, action, name, effect, duration):
        card.setdefault('buffs',[]).append(dict(name=name,effect=effect,source=action['name'],duration=duration,
                                               icon='shield' if name == 'Protection' else 'strength',debuff=False))

    def ability_options(self, i, c):
        """Explicit abilities share authoritative legality with the review UI."""
        result=[]
        for index, spec in enumerate(c.get('abilities',[])):
            item=copy.deepcopy(spec)
            item['speed'] = 'Sorcery' if spec['timing'] == 'main' else 'Instant'
            item.update(index=index,targets=self.targets(i,spec['target']) if spec.get('target') else [])
            reason=''
            if self.finished or not self.players[i]['alive'] or c['owner'] != i or self.find(c['uid'])[1] != 'board':
                reason='Not your battlefield card'
            elif self.choice or i != self.priority:
                reason='Wait for your priority'
            elif self.phase in ('opening','grow'):
                reason='Finish the current decision'
            elif spec['timing'] == 'main' and (i != self.active or self.phase not in ('main','main2') or self.stack):
                reason='Your main phase, empty stack only'
            elif spec['timing'] == 'response' and not self.stack:
                reason='A pending action is required'
            elif spec.get('exhaust') and not self.attack_ready(c):
                reason='Creature must be ready (or have Haste if new)'
            elif not self.pay(i,spec.get('cost',0),spec.get('pips',{}),False):
                reason='Not enough mana'
            elif spec.get('health_cost',0) >= self.players[i]['hp']:
                reason='Not enough health'
            elif spec.get('discard') and not self.players[i]['hand']:
                reason='Need a card to discard'
            elif spec.get('sacrifice') and not any(x['uid'] != c['uid'] for x in self.players[i]['board']):
                reason='Need another creature to sacrifice'
            elif spec.get('target') and not item['targets']:
                reason='No legal targets'
            item.update(available=not reason,reason=reason)
            result.append(item)
        return result

    def activate_explicit(self, i, c, data):
        index=data.get('ability',0)
        if not isinstance(index,int) or not 0 <= index < len(c['abilities']):
            raise RuleError('Choose a valid ability.')
        spec=self.ability_options(i,c)[index]
        if not spec['available']:
            raise RuleError(spec['reason'])
        target=data.get('target')
        if spec.get('target') and target not in spec['targets']:
            raise RuleError('Choose a legal ability target.')
        _,zone,tcard=self.find(target)
        cost=spec.get('cost',0)+(1 if tcard and zone == 'board' and tcard['owner'] != i and 'Ward' in self.keywords(tcard) else 0)
        p=self.players[i]
        sacrifice=self.find(data.get('sacrifice'))[2] if spec.get('sacrifice') else None
        discard=next((x for x in p['hand'] if x['uid'] == data.get('discard')),None) if spec.get('discard') else None
        if spec.get('sacrifice') and (not sacrifice or sacrifice is c or sacrifice not in p['board']):
            raise RuleError('Choose another creature to sacrifice.')
        if spec.get('discard') and not discard:
            raise RuleError('Choose a card to discard.')
        if not self.pay(i,cost,spec.get('pips',{})):
            raise RuleError('Not enough mana including targeting costs.')
        p['hp']-=spec.get('health_cost',0)
        if spec.get('exhaust'): c['tapped']=True
        if sacrifice: self.death(p,sacrifice)
        if discard: p['hand'].remove(discard);p['grave'].append(discard)
        if spec['effect'] == 'mana' and not spec.get('target') and not spec.get('extra_effects'):
            color = spec.get('mana_color', 'G')
            p['mana'][color] = p['mana'].get(color, 0)+spec.get('amount', 1)
            self.check()
            return
        if self.phase == 'blocks':
            self.phase='block_ability_response'
        self.push(i,spec['effect'],target,spec.get('amount',1),name=spec['name'],source=c,kind='ability')
        pending = self.stack[-1]
        pending.update(source_uid=c['uid'],target_kind=spec.get('target'),requires_source=spec.get('requires_source',False))
        self.queue_ward(i, target, pending)
        self.check()

    def combat_damage(self):
        before=self.presentation_state()
        visual=self.visual_event('combat',dict(owner=self.active,effect='combat',name='Combat damage',kind='combat',amount=0))
        visual['attacks']=[dict(uid=a['uid'],defender=a['defender'],blockers=list(self.blocks.get(a['uid'],[]))) for a in self.attacks]
        pending = []
        visual['hits'] = []
        for a in self.attacks:
            _,zone,attacker = self.find(a['uid'])
            if not attacker or zone != 'board':
                continue
            power = self.stats(attacker)[0]
            blocker_ids = self.blocks.get(a['uid'], [])
            blockers = [self.find(uid)[2] for uid in blocker_ids]
            blockers = [b for b in blockers if b and self.find(b['uid'])[1] == 'board']
            for b in blockers:
                lethal = max(0,self.stats(b)[1]-b['damage'])
                assigned = min(power,lethal)
                pending.append((attacker,b,assigned))
                pending.append((b,attacker,self.stats(b)[0]))
                power -= assigned
            if a['uid'] not in self.blocked or 'Trample' in self.keywords(attacker):
                pending.append((attacker, f"p:{a['defender']}", power))
        for source,target,amount in pending:
            target_uid = target if isinstance(target,str) else target['uid']
            remaining = self.players[int(target[2:])]['hp'] if isinstance(target,str) else max(0,self.stats(target)[1]-target['damage'])
            if isinstance(target,str):
                dealt = self.damage_player(int(target[2:]),amount,source['owner'])
            else:
                dealt = self.damage_creature(target,amount)
            visual['hits'].append(dict(source=source['uid'],target=target_uid,attempted=amount,
                                       dealt=dealt,remaining=remaining))
            if 'Lifesteal' in self.keywords(source):
                self.players[source['owner']]['hp'] += dealt
        visual['results']=self.presentation_changes(before)
        self.attacks = []
        self.blocks = {}
        self.blocked = []
        self.phase = 'combat_end'
        self.check()

    def advance(self):
        if self.phase == 'draw':
            self.phase = 'grow' if sum(self.players[self.active]['capacity'].values()) < 10 else 'main'
            if self.phase == 'main':
                self.begin_main()
        elif self.phase == 'main':
            self.phase = 'precombat'
        elif self.phase == 'precombat':
            self.phase = 'combat'
        elif self.phase == 'attack_response':
            self.defenders = sorted(set(a['defender'] for a in self.attacks), key=lambda i:(i-self.active)%len(self.players))
            self.phase = 'blocks' if self.defenders else 'damage_response'
            if self.defenders:
                self.priority = self.defenders[0]
        elif self.phase == 'block_ability_response':
            self.phase='blocks'
            self.priority=self.defenders[0]
        elif self.phase == 'damage_response':
            self.combat_damage()
        elif self.phase == 'combat_end':
            self.phase = 'main2'
        elif self.phase == 'main2':
            self.phase = 'end'
            p = self.players[self.active]
            amount = self.effect_strength(p['id'], 'reserves')
            if amount and sum(p['mana'].values())+p['temporary'] >= 2:
                self.push(p['id'], 'heal', f"p:{p['id']}", amount, name='Patient Reserves')
        elif self.phase == 'end':
            p = self.players[self.active]
            p['completed_turn'] = True
            for other in self.players:
                for c in other['board']:
                    c['end_buffs'] = []
                    c['protected'] = False
                    c['buffs'] = [x for x in c.get('buffs',[]) if x.get('duration') != 'End of this turn']
                    if c['goad'] and c['owner'] == self.active and p['turns'] >= c['goad']['until']:
                        c['goad'] = None
            # Expiring toughness can cause deaths and create a response window.
            self.phase = 'cleanup'
            self.check()
            if not self.finished and not self.stack:
                self.start_turn(self.next_player(self.active))
            else:
                self.priority = self.active
                self.passes = 0
            return
        elif self.phase == 'cleanup':
            self.start_turn(self.next_player(self.active))
            return
        self.priority = self.active if self.phase != 'blocks' else self.priority
        self.passes = 0

    def _action(self, i, action, **data):
        if self.finished:
            raise RuleError('This battle has ended.')
        p = self.players[i]
        if action == 'stop_loop' and self.loop and self.loop['owner'] == i:
            self.note(f"{p['name']} stops the declared loop.")
            self.loop = None
            return
        if self.item_choice(i, action, data):
            return
        if self.choice:
            if action != 'choose_discard' or i != self.choice['owner']:
                raise RuleError('The resolving player must choose a card to discard.')
            c = next((c for c in p['hand'] if c['uid'] == str(data.get('uid'))),None)
            if not c:
                raise RuleError('Choose one of your hand cards.')
            p['hand'].remove(c)
            p['grave'].append(c)
            self.note(f"{p['name']} discards {c['name']}.")
            self.choice = None
            self.priority = self.active if self.players[self.active]['alive'] else self.next_player(self.active)
            self.passes = 0
            return
        if self.phase == 'opening':
            count = p.get('mulligan_count',int(p.get('mulligan',False)))
            if action == 'mulligan' and not p['kept'] and count < 6:
                p['deck'].extend(p['hand'])
                p['hand'] = []
                self.rng.shuffle(p['deck'])
                self.draw(i,5)
                p['mulligan'] = True
                p['mulligan_count'] = count+1
                self.note(f"{p['name']} redraws five; bottom {max(0,count)} on keep.")
                return
            if action == 'keep' and not p['kept']:
                p['kept'] = True
                p['bottom_remaining'] = max(0,count-1)
                self.finish_opening()
                return
            if action == 'bottom' and p['kept'] and p.get('bottom_remaining',0):
                c = next((c for c in p['hand'] if c['uid'] == str(data.get('uid'))),None)
                if not c:
                    raise RuleError('Choose one opening hand card to put on the bottom.')
                p['hand'].remove(c)
                p['deck'].insert(0,c)
                p['bottom_remaining'] -= 1
                self.note(f"{p['name']} bottoms an opening card ({p['bottom_remaining']} remaining).")
                self.finish_opening()
                return
            raise RuleError('Keep your hand and finish any required bottom choices.')
        if i != self.priority:
            raise RuleError('Wait for your priority.')
        if self.item_action(i, action, data):
            return
        if action == 'loop':
            _,zone,c = self.find(data.get('uid'))
            count = data.get('count')
            engines = {e['effect'] for e in p['engines']}
            if self.stack or not c or zone != 'board' or c['owner'] != i or c['effect'] != 'sacrifice' or not self.attack_ready(c) or not {'relay','foundry'} <= engines or not any(t['token'] for t in p['board']):
                raise RuleError('A loop needs a ready Bone Broker, a token, Recruit Foundry and Reclamation Relay.')
            if isinstance(count,bool) or not isinstance(count,int) or not 1 <= count <= 1000000:
                raise RuleError('Declare a finite repetition count from 1 to 1,000,000.')
            self.loop = dict(owner=i,uid=c['uid'],remaining=count)
            self.note(f"{p['name']} declares {count} Broker repetitions. Every response window remains open.")
            return
        if action == 'color' and self.phase == 'grow' and data.get('color') in p['colors']:
            self.gain_capacity(i,data['color'])
            if not p.get('opening_color'):
                p['opening_color'] = data['color']
            self.begin_main()
            return
        if action in ('enter_combat', 'end_combat', 'end_turn'):
            expected = {'enter_combat':'main', 'end_combat':'combat_end', 'end_turn':'main2'}[action]
            if i != self.active or self.phase != expected or self.stack:
                raise RuleError('Finish pending actions before advancing this phase.')
            self.advance()
            if action == 'enter_combat':
                self.priority = self.next_player(i)
                self.passes = 1
            return
        if action == 'cast':
            uid = str(data.get('uid'))
            if uid == 'commander' and p['commander_zone'] == 'command':
                c = self.instance(p['commander'],i,True)
            else:
                c = next((c for c in p['hand'] if c['uid'] == uid),None)
            target = data.get('target')
            if not c or not self.castable(i,c,target):
                raise RuleError('Cannot cast that card with this timing, target, or mana.')
            if self.loop and self.loop['owner'] != i:
                self.note('Declared loop interrupted by an opposing spell.')
                self.loop = None
            discard = None
            if c['id'] == 'r_loot':
                discard = next((d for d in p['hand'] if d['uid'] == str(data.get('discard')) and d is not c),None)
                if not discard:
                    raise RuleError('Choose a different hand card to discard as a cost.')
            self.pay(i,self.cost_for(i,c,target),c['pips'])
            if c['effect'] in ('destroy','bargain'):
                p['hp'] -= 2
            if discard:
                p['hand'].remove(discard)
                p['grave'].append(discard)
            if c.get('commander'):
                p['tax'] += 2
                p['commander_zone'] = 'stack'
            else:
                p['hand'].remove(c)
            self.push(i,c['effect'],target,c.get('amount',0),c,c['kind'])
            pending = self.stack[-1]
            self.triggers_cast(i,c)
            self.queue_ward(i, target, pending)
            return
        if action == 'ability':
            if self.phase == 'grow':
                raise RuleError('Choose your main-phase mana color first.')
            _,zone,c = self.find(data.get('uid'))
            if c and c.get('abilities'):
                self.activate_explicit(i,c,data)
                return
            if not c or zone != 'board' or c['owner'] != i or not self.attack_ready(c):
                raise RuleError('That creature cannot exhaust for an ability.')
            target = data.get('target')
            if c.get('commander'):
                effect = self.package(i)['active']
            else:
                effect = c['effect']
                if effect not in ('mana', 'sacrifice'):
                    raise RuleError('This creature has no printed activated ability.')
            if effect not in ('mana','sacrifice','draw','loot','ramp','damage','token','buff','protect','bounce','recall'):
                raise RuleError('This creature has no active ability.')
            target_kind = {'damage':'any','buff':'friendly','protect':'friendly','bounce':'creature','recall':'grave'}.get(effect)
            if target_kind and target not in self.targets(i,target_kind):
                raise RuleError('Choose a legal ability target.')
            cost = 0 if effect == 'mana' else 1 if not c.get('commander') else 2
            _,tzone,tcard = self.find(target)
            if tcard and tzone == 'board' and tcard['owner'] != i and 'Ward' in self.keywords(tcard):
                cost += 1
            sacrifice = None
            discard = None
            if effect == 'sacrifice':
                _,z,sacrifice = self.find(data.get('sacrifice'))
                if not sacrifice or z != 'board' or sacrifice['owner'] != i or sacrifice is c:
                    raise RuleError('Choose another friendly creature to sacrifice.')
            if effect == 'loot':
                discard = next((d for d in p['hand'] if d['uid'] == str(data.get('discard'))),None)
                if not discard:
                    raise RuleError('Choose a hand card to discard.')
            if not self.pay(i,cost):
                raise RuleError('Not enough mana for the ability.')
            c['tapped'] = True
            if sacrifice:
                self.death(p,sacrifice)
            if discard:
                p['hand'].remove(discard)
                p['grave'].append(discard)
            if effect == 'mana':
                p['mana']['G'] = p['mana'].get('G',0)+1
            else:
                resolved_effect = {'token':'tokens','sacrifice':'draw','loot':'draw'}.get(effect,effect)
                amount = 2 if effect in ('damage','buff','loot') or (effect == 'sacrifice' and c.get('commander')) else 1
                self.push(i,resolved_effect,target,amount,name=c['name']+' active',source=c,kind='ability')
                self.queue_ward(i, target, self.stack[-1])
            self.check()
            return
        if action == 'pass':
            if self.phase in ('grow','blocks') or (self.phase == 'combat' and not self.stack):
                raise RuleError('Make the current mandatory choice first.')
            self.passes += 1
            if self.passes == len(self.living()):
                self.passes = 0
                if self.stack:
                    self.resolve(self.stack.pop())
                    self.check()
                    self.priority = self.choice['owner'] if self.choice else self.active if self.players[self.active]['alive'] else self.next_player(self.active)
                else:
                    if not self.players[self.active]['alive']:
                        self.start_turn(self.next_player(self.active))
                    else:
                        self.advance()
            else:
                self.priority = self.next_player(i)
            return
        if action == 'attack' and i == self.active and self.phase == 'combat' and not self.stack:
            attacks = data.get('attacks',[])
            used = set()
            for a in attacks:
                _,zone,c = self.find(a['uid'])
                defender = a['defender']
                if not c or zone != 'board' or c['owner'] != i or not self.attack_ready(c) or a['uid'] in used or defender not in self.living() or defender == i:
                    raise RuleError('Illegal attacker or defender.')
                if c['goad'] and defender == c['goad']['by'] and any(j not in (i,defender) for j in self.living()):
                    raise RuleError('Goad requires another opponent if available.')
                used.add(a['uid'])
            required = [c['uid'] for c in p['board'] if c['goad'] and self.attack_ready(c)]
            if any(uid not in used for uid in required):
                raise RuleError('Goaded creatures must attack if able.')
            self.attacks = copy.deepcopy(attacks)
            for a in attacks:
                c = self.find(a['uid'])[2]
                if 'Guard' not in self.keywords(c):
                    c['tapped'] = True
            self.phase = 'attack_response'
            self.item_attack_triggers(i, attacks)
            self.passes = 0
            return
        if action == 'block' and self.phase == 'blocks' and self.defenders[0] == i:
            assignments = data.get('blocks',{})
            used = set()
            for attacker_uid, blockers in assignments.items():
                a = next((a for a in self.attacks if a['uid'] == attacker_uid and a['defender'] == i),None)
                attacker = self.find(attacker_uid)[2]
                if not a or not attacker:
                    raise RuleError('Not an attack against you.')
                for uid in blockers:
                    _,z,c = self.find(uid)
                    if not c or z != 'board' or c['owner'] != i or c['tapped'] or uid in used:
                        raise RuleError('Illegal blocker.')
                    if 'Flying' in self.keywords(attacker) and not self.keywords(c) & {'Flying','Reach'}:
                        raise RuleError('Flying requires Flying or Reach to block.')
                    used.add(uid)
            for uid,blockers in assignments.items():
                self.blocks[uid] = blockers[:]
                if blockers:
                    self.blocked.append(uid)
            self.defenders.pop(0)
            if self.defenders:
                self.priority = self.defenders[0]
            else:
                self.phase = 'damage_response'
                self.priority = self.active
            self.passes = 0
            return
        if action == 'order' and i == self.active and self.phase == 'damage_response' and not self.stack:
            uid = data.get('uid')
            order = data.get('order',[])
            if sorted(order) != sorted(self.blocks.get(uid,[])):
                raise RuleError('Order must contain exactly the assigned blockers.')
            self.blocks[uid] = order[:]
            self.passes = 0
            return
        if action == 'concede' and not self.stack:
            p['hp'] = 0
            p['eliminator'] = None
            # Concessions are explicit departures, including during opening protection.
            p['turns'] = max(1,p['turns'])
            p['alive'] = False
            p['eliminated_at'] = time.time()
            p['eliminated_elapsed'] = self.elapsed
            for zone in ('board','hand','deck','grave','exile','engines','gear'):
                p[zone].clear()
            self.note(f"{p['name']} concedes; no elimination point awarded.")
            self.attacks = [a for a in self.attacks if a['defender'] != i]
            self.defenders = [j for j in self.defenders if j != i]
            self.check()
            return
        raise RuleError('That action is unavailable now.')

    def view(self, viewer):
        result = dict(phase=self.phase, active=self.active, priority=self.priority, stack=[],
                      attacks=self.attacks, blocks=self.blocks, finished=self.finished,
                      survivor=self.survivor, opening_protection=self.protected_opening(),
                      visual_events=copy.deepcopy(getattr(self,'visual_events',[])),
                      loop=copy.deepcopy(self.loop),
                      choice=copy.deepcopy(self.choice),
                      log=self.log[-100:], players=[], keywords=KEYWORDS, encounter=self.encounter)
        for p in self.players:
            out = {k:copy.deepcopy(v) for k,v in p.items() if k not in ('hand','deck','opening_color')}
            out['hand_count'],out['deck_count'] = len(p['hand']),len(p['deck'])
            out['hand'] = copy.deepcopy(p['hand']) if p['id'] == viewer else []
            for card in out['hand']:
                card['speed'] = 'Instant' if self.instant_card(p['id'], card) else 'Sorcery'
                card['keywords'] = sorted(self.keywords(card))
            out['creature_flash'] = self.timing_override(p['id'], 'creature_cast')
            out['instant_equip'] = self.timing_override(p['id'], 'equip')
            if p.get('equipment') is not None:
                out['equipment'] = [equipment_view(item) for item in p['equipment']]
            out['opening_color'] = p['opening_color'] if p['id'] == viewer or self.phase != 'opening' else None
            out['board'] = []
            for c in p['board']:
                shown = copy.deepcopy(c)
                shown['shown_attack'],shown['shown_health'] = self.stats(c)
                shown['keywords'] = sorted(self.keywords(c))
                shown['ability_speed'] = 'Instant'
                shown['ward_cost'] = int(bool('Ward' in c['keywords'] or (c.get('commander') and self.package(c['owner'])['passive'] == 'ward')))
                shown['ward_payments'] = [g['bearer_ward'] for g in self.attachments(c) if g.get('bearer_ward')]
                if c.get('abilities'):
                    shown['abilities'] = self.ability_options(viewer,c)
                out['board'].append(shown)
            result['players'].append(out)
        for out in result['players']:
            out['pouch'] = [dict(item, **CONSUMABLE_MAP[item['design']], speed='Sorcery' if CONSUMABLE_MAP[item['design']].get('sorcery') else 'Instant') for item in out.get('pouch', [])]
        for s in self.stack:
            result['stack'].append({k:v for k,v in s.items() if k != 'card'})
        result['targets'] = {kind:self.targets(viewer,kind) for kind in ('any','creature','friendly','enemy','large','grave','small_grave','stack','engine') + EXTRA_TARGETS}
        return result

    def loop_step(self):
        """Automate only the initiator; opponents keep normal priority and can stop it."""
        if not self.loop or self.finished:
            return False
        if self.choice:
            return False
        loop = self.loop
        if self.priority != loop['owner']:
            return False
        if self.stack:
            self.action(self.priority,'pass')
            return True
        if loop['remaining'] == 0:
            self.loop = None
            return False
        p = self.players[loop['owner']]
        _,zone,c = self.find(loop['uid'])
        token = next((t for t in p['board'] if t['token']),None)
        engines = {e['effect'] for e in p['engines']}
        if not c or zone != 'board' or not self.attack_ready(c) or not token or not {'relay','foundry'} <= engines or not self.pay(p['id'],1,commit=False):
            self.note('Declared loop stopped: a required piece or resource is unavailable.')
            self.loop = None
            return False
        self.action(p['id'],'ability',uid=c['uid'],sacrifice=token['uid'])
        loop['remaining'] -= 1
        return True

    def has_legal_response(self, i, meaningful=False):
        """Check actual costs, targets and timings without paying or revealing hands."""
        if self.finished or self.choice or i != self.priority:
            return False
        p = self.players[i]
        for item in p.get('pouch', []):
            spec = CONSUMABLE_MAP[item['design']]
            if not spec.get('sorcery') and spec.get('target') and self.phase not in ('opening', 'grow', 'blocks') and any(self.pay(i, self.cost_for(i, spec, t), spec['pips'], False) for t in self.targets(i, spec['target'])):
                return True
            if not spec.get('sorcery') and not spec.get('target') and self.pay(i, spec['cost'], spec['pips'], False):
                return True
        for card in p['hand']:
            if self.instant_card(i, card):
                targets = self.targets(i,card['target']) if card.get('target') else [None]
                if any(self.castable(i,card,target) for target in targets):
                    return True
        for card in p['board']:
            candidates = []
            if meaningful and card['effect'] == 'mana' and not card.get('abilities'):
                continue
            if card.get('abilities'):
                for spec in self.ability_options(i,card):
                    if spec['timing'] == 'main' or not spec['available'] or (meaningful and spec['effect'] == 'mana' and not spec.get('target') and not spec.get('extra_effects')):
                        continue
                    for target in spec['targets'] if spec.get('target') else [None]:
                        candidates.append(dict(uid=card['uid'],ability=spec['index'],target=target))
            else:
                effect = self.package(i)['active'] if card.get('commander') else card['effect']
                kind = {'damage':'any','buff':'friendly','protect':'friendly','bounce':'creature','recall':'grave'}.get(effect)
                for target in self.targets(i,kind) if kind else [None]:
                    candidates.append(dict(uid=card['uid'],target=target))
            for data in candidates:
                data.update(sacrifice=next((c['uid'] for c in p['board'] if c is not card),None),
                            discard=p['hand'][0]['uid'] if p['hand'] else None)
                trial = copy.deepcopy(self)
                try:
                    trial.action(i,'ability',**data)
                    return True
                except RuleError:
                    pass
        return False

    def should_auto_pass(self):
        if self.finished or self.choice or self.phase in ('opening','grow','blocks'):
            return False
        if not self.stack and (self.phase == 'combat' or
                (self.priority == self.active and self.phase in ('main','main2','combat_end'))):
            return False
        return not self.meaningful_response(self.priority)

    def auto_pass_unavailable(self):
        """Advance empty response windows, stopping at every real decision."""
        count = 0
        while count < 64 and self.should_auto_pass():
            self.action(self.priority,'pass')
            count += 1
        return count

    def ai_action(self, i):
        """Only own hand plus public state; no opponent hand/deck inspection."""
        p = self.players[i]
        if self.choice and self.choice['kind'] == 'trigger_order':
            return dict(action='order_triggers',order=self.choice['uids'][:])
        if self.choice and self.choice['kind'] != 'discard':
            return self.item_ai(i)
        if self.choice:
            return dict(action='choose_discard',uid=max(p['hand'],key=lambda c:c['cost'])['uid'])
        if self.phase == 'opening':
            if p.get('bottom_remaining',0):
                return dict(action='bottom',uid=max(p['hand'],key=lambda c:c['cost'])['uid'])
            if not p['kept']:
                return dict(action='keep')
            return dict(action='color',color=p['colors'][0])
        if self.phase == 'grow':
            return dict(action='color',color=min(p['colors'],key=lambda c:p['capacity'].get(c,0)))
        if self.phase == 'blocks':
            assignments = {}
            ready = [c for c in p['board'] if not c['tapped']]
            for a in self.attacks:
                if a['defender'] != i:
                    continue
                attacker = self.find(a['uid'])[2]
                if not attacker:
                    continue
                legal = [c for c in ready if 'Flying' not in self.keywords(attacker) or self.keywords(c)&{'Flying','Reach'}]
                if legal:
                    blocker = min(legal,key=lambda c:self.stats(c)[0])
                    assignments[a['uid']] = [blocker['uid']]
                    ready.remove(blocker)
            return dict(action='block',blocks=assignments)
        if self.phase == 'combat' and not self.stack:
            opponents = [j for j in self.living() if j != i]
            # Coordinated encounters publicly declare their exception to self-interest.
            def threat(j):
                other = self.players[j]
                return sum(self.stats(c)[0] for c in other['board']) + len(other['engines'])*3 + (25-other['hp'])/3
            target = 0 if self.encounter.get('coordinated') and i != 0 and 0 in opponents else (
                max(opponents,key=threat) if self.encounter.get('act',1) >= 2 else min(opponents,key=lambda j:self.players[j]['hp']))
            attacks = []
            ready = [c for c in p['board'] if self.attack_ready(c)]
            for c in ready:
                defender = target
                if c['goad'] and defender == c['goad']['by']:
                    alternatives = [j for j in opponents if j != defender]
                    if alternatives:
                        defender = alternatives[0]
                opposing = [b for b in self.players[defender]['board'] if not b['tapped']]
                safe = not opposing or self.stats(c)[0] >= max(self.stats(b)[1]-b['damage'] for b in opposing)
                if c['goad'] or safe or len(ready) > 2 or p['hp'] < 8:
                    attacks.append(dict(uid=c['uid'],defender=defender))
            return dict(action='attack',attacks=attacks)
        item_move = self.item_ai(i)
        if item_move:
            return item_move
        candidates = list(p['hand'])
        if p['commander_zone'] == 'command' and not self.stack and i == self.active:
            # A preview must not consume the instance serial.
            serial = self.serial
            cmd = self.instance(p['commander'],i,True)
            self.serial = serial
            candidates.append(cmd)
        for c in sorted(candidates,key=lambda c:(c['kind'] != 'creature',c['cost'])):
            targets = self.targets(i,c.get('target',''))
            target = None
            kind = c.get('target')
            if kind == 'stack':
                targets = [s['uid'] for s in self.stack if s['owner'] != i]
            elif kind in ('creature','enemy','large','engine'):
                targets = [t for t in targets if self.find(t)[0]['id'] != i]
            elif kind == 'any':
                targets = [f'p:{j}' for j in self.living() if j != i]
                targets.sort(key=lambda t:self.players[int(t[2:])]['hp'])
            elif kind == 'friendly' and c['effect'] == 'protect':
                threatened = {a['uid'] for a in self.attacks} | {uid for group in self.blocks.values() for uid in group}
                targets = [t for t in targets if t in threatened]
            if kind:
                if not targets:
                    continue
                target = targets[0]
            if c['kind'] == 'response' and not self.stack and self.phase not in ('damage_response','main','main2'):
                continue
            if c['effect'] == 'team_buff' and len(p['board']) < 2:
                continue
            if c['effect'] == 'fight' and not any(not u['tapped'] for u in p['board']):
                continue
            if c['effect'] == 'wipe':
                own = sum(self.stats(u)[1]-u['damage'] <= c['amount'] for u in p['board'])
                others = sum(self.stats(u)[1]-u['damage'] <= c['amount'] for other in self.players if other['id'] != i for u in other['board'])
                if others <= own:
                    continue
            if self.castable(i,c,target):
                action = dict(action='cast',uid='commander' if c.get('commander') else c['uid'],target=target)
                if c['id'] == 'r_loot':
                    other = [d for d in p['hand'] if d is not c]
                    if not other:
                        continue
                    action['discard'] = max(other,key=lambda d:d['cost'])['uid']
                return action
        for c in p['board']:
            if c['effect'] == 'mana' and self.attack_ready(c) and any(
                    self.cost_for(i,d) <= sum(p['mana'].values())+p['temporary']+1 for d in p['hand']):
                return dict(action='ability',uid=c['uid'])
            if c['effect'] == 'sacrifice' and self.attack_ready(c) and p['deck'] and len(p['hand'])<5 and self.pay(i,1,commit=False):
                expendable = [d for d in p['board'] if d is not c and (d['token'] or d['effect']=='death_drain')]
                if expendable:
                    return dict(action='ability',uid=c['uid'],sacrifice=expendable[0]['uid'])
            if c.get('commander') and i == self.active and self.phase in ('main','main2') and not self.stack and self.attack_ready(c) and self.pay(i,2,commit=False):
                effect = self.package(i)['active']
                kind = {'damage':'any','buff':'friendly','protect':'friendly','bounce':'creature','recall':'grave'}.get(effect)
                targets = self.targets(i,kind or '')
                if effect in ('protect','buff'):
                    continue  # Keep combat threats instead of spending defense in an empty main phase.
                action = dict(action='ability',uid=c['uid'])
                if kind:
                    if effect == 'damage':
                        targets = [f'p:{j}' for j in self.living() if j != i]
                    if effect == 'bounce':
                        targets = [t for t in targets if self.find(t)[0]['id'] != i]
                    if not targets:
                        continue
                    action['target'] = targets[0]
                if effect == 'loot':
                    if not p['hand']:
                        continue
                    action['discard'] = max(p['hand'],key=lambda d:d['cost'])['uid']
                if effect == 'sacrifice':
                    expendable = [d for d in p['board'] if d is not c and (d['token'] or d['effect']=='death_drain')]
                    if not expendable:
                        continue
                    action['sacrifice'] = expendable[0]['uid']
                if effect == 'ramp' and sum(p['capacity'].values()) >= 10:
                    continue
                return action
        return dict(action='pass')

    def to_dict(self):
        data = {k:copy.deepcopy(v) for k,v in self.__dict__.items() if k != 'rng'}
        data['random_state'] = self.rng.getstate()
        return data

    @classmethod
    def from_dict(cls, data):
        b = cls.__new__(cls)
        b.__dict__.update({k:v for k,v in data.items() if k != 'random_state'})
        b.gear_cards = {int(k):v for k,v in getattr(b, 'gear_cards', {}).items()}
        b.card_upgrades = {int(k):v for k,v in getattr(b,'card_upgrades',{}).items()}
        for p in b.players:
            p.setdefault('mulligan_count',int(p.get('mulligan',False)))
            p.setdefault('bottom_remaining',0)
            p.setdefault('gear', [])
            p.setdefault('pouch', [])
            p.setdefault('spent_consumables', [])
            # Refresh explanatory text in resumed games without changing card stats or effects.
            for zone in ('hand','deck','board','engines','grave','exile'):
                for card in p.get(zone,[]):
                    if card.get('commander'):
                        card['text'] = b.package(p['id'])['description']
                    elif card.get('id') in CARD_MAP and not card.get('token') and not card.get('abilities') and not card.get('gems'):
                        card['text'] = upgraded_card(card['id'],card.get('upgrade',0))['text']
        b.entry_serial = max([getattr(b, 'entry_serial', 0), *[c.get('entry_order', 0) for p in b.players for c in p['board']+p['engines']]])
        for p in b.players:
            for card in p['board']+p['engines']:
                if 'entry_order' not in card:
                    b.mark_entry(card)
        b.rng = random.Random()
        def tuples(x):
            return tuple(tuples(v) for v in x) if isinstance(x,list) else x
        b.rng.setstate(tuples(data['random_state']))
        if b.phase == 'opening':
            b.finish_opening()
        return b
