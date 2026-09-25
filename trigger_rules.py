"""Data-driven triggered abilities for the archetype expansion."""
from models import Card


class TriggerRules:
    def ability(self, card):
        return next((c.get('trigger') for c in self.run.pool['cards'] if c['name'] == card.name), None)

    def queue_trigger(self, source, side, ability, target=None):
        from engine import StackItem
        if not self.condition_met(ability.get('condition'), side, source):
            return
        if ability.get('once_per_turn'):
            serial = getattr(self, 'turn_serial', 0)
            if getattr(source, 'trigger_turn', None) == serial:
                return
            source.trigger_turn = serial
        if not self.stack and self.phase != 'RESPONSE':
            self.return_phase = self.phase
        item = StackItem(source, side, target)
        item.ability = ability.copy()
        self.stack.append(item)
        self.phase = 'RESPONSE'
        self.note(f'{source.name}: {ability["event"].replace("_", " ")} ability triggers.')

    def emit_trigger(self, event, side, subject=None, sources=None):
        for source in list(side.board) if sources is None else sources:
            ability = self.ability(source)
            if not ability or ability['event'] != event:
                continue
            if event in ('enter', 'dies') and source is not subject:
                continue
            if event in ('ally_enters', 'ally_dies') and source is subject:
                continue
            if event == 'ally_enters' and subject.token:
                continue
            self.queue_trigger(source, side, ability)

    def copy_targets(self, source):
        return [c for c in self.combat_side.board if c is not source and not c.token]

    def attack_triggers(self, side):
        self.attack_choices = []
        self.phase = 'DECLARE_BLOCKS' if side is self.player else 'BLOCK'
        for source in list(self.attackers):
            source.tapped = not self.has_keyword(source, 'vigilance')
            ability = self.ability(source)
            if not ability or ability['event'] != 'attack':
                continue
            if ability['effect'] == 'copy':
                targets = self.copy_targets(source)
                if not targets:
                    continue
                if side is self.player:
                    self.attack_choices.append(source)
                else:
                    self.queue_trigger(source, side, ability, max(targets, key=lambda c:c.attack))
            else:
                self.queue_trigger(source, side, ability)
        if self.attack_choices:
            self.phase = 'ATTACK_TARGET'
        elif self.stack:
            self.phase = 'RESPONSE'
        elif side is self.player:
            self.declare_enemy_blocks()

    def choose_attack_copy(self, target):
        if self.phase != 'ATTACK_TARGET' or not self.attack_choices:
            return False
        source = self.attack_choices[0]
        if target is not None and target not in self.copy_targets(source):
            return False
        self.attack_choices.pop(0)
        # Preserve the continuation even when this is the first queued trigger.
        self.phase = 'RESPONSE' if self.stack else 'DECLARE_BLOCKS'
        if target is not None:
            self.queue_trigger(source, self.player, self.ability(source), target)
        if self.attack_choices:
            self.phase = 'ATTACK_TARGET'
        elif self.stack:
            self.phase = 'RESPONSE'
        else:
            self.declare_enemy_blocks()
        return True

    def resolve_trigger(self, item):
        if item.ability['effect'] == 'copy' and (item.target not in item.side.board or item.target.token):
            self.note('Copy ability fizzles: target has left the battlefield.')
            return
        self.note(f'{item.card.name}: {item.ability["effect"].replace("_", " ")} ability resolves.')
        self.apply_trigger_effect(item, item.ability)
        for extra in item.ability.get('then', []):
            self.apply_trigger_effect(item, extra)
        self.cleanup_deaths()
        self.check_result()

    def apply_trigger_effect(self, item, ability):
        source, side, target = item.card, item.side, item.target
        if not self.condition_met(ability.get('condition'), side, source):
            return
        effect = ability['effect']; amount = self.effect_amount(ability, side, source)
        if self.identity_effect(ability, side, source, target):
            return
        foe = self.opponent(side)
        if effect == 'copy':
            if target not in side.board or target.token:
                self.note('Copy ability fizzles: target has left the battlefield.')
                return
            for _ in range(self.token_multiplier(side)):
                copy = self.base_card(target)
                copy.token = True
                copy.exile_at_end = ability.get('copy_mode') != 'permanent'
                if ability.get('copy_mode') == 'small':
                    copy.attack = copy.max_health = copy.current_health = 1
                if self.summon(side, copy):
                    copy.tapped = True
                    self.attackers.append(copy)
                    self.enter_effect(side, copy, foe.board[0] if foe.board else None)
        elif effect == 'tokens':
            self.tokens(side, amount)
        elif effect == 'draw':
            self.draw(side, amount, effect=True)
        elif effect == 'heal':
            self.heal(side, amount)
        elif effect == 'damage':
            self.damage(foe, amount)
        elif effect == 'drain':
            foe.hp -= amount
            self.heal(side, amount)
        elif effect == 'recall':
            for _ in range(amount):
                card = max((c for c in side.discard if c.is_creature),key=lambda c:c.mana_cost,default=None)
                if card:
                    side.discard.remove(card); side.hand.append(card)
        elif effect == 'search':
            self.search_lands(side, amount)
        elif effect == 'land':
            for card in [c for c in side.deck if c.card_type == 'Land'][:amount]:
                side.deck.remove(card)
                card.tapped = True
                side.lands.append(card)
        elif effect == 'team_buff':
            for card in side.board:
                card.attack += amount; card.max_health += amount; card.current_health += amount
                card.temp_attack += amount; card.temp_health += amount
        elif effect == 'self_buff' and source in side.board:
            source.attack += amount; source.max_health += amount; source.current_health += amount
