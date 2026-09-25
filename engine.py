"""Run progression and MTG-inspired combat with colored mana and response priority."""
import json
import random
from pathlib import Path

from trigger_rules import TriggerRules
from spell_rules import SpellRules
from identity_rules import IdentityRules
from models import Card, color_starters, complete_node, generate_spire_map


UNLOCKS = [
    dict(name='Mind Vault', color='U', archetype='Card Advantage',
         desc='Draw an extra card each turn. No hand size limit.', stat='cards_drawn', goal=15),
    dict(name='Endless Horde', color='B', archetype='Graveyard',
         desc='Your non-token creatures return to hand with 1 toughness when they die.', stat='kills', goal=10),
    dict(name='Overcharge Core', color='R', archetype='Spells',
         desc='Spells cost 1 less mana (minimum 1).', stat='spell_damage', goal=50),
    dict(name='Radiant Foundry', color='W', archetype='Token',
         desc='Your creature tokens enter with +1/+1.', stat='tokens_created', goal=20),
    dict(name='Rift Sanctuary', color='U', archetype='Blink',
         desc='Whenever you blink or return a creature, heal your hero for 2.', stat='blink_returns', goal=8),
    dict(name='Graveplate', color='B', archetype='Graveyard',
         desc='Whenever a friendly creature dies, gain 1 armor.', stat='friendly_deaths', goal=15),
    dict(name='Runic Ward', color='R', archetype='Spells',
         desc='Whenever you cast a noncreature spell, gain 1 armor.', stat='spells_cast', goal=20),
    dict(name='Living Roots', color='G', archetype='Ramp',
         desc='Whenever you play a land, heal your hero for 2.', stat='lands_played', goal=10),
]


class Progress:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).resolve().parent / 'save.json'
        self.unlocked = set()
        self.error = ''
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(data, dict) and isinstance(data.get('unlocked'), list):
                self.unlocked = {name for name in data['unlocked'] if isinstance(name, str)}
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self.error = 'Could not read achievements; this session starts with default unlocks.'

    def check(self, stats):
        new = [u['name'] for u in UNLOCKS
               if stats.get(u['stat'], 0) >= u['goal'] and u['name'] not in self.unlocked]
        if new:
            self.unlocked.update(new)
            try:
                temp = self.path.with_suffix('.tmp')
                temp.write_text(json.dumps({'unlocked': sorted(self.unlocked)}, indent=2), encoding='utf-8')
                temp.replace(self.path)
            except OSError:
                self.error = 'Achievements unlocked for this session, but could not be saved.'
        return new


class Run:
    def __init__(self, commander, pool):
        self.commander, self.pool = commander, pool
        self.deck = []
        for color, archetype in zip(commander.colors, commander.archetypes):
            self.deck.extend(color_starters(pool, color, archetype))
        self.hp = self.max_hp = 30
        self.gold = 35
        self.relics = []
        self.stats = dict(cards_drawn=0, kills=0, spell_damage=0)
        self.grid = generate_spire_map()
        self.node = None
        self.shop = []
        self.choices = []
        self.won = False
        self.rewards = []
        self.reward_pending = False
        self.service_used = False

    def record(self, stat, amount=1):
        self.stats[stat] = self.stats.get(stat, 0) + amount

    def enter(self, node):
        if self.node is not None or self.reward_pending or not node.available or node.visited:
            return False
        self.node = node
        self.service_used = False
        if node.node_type == 'Merchant':
            self.shop = [dict(card=c, price=25 + 5 * c['cost'], sold=False)
                         for c in random.sample(self.card_choices(), 5)]
        if node.node_type == 'Treasure':
            remaining = [r for r in self.pool['relics'] if r not in self.relics]
            self.choices = random.sample(remaining, min(3, len(remaining)))
        return True

    def finish(self):
        if self.node is None:
            return False
        node = self.node
        if not complete_node(self.grid, node):
            return False
        self.won = node.node_type == 'Boss'
        self.node = None
        return True

    def buy(self, index):
        if self.node is None or self.node.node_type != 'Merchant' or not 0 <= index < len(self.shop):
            return False
        item = self.shop[index]
        if item['sold'] or self.gold < item['price']:
            return False
        self.gold -= item['price']
        self.deck.append(Card.from_dict(item['card']))
        item['sold'] = True
        return True

    def card_choices(self):
        return [c for c in self.pool['cards'] if c['color'] in self.commander.colors]

    def offer_rewards(self):
        self.rewards = random.sample(self.card_choices(), 3)
        self.reward_pending = True

    def take_card_reward(self, index=None):
        if not self.reward_pending or (index is not None and not 0 <= index < len(self.rewards)):
            return False
        if index is not None:
            self.deck.append(Card.from_dict(self.rewards[index]))
        self.reward_pending = False
        self.rewards = []
        return True

    def service(self, card, action):
        if self.node is None or self.service_used or card not in self.deck:
            return False
        merchant = self.node.node_type == 'Merchant'
        if action not in ('upgrade', 'remove') or self.node.node_type not in ('Merchant', 'Rest'):
            return False
        if not merchant and action != 'upgrade':
            return False
        price = 40 if action == 'remove' else 30
        if merchant and self.gold < price:
            return False
        if action == 'remove':
            if len(self.deck) <= 10 or (card.card_type == 'Land' and
                    sum(c.card_type == 'Land' and c.color_code == card.color_code for c in self.deck) <= 2):
                return False
            self.deck.remove(card)
        elif not card.upgrade():
            return False
        if merchant:
            self.gold -= price
        self.service_used = True
        if not merchant:
            self.finish()
        return True

    def rest(self):
        if self.node is None or self.node.node_type != 'Rest':
            return 0
        healed = min(self.max_hp - self.hp, 10)
        self.hp += healed
        self.finish()
        return healed

    def take_relic(self, index):
        if self.node is None or self.node.node_type != 'Treasure':
            return False
        if self.choices:
            self.relics.append(self.choices[index])
        else:
            self.gold += 25
        self.finish()
        return True


