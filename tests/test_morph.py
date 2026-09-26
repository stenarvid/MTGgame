"""Pink morph identity, board-wide mutations, blink reuse and priority automation."""
import unittest
import pygame
import test_expansion as fixtures
from models import Card, generate_procedural_commander
from engine import Battle, Run


class MorphRules(unittest.TestCase):
    def setUp(self):
        base = fixtures.ExpansionRules(); base.setUp()
        self.pool = base.pool
        _, meta, _ = fixtures.load_game_data()
        passive = next(value for value in meta['passives'] if value['name'] == 'Living Mosaic')
        active = next(value for value in meta['actives'] if value['name'] == 'Adaptive Bloom')
        commander = generate_procedural_commander(meta, [], [], passive, active)
        run = Run(commander, self.pool); run.enter(run.grid[0][0])
        self.b = Battle(run); self.b.keep_hand(); self.b.enemy.hand = []
        self.b.theme = 'C'
        self.b.player.colored_mana = dict.fromkeys('WUBRGP', 30)
        self.b.enemy.colored_mana = dict.fromkeys('WUBRGP', 30)

    def card(self, name):
        return Card.from_dict(next(c for c in self.pool['cards'] if c['name'] == name))

    def cast(self, name, target=None):
        card = self.card(name); self.b.player.hand.append(card)
        self.assertTrue(self.b.play(card, target))
        while self.b.phase == 'RESPONSE': self.b.pass_priority()

    def test_pink_deck_has_pink_lands_and_cards(self):
        self.assertIn('P', self.b.run.commander.colors)
        self.assertTrue(any(card.color_code == 'P' and card.card_type == 'Land' for card in self.b.run.deck))
        self.assertTrue(any(card.color_code == 'P' and card.card_type != 'Land' for card in self.b.run.deck))

    def test_board_morph_curses_enemy_deaths(self):
        enemies = [self.card('Thorn Sentinel'), self.card('Citadel Recruit')]
        self.b.enemy.board = enemies
        self.cast('Hostile Rewrite')
        self.assertTrue(all(card.perpetual['death_curse'] == 1 for card in enemies))
        before = self.b.enemy.hp
        for card in enemies: card.current_health = 0
        self.b.cleanup_deaths()
        self.assertEqual(self.b.enemy.hp, before - 2)

    def test_chorus_is_board_wide_and_scales_with_morphed_board(self):
        friends = [self.card('Thorn Sentinel'), self.card('Citadel Recruit')]
        self.b.player.board = friends
        self.cast('Chorus Evolution')
        self.b.player.hp = 10
        self.b.start_turn(self.b.player)
        self.assertEqual(self.b.player.hp, 12)
        self.assertTrue(all(card.attack >= (4 if card.name == 'Thorn Sentinel' else 3) for card in friends))

    def test_perpetual_morph_stats_survive_blink(self):
        creature = self.card('Citadel Recruit'); self.b.player.board = [creature]
        base = (creature.attack, creature.max_health)
        self.b.morph(self.b.player, creature, 'insight')
        self.b.return_unit(self.b.player, creature, blink=True)
        returned = self.b.player.board[0]
        # The mutation and Living Mosaic each grant +1/+1.
        self.assertEqual((returned.attack, returned.max_health), (base[0] + 2, base[1] + 2))
        self.assertEqual(returned.perpetual['insight'], 1)
        self.assertEqual(returned.plus_one_counters, 2)

    def test_board_blink_retriggers_perpetual_insight(self):
        friends = [self.card('Thorn Sentinel'), self.card('Citadel Recruit')]
        self.b.player.board = friends
        self.cast('Memory Migration')
        before = len(self.b.player.hand)
        self.cast('Grand Reassembly')
        self.assertEqual(len(self.b.player.board), 2)
        self.assertGreaterEqual(len(self.b.player.hand), before + 2)
        self.assertTrue(all(card.perpetual.get('insight') for card in self.b.player.board))

    def test_board_morph_rewrites_battlefield_deck_and_graveyard(self):
        battlefield = self.card('Citadel Recruit')
        library = self.card('Thorn Sentinel')
        graveyard = self.card('Grove Sprite')
        noncreature = self.card('Magma Bolt')
        self.b.player.board = [battlefield]
        self.b.player.deck = [library, noncreature]
        self.b.player.discard = [graveyard]
        self.cast('Memory Migration')
        for creature in (battlefield, library, graveyard):
            self.assertEqual(creature.perpetual.get('insight'), 1)
        self.assertFalse(noncreature.perpetual)
        before = len(self.b.player.hand)
        self.b.player.deck.remove(library)
        self.b.summon(self.b.player, library)
        self.assertEqual(len(self.b.player.hand), before + 1)

    def test_hostile_board_morph_rewrites_enemy_deck_and_graveyard(self):
        battlefield = self.card('Citadel Recruit')
        library = self.card('Thorn Sentinel')
        graveyard = self.card('Grove Sprite')
        self.b.enemy.board = [battlefield]
        self.b.enemy.deck = [library]
        self.b.enemy.discard = [graveyard]
        self.cast('Hostile Rewrite')
        self.assertTrue(all(card.perpetual.get('death_curse') == 1
                            for card in (battlefield, library, graveyard)))

    def test_adaptive_bloom_choice_is_temporary_and_stronger_on_morphed_target(self):
        target = self.card('Citadel Recruit'); self.b.player.board = [target]
        self.b.morph(self.b.player, target, 'chorus')
        base = (target.attack, target.max_health)
        self.assertTrue(self.b.use_active(target, 'might'))
        self.assertEqual((target.attack, target.max_health), (base[0] + 3, base[1] + 3))
        self.b.end_cleanup()
        self.assertEqual((target.attack, target.max_health), base)

    def test_cross_color_morph_triggers(self):
        host = self.card('Citadel Recruit')
        victim = self.card('Grove Sprite')
        self.b.player.board = [host]
        self.b.player.hp = 10

        self.cast('Welcoming Shape', host)
        self.b.summon(self.b.player, self.card('Thorn Sentinel'))
        self.assertEqual(self.b.player.hp, 11)

        self.cast('Cinder Shape', host)
        enemy_hp = self.b.enemy.hp
        self.cast('Aether Spark')
        self.assertEqual(self.b.enemy.hp, enemy_hp - 1)

        self.cast('Rooted Shape', host)
        before = (host.attack, host.max_health)
        land = Card('P Mana Conduit', 'Land', 'P', 0)
        self.b.player.hand.append(land)
        self.assertTrue(self.b.play(land))
        self.assertEqual((host.attack, host.max_health), (before[0] + 1, before[1] + 1))

        self.cast('Mourning Shape', host)
        self.b.player.hp = 10
        victim.current_health = 0
        self.b.player.board.append(victim)
        self.b.cleanup_deaths()
        self.assertEqual(self.b.player.hp, 11)

    def test_cross_color_mutations_survive_blink(self):
        host = self.card('Citadel Recruit'); self.b.player.board = [host]
        self.b.morph(self.b.player, host, 'landgrowth')
        host.perpetual['growth_bonus'] = 2
        host.plus_one_counters += 2
        host.attack += 2; host.max_health += 2; host.current_health += 2
        expected = (host.attack, host.max_health)
        self.b.return_unit(self.b.player, host, blink=True)
        returned = self.b.player.board[0]
        self.assertEqual((returned.attack, returned.max_health), expected)
        self.assertEqual(returned.perpetual['landgrowth'], 1)
        self.assertEqual(returned.plus_one_counters, 4)

    def test_priority_only_pauses_for_legal_player_response(self):
        self.b.player.hand.clear()
        spell = self.card('Magma Bolt'); self.b.enemy.hand.append(spell)
        self.b.phase = 'ENEMY_MAIN'; self.assertTrue(self.b.play(spell, side=self.b.enemy))
        self.assertFalse(self.b.player_can_respond())
        counter = self.card('Null Sigil'); self.b.player.hand.append(counter)
        self.b.player.colored_mana['U'] = 30
        self.assertTrue(self.b.player_can_respond())


if __name__ == '__main__': unittest.main()
