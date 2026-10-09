"""Server-owned response automation, phase stops and deterministic trigger order."""
import copy
import time

PHASES = ('draw', 'main', 'combat', 'main2', 'end')


def checkpoint(phase):
    if phase == 'grow':
        return 'main'
    if phase in ('precombat', 'attack_response', 'blocks', 'damage_response', 'combat_end'):
        return 'combat'
    return phase


def preferences(member):
    member.setdefault('auto', True)
    member.setdefault('hold_priority', False)
    member.setdefault('auto_advance', False)
    member.setdefault('auto_order', True)
    member.setdefault('phase_stops', [])


class PriorityRules:
    def timing_override(self, i, category):
        """Explicit categories; Flash never changes activated ability timing."""
        p = self.players[i]
        from .items import ITEM_MAP
        from .content import RELIC_MAP
        sources = [p, *(p.get('equipment') or []), *p.get('engines', [])]
        if p.get('equipment') is None:
            sources.append(RELIC_MAP.get(p.get('relic'), {}))
        for source in sources:
            template = ITEM_MAP.get(source.get('design'), RELIC_MAP.get(source.get('design'), {}))
            permissions = source.get('instant_actions', template.get('instant_actions', []))
            if category in permissions:
                return True
        return False

    def mark_entry(self, card):
        self.entry_serial = getattr(self, 'entry_serial', 0)+1
        card['entry_order'] = self.entry_serial

    def instant_card(self, i, card):
        return card['kind'] == 'response' or 'Flash' in self.keywords(card) or self.timing_override(
            i, 'creature_cast' if card['kind'] == 'creature' else 'noncreature_sorcery_cast')

    def decision_key(self):
        return repr((self.active, self.priority, self.phase, self.passes,
                tuple(s['uid'] for s in self.stack), repr(self.choice),
                getattr(self, 'decision_serial', 0)))

    def trigger_key(self, s):
        p = self.players[s['owner']]
        source = s.get('source_uid')
        relics = p.get('equipment') or []
        for n, item in enumerate(relics):
            if item['uid'] == s.get('relic_uid'):
                return (0, n, int(s['uid'][1:]))
        if str(s.get('card_id', '')).startswith('relic_'):
            return (0, len(relics), int(s['uid'][1:]))
        for n, g in enumerate(sorted(p.get('gear', []), key=lambda g:g.get('attachment_order', 0))):
            if g['uid'] == source:
                return (1, n, int(s['uid'][1:]))
        return (1 if s.get('source_category') == 'equipment' else 2,
                s.get('source_order', 10**9), int(s['uid'][1:]))

    def action(self, i, action, **data):
        from .battle import RuleError
        if self.finished:
            raise RuleError('This battle has ended.')
        if self.choice and self.choice['kind'] == 'trigger_order':
            if i != self.choice['owner'] or action != 'order_triggers':
                raise RuleError('Choose the resolution order of your triggers.')
            ids = self.choice['uids']
            order = data.get('order', [])
            if not isinstance(order, list) or not all(isinstance(uid, str) for uid in order) or len(order) != len(ids) or set(order) != set(ids):
                raise RuleError('Include each trigger exactly once.')
            entries = {s['uid']:s for s in self.stack if s['uid'] in ids}
            positions = [n for n,s in enumerate(self.stack) if s['uid'] in ids]
            for n, uid in zip(positions, reversed(order)):
                self.stack[n] = entries[uid]
            self.choice = None
            self.priority = self.active
            self._next_trigger_choice()
            self._finish_submission_priority()
            self.decision_serial = getattr(self, 'decision_serial', 0)+1
            return
        pending_batch = self.choice.get('trigger_batch') if self.choice else None
        old = {s['uid'] for s in self.stack}
        self._action(i, action, **data)
        new = [s for s in self.stack if s['uid'] not in old]
        # Explicit casts/activations retain their kind; their automatic effects
        # form a simultaneous batch before the next priority checkpoint.
        primary = [s for s in new if s.get('kind') != 'trigger']
        triggers = [s for s in new if s not in primary]
        if triggers:
            batch_id = pending_batch or 't'+str(getattr(self, 'decision_serial', 0)+1)
            if pending_batch:
                triggers += [s for s in self.stack if s['uid'] in old and s.get('trigger_batch') == pending_batch]
                self.trigger_choices = [choice for choice in getattr(self, 'trigger_choices', []) if choice.get('trigger_batch') != pending_batch]
            for s in triggers:
                s['kind'] = 'trigger'
                s['trigger_batch'] = batch_id
            if self.choice and self.choice['kind'] in ('counter_target', 'attachment_target'):
                self.choice['trigger_batch'] = batch_id
            turn_order = self.living()
            turn_order.sort(key=lambda owner:(owner-self.active)%len(self.players))
            ordered = []
            for owner in turn_order:
                batch = sorted((s for s in triggers if s['owner'] == owner), key=self.trigger_key)
                ordered.extend(batch)
                if len(batch) > 1 and not getattr(self, 'auto_order', {}).get(str(owner), True):
                    self.__dict__.setdefault('trigger_choices', []).append(dict(
                        owner=owner, kind='trigger_order', trigger_batch=batch_id, uids=[s['uid'] for s in reversed(batch)]))
            self.stack = [s for s in self.stack if s not in triggers]+ordered
        self._next_trigger_choice()
        if action in ('cast', 'ability', 'consume', 'equip_gear') and primary:
            self.submission_priority = dict(owner=i, hold=bool(data.get('hold_priority', False)))
        self._finish_submission_priority()
        self.decision_serial = getattr(self, 'decision_serial', 0)+1

    def _finish_submission_priority(self):
        if not self.choice and getattr(self, 'submission_priority', None):
            submission = self.submission_priority
            self.submission_priority = None
            owner = submission['owner']
            if self.players[owner]['alive']:
                self.priority = owner if submission['hold'] else self.next_player(owner)
                self.passes = 0 if submission['hold'] else 1

    def _next_trigger_choice(self):
        while not self.choice and getattr(self, 'trigger_choices', []):
            choice = self.trigger_choices.pop(0)
            present = {s['uid'] for s in self.stack}
            choice['uids'] = [uid for uid in choice['uids'] if uid in present]
            if self.players[choice['owner']]['alive'] and len(choice['uids']) > 1:
                self.choice = choice
                self.priority = choice['owner']

    def meaningful_response(self, i):
        """Mana-only abilities don't stop auto-pass. Include reachable mana first."""
        if self.has_legal_response(i, meaningful=True):
            return True
        from .battle import RuleError
        p = self.players[i]
        # Above the largest payable action cost, extra mana cannot create a new
        # response. Capping only the search key also handles repeatable generators.
        costs = [c['cost'] for c in p['hand']]
        costs += [a.get('cost', 0) for c in p['board'] for a in c.get('abilities', [])]
        cap = max([4+p['tax'], *costs])+10
        initial = copy.deepcopy(self)
        for c in initial.players[i]['board']:
            if c['effect'] == 'mana' and not c.get('abilities') and initial.attack_ready(c):
                initial._action(i, 'ability', uid=c['uid'])
        if initial.has_legal_response(i, meaningful=True):
            return True
        frontier, seen = [initial], set()
        while frontier:
            state = frontier.pop()
            player = state.players[i]
            key = (tuple(sorted((color,min(cap,n)) for color,n in player['mana'].items())),
                   min(cap,player['temporary']), player['hp'],
                   tuple((c['uid'],c['tapped']) for c in player['board']),
                   tuple(c['uid'] for c in player['hand']))
            if key in seen:
                continue
            seen.add(key)
            for c in player['board']:
                options = []
                for index,spec in enumerate(c.get('abilities', [])):
                    if spec['effect'] == 'mana' and not spec.get('target') and not spec.get('extra_effects'):
                        options.append(dict(uid=c['uid'],ability=index))
                for option in options:
                    trial = copy.deepcopy(state)
                    try:
                        trial._action(i, 'ability', **option)
                    except RuleError:
                        continue
                    if trial.has_legal_response(i, meaningful=True):
                        return True
                    frontier.append(trial)
        return False