class Side:
    def __init__(self, deck, hp, max_hp, name):
        self.name = name
        self.hp, self.max_hp = hp, max_hp
        self.deck = [c.fresh() for c in deck]
        random.shuffle(self.deck)
        self.hand, self.board, self.lands, self.discard = [], [], [], []
        self.mana = 0
        self.colored_mana = dict.fromkeys('WUBRG', 0)
        self.armor = 0
        self.land_played = False
        self.creatures_played = 0
        self.fatigue = 0
        # Two lands start in play. Every other card remains in the draw pile.
        lands = [c for c in self.deck if c.card_type == 'Land']
        opening = []
        for color in dict.fromkeys(c.color_code for c in lands):
            opening.append(next(c for c in lands if c.color_code == color))
        opening = opening[:2]
        opening += [c for c in lands if c not in opening][:2 - len(opening)]
        for card in opening:
            self.deck.remove(card)
            self.lands.append(card)


class StackItem:
    def __init__(self, card, side, target):
        self.card, self.side, self.target = card, side, target


ENCOUNTERS = {
    'W': ('Dawn Marshal', 'Mustering: summons a Recruit every second turn (every turn for elites).'),
    'U': ('Tide Archivist', 'Study: draws an extra card on even turns.'),
    'B': ('Crypt Matron', 'Soul feast: heals 1 HP whenever any creature dies.'),
    'R': ('Ember Duelist', 'Ignition: the first damage spell each turn deals +1 damage.'),
    'G': ('Grove Warden', 'Cultivate: the first creature played each turn gets +1/+1.'),
}


