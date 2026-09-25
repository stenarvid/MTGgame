"""Shared mechanics for conditional, specialized card designs."""
from models import Card


class IdentityRules:
    def has_keyword(self, card, keyword):
        legacy = {'Citadel Recruit': ['guard'], 'Thorn Sentinel': ['trample'], 'Ember Duelist': ['haste']}
        return keyword in getattr(card, 'keywords', []) or keyword in legacy.get(card.name, [])

    def condition_met(self, condition, side, source=None):
        if not condition:
            return True
        foe = self.opponent(side)
        checks = {
            'outnumbered': len(side.board) < len(foe.board),
            'low_life': side.hp <= side.max_hp // 2,
            'has_tokens': any(c.token for c in side.board),
            'no_tokens': not any(c.token for c in side.board),
            'wide_board': len(side.board) >= 4,
            'large_creature': any(c.attack >= 4 for c in side.board),
            'six_lands': len(side.lands) >= 6,
            'empty_hand': len(side.hand) <= 1,
            'graveyard_full': sum(c.is_creature for c in side.discard) >= 3,
            'solo_attack': len(self.attackers) == 1 and source in self.attackers,
            'second_spell': getattr(side, 'spells_this_turn', 0) >= 2,
        }
        return checks.get(condition, False)

    def effect_amount(self, effect, side, source=None, bonus=0):
        scale = effect.get('scale')
        values = {'tokens': sum(c.token for c in side.board), 'lands': len(side.lands),
                  'graveyard': sum(c.is_creature for c in side.discard),
                  'attackers': sum(c in side.board for c in self.attackers),
                  'spells': getattr(side, 'spells_this_turn', 0),
                  'source_power': max(0, source.attack) if source else 0,
                  'missing_life': max(0, side.max_hp - side.hp)}
        extra = min(effect.get('cap', 3), values.get(scale, 0)) if scale else 0
        return effect.get('amount', 0) + extra + bonus

    def matching_units(self, side, selection):
        return [c for c in side.board if selection == 'all' or
                (selection == 'tokens' and c.token) or
                (selection == 'nontokens' and not c.token) or
                (selection == 'attacking' and c in self.attackers) or
                (selection == 'small' and c.attack <= 2)]

    def custom_tokens(self, side, amount, template):
        for _ in range(amount * self.token_multiplier(side)):
            token = Card(template['name'], 'Cyber Fighter', template.get('color', 'W'), 0,
                         template['attack'], template['health'], template.get('text', ''))
            token.keywords = list(template.get('keywords', []))
            token.token = True
            self.summon(side, token)
        if side is self.player and self.passive == 'Valkyrie Grace':
            # One extra Recruit per creation event, including specialized tokens.
            self.tokens(side, 0)

    def identity_effect(self, effect, side, source=None, target=None, bonus=0):
        """Return True for a handled specialty effect; originals keep their paths."""
        if not self.condition_met(effect.get('condition'), side, source):
            return True
        kind = effect['effect']; amount = self.effect_amount(effect, side, source, bonus)
        foe = self.opponent(side)
        if kind == 'custom_tokens':
            self.custom_tokens(side, amount, effect['token'])
        elif kind == 'loot':
            self.draw(side, amount, effect=True)
            if side.hand:
                discarded = max(side.hand, key=lambda c:c.mana_cost)
                side.hand.remove(discarded); side.discard.append(discarded.fresh())
                self.note(f'{side.name} discards {discarded.name} (highest mana value).')
        elif kind == 'mill':
            for _ in range(min(amount, len(side.deck))):
                side.discard.append(side.deck.pop())
        elif kind == 'recover_spell':
            for _ in range(amount):
                card = max((c for c in side.discard if c.card_type == 'Instant Spell'),key=lambda c:c.mana_cost,default=None)
                if card:
                    side.discard.remove(card); side.hand.append(card)
        elif kind == 'reanimate':
            candidates = [c for c in side.discard if c.is_creature and c.mana_cost <= effect.get('max_cost', 3)]
            for card in sorted(candidates, key=lambda c:-c.mana_cost)[:amount]:
                side.discard.remove(card)
                self.summon(side, card)
                self.enter_effect(side, card, foe.board[0] if foe.board else None)
        elif kind == 'armor':
            side.armor += amount
        elif kind == 'pay_life':
            side.hp -= amount
        elif kind == 'buff_group':
            for card in self.matching_units(side, effect.get('selection', 'all')):
                power = effect.get('power', amount) + (bonus if 'power' in effect else 0)
                card.attack += power; card.max_health += amount; card.current_health += amount
                if not effect.get('permanent'):
                    card.temp_attack += power; card.temp_health += amount
        elif kind == 'grant_keyword':
            for card in ([target] if target in side.board else self.matching_units(side, effect.get('selection','all'))):
                if not hasattr(card, 'keywords'):
                    card.keywords = []
                keyword = effect['keyword']
                if keyword not in card.keywords:
                    card.keywords.append(keyword)
                if keyword == 'haste':
                    card.sick = False
        elif kind == 'untap_lands':
            for land in [c for c in side.lands if c.tapped][:amount]:
                land.tapped = False
        elif kind == 'freeze':
            units = [target] if target in foe.board else sorted(foe.board, key=lambda c:-c.attack)[:amount]
            for card in units:
                card.tapped = True
                card.frozen = True
        elif kind == 'sacrifice':
            if target in side.board:
                target.current_health = 0
                self.cleanup_deaths()
        elif kind == 'power_damage':
            if target in side.board:
                self.spell_damage(side, foe, max(0, target.attack) + bonus)
        else:
            return False
        return True
