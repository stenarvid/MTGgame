"""Command-zone costs, alternate casting, saves and arena input regressions."""
import unittest
import pygame
import test_expansion as fixtures
from persistence import encode_graph, decode_graph
import test_arena as arena_fixture


class CommandZoneTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ExpansionRules()
        self.f.setUp()
        self.b = self.f.b

    def test_commander_cast_death_recast_and_cost(self):
        b = self.b
        card = b.commander
        original = b.cost(b.player, card)
        self.assertTrue(b.play(card))
        self.assertEqual(b.commander_casts, 1)
        self.assertEqual(b.commander_zone, 'STACK')
        self.f.resolve()
        self.assertIn(card, b.player.board)
        self.assertTrue(card.sick)
        card.current_health = 0
        b.cleanup_deaths()
        self.assertEqual(b.commander_zone, 'COMMAND')
        self.assertNotIn(card, b.player.discard)
        self.assertEqual(b.cost(b.player, b.commander), original + 2)
        self.assertTrue(b.commander.mana_label(b.cost(b.player, b.commander)).startswith('2'))
        self.assertTrue(b.play(b.commander))
        self.assertEqual(b.commander_casts, 2)

    def test_commander_blink_bounce_and_counter(self):
        b = self.b
        b.play(b.commander); self.f.resolve()
        b.return_unit(b.player, b.commander, blink=True)
        self.assertEqual(b.commander_zone, 'BOARD')
        b.return_unit(b.player, b.commander)
        self.assertEqual(b.commander_zone, 'COMMAND')
        self.assertEqual(b.commander_casts, 1)
        b.play(b.commander)
        target = b.stack[-1]
        counter = self.f.card('Null Sigil')
        b.enemy.hand.append(counter)
        self.assertTrue(b.play(counter, target, b.enemy))
        self.f.resolve()
        self.assertEqual(b.commander_zone, 'COMMAND')
        self.assertEqual(b.commander_casts, 2)

    def test_flashback_resolves_and_exiles_once(self):
        b = self.b
        card = self.f.card('Grave Recall')
        b.player.discard = [card, self.f.card('Thorn Sentinel')]
        self.assertEqual(b.cost(b.player, card), 4)
        self.assertEqual(card.mana_label(4), '3B')
        self.assertTrue(b.play(card))
        self.f.resolve()
        self.assertTrue(any(c.name == 'Thorn Sentinel' for c in b.player.hand))
        self.assertEqual(len(b.player.exile), 1)
        self.assertFalse(b.play(b.player.exile[0]))
        self.assertFalse(b.alternate_cards())

    def test_countered_flashback_is_exiled(self):
        b = self.b
        card = self.f.card('Grave Recall')
        b.player.discard.append(card)
        self.assertTrue(b.play(card))
        target = b.stack[-1]
        counter = self.f.card('Null Sigil'); b.enemy.hand.append(counter)
        self.assertTrue(b.play(counter, target, b.enemy))
        self.f.resolve()
        self.assertEqual([c.name for c in b.player.exile], ['Grave Recall'])
        self.assertFalse(any(c.name == 'Grave Recall' for c in b.player.discard))

    def test_alternate_cast_requires_permission_mana_and_timing(self):
        b = self.b
        ordinary = self.f.card('Magma Bolt'); b.player.discard.append(ordinary)
        self.assertFalse(b.play(ordinary))
        flashback = self.f.card('Grave Recall'); b.player.discard.append(flashback)
        b.player.colored_mana = dict.fromkeys('WUBRG', 0)
        b.player.lands = []; b.player.mana = 10
        self.assertFalse(b.play(flashback))  # Generic mana cannot pay B.
        self.assertIn(flashback, b.player.discard)
        b.player.colored_mana['B'] = 10
        b.phase = 'ENEMY_MAIN'
        self.assertFalse(b.play(flashback))
        b.phase = 'MAIN'
        b.player.exile.append(ordinary)
        b.player.discard.remove(ordinary)
        self.assertFalse(b.play(ordinary))
        ordinary.play_from_exile = True
        b.player.colored_mana['R'] = 10
        self.assertTrue(b.play(ordinary))

    def test_saved_commander_stack_and_flashback_permission(self):
        b = self.b
        b.play(b.commander)
        b.player.discard.append(self.f.card('Grave Recall'))
        saved = decode_graph(encode_graph(self.f.payload()), self.f.pool)['battle']
        self.assertIs(saved.commander, saved.stack[-1].card)
        self.assertEqual(saved.commander_casts, 1)
        self.assertEqual(saved.alternate_cards()[0].flashback_cost, 4)

    def test_flashback_exile_destination_survives_save_on_stack(self):
        b = self.b
        card = self.f.card('Grave Recall'); b.player.discard.append(card)
        self.assertTrue(b.play(card))
        saved = decode_graph(encode_graph(self.f.payload()), self.f.pool)['battle']
        saved.pass_priority()
        self.assertEqual([c.name for c in saved.player.exile], ['Grave Recall'])
        self.assertFalse(saved.alternate_cards())

    def test_pre_command_zone_save_migrates(self):
        encoded = encode_graph(self.f.payload())
        for obj in encoded['objects']:
            if obj['type'] == 'Battle':
                for key in ('commander', 'commander_casts', 'commander_zone'):
                    obj['attributes'].pop(key, None)
            if obj['type'] == 'Side':
                obj['attributes'].pop('exile', None)
        loaded = decode_graph(encoded, self.f.pool)['battle']
        self.assertEqual(loaded.commander_zone, 'COMMAND')
        self.assertEqual(loaded.commander_casts, 0)
        self.assertEqual(loaded.player.exile, [])