class Battle(TriggerRules, SpellRules, IdentityRules):
    def __init__(self, run):
        self.run = run
        self.relics = {r['name'] for r in run.relics}
        self.passive = run.commander.passive_name
        self.active = run.commander.active_name
        self.player = Side(run.deck, run.hp, run.max_hp, run.commander.name)
        row = run.node.row if run.node else 0
        kind = run.node.node_type if run.node else 'Combat'
        elite, boss = kind == 'Elite', kind == 'Boss'
        enemy_hp = 12 + row * 2 + (6 if elite else 12 if boss else 0)
        colors = ['U', 'R'] if boss else random.sample(list('WUBRG'), 2)
        self.theme = colors[0]
        self.elite, self.boss = elite, boss
        self.boss_enraged = False
        self.enemy_turn_number = 0
        self.enemy_damage_bonus_used = False
        self.intent = ('Sovereign: alternates extra draws and 1 hero damage; at half HP, summons two Guards and empowers its board.'
                       if boss else ENCOUNTERS[self.theme][1])
        archetypes = dict(W='Token', U='Blink', B='Graveyard', R='Spells', G='Ramp')
        enemy_deck = sum((color_starters(run.pool, c, archetypes[c]) for c in colors), [])
        enemy_deck += [Card.from_dict(c) for c in run.pool['cards']
                       if c['color'] in colors and c['name'] in ('Dawn Medic', 'Null Sigil', 'Soul Collector',
                                                               'Ember Duelist', 'Thorn Sentinel')]
        # Every opponent has a creature-heavy deck and its own mana/hand.
        for i in range(4):
            enemy_deck.append(Card('Spire Guardian' if boss else 'Spire Raider',
                                   'Cyber Fighter', colors[0], 2,
                                   2 + int(boss), 2 + int(elite or boss)))
        self.enemy = Side(enemy_deck, enemy_hp, enemy_hp,
                          'Spire Sovereign' if boss else ('Elite ' if elite else '') + ENCOUNTERS[self.theme][0])
        self.phase = 'MULLIGAN'
        self.return_phase = 'MAIN'
        self.stack = []
        self.enemy_queue = []
        self.blocked = set()
        self.combat_side = self.player
        self.mulligan_used = False
        self.events = []
        self.event_serial = 0
        self.turn = 0
        self.active_used = False
        self.attackers = []
        self.assignments = {}
        self.result = None
        self.settled = False
        self.log = []
        if 'Valkyrie Plating' in self.relics:
            self.player.armor = 5
        if 'Starlight Pendant' in self.relics:
            self.heal(self.player, 3)
        self.draw(self.player, 5)
        self.draw(self.enemy, 5)
        self.note('Choose cards to replace once for free, or keep your opening hand.')

    def mulligan(self, cards):
        if self.phase != 'MULLIGAN' or self.mulligan_used:
            return False
        selected = [c for c in self.player.hand if c in cards]
        if not selected:
            return False
        self.mulligan_used = True
        for c in selected:
            self.player.hand.remove(c)
        self.draw(self.player, len(selected))
        self.player.deck.extend(selected)
        random.shuffle(self.player.deck)
        self.note(f'Replaced {len(selected)} opening cards. Keep this hand to begin.')
        return True

    def keep_hand(self):
        if self.phase != 'MULLIGAN':
            return False
        self.phase = 'MAIN'
        self.start_turn(self.player)
        if 'Chronosphere Core' in self.relics:
            self.player.mana += 1
        return True

    def note(self, text):
        self.log.append(text)
        self.log = self.log[-300:]

    def event(self, target, label, kind='damage'):
        self.event_serial += 1
        self.events.append(dict(serial=self.event_serial, target=target, label=label, kind=kind))
        self.events = self.events[-100:]

    def opponent(self, side):
        return self.enemy if side is self.player else self.player

    def heal(self, target, amount):
        maximum = target.max_hp if isinstance(target, Side) else target.max_health
        attr = 'hp' if isinstance(target, Side) else 'current_health'
        setattr(target, attr, min(maximum, getattr(target, attr) + amount))
        self.event(target, f'+{amount}', 'heal')

    def damage(self, target, amount):
        amount = max(0, amount)
        self.event(target, f'-{amount}')
        if isinstance(target, Side):
            absorbed = min(target.armor, amount)
            target.armor -= absorbed
            target.hp -= amount - absorbed
            return amount - absorbed
        dealt = min(max(0, target.current_health), amount)
        target.current_health -= amount
        return dealt

    def draw(self, side, count=1, effect=False):
        if effect and side is self.player and 'Aether Prism' in self.relics:
            count += 1
        for _ in range(count):
            if not side.deck and side.discard:
                side.deck = [c.fresh() for c in side.discard]
                side.discard.clear()
                random.shuffle(side.deck)
            if not side.deck:
                side.fatigue += 1
                self.damage(side, side.fatigue)
                self.note(f'{side.name}: empty deck, {side.fatigue} fatigue damage.')
                continue
            side.hand.append(side.deck.pop())
            if side is self.player:
                self.run.stats['cards_drawn'] += 1

    def start_turn(self, side):
        self.enemy_damage_bonus_used = False
        self.turn_serial = getattr(self, 'turn_serial', 0) + 1
        for combatant in (self.player, self.enemy):
            combatant.spells_this_turn = 0
        side.land_played = False
        side.creatures_played = 0
        side.mana = 0
        side.colored_mana = dict.fromkeys('WUBRG', 0)
        for card in side.board + side.lands:
            if getattr(card, 'frozen', False):
                card.frozen = False
            else:
                card.tapped = False
            card.sick = False
        side.colored_mana['G'] += sum(2 for c in side.board if c.name == 'Titan Overseer')
        if side is self.player:
            self.turn += 1
        else:
            self.enemy_turn_number += 1
            self.enemy_damage_bonus_used = False
            if self.boss:
                if self.enemy_turn_number % 2:
                    self.draw(side, effect=True)
                    self.note('Sovereign studies the stars: draws an extra card.')
                else:
                    self.damage(self.player, 1)
                    self.note('Sovereign starfall: 1 damage to your hero.')
            elif self.theme == 'W' and (self.elite or self.enemy_turn_number % 2 == 0):
                self.tokens(side, 1)
                self.note('Dawn Marshal musters a Recruit.')
            elif self.theme == 'U' and self.enemy_turn_number % 2 == 0:
                self.draw(side, effect=True)
                self.note('Tide Archivist draws an extra card.')
        self.draw(side, 2 if side is self.player and self.passive == 'Mind Vault' else 1)
        self.check_result()

    def available_mana(self, side):
        return side.mana + sum(side.colored_mana.values()) + sum(not c.tapped for c in side.lands)

    def cost(self, side, card):
        cost = card.mana_cost
        if side is self.player:
            if card.is_creature and 'Titan Gauntlet' in self.relics:
                cost = max(1, cost - 1)
            if card.card_type == 'Instant Spell' and self.passive == 'Overcharge Core':
                cost = max(1, cost - 1)
        return max(cost, sum(card.pips.values()))

    def payment_plan(self, side, card):
        pool = dict(side.colored_mana, C=side.mana)
        lands = [c for c in side.lands if not c.tapped]
        tapped = []
        for color, required in card.pips.items():
            for _ in range(required):
                if pool.get(color, 0):
                    pool[color] -= 1
                else:
                    land = next((c for c in lands if c.color_code == color), None)
                    if land is None:
                        return None
                    lands.remove(land)
                    tapped.append(land)
        generic = self.cost(side, card) - sum(card.pips.values())
        for color in 'CWUBRG':
            used = min(generic, pool.get(color, 0))
            pool[color] -= used
            generic -= used
        if generic > len(lands):
            return None
        tapped += lands[:generic]
        return pool, tapped

    def can_pay(self, side, card):
        return self.payment_plan(side, card) is not None

    def pay(self, side, card):
        plan = self.payment_plan(side, card)
        if plan is None:
            return False
        pool, tapped = plan
        side.mana = pool.pop('C')
        side.colored_mana = pool
        for land in tapped:
            land.tapped = True
        return True

    def mana_summary(self, side):
        counts = {c: side.colored_mana[c] + sum(not l.tapped and l.color_code == c for l in side.lands) for c in 'WUBRG'}
        return ' '.join(f'{c}:{n}' for c, n in counts.items() if n) + (f' C:{side.mana}' if side.mana else '') or '0'

    def search_lands(self, side, count):
        found = [c for c in side.deck if c.card_type == 'Land'][:count]
        for card in found:
            side.deck.remove(card)
            side.hand.append(card)
        random.shuffle(side.deck)
        self.note(f'{side.name} found {len(found)} land(s).')

    def summon(self, side, card, played=False):
        card.tapped = False
        card.sick = not self.has_keyword(card, 'haste')
        for other in side.board:
            if other.name == 'Legion Vanguard':
                card.attack += 1
                card.max_health += 1
                card.current_health += 1
        if side is self.player and played:
            if self.passive == 'Titan Growth' and side.creatures_played == 0:
                card.attack += 2
                card.max_health += 2
                card.current_health += 2
        if side is self.enemy and 'Void Core' in self.relics:
            card.attack = max(0, card.attack - 1)
        if side is self.enemy and played and self.theme == 'G' and not self.boss and side.creatures_played == 0:
            card.attack += 1
            card.max_health += 1
            card.current_health += 1
        if side is self.player and card.token:
            self.run.record('tokens_created')
            if self.passive == 'Radiant Foundry':
                card.attack += 1
                card.max_health += 1
                card.current_health += 1
        side.board.append(card)
        self.emit_trigger('ally_enters', side, card)
        if played:
            side.creatures_played += 1
        return True

    def token_multiplier(self, side):
        return 2 if side is self.player and self.passive == 'Mirror Legion' else 1

    def tokens(self, side, count):
        if side is self.player and self.passive == 'Valkyrie Grace':
            count += 1
        count *= self.token_multiplier(side)
        for _ in range(count):
            card = Card('Token Recruit', 'Cyber Fighter', 'W', 0, 1, 1)
            card.token = True
            self.summon(side, card)

    def return_unit(self, side, card, blink=False, actor=None):
        actor = actor or self.player
        side.board.remove(card)
        if actor is self.player:
            self.run.record('blink_returns')
            if self.passive == 'Rift Sanctuary':
                self.heal(self.player, 2)
        if not card.token:
            fresh = self.base_card(card)
            if blink:
                self.summon(side, fresh)
                foe = self.opponent(side)
                self.enter_effect(side, fresh, foe.board[0] if foe.board else None)
            else:
                side.hand.append(fresh)
        if actor is self.player and self.passive == 'Aether Flux':
            self.draw(self.player, effect=True)

    def base_card(self, card):
        data = next((c for c in self.run.pool['cards'] if c['name'] == card.name), None)
        fresh = Card.from_dict(data) if data else card.fresh()
        if card.upgraded and not fresh.upgraded:
            fresh.upgrade()
        return fresh

    def enter_effect(self, side, card, target=None):
        self.emit_trigger('enter', side, card)
        foe = self.opponent(side)
        if card.name == 'Phase Shifter' and target in foe.board:
            self.return_unit(foe, target, actor=side)
        elif card.name == 'Dawn Medic':
            self.heal(side, 3)
        elif card.name == 'Tide Scholar':
            self.draw(side, effect=True)

    def damage_spell_bonus(self, side):
        if side is self.enemy and self.theme == 'R' and not self.boss and not self.enemy_damage_bonus_used:
            self.enemy_damage_bonus_used = True
            return 1
        return 0

    def spell_damage(self, side, target, amount, enemy_bonus=0):
        if side is self.player:
            amount += 2 if self.passive == 'Plasma Surge' else 0
            amount *= 2 if 'Plasma Reactor' in self.relics else 1
        else:
            amount += enemy_bonus
        dealt = self.damage(target, amount)
        if side is self.player:
            self.run.stats['spell_damage'] += dealt
            if dealt and 'Shadow Fang' in self.relics:
                self.damage(self.enemy, 1)
                self.heal(self.player, 1)

    def targets(self, name, side=None):
        side = side or self.player
        foe = self.opponent(side)
        definition = self.spell_definition(name)
        if definition:
            return self.spell_targets(definition, side)
        if name == 'Overcharge Bolt' or name == 'Flame Burst':
            return [foe, side] + foe.board + side.board
        if name in ('Aether Warp', 'Radiant Aegis', 'Verdant Surge'):
            return list(side.board)
        if name == 'Null Sigil':
            return [item for item in self.stack if item.side is foe and not hasattr(item, 'ability')]
        if name == 'Phase Shifter':
            return list(foe.board)
        if name == 'Holy Light':
            return [side, foe] + side.board + foe.board
        if name == 'Time Reversal':
            return side.board + foe.board
        if name == 'Soul Reaper':
            return [c for c in side.board + foe.board if c.mana_cost <= 3]
        return []

    def play(self, card, target=None, side=None):
        side = side or self.player
        if self.result or card not in side.hand:
            return False
        main_phase = self.phase in ('MAIN', 'MAIN2') if side is self.player else self.phase == 'ENEMY_MAIN'
        response_phase = self.phase in ('RESPONSE', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE')
        if not main_phase and not (response_phase and card.card_type == 'Instant Spell'):
            return False
        if card.card_type == 'Land':
            if side.land_played:
                self.note('Only one land can be played each turn.')
                return False
            side.hand.remove(card)
            card.tapped = False
            side.lands.append(card)
            side.land_played = True
            self.note(f'{side.name} plays a {card.color_code} land.')
            if side is self.player:
                self.run.record('lands_played')
                if self.passive == 'Living Roots':
                    self.heal(side, 2)
            self.emit_trigger('land', side, card)
            return True
        if not self.can_pay(side, card):
            self.note(f'Need {card.mana_label(self.cost(side, card))}; available mana: {self.mana_summary(side)}.')
            return False
        targets = self.targets(card.name, side)
        definition = self.spell_definition(card.name)
        mandatory = bool(definition and definition.get('target')) or card.name in ('Aether Warp', 'Radiant Aegis', 'Verdant Surge', 'Null Sigil', 'Overcharge Bolt')
        if (targets and target not in targets) or (mandatory and not targets):
            self.note('Choose a valid target first.')
            return False
        supported = {'Phalanx Barrier', 'Aether Warp', 'Siphon Life', 'Overcharge Bolt',
                     "Nature's Bounty", 'Aether Spark', 'Magma Bolt', 'Radiant Aegis',
                     'Null Sigil', 'Grave Recall', 'Cinder Volley', 'Verdant Surge'}
        if not card.is_creature and card.name not in supported and not definition:
            self.note(f'No implemented effect for {card.name}. Card was not spent.')
            return False
        self.pay(side, card)
        side.hand.remove(card)
        if not self.stack:
            self.return_phase = self.phase
        self.stack.append(StackItem(card, side, target))
        self.phase = 'RESPONSE'
        self.note(f'{side.name} casts {card.name}. Response window opens.')
        self.event(side, card.name, 'cast')
        if not card.is_creature:
            side.spells_this_turn = getattr(side, 'spells_this_turn', 0) + 1
            if side is self.player:
                self.run.record('spells_cast')
                if self.passive == 'Runic Ward':
                    side.armor += 1
            self.emit_trigger('spell_cast', side, card)
        for creature in side.board:
            if not card.is_creature and creature.name == 'Spellweaver Pyromancer':
                self.damage(self.opponent(side), 1)
        self.cleanup_deaths()
        self.check_result()
        return True

    def resolve_card(self, item):
        if hasattr(item, 'ability'):
            self.resolve_trigger(item)
            return
        card, side, target = item.card, item.side, item.target
        foe = self.opponent(side)
        bonus = int(card.upgraded)
        if target is not None and target not in self.targets(card.name, side):
            # A creature still enters if its entry-effect target has disappeared.
            if not card.is_creature:
                self.note(f'{card.name} fizzles: target is no longer legal.')
                side.discard.append(self.base_card(card))
                return
            target = None
        self.note(f'{card.name} resolves.')
        definition = self.spell_definition(card.name)
        if definition:
            self.resolve_structured_spell(card, side, target, definition)
            return
        enemy_bonus = self.damage_spell_bonus(side) if card.name in ('Overcharge Bolt', 'Magma Bolt', 'Cinder Volley') else 0
        if card.is_creature:
            self.summon(side, card, played=True)
            self.enter_effect(side, card, target)
        else:
            if card.name == 'Phalanx Barrier':
                self.tokens(side, 2 + bonus)
            elif card.name == 'Aether Warp':
                self.return_unit(side, target, blink=True, actor=side)
                self.draw(side, 1 + bonus, effect=True)
            elif card.name == 'Siphon Life':
                # Loss of life is distinct from damage; armor and damage bonuses do not apply.
                foe.hp -= 2 + bonus
                self.event(foe, f'-{2 + bonus} life')
                self.heal(side, 2 + bonus)
            elif card.name == 'Overcharge Bolt':
                self.spell_damage(side, target, 3 + bonus, enemy_bonus)
            elif card.name == 'Magma Bolt':
                self.spell_damage(side, foe, 2 + bonus, enemy_bonus)
            elif card.name == "Nature's Bounty":
                self.search_lands(side, 2 + bonus)
            elif card.name == 'Aether Spark':
                self.draw(side, 1 + bonus, effect=True)
            elif card.name in ('Radiant Aegis', 'Verdant Surge'):
                power = (0 if card.name == 'Radiant Aegis' else 3) + bonus
                health = 3 + bonus
                target.attack += power
                target.max_health += health
                target.current_health += health
                target.temp_attack += power
                target.temp_health += health
            elif card.name == 'Null Sigil':
                self.stack.remove(target)
                target.side.discard.append(self.base_card(target.card))
                self.note(f'{target.card.name} was countered.')
                if bonus:
                    self.draw(side, effect=True)
            elif card.name == 'Grave Recall':
                for _ in range(1 + bonus):
                    creature = max((c for c in side.discard if c.is_creature), key=lambda c: c.mana_cost, default=None)
                    if creature:
                        side.discard.remove(creature)
                        side.hand.append(creature)
            elif card.name == 'Cinder Volley':
                for creature in list(foe.board):
                    self.spell_damage(side, creature, 1 + bonus, enemy_bonus)
            side.discard.append(self.base_card(card))
        self.cleanup_deaths()
        self.check_result()

    def ai_target(self, card, side):
        definition = self.spell_definition(card.name)
        if definition and definition.get('target') == 'any':
            return self.opponent(side)
        targets = self.targets(card.name, side)
        foe = self.opponent(side)
        if card.name == 'Null Sigil':
            return targets[-1] if targets else None
        if card.name == 'Overcharge Bolt':
            return next((c for c in foe.board if c.current_health <= 3), foe)
        if card.name in ('Aether Warp', 'Radiant Aegis', 'Verdant Surge'):
            return max(targets, key=lambda c: c.attack, default=None)
        return max(targets, key=lambda c: c.attack, default=None)

    def enemy_response(self):
        if self.result:
            return False
        top = self.stack[-1] if self.stack else None
        if top and top.side is self.enemy:
            return False
        for card in list(self.enemy.hand):
            if card.card_type != 'Instant Spell' or not self.can_pay(self.enemy, card):
                continue
            if card.name == 'Null Sigil' and top and not hasattr(top, 'ability'):
                return self.play(card, top, self.enemy)
            if card.name in ('Radiant Aegis', 'Verdant Surge') and self.enemy.board:
                threatened = top.target if top and top.target in self.enemy.board else None
                if threatened or self.phase in ('ATTACK_RESPONSE', 'DEFEND_RESPONSE'):
                    return self.play(card, threatened or self.enemy.board[0], self.enemy)
            if card.name == 'Overcharge Bolt' and (self.player.board or self.player.hp <= 3):
                return self.play(card, self.ai_target(card, self.enemy), self.enemy)
        return False

    def pass_priority(self):
        if self.phase != 'RESPONSE' or self.result:
            return False
        if self.enemy_response():
            return True
        if self.stack:
            item = self.stack.pop()
            self.resolve_card(item)
        if not self.stack and not self.result:
            self.phase = self.return_phase
            if self.phase == 'DECLARE_BLOCKS':
                self.declare_enemy_blocks()
            elif self.phase == 'AFTER_PLAYER_COMBAT':
                self.complete_player_combat()
            elif self.phase == 'AFTER_ENEMY_COMBAT':
                self.begin_player_turn()
            elif self.phase == 'ENEMY_MAIN':
                self.enemy_step()
        return True

    def use_active(self, target=None):
        if self.result or self.phase not in ('MAIN', 'MAIN2') or self.active_used:
            return False
        targets = self.targets(self.active)
        if self.active != 'Wild Growth' and target not in targets:
            self.note('Choose a valid target for your commander ability.')
            return False
        self.active_used = True
        if self.active == 'Holy Light':
            self.heal(target, 3)
        elif self.active == 'Time Reversal':
            owner = self.player if target in self.player.board else self.enemy
            self.return_unit(owner, target)
        elif self.active == 'Soul Reaper':
            target.current_health = 0
        elif self.active == 'Flame Burst':
            self.damage(target, 3)
        elif self.active == 'Wild Growth':
            self.search_lands(self.player, 1)
        self.note(f'Commander uses {self.active}.')
        self.cleanup_deaths()
        self.check_result()
        return True

    def tap_sprite(self, card):
        if (self.phase not in ('MAIN', 'MAIN2', 'RESPONSE', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE') or self.result or card not in self.player.board
                or card.name != 'Grove Sprite' or card.sick or card.tapped):
            return False
        card.tapped = True
        self.player.colored_mana['G'] += 1
        return True

    def cleanup_deaths(self):
        snapshots = {s: list(s.board) for s in (self.player, self.enemy)}
        dead = [(s, c) for s in (self.player, self.enemy) for c in s.board if c.current_health <= 0]
        for side, card in dead:
            self.note(f'{card.name} dies.')
            side.board.remove(card)
            if side is self.enemy:
                self.run.stats['kills'] += 1
            else:
                self.run.record('friendly_deaths')
                if self.passive == 'Graveplate':
                    side.armor += 1
            if not card.token:
                if side is self.player and self.passive == 'Endless Horde':
                    returned = self.base_card(card)
                    returned.max_health = returned.current_health = 1
                    side.hand.append(returned)
                else:
                    side.discard.append(self.base_card(card))
        for side, card in dead:
            self.emit_trigger('dies', side, card, snapshots[side])
            self.emit_trigger('ally_dies', side, card, snapshots[side])
            self.emit_trigger('enemy_dies', self.opponent(side), card, snapshots[self.opponent(side)])
            if self.theme == 'B' and not self.boss:
                self.heal(self.enemy, 1)
            for collector in snapshots[self.opponent(side)]:
                if collector.name == 'Soul Collector':
                    side.hp -= 1
                    self.heal(self.opponent(side), 1)
            if self.passive == 'Shadow Veil':
                self.heal(self.player, 2)
            if card.name == 'Crypt Shambler':
                self.opponent(side).hp -= 1
                self.heal(side, 1)
            if card.name == 'Crypt Ghoul':
                candidates = [c for c in side.discard if c.is_creature]
                if candidates:
                    returned = random.choice(candidates)
                    side.discard.remove(returned)
                    side.hand.append(returned)

    def check_result(self):
        if self.result:
            return self.result
        if self.player.hp <= 0:
            self.result = 'DEFEAT'
        elif self.enemy.hp <= 0:
            self.result = 'VICTORY'
        elif self.boss and not self.boss_enraged and self.enemy.hp <= self.enemy.max_hp // 2:
            self.boss_enraged = True
            for _ in range(2):
                guard = Card('Spire Guardian', 'Cyber Fighter', 'U', 2, 2, 3)
                guard.token = True
                self.summon(self.enemy, guard)
            for c in self.enemy.board:
                c.attack += 1
            self.note('Sovereign ascends! Two Guards enter; all enemy creatures gain +1 attack.')
            self.event(self.enemy, 'ASCENSION', 'cast')
        if self.result:
            self.phase = 'FINISHED'
            self.run.hp = max(0, self.player.hp)
            self.note(self.result.title())
        return self.result

    def damage_plan(self, side, attackers, assignments, blocked=None):
        """Pure simultaneous damage allocation; blocker order is explicit."""
        blocked = set(assignments) if blocked is None else blocked
        foe = self.opponent(side)
        plan = {}
        def hit(target, amount):
            plan[target] = plan.get(target, 0) + max(0, amount)
        for attacker in attackers:
            if attacker not in side.board:
                continue
            blockers = assignments.get(attacker, [])
            if isinstance(blockers, Card):
                blockers = [blockers]
            blockers = [c for c in blockers if c in foe.board]
            remaining = max(0, attacker.attack)
            if not blockers and attacker not in blocked:
                hit(foe, remaining)
                continue
            for i, blocker in enumerate(blockers):
                guard = int(self.has_keyword(blocker, 'guard'))
                lethal = max(0, blocker.current_health) + guard
                assigned = min(remaining, lethal)
                if i == len(blockers) - 1 and not self.has_keyword(attacker, 'trample'):
                    assigned = remaining
                hit(blocker, assigned - guard)
                remaining -= assigned
                hit(attacker, blocker.attack)
            if self.has_keyword(attacker, 'trample'):
                hit(foe, remaining)
        return plan

    def combat_preview(self):
        if self.phase not in ('BLOCK', 'DEFEND_RESPONSE', 'ATTACK_RESPONSE'):
            return None
        blocked = set(self.assignments) if self.phase == 'BLOCK' else self.blocked
        plan = self.damage_plan(self.combat_side, self.attackers, self.assignments, blocked)
        return dict(player_damage=max(0, plan.get(self.player, 0) - self.player.armor),
                    enemy_damage=max(0, plan.get(self.enemy, 0) - self.enemy.armor),
                    deaths=[c for c, damage in plan.items() if isinstance(c, Card) and damage >= c.current_health])

    def resolve_attack(self, side, attackers, assignments, blocked=None):
        for attacker in attackers:
            if not self.has_keyword(attacker, 'vigilance'):
                attacker.tapped = True
        for target, amount in self.damage_plan(side, attackers, assignments, blocked).items():
            self.damage(target, amount)
            self.note(f'{target.name} takes {amount} combat damage.')
        self.cleanup_deaths()
        self.check_result()

    def clear_mana(self):
        for side in (self.player, self.enemy):
            side.mana = 0
            side.colored_mana = dict.fromkeys('WUBRG', 0)

    def end_cleanup(self):
        self.clear_mana()
        for side in (self.player, self.enemy):
            for card in list(side.board):
                if getattr(card, 'exile_at_end', False):
                    side.board.remove(card)
                    self.note(f'{card.name} temporary copy is exiled.')
                    continue
                card.attack -= card.temp_attack
                card.max_health -= card.temp_health
                card.temp_attack = card.temp_health = 0
                card.current_health = card.max_health

    def attack(self, chosen):
        if self.phase != 'MAIN' or self.result:
            return False
        self.clear_mana()
        self.combat_side = self.player
        self.attackers = [c for c in self.player.board if c in chosen and not c.sick and not c.tapped]
        self.assignments = {}
        self.attack_triggers(self.player)
        return True

    def declare_enemy_blocks(self):
        self.attackers = [c for c in self.attackers if c in self.player.board]
        self.assignments = {}
        available = [c for c in self.enemy.board if not c.tapped]
        for attacker in sorted(self.attackers, key=lambda c: c.attack, reverse=True):
            if not self.has_keyword(attacker, 'vigilance'):
                attacker.tapped = True
            if not available:
                continue
            blockers = []
            # Group small defenders to kill a large attacker when possible.
            for blocker in sorted(available, key=lambda c: (-c.attack, c.mana_cost)):
                blockers.append(blocker)
                if sum(c.attack for c in blockers) >= attacker.current_health:
                    break
            if sum(c.attack for c in blockers) < attacker.current_health:
                blockers = [min(available, key=lambda c: c.mana_cost)]
            self.assignments[attacker] = blockers
            for blocker in blockers:
                available.remove(blocker)
            self.note(f'{attacker.name} blocked by ' + ', '.join(c.name for c in blockers))
        self.blocked = set(self.assignments)
        self.phase = 'ATTACK_RESPONSE' if self.attackers else 'MAIN2'
        return True

    def reorder_blocker(self, blocker):
        if self.phase != 'ATTACK_RESPONSE':
            return False
        for blockers in self.assignments.values():
            if blocker in blockers:
                blockers.remove(blocker)
                blockers.append(blocker)
                return True
        return False

    def finish_attack(self):
        if self.phase != 'ATTACK_RESPONSE' or self.result:
            return False
        if self.enemy_response():
            return True
        self.phase = 'AFTER_PLAYER_COMBAT'
        self.resolve_attack(self.player, self.attackers, self.assignments, self.blocked)
        if not self.stack:
            self.complete_player_combat()
        return True

    def complete_player_combat(self):
        self.clear_mana()
        if not self.result:
            self.phase = 'MAIN2'
            self.attackers, self.assignments, self.blocked = [], {}, set()
            self.note('Second main phase: play cards, then end your turn.')
        return True

    def end_turn(self):
        if self.phase != 'MAIN2' or self.result:
            return False
        self.end_cleanup()
        self.enemy_turn()
        return True

    def enemy_turn(self):
        self.phase = 'ENEMY_MAIN'
        self.start_turn(self.enemy)
        self.enemy_queue = sorted(list(self.enemy.hand), key=lambda c: (c.card_type != 'Land', not c.is_creature))
        if not self.result:
            self.enemy_step()

    def enemy_step(self):
        while self.enemy_queue and not self.result:
            card = self.enemy_queue.pop(0)
            if card not in self.enemy.hand or (card.card_type != 'Land' and not self.can_pay(self.enemy, card)):
                continue
            if card.name == 'Null Sigil':
                continue
            if self.play(card, self.ai_target(card, self.enemy), self.enemy) and self.stack:
                return
        if self.result:
            return
        self.clear_mana()
        self.combat_side = self.enemy
        self.attackers = [c for c in self.enemy.board if not c.sick and not c.tapped and c.attack > 0]
        for c in self.attackers:
            c.tapped = not self.has_keyword(c, 'vigilance')
        self.assignments, self.blocked = {}, set()
        self.phase = 'BLOCK'
        self.attack_triggers(self.enemy)
        if not self.attackers and not self.stack:
            self.begin_player_turn()
        else:
            self.note('Enemy attacks. Assign one or more blockers to each attacker, or cast an instant.')

    def assign_blocker(self, attacker, blocker):
        if (self.phase != 'BLOCK' or attacker not in self.attackers or blocker not in self.player.board or blocker.tapped):
            return False
        previous = next((a for a, group in self.assignments.items() if blocker in group), None)
        if previous:
            self.assignments[previous].remove(blocker)
            if not self.assignments[previous]:
                del self.assignments[previous]
        if previous is not attacker:
            self.assignments.setdefault(attacker, []).append(blocker)
            # Enemy attacker chooses damage order: dangerous blockers first.
            self.assignments[attacker].sort(key=lambda c: (-c.attack, c.current_health))
        return True

    def begin_player_turn(self):
        self.end_cleanup()
        self.attackers, self.assignments, self.blocked = [], {}, set()
        if not self.result:
            self.phase = 'MAIN'
            self.start_turn(self.player)

    def finish_blocks(self):
        if self.result or self.phase not in ('BLOCK', 'DEFEND_RESPONSE'):
            return False
        if self.phase == 'BLOCK':
            self.assignments = {a: [c for c in group if c in self.player.board and not c.tapped]
                                for a, group in self.assignments.items() if a in self.enemy.board}
            self.assignments = {a: group for a, group in self.assignments.items() if group}
            self.blocked = set(self.assignments)
            self.phase = 'DEFEND_RESPONSE'
            self.note('Blocks locked. Cast instants or resolve combat damage.')
            return True
        if self.enemy_response():
            return True
        self.phase = 'AFTER_ENEMY_COMBAT'
        self.resolve_attack(self.enemy, self.attackers, self.assignments, self.blocked)
        if not self.result and not self.stack:
            self.begin_player_turn()
        return True

    def collect_reward(self):
        if self.result != 'VICTORY' or self.settled:
            return 0
        self.settled = True
        gold = {'Combat': 20, 'Elite': 35, 'Boss': 60}[self.run.node.node_type]
        self.run.gold += gold
        self.run.finish()
        self.run.offer_rewards()
        return gold

