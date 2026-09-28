"""Structured spell effects for expansion cards."""


class SpellRules:
    def spell_definition(self, name):
        return next((c.get('spell') for c in self.run.pool['cards'] if c['name'] == name), None)

    def spell_targets(self, definition, side):
        foe = self.opponent(side)
        kind = definition.get('target')
        if kind == 'friendly':
            return list(side.board)
        if kind == 'enemy':
            return list(foe.board)
        if kind == 'any':
            return [side, foe] + side.board + foe.board
        return []

    def resolve_structured_spell(self, card, side, target, definition):
        foe = self.opponent(side)
        bonus = getattr(card, 'upgrade_level', int(card.upgraded))
        enemy_bonus = self.damage_spell_bonus(side) if any(e['effect'] in ('damage', 'area_damage') for e in definition['effects']) else 0
        for effect in definition['effects']:
            kind = effect['effect']
            if not self.condition_met(effect.get('condition'), side, card):
                continue
            amount = self.effect_amount(effect, side, card, bonus)
            if self.identity_effect(effect, side, card, target, bonus):
                continue
            if kind == 'tokens':
                self.tokens(side, amount)
            elif kind == 'heal':
                self.heal(side, amount)
            elif kind == 'draw':
                self.draw(side, amount, effect=True)
            elif kind == 'armor':
                side.armor += amount
            elif kind == 'drain':
                foe.hp -= amount
                self.heal(side, amount)
            elif kind == 'damage':
                self.spell_damage(side, target if target is not None else foe, amount, enemy_bonus)
            elif kind == 'area_damage':
                for creature in list(foe.board):
                    self.spell_damage(side, creature, amount, enemy_bonus)
            elif kind == 'buff':
                # These effects only target creatures and last until turn end.
                if target in side.board or target in foe.board:
                    power = effect.get('power', 0) + bonus
                    target.attack += power; target.temp_attack += power
                    target.max_health += amount; target.current_health += amount; target.temp_health += amount
            elif kind == 'team_buff':
                for creature in list(side.board):
                    creature.attack += amount; creature.temp_attack += amount
                    creature.max_health += amount; creature.current_health += amount; creature.temp_health += amount
            elif kind == 'blink':
                if target in side.board:
                    self.return_unit(side, target, blink=True, actor=side)
            elif kind == 'bounce':
                if target in foe.board:
                    self.return_unit(foe, target, actor=side)
            elif kind == 'destroy':
                if target in foe.board:
                    target.current_health = 0
            elif kind == 'recall':
                for _ in range(amount):
                    creature = max((c for c in side.discard if c.is_creature), key=lambda c:c.mana_cost, default=None)
                    if creature:
                        side.discard.remove(creature); side.hand.append(creature)
            elif kind == 'search':
                self.search_lands(side, amount)
            elif kind == 'ramp':
                self.search_lands(side, amount)
            elif kind == 'morph':
                self.morph(side, target, effect['mutation'], amount)
            elif kind == 'morph_board':
                self.morph_board(side, effect.get('selection', 'friendly'), effect['mutation'], amount)
            elif kind == 'blink_board':
                for creature in list(side.board):
                    if creature in side.board and not creature.token:
                        self.return_unit(side, creature, blink=True, actor=side)
        self.finish_spell(side, card)
        self.cleanup_deaths()
        self.check_result()
