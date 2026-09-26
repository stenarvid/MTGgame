import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import random
import tempfile
import unittest
from pathlib import Path

from engine import Battle, Progress, Run, Side, UNLOCKS
from models import Card, color_starters, complete_node, generate_procedural_commander, load_game_data


class RulesTests(unittest.TestCase):
    def setUp(self):
        random.seed(7)
        _, self.meta, self.pool = load_game_data()
        self.cmd = generate_procedural_commander(self.meta, [], [],
                                                self.meta['passives'][0], self.meta['actives'][0])
        self.run = Run(self.cmd, self.pool)
        self.run.enter(self.run.grid[0][0])
        self.b = Battle(self.run)
        self.b.keep_hand()
        self.b.enemy.hand = []
        self.b.theme = 'C'
        self.b.player.mana = 100
        self.b.player.colored_mana = dict.fromkeys('WUBRG', 100)

    def card(self, name):
        return Card.from_dict(next(c for c in self.pool['cards'] if c['name'] == name))

    def play(self, name, target=None):
        card = self.card(name)
        self.b.player.hand.append(card)
        self.assertTrue(self.b.play(card, target))
        while self.b.phase == 'RESPONSE':
            self.b.pass_priority()
        return card

    def test_pool_starters_and_preview_are_stable(self):
        self.assertEqual(len(self.pool['cards']), 161)
        first = color_starters(self.pool, 'R', 'Spells')
        self.assertEqual([c.name for c in first], [c.name for c in color_starters(self.pool, 'R', 'Spells')])
        self.assertIn('Spellweaver Pyromancer', [c.name for c in first])
        self.assertEqual(len(color_starters(self.pool, 'P', 'Morph')), len(first))
        self.assertEqual(len(color_starters(self.pool, 'P', 'Morph')), 8)
        self.assertEqual(len(self.run.deck), 16)
        self.assertEqual(self.run.stats['kills'], 0)

    def test_opening_conserves_all_lands_and_cards(self):
        player = self.b.player
        cards = player.deck + player.hand + player.lands
        self.assertEqual(len(cards), len(self.run.deck))
        self.assertEqual(sum(c.card_type == 'Land' for c in cards), 8)
        self.assertEqual(len(player.lands), 2)
        self.assertEqual(len(player.hand), 6)

    def test_lands_persist_one_per_turn_and_untap(self):
        b = self.b
        b.player.mana = 0
        b.player.colored_mana = dict.fromkeys('WUBRG', 0)
        lands = [Card('Land', 'Land', 'W', 0) for _ in range(2)]
        b.player.hand.extend(lands)
        self.assertTrue(b.play(lands[0]))
        self.assertFalse(b.play(lands[1]))
        self.play('Citadel Recruit')
        self.assertEqual(b.available_mana(b.player), 2)
        self.assertEqual(len(b.player.lands), 3)
        b.start_turn(b.player)
        self.assertEqual(b.available_mana(b.player), 3)
        self.assertTrue(b.play(lands[1]))

    def test_summoning_sickness_and_new_creatures_can_block(self):
        recruit = self.play('Citadel Recruit')
        self.assertTrue(recruit.sick)
        enemy = self.card('Crypt Shambler')
        self.b.enemy.board = [enemy]
        self.b.attackers = [enemy]
        self.b.phase = 'BLOCK'
        self.assertTrue(self.b.assign_blocker(enemy, recruit))
        recruit.tapped = True
        self.assertFalse(self.b.assign_blocker(enemy, recruit))
        self.b.start_turn(self.b.player)
        self.assertFalse(recruit.sick)
        self.assertFalse(recruit.tapped)

    def test_simultaneous_combat_and_no_spillover(self):
        attacker = Card('Big', 'Creature', 'G', 2, 4, 2)
        blocker = Card('Small', 'Creature', 'G', 1, 2, 1)
        self.b.player.board = [attacker]
        self.b.enemy.board = [blocker]
        hp = self.b.enemy.hp
        self.b.resolve_attack(self.b.player, [attacker], {attacker: blocker})
        self.assertEqual(self.b.enemy.hp, hp)
        self.assertEqual(self.b.player.board, [])
        self.assertEqual(self.b.enemy.board, [])
        self.assertEqual(self.run.stats['kills'], 1)

    def test_unblocked_damage_and_cleanup(self):
        creature = Card('Big', 'Creature', 'G', 2, 4, 5)
        creature.current_health = 2
        self.b.player.board = [creature]
        hp = self.b.enemy.hp
        self.b.resolve_attack(self.b.player, [creature], {})
        self.assertEqual(self.b.enemy.hp, hp - 4)
        self.assertTrue(creature.tapped)
        self.b.end_cleanup()
        self.assertEqual(creature.current_health, 5)
        self.assertTrue(creature.tapped)

    def test_blocker_cannot_block_twice(self):
        attackers = [self.card('Grove Sprite'), self.card('Grove Sprite')]
        blocker = self.play('Citadel Recruit')
        self.b.phase = 'BLOCK'
        self.b.attackers = attackers
        self.b.assign_blocker(attackers[0], blocker)
        self.b.assign_blocker(attackers[1], blocker)
        self.assertEqual(self.b.assignments, {attackers[1]: [blocker]})

    def test_guard_reduces_blocking_damage(self):
        guard = self.play('Citadel Recruit')
        attacker = Card('Raider', 'Creature', 'R', 2, 2, 3)
        self.b.enemy.board = [attacker]
        self.b.resolve_attack(self.b.enemy, [attacker], {attacker: guard})
        self.assertEqual(guard.current_health, 1)

    def test_spell_target_validation_does_not_spend(self):
        bolt = self.card('Overcharge Bolt')
        self.b.player.hand.append(bolt)
        mana = self.b.player.mana
        self.assertFalse(self.b.play(bolt))
        self.assertIn(bolt, self.b.player.hand)
        self.assertEqual(self.b.player.mana, mana)
        self.assertTrue(self.b.play(bolt, self.b.enemy))
        self.b.pass_priority()
        self.assertEqual(self.run.stats['spell_damage'], 3)

    def test_unknown_spell_is_not_consumed(self):
        card = Card('Future Spell', 'Instant Spell', 'U', 1)
        self.b.player.hand.append(card)
        self.assertFalse(self.b.play(card))
        self.assertIn(card, self.b.player.hand)

    def test_token_passive_and_vanguard(self):
        vanguard = self.play('Legion Vanguard')
        self.play('Phalanx Barrier')
        tokens = [c for c in self.b.player.board if c.token]
        self.assertEqual(len(tokens), 3)
        self.assertTrue(all(c.attack == 2 and c.max_health == 2 for c in tokens))
        self.assertEqual(vanguard.attack, 1)

    def test_unlimited_tokens_leave_no_discard(self):
        self.b.tokens(self.b.player, 20)
        self.assertEqual(len(self.b.player.board), 21)
        self.b.return_unit(self.b.player, self.b.player.board[0])
        self.assertFalse(any(c.token for c in self.b.player.hand))
        for c in self.b.player.board:
            c.current_health = 0
        self.b.cleanup_deaths()
        self.assertFalse(any(c.token for c in self.b.player.discard))

    def test_blink_and_flux(self):
        self.b.passive = 'Aether Flux'
        creature = self.play('Citadel Recruit')
        creature.attack = 20
        creature.tapped = True
        count = self.run.stats['cards_drawn']
        self.play('Aether Warp', creature)
        fresh = self.b.player.board[0]
        self.assertIsNot(fresh, creature)
        self.assertEqual(fresh.attack, 1)
        self.assertTrue(fresh.sick)
        self.assertFalse(fresh.tapped)
        self.assertEqual(self.run.stats['cards_drawn'], count + 2)
        self.assertIn('blink', [event['kind'] for event in self.b.events])

    def test_phase_shifter_returns_enemy(self):
        enemy = self.card('Grove Sprite')
        self.b.enemy.board.append(enemy)
        self.play('Phase Shifter', enemy)
        shifter = next(card for card in self.b.player.board if card.name == 'Phase Shifter')
        self.assertIs(self.b.pending_entry, shifter)
        self.assertIn(enemy, self.b.enemy.board)
        self.assertTrue(self.b.resolve_pending_entry(enemy))
        self.assertEqual(self.b.enemy.board, [])
        self.assertEqual(self.b.enemy.hand[-1].name, 'Grove Sprite')
        self.assertEqual(self.b.events[-1]['kind'], 'return')

    def test_blink_and_death_publish_animation_events(self):
        creature = self.card('Grove Sprite')
        self.b.player.board = [creature]
        self.b.return_unit(self.b.player, creature, blink=True)
        self.assertEqual(self.b.events[-1]['kind'], 'blink')
        returned = self.b.player.board[0]
        returned.current_health = 0
        self.b.cleanup_deaths()
        self.assertEqual(self.b.events[-1]['kind'], 'death')

    def test_multiple_targeted_etbs_queue_and_do_not_softlock(self):
        first = self.card('Phase Shifter'); second = self.card('Phase Shifter')
        enemy = self.card('Grove Sprite')
        self.b.player.board = [first, second]
        self.b.enemy.board = [enemy]
        self.b.begin_enter_effect(self.b.player, first)
        self.b.begin_enter_effect(self.b.player, second)
        self.assertIs(self.b.pending_entry, first)
        self.assertEqual(self.b.pending_entries, [second])
        self.assertTrue(self.b.resolve_pending_entry(enemy))
        self.assertIsNone(self.b.pending_entry)
        self.assertEqual(self.b.pending_entries, [])
        self.assertEqual(self.b.enemy.hand[-1].name, enemy.name)

    def test_titan_growth_only_first_played_creature(self):
        self.b.passive = 'Titan Growth'
        first = self.play('Grove Sprite')
        second = self.play('Grove Sprite')
        self.assertEqual((first.attack, second.attack), (3, 1))
        self.b.start_turn(self.b.player)
        self.b.player.mana = 100
        self.b.player.colored_mana['G'] = 1
        third = self.play('Grove Sprite')
        self.assertEqual(third.attack, 3)

    def test_spell_bonuses_prism_and_pyromancer(self):
        self.b.passive = 'Plasma Surge'
        self.b.relics.update(['Plasma Reactor', 'Shadow Fang', 'Aether Prism'])
        self.b.enemy.hp = 100
        self.b.player.hp = 20
        self.play('Spellweaver Pyromancer')
        self.play('Magma Bolt')
        self.assertEqual(self.run.stats['spell_damage'], 8)
        self.assertEqual(self.b.enemy.hp, 90)
        self.assertEqual(self.b.player.hp, 21)
        drawn = self.run.stats['cards_drawn']
        self.play('Aether Spark')
        self.assertEqual(self.run.stats['cards_drawn'], drawn + 2)

    def test_life_loss_not_damage(self):
        self.b.enemy.armor = 5
        hp = self.b.enemy.hp
        self.b.player.hp = 20
        self.play('Siphon Life')
        self.assertEqual(self.b.enemy.hp, hp - 2)
        self.assertEqual(self.b.enemy.armor, 5)
        self.assertEqual(self.b.player.hp, 22)

    def test_death_triggers_and_horde(self):
        self.b.passive = 'Shadow Veil'
        self.b.player.hp = 20
        shambler = self.play('Crypt Shambler')
        hp = self.b.enemy.hp
        shambler.current_health = 0
        self.b.cleanup_deaths()
        self.assertEqual(self.b.player.hp, 23)
        self.assertEqual(self.b.enemy.hp, hp - 1)
        ghoul = self.play('Crypt Ghoul')
        ghoul.current_health = 0
        self.b.cleanup_deaths()
        self.assertIn(self.b.player.hand[-1].name, ['Crypt Shambler', 'Crypt Ghoul'])
        self.b.passive = 'Endless Horde'
        recruit = self.play('Citadel Recruit')
        recruit.current_health = 0
        self.b.cleanup_deaths()
        self.assertEqual(self.b.player.hand[-1].max_health, 1)

    def test_ramp_and_sprite_sickness(self):
        sprite = self.play('Grove Sprite')
        self.assertFalse(self.b.tap_sprite(sprite))
        self.play('Titan Overseer')
        self.b.start_turn(self.b.player)
        self.assertEqual(self.b.player.colored_mana['G'], 2)
        self.assertTrue(self.b.tap_sprite(sprite))
        self.assertFalse(self.b.tap_sprite(sprite))
        self.assertEqual(self.b.player.colored_mana['G'], 3)
        before = sum(c.card_type == 'Land' for c in self.b.player.hand)
        available = sum(c.card_type == 'Land' for c in self.b.player.deck)
        self.play("Nature's Bounty")
        self.assertEqual(sum(c.card_type == 'Land' for c in self.b.player.hand), before + min(2, available))

    def test_all_actives_once_per_battle(self):
        b = self.b
        for name in ['Holy Light', 'Time Reversal', 'Soul Reaper', 'Flame Burst', 'Wild Growth']:
            with self.subTest(active=name):
                b.active, b.active_used = name, False
                enemy = self.card('Citadel Recruit')
                b.enemy.board = [enemy]
                b.player.hp = 20
                target = b.player if name == 'Holy Light' else enemy
                self.assertTrue(b.use_active(target))
                self.assertFalse(b.use_active(target))
                if name == 'Holy Light':
                    self.assertEqual(b.player.hp, 23)
                elif name in ('Soul Reaper', 'Time Reversal', 'Flame Burst'):
                    self.assertNotIn(enemy, b.enemy.board)

    def test_invalid_active_does_not_consume_use(self):
        self.b.active = 'Soul Reaper'
        giant = Card('Giant', 'Creature', 'G', 6, 6, 6)
        self.b.enemy.board = [giant]
        self.assertFalse(self.b.use_active(giant))
        self.assertFalse(self.b.active_used)

    def test_starting_relics_and_discounts(self):
        self.run.relics = self.pool['relics']
        self.run.hp = 20
        b = Battle(self.run)
        b.keep_hand()
        self.assertEqual(b.player.hp, 23)
        self.assertEqual(b.player.armor, 5)
        self.assertEqual(b.available_mana(b.player), 3)
        self.assertEqual(b.cost(b.player, self.card('Titan Overseer')), 2)
        b.passive = 'Overcharge Core'
        spell = Card('Test', 'Instant Spell', 'R', 3)
        self.assertEqual(b.cost(b.player, spell), 2)
        enemy = self.card('Citadel Recruit')
        b.summon(b.enemy, enemy)
        self.assertEqual(enemy.attack, 0)
        b.damage(b.player, 7)
        self.assertEqual(b.player.hp, 21)

    def test_hand_retained_reshuffle_fatigue_and_mind_vault(self):
        b = self.b
        held = b.player.hand[0]
        b.passive = 'Mind Vault'
        drawn = self.run.stats['cards_drawn']
        b.start_turn(b.player)
        self.assertIn(held, b.player.hand)
        self.assertEqual(self.run.stats['cards_drawn'], drawn + 2)
        b.player.deck = []
        b.player.discard = [self.card('Magma Bolt')]
        b.draw(b.player)
        self.assertEqual(b.player.hand[-1].name, 'Magma Bolt')
        hp = b.player.hp
        b.draw(b.player, 2)
        self.assertEqual(b.player.hp, hp - 3)

    def test_map_locks_siblings_and_has_one_boss(self):
        node = self.run.node
        self.assertEqual(len(self.run.grid[-1]), 1)
        self.assertTrue(complete_node(self.run.grid, node))
        self.assertFalse(complete_node(self.run.grid, node))
        available = [n for row in self.run.grid for n in row if n.available]
        self.assertEqual(set(available), set(node.connections))
        self.assertFalse(any(n.available for n in self.run.grid[0]))

    def test_battle_rewards_once_and_hp_carries(self):
        self.b.player.hp = 17
        self.b.enemy.hp = 0
        self.b.check_result()
        gold = self.run.gold
        self.assertEqual(self.b.collect_reward(), 20)
        self.assertEqual(self.b.collect_reward(), 0)
        self.assertEqual(self.run.gold, gold + 20)
        self.assertEqual(self.run.hp, 17)
        self.assertIsNone(self.run.node)

    def test_loss_does_not_unlock_map(self):
        self.b.player.hp = 0
        self.b.check_result()
        self.assertEqual(self.b.result, 'DEFEAT')
        self.assertEqual(self.b.collect_reward(), 0)
        self.assertFalse(self.run.node.visited)

    def test_shop_rest_treasure_and_new_run_reset(self):
        self.run.node.node_type = 'Merchant'
        node = self.run.node
        self.run.node = None
        self.assertTrue(self.run.enter(node))
        self.run.gold = 100
        size = len(self.run.deck)
        price = self.run.shop[0]['price']
        self.assertTrue(self.run.buy(0))
        self.assertFalse(self.run.buy(0))
        self.assertEqual(len(self.run.deck), size + 1)
        self.assertEqual(self.run.gold, 100 - price)
        self.run.gold = 0
        self.assertFalse(self.run.buy(1))
        self.run.finish()
        next_node = node.connections[0]
        next_node.node_type = 'Rest'
        self.run.enter(next_node)
        self.run.hp = 25
        self.assertEqual(self.run.rest(), 5)
        treasure = next_node.connections[0]
        treasure.node_type = 'Treasure'
        self.run.enter(treasure)
        self.assertEqual(len(self.run.choices), 3)
        self.assertTrue(self.run.take_relic(0))
        self.assertFalse(self.run.take_relic(0))
        self.assertEqual(len(self.run.relics), 1)
        fresh = Run(self.cmd, self.pool)
        self.assertEqual((fresh.hp, fresh.gold, len(fresh.deck), fresh.relics), (30, 35, 16, []))

    def test_achievement_persistence_and_bad_save(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'save.json'
            progress = Progress(path)
            self.assertEqual(progress.check(dict(cards_drawn=0, kills=0, spell_damage=0)), [])
            new = progress.check(dict(cards_drawn=15, kills=10, spell_damage=50))
            self.assertEqual(len(new), 3)
            self.assertEqual(Progress(path).unlocked, {u['name'] for u in UNLOCKS[:3]})
            stats = {u['stat']: u['goal'] for u in UNLOCKS}
            self.assertEqual(len(progress.check(stats)), len(UNLOCKS) - 3)
            self.assertEqual(progress.check(stats), [])
            self.assertEqual(Progress(path).unlocked, {u['name'] for u in UNLOCKS})
            path.write_text('broken', encoding='utf-8')
            self.assertTrue(Progress(path).error)


if __name__ == '__main__':
    unittest.main()

