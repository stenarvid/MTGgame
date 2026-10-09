"""Equipment, relics and pouch rules mixed into the authoritative battle engine."""
import copy
from .items import ITEM_MAP, CONSUMABLE_MAP, compose, EXTRA_TARGETS


class ItemBattle:
    def attachments(self, creature):
        return [g for p in self.players for g in p.get('gear', []) if g.get('attachment') == creature['uid']]

    def qualifies(self, c, condition):
        return {'equipped': bool(self.attachments(c)), 'token': c.get('token', False),
                'nontoken': not c.get('token'), 'legendary': bool(c.get('legendary') or c.get('commander'))}.get(condition, False)

    def item_stats(self, c):
        attack = health = 0
        for g in self.attachments(c):
            attack += g['gear_attack']; health += g['gear_health']
        if c.get('effect') == 'equipped_recruit' and self.attachments(c):
            attack += 1; health += 1
        for item in self.players[c['owner']].get('equipment') or []:
            if item['design'] in ITEM_MAP and ITEM_MAP[item['design']]['category'] == 'relic':
                r = compose(item)
                if not r['triggered'] and self.qualifies(c, r['condition']):
                    attack += r['attack']; health += r['health']
        for buff in c.get('end_buffs', []):
            attack += buff.get('attack', 0); health += buff.get('health', 0)
        return attack, health

    def item_keywords(self, c):
        words = {k for g in self.attachments(c) for k in g.get('granted_keywords', [])}
        if c.get('effect') == 'equipped_recruit' and self.attachments(c):
            words.add('Vigilance')
        for buff in c.get('end_buffs', []):
            words.update(buff.get('keywords', []))
        if 'Vigilance' in words: words.add('Guard')
        if 'Lifelink' in words: words.add('Lifesteal')
        if c.get('ward') or any(g.get('bearer_ward') for g in self.attachments(c)):
            words.add('Ward')
        return words

    def item_target_allowed(self, i, c):
        return c['owner'] == i or 'Hexproof' not in self.keywords(c)

    def item_targets(self, i, kind):
        if kind == 'artifact':
            return [g['uid'] for p in self.players if p['alive'] for g in p.get('gear', []) if self.item_target_allowed(i, g)]
        if kind == 'small_creature':
            return [c['uid'] for p in self.players if p['alive'] for c in p['board'] if c['cost'] <= 3 and self.item_target_allowed(i, c)]
        if kind == 'noncreature_spell':
            return [s['uid'] for s in self.stack if s.get('card') and s['kind'] != 'creature']
        return []

    def equipment_cast_triggers(self, i, card):
        if card['kind'] != 'equipment': return
        p = self.players[i]
        for engine in p['engines']:
            if engine['effect'] == 'equipment_study':
                self.push(i, 'draw', amount=1, name=engine['name'], source=engine)
        tenders = [dict(name=c['name'],source_uid=c['uid']) for c in p['board'] if c['effect'] == 'equipment_cast_counter']
        if tenders and self.targets(i, 'friendly'):
            self.choice = dict(owner=i, kind='counter_target', **tenders.pop(0), remaining=tenders)

    def item_attack_triggers(self, i, attacks):
        p = self.players[i]
        for attack in attacks:
            c = self.find(attack['uid'])[2]
            for item in p.get('equipment') or []:
                if item['design'] in ITEM_MAP and ITEM_MAP[item['design']]['category'] == 'relic':
                    r = compose(item)
                    if r['triggered'] and self.qualifies(c, r['condition']):
                        self.push(i, 'relic_attack', c['uid'], name=r['name'])
                        self.stack[-1]['stat_bonus'] = [r['attack'], r['health']]
            if c['effect'] == 'equipment_attack_loot' and self.attachments(c):
                self.push(i, 'optional_loot', c['uid'], name=c['name'], source=c)

    def item_death_triggers(self, p, c, watchers):
        if not self.attachments(c): return
        for w in watchers:
            if w['effect'] == 'equipment_death':
                self.push(p['id'], 'optional_death_draw', name=w['name'], source=w)

    def detach(self, c):
        for g in self.attachments(c): g['attachment'] = None
        if c['kind'] == 'equipment': c['attachment'] = None

    def queue_ward(self, i, target, pending):
        _, zone, c = self.find(target)
        if not c or c['owner'] == i or zone not in ('board', 'gear'): return
        costs = ([c['ward']] if c.get('ward') else []) + [g['bearer_ward'] for g in self.attachments(c) if g.get('bearer_ward')]
        for cost in costs:
            self.push(c['owner'], 'item_ward', pending['uid'], cost, name=f'Ward {{{cost}}}', source=c)
            self.stack[-1]['payer'] = i

    def item_action(self, i, action, data):
        if action not in ('equip_gear', 'consume'): return False
        self.rule(i == self.priority and not self.finished and not self.choice and self.phase not in ('opening', 'grow', 'blocks'), 'Wait for priority and finish the current decision.')
        p = self.players[i]; target = data.get('target')
        if action == 'equip_gear':
            _, zone, c = self.find(data.get('uid'))
            self.rule(c is not None and zone == 'gear' and c['owner'] == i, 'Choose Equipment you control.')
            self.rule(self.timing_override(i, 'equip') or (i == self.active and self.phase in ('main', 'main2') and not self.stack), 'Equip only as a sorcery unless an item grants Instant Equip.')
            self.rule(target in self.targets(i, 'friendly'), 'Choose a creature you control.')
            self.rule(self.pay(i, c['equip_cost'], commit=False), 'Not enough mana to equip.')
            self.pay(i, c['equip_cost'])
            self.push(i, 'attach', target, name=c['name']+' — Equip', source=c, kind='ability')
            self.stack[-1].update(target_kind='friendly', equipment_uid=c['uid'])
        else:
            item = next((x for x in p.get('pouch', []) if x['uid'] == data.get('uid')), None)
            self.rule(item is not None, 'Choose an unspent pouch item.')
            c = CONSUMABLE_MAP[item['design']]
            self.rule(c['color'] in p['colors']+['C'], 'Consumable is outside your color identity.')
            self.rule(not c.get('sorcery') or (i == self.active and self.phase in ('main', 'main2') and not self.stack), 'Activate only as a sorcery.')
            self.rule(not c.get('target') or target in self.targets(i, c['target']), 'Choose a legal target.')
            self.rule(self.pay(i, self.cost_for(i, c, target), c['pips'], False), 'Not enough mana.')
            self.pay(i, self.cost_for(i, c, target), c['pips'])
            p['pouch'].remove(item)
            p.setdefault('spent_consumables', []).append(item['uid'])
            self.push(i, c['effect'], target, c.get('amount', 0), name=c['name'], kind='ability')
            self.stack[-1].update(target_kind=c.get('target'))
            self.queue_ward(i, target, self.stack[-1])
        self.check()
        return True

    def rule(self, condition, message):
        if not condition:
            from .battle import RuleError
            raise RuleError(message)

    def item_resolve(self, s, c, zone, invalid):
        i = s['owner']; p = self.players[i]; effect = s['effect']
        if effect not in ('equipment', 'equipment_study', 'attach', 'choose_attachment', 'choose_counter_target',
                          'item_counter', 'soft_counter', 'item_ward', 'destroy_small', 'destroy_artifact',
                          'stand_together', 'barkskin', 'hexproof', 'soldier', 'relic_attack',
                          'optional_loot', 'optional_death_draw'): return False
        if invalid: return True
        if effect == 'equipment':
            card = s['card']; p['gear'].append(card)
            card['attachment'] = None
            if card.get('auto_attach') and not (i == 0 and 'silent_entry' in self.encounter.get('modifiers', [])):
                # Target choice is made before this entry trigger is put on the stack.
                self.choice = dict(owner=i, kind='attachment_target', equipment_uid=card['uid'], name=card['name']) if self.targets(i, 'friendly') else None
        elif effect == 'equipment_study':
            self.mark_entry(s['card'])
            p['engines'].append(s['card'])
        elif effect == 'attach':
            g = self.find(s.get('equipment_uid'))[2]
            if g and self.find(g['uid'])[1] == 'gear' and c and zone == 'board':
                self.serial += 1
                g['attachment_order'] = self.serial
                g['attachment'] = c['uid']
        elif effect == 'choose_counter_target':
            if self.targets(i, 'friendly'):
                self.choice = dict(owner=i, kind='counter_target', name=s['name'])
        elif effect == 'item_counter':
            if c: c['attack'] += 1; c['health'] += 1
        elif effect == 'soft_counter':
            pending = next((x for x in self.stack if x['uid'] == s['target']), None)
            if pending: self.choice = dict(owner=pending['owner'], kind='payment', cost=3, pending=pending['uid'], name=s['name'])
        elif effect == 'item_ward':
            if any(x['uid'] == s['target'] for x in self.stack):
                self.choice = dict(owner=s['payer'], kind='payment', cost=s['amount'], pending=s['target'], name=s['name'])
        elif effect in ('destroy_small', 'destroy_artifact'):
            if c and zone == 'board': self.death(self.find(c['uid'])[0], c)
            elif c and zone == 'gear': self.move_out(self.find(c['uid'])[0], c)
        elif effect in ('stand_together', 'barkskin', 'hexproof'):
            if c:
                buff = dict(attack=2, health=2) if effect == 'stand_together' else dict(attack=1, health=2) if effect == 'barkskin' else dict(keywords=['Hexproof'])
                c.setdefault('end_buffs', []).append(buff)
            if effect == 'stand_together': p['hp'] += 2
        elif effect == 'soldier':
            t = self.instance('w_recruit', i)
            t.update(name='Soldier', attack=1, health=1, printed_attack=1, printed_health=1, token=True, upgrade=0, text='', keywords=[])
            self.mark_entry(t)
            p['board'].append(t)
        elif effect == 'relic_attack':
            if c and zone == 'board':
                a, h = s['stat_bonus']; c.setdefault('end_buffs', []).append(dict(attack=a, health=h))
            p['hp'] += 1
        elif effect == 'optional_loot':
            if c and self.attachments(c) and p['hand']:
                self.choice = dict(owner=i, kind='optional_loot', name=s['name'])
        elif effect == 'optional_death_draw':
            self.choice = dict(owner=i, kind='optional_death_draw', name=s['name'])
        return True

    def item_choice(self, i, action, data):
        choice = self.choice
        if not choice or choice['kind'] == 'discard': return False
        self.rule(i == choice['owner'], 'The resolving player must choose.')
        p = self.players[i]; kind = choice['kind']
        if kind in ('attachment_target', 'counter_target'):
            self.rule(action == 'choose_item_target' and data.get('target') in self.targets(i, 'friendly'), 'Choose a creature you control.')
            if kind == 'attachment_target':
                g = self.find(choice['equipment_uid'])[2]
                self.push(i, 'attach', data['target'], name=choice['name']+' entry', source=g)
                self.stack[-1].update(target_kind='friendly', equipment_uid=g['uid'])
            else:
                # This choice starts the targeted cast trigger before anyone can respond.
                self.push(i, 'item_counter', data['target'], name=choice['name'], source=self.find(choice.get('source_uid'))[2])
                self.stack[-1]['target_kind'] = 'friendly'
        elif kind == 'payment':
            self.rule(action == 'choose_item_payment' and type(data.get('pay')) is bool, 'Choose Pay or Decline.')
            if data['pay']:
                self.rule(self.pay(i, choice['cost'], commit=False), 'Not enough mana.')
                self.pay(i, choice['cost'])
            else:
                pending = next((x for x in self.stack if x['uid'] == choice['pending']), None)
                if pending:
                    self.stack.remove(pending); self.visual_event('resolve', pending, 'countered'); self.finish_card(pending)
        elif kind == 'optional_death_draw':
            self.rule(action == 'choose_item_payment' and type(data.get('pay')) is bool, 'Choose Pay or Decline.')
            if data['pay']:
                self.rule(self.pay(i, 1, commit=False), 'Not enough mana.')
                self.pay(i, 1); self.draw(i, 1); p['hp'] -= 1
        elif kind == 'optional_loot':
            self.rule(action in ('choose_item_discard', 'decline_item_choice'), 'Choose a card or decline.')
            if action == 'choose_item_discard':
                card = next((c for c in p['hand'] if c['uid'] == data.get('uid')), None)
                self.rule(card is not None, 'Choose a hand card.')
                p['hand'].remove(card); p['grave'].append(card); self.draw(i, 1)
        if kind == 'counter_target' and choice.get('remaining'):
            remaining = choice['remaining']
            next_source = remaining.pop(0)
            if isinstance(next_source, str):
                next_source = dict(name=next_source)  # Existing saved choices.
            self.choice = dict(owner=i, kind=kind, **next_source, remaining=remaining, trigger_batch=choice.get('trigger_batch'))
        else:
            self.choice = None
        self.priority = self.active; self.passes = 0
        self.check()
        return True

    def change_control(self, uid, controller):
        owner, zone, card = self.find(uid)
        self.rule(card is not None and zone in ('board', 'gear', 'engines') and controller in self.living(), 'Choose a battlefield permanent and living controller.')
        if card['owner'] != controller:
            owner[zone].remove(card)
            card['owner'] = controller
            card['sick'] = True
            self.players[controller][zone].append(card)
        self.check()

    def copy_equipment(self, uid, controller):
        _, zone, card = self.find(uid)
        self.rule(card is not None and zone == 'gear', 'Choose Equipment on the battlefield.')
        self.serial += 1
        token = copy.deepcopy(card)
        token.update(uid=str(self.serial), owner=controller, origin_owner=controller, token=True,
                     attachment=None, tapped=False, sick=True)
        token.pop('item_uid', None)
        self.players[controller]['gear'].append(token)
        if token.get('auto_attach') and self.targets(controller, 'friendly'):
            self.choice = dict(owner=controller, kind='attachment_target', equipment_uid=token['uid'], name=token['name'])
        return token

    def item_ai(self, i):
        p = self.players[i]
        if self.choice and self.choice['kind'] != 'discard':
            if self.choice['owner'] != i: return dict(action='pass')
            kind = self.choice['kind']
            if kind in ('attachment_target', 'counter_target'):
                return dict(action='choose_item_target', target=max(p['board'], key=lambda c:self.stats(c)[0])['uid'])
            if kind in ('payment', 'optional_death_draw'):
                return dict(action='choose_item_payment', pay=self.pay(i, self.choice.get('cost', 1), commit=False))
            return dict(action='choose_item_discard', uid=p['hand'][0]['uid']) if p['hand'] else dict(action='decline_item_choice')
        if self.phase in ('main', 'main2') and not self.stack and i == self.active:
            for g in p.get('gear', []):
                if not g.get('attachment') and p['board'] and self.pay(i, g['equip_cost'], commit=False):
                    return dict(action='equip_gear', uid=g['uid'], target=max(p['board'], key=lambda c:self.stats(c)[0])['uid'])
        for item in p.get('pouch', []):
            spec = CONSUMABLE_MAP[item['design']]
            if spec['effect'] == 'heal' and p['hp'] > 18: continue
            if spec.get('sorcery') and (i != self.active or self.phase not in ('main', 'main2') or self.stack): continue
            if spec.get('target'):
                targets = self.targets(i, spec['target'])
                targets = [uid for uid in targets if (self.find(uid)[2]['owner'] == i) == (spec['effect'] != 'damage')]
                if not targets: continue
                target = targets[0]
            else: target = None
            if self.phase not in ('opening', 'grow', 'blocks') and self.pay(i, self.cost_for(i, spec, target), spec['pips'], False):
                return dict(action='consume', uid=item['uid'], target=target)
        return None