class ArenaInputTests(unittest.TestCase):
    setUp = arena_fixture.DragTests.setUp
    tearDown = arena_fixture.DragTests.tearDown
    event = arena_fixture.DragTests.event
    def test_attack_selection_and_declaration(self):
        b = self.game.battle
        b.phase = 'COMBAT'
        card = self.card('Thorn Sentinel'); card.sick = False
        b.player.board = [card]; b.enemy.board = []
        self.game.draw()
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=card.rect.center)
        self.assertIn(card, self.game.chosen)
        self.game.draw()
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1140, 610))
        self.assertIn(card, b.attackers)
        self.assertEqual(b.phase, 'ATTACK_RESPONSE')
        self.assertTrue(card.tapped)
        before = b.enemy.hp
        self.game.advance_combat()
        self.assertEqual(b.enemy.hp, before - card.attack)
        self.assertGreater(card.attack_animation_started, 0)

    def test_tapped_lands_render_with_a_subtle_tilt(self):
        lands = self.game.battle.player.lands
        lands[0].tapped = False; lands[1].tapped = True
        self.game.draw()
        rects = {card: rect for card, rect in self.game.land_hits[True]}
        self.assertGreater(rects[lands[0]].w, rects[lands[0]].h)
        self.assertGreater(rects[lands[1]].w, rects[lands[1]].h)
        self.assertGreater(rects[lands[1]].h, rects[lands[0]].h)

    def test_alternate_tray_click_and_hero_target_geometry(self):
        b = self.game.battle
        card = self.card('Grave Recall'); b.player.discard.append(card)
        self.game.draw()
        rect = self.game.alternate_hits[0][1]
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center)
        self.assertIs(b.stack[-1].card, card)
        self.assertIs(self.game.drop_target(self.game.hero_rect(False).center), b.enemy)
        self.assertIs(self.game.drop_target(self.game.hero_rect(True).center), b.player)

    def test_commander_slot_casts(self):
        self.game.draw()
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.game.commander_rect.center)
        self.assertEqual(self.game.battle.commander_zone, 'STACK')

    def test_commander_slot_uses_active_from_battlefield(self):
        b = self.game.battle
        b.commander_zone = 'BOARD'
        b.player.board.append(b.commander)
        b.active = 'Adaptive Bloom'
        b.phase = 'MAIN'
        self.game.draw()
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.game.commander_active_rect.center)
        self.assertEqual(self.game.pending, 'ACTIVE')
        self.assertIn('+3/+3', self.game.adaptive_bloom_description('might'))
        self.assertIn('Draw 2', self.game.adaptive_bloom_description('insight'))
        self.assertIn('Gain 3', self.game.adaptive_bloom_description('renewal'))

    def test_commander_slot_selects_and_assigns_commander_as_blocker(self):
        b = self.game.battle
        b.commander_zone = 'BOARD'
        b.commander.tapped = False
        second_blocker = self.card('Citadel Recruit')
        second_blocker.tapped = False
        b.player.board = [b.commander, second_blocker]
        attacker = self.card('Thorn Sentinel')
        b.enemy.board = [attacker]
        b.attackers = [attacker]
        b.assignments = {}
        b.phase = 'BLOCK'

        self.game.draw()
        commander_rect = next(rect for card, rect in self.game.board_hits if card is b.commander)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=commander_rect.center)
        self.assertEqual(self.game.blockers, {b.commander})

        self.game.draw()
        blocker_rect = next(rect for card, rect in self.game.board_hits if card is second_blocker)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=blocker_rect.center)
        self.assertEqual(self.game.blockers, {b.commander, second_blocker})

        self.game.draw()
        enemy_rect = next(rect for card, rect in self.game.board_hits if card is attacker)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=enemy_rect.center)
        self.assertEqual(set(b.assignments[attacker]), {b.commander, second_blocker})
        self.assertFalse(self.game.blockers)


if __name__ == '__main__':
    unittest.main()