class PrioritySession:
    def priority_control(self, member, action, data):
        from .battle import RuleError
        preferences(member)
        b = self.battle
        seat = member.get('seat', 0)
        if action in ('auto', 'respond', 'hold_priority', 'resume_auto', 'pass_once', 'priority_settings', 'phase_stop'):
            if self.stage != 'battle' or b.finished:
                raise RuleError('Priority controls are available during battle.')
            if action == 'phase_stop':
                phase, side = data.get('phase'), data.get('side')
                if phase not in PHASES or side not in ('own', 'opponent'):
                    raise RuleError('Choose a phase and turn owner.')
                stops = member['phase_stops']
                old = next((x for x in stops if x['phase'] == phase and x['side'] == side), None)
                if old:
                    stops.remove(old)
                else:
                    stops.append(dict(phase=phase, side=side, repeat=bool(data.get('repeat'))))
            elif action == 'priority_settings':
                for key in ('auto_advance', 'auto_order'):
                    if key in data:
                        member[key] = bool(data[key])
            elif action == 'hold_priority':
                member['hold_priority'] = bool(data.get('enabled'))
                if member['hold_priority']:
                    member['auto'] = False
            elif action == 'respond':
                member['auto'] = False
            elif action == 'pass_once':
                if member['auto']:
                    raise RuleError('Pause auto-pass before passing once.')
                b.action(seat, 'pass')
            else:
                enabled = action == 'resume_auto' or bool(data.get('enabled'))
                member['auto'] = enabled
                if enabled:
                    member['hold_priority'] = False
                    if self.response_checkpoint(b, member):
                        if not b.stack and seat == b.active and b.phase in ('main', 'main2', 'combat_end'):
                            transition = {'main':'enter_combat', 'main2':'end_turn', 'combat_end':'end_combat'}[b.phase]
                            b.action(seat, transition)
                            self.after_phase_action(member, transition)
                        else:
                            b.action(seat, 'pass')
            # Preferences never refresh the multiplayer decision clock.
            if action == 'priority_settings':
                b.auto_order = {str(x.get('seat', 0)):x.get('auto_order', True) for x in self.members}
            self.apply_results()
            return True
        return False

    def response_checkpoint(self, b, member):
        if b.finished or b.choice or b.priority != member.get('seat', -1) or b.phase in ('opening', 'grow', 'blocks'):
            return False
        if not b.stack and b.phase == 'combat':
            return False
        if not b.stack and b.active == member['seat'] and b.phase in ('main', 'main2', 'combat_end'):
            return member['auto_advance']
        return True

    def automation_tick(self, b, member, now):
        preferences(member)
        self.apply_phase_stops(b)
        if (member['auto'] and member['auto_advance'] and not b.choice and not b.stack
                and b.priority == b.active == member['seat'] and b.phase in ('main', 'main2', 'combat_end')):
            action = {'main':'enter_combat', 'main2':'end_turn', 'combat_end':'end_combat'}[b.phase]
            b.action(member['seat'], action)
            self.after_phase_action(member, action)
            self.apply_results()
            return True
        self.refresh_response_window(b, now)
        if member['bot'] or not member['auto'] or not self.response_checkpoint(b, member):
            return False
        if not b.meaningful_response(member['seat']) or now >= self.response_deadline:
            b.action(member['seat'], 'pass')
            self.apply_results()
            return True
        return False

    def after_phase_action(self, member, action):
        hit = self.apply_phase_stops(self.battle)
        if action == 'enter_combat' and member['id'] in hit:
            # A selected stop is the first checkpoint of the new phase, before
            # the active player's implicit pass caused by Enter Combat.
            self.battle.priority = self.battle.active
            self.battle.passes = 0

    def apply_phase_stops(self, b):
        # Stops happen after automatic actions and all mandatory choices.
        hit_members = []
        phase = checkpoint(b.phase)
        stop_key = (b.active, b.players[b.active]['turns'], phase)
        if not b.choice and b.phase not in ('opening', 'grow', 'blocks'):
            for viewer in self.members:
                preferences(viewer)
                side = 'own' if viewer.get('seat') == b.active else 'opponent'
                hit = next((s for s in viewer['phase_stops'] if s['phase'] == phase and s['side'] == side), None)
                if hit and viewer.get('last_phase_stop') != stop_key and viewer.get('last_phase_stop') != list(stop_key):
                    viewer['last_phase_stop'] = stop_key
                    viewer['auto'] = False
                    hit_members.append(viewer['id'])
                    if not hit['repeat']:
                        viewer['phase_stops'].remove(hit)
        return hit_members

    def refresh_response_window(self, b, now):
        key = b.decision_key()
        if getattr(self, 'response_key', None) != key:
            self.response_key = key
            self.response_deadline = now+3

    def priority_view(self, member):
        preferences(member)
        b = self.battle
        # An action response can be read before the next tick. Publish its new
        # deadline atomically; further polls of the same decision retain it.
        self.refresh_response_window(b, time.time())
        return dict(server_now=time.time(), deadline=getattr(self, 'response_deadline', None) if member['auto'] and self.response_checkpoint(b, member) else None,
                    auto=member['auto'], hold=member['hold_priority'], auto_advance=member['auto_advance'],
                    auto_order=member['auto_order'], stops=copy.deepcopy(member['phase_stops']))
