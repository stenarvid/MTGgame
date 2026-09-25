import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame

from engine import Battle, Run, StackItem
from models import Card, generate_procedural_commander, load_game_data
from persistence import RunStore, encode_graph, decode_graph
from main import Game


class ExpansionRules(unittest.TestCase):
    def setUp(self):
        random.seed(20)
        _, meta, self.pool = load_game_data()
        commander = generate_procedural_commander(meta, [], [], meta['passives'][1], meta['actives'][3])
        self.run = Run(commander, self.pool)
        self.run.enter(self.run.grid[0][0])
        self.b = Battle(self.run)
        self.b.keep_hand()
        self.b.enemy.hand = []
        self.b.theme = 'C'
        self.b.player.colored_mana = dict.fromkeys('WUBRG', 30)
        self.b.enemy.colored_mana = dict.fromkeys('WUBRG', 30)

    def card(self, name):
        return Card.from_dict(next(c for c in self.pool['cards'] if c['name'] == name))

    def cast(self, name, target=None, side=None, upgrade=False):
        card = self.card(name)
        if upgrade:
            card.upgrade()
        side = side or self.b.player
        side.hand.append(card)
        self.assertTrue(self.b.play(card, target, side))
        return card

    def resolve(self):
        for _ in range(50):
            if self.b.phase != 'RESPONSE' or self.b.result:
                return
            self.b.pass_priority()
        self.fail('Stack did not resolve')

    def payload(self, state='BATTLE'):
        return dict(run=self.run, battle=self.b, state=state, rng=random.getstate(), ui={})

    def test_colored_cost_requires_color_and_generic_cannot_substitute(self):
        side = self.b.player
        side.lands = [Card('Plains', 'Land', 'W', 0), Card('Mountain', 'Land', 'R', 0)]
        side.colored_mana = dict.fromkeys('WUBRG', 0)
        side.mana = 99
        blue = self.card('Aether Spark')
        self.assertFalse(self.b.can_pay(side, blue))
        self.assertFalse(self.b.pay(side, blue))
        self.assertTrue(all(not c.tapped for c in side.lands))
        red = self.card('Ember Duelist')
        self.assertTrue(self.b.pay(side, red))
        self.assertFalse(side.lands[0].tapped)
        self.assertTrue(side.lands[1].tapped)
        self.assertEqual(side.mana, 98)
        self.assertEqual(red.mana_label(), '1R')

    def test_opening_lands_cover_both_commander_colors(self):
        self.assertEqual({c.color_code for c in self.b.player.lands}, {'U', 'R'})

    def test_mulligan_one_time_keeps_lands_and_card_count(self):
        b = Battle(self.run)
        self.assertEqual(b.phase, 'MULLIGAN')
        self.assertEqual(len(b.player.hand), 5)
        original = list(b.player.hand[:3])
        lands = list(b.player.lands)
        self.assertTrue(b.mulligan(original))
        self.assertEqual(len(b.player.hand), 5)
        self.assertFalse(any(c in b.player.hand for c in original))
        self.assertTrue(all(c in b.player.deck for c in original))
        self.assertEqual(b.player.lands, lands)
        self.assertFalse(b.mulligan(b.player.hand))
        self.assertTrue(b.keep_hand())
        self.assertEqual(len(b.player.hand), 6)
        self.assertFalse(b.keep_hand())

    def test_response_stack_last_in_first_out_and_counter(self):
        hp = self.b.enemy.hp
        self.cast('Magma Bolt')
        first = self.b.stack[-1]
        self.assertEqual(self.b.enemy.hp, hp)
        self.cast('Null Sigil', first, self.b.enemy)
        enemy_counter = self.b.stack[-1]
        self.cast('Null Sigil', enemy_counter)
        self.b.pass_priority()
        self.assertEqual(len(self.b.stack), 1)
        self.assertIs(self.b.stack[0], first)
        self.resolve()
        self.assertEqual(self.b.enemy.hp, hp - 2)
        self.assertEqual(self.b.phase, 'MAIN')

    def test_target_disappearing_fizzles_without_refunding_mana(self):
        creature = self.card('Citadel Recruit')
        self.b.enemy.board = [creature]
        self.cast('Overcharge Bolt', creature)
        self.cast('Aether Warp', creature, self.b.enemy)
        self.resolve()
        self.assertNotIn(creature, self.b.enemy.board)
        self.assertEqual(self.b.enemy.board[0].current_health, 2)
        self.assertTrue(any('fizzles' in line for line in self.b.log))
        self.assertEqual(self.run.stats['spell_damage'], 0)

    def test_instants_on_enemy_turn_but_not_creatures_or_lands(self):
        self.b.phase = 'BLOCK'
        self.b.combat_side = self.b.enemy
        creature, land = self.card('Dawn Medic'), Card('Plains', 'Land', 'W', 0)
        self.b.player.hand += [creature, land]
        self.assertFalse(self.b.play(creature))
        self.assertFalse(self.b.play(land))
        self.cast('Magma Bolt')
        self.resolve()
        self.assertEqual(self.b.phase, 'BLOCK')

    def test_second_main_phase_before_enemy_turn(self):
        self.assertTrue(self.b.attack([]))
        self.assertEqual(self.b.phase, 'MAIN2')
        self.assertEqual(self.b.enemy_turn_number, 0)
        self.b.player.colored_mana['W'] = 3
        self.cast('Dawn Medic')
        self.resolve()
        self.assertEqual(self.b.phase, 'MAIN2')
        self.assertEqual(self.b.player.board[-1].name, 'Dawn Medic')
        self.b.end_turn()
        self.assertEqual(self.b.enemy_turn_number, 1)

    def test_multiple_blockers_and_damage_order(self):
        attacker = Card('Attacker', 'Creature', 'R', 2, 3, 4)
        first = Card('First', 'Creature', 'G', 1, 2, 2)
        second = Card('Second', 'Creature', 'G', 1, 2, 2)
        self.b.player.board, self.b.enemy.board = [attacker], [first, second]
        self.b.resolve_attack(self.b.player, [attacker], {attacker: [first, second]})
        self.assertNotIn(attacker, self.b.player.board)
        self.assertNotIn(first, self.b.enemy.board)
        self.assertIn(second, self.b.enemy.board)
        self.assertEqual(second.current_health, 1)

    def test_preview_matches_combat_without_mutating_state(self):
        a = Card('Attacker', 'Creature', 'R', 2, 4, 4)
        blockers = [Card('Blocker', 'Creature', 'W', 1, 2, 2) for _ in range(2)]
        self.b.enemy.board, self.b.player.board = [a], blockers
        self.b.phase, self.b.combat_side, self.b.attackers = 'BLOCK', self.b.enemy, [a]
        for c in blockers:
            self.assertTrue(self.b.assign_blocker(a, c))
        before = json.dumps(encode_graph(self.payload()), sort_keys=True)
        preview = self.b.combat_preview()
        self.assertEqual(set(preview['deaths']), set(blockers + [a]))
        self.assertEqual(preview['player_damage'], 0)
        self.assertEqual(before, json.dumps(encode_graph(self.payload()), sort_keys=True))
        self.b.finish_blocks()
        self.b.finish_blocks()
        self.assertEqual(self.b.player.board, [])
        self.assertEqual(self.b.enemy.board, [])

    def test_blocked_attacker_stays_blocked_after_blocker_bounced(self):
        attacker, blocker = self.card('Thorn Sentinel'), self.card('Citadel Recruit')
        attacker.name = 'No trample'
        self.b.enemy.board, self.b.player.board = [attacker], [blocker]
        self.b.phase, self.b.combat_side, self.b.attackers = 'BLOCK', self.b.enemy, [attacker]
        self.b.assign_blocker(attacker, blocker)
        self.b.finish_blocks()
        self.b.return_unit(self.b.player, blocker)
        self.assertEqual(self.b.combat_preview()['player_damage'], 0)

    def test_blocker_removed_before_declaration_does_not_block(self):
        attacker, blocker = self.card('Ember Duelist'), self.card('Citadel Recruit')
        self.b.enemy.board, self.b.player.board = [attacker], [blocker]
        self.b.phase, self.b.combat_side, self.b.attackers = 'BLOCK', self.b.enemy, [attacker]
        self.b.assign_blocker(attacker, blocker)
        self.b.return_unit(self.b.player, blocker)
        self.b.finish_blocks()
        self.assertEqual(self.b.combat_preview()['player_damage'], 3)

    def test_trample_and_temporary_buffs_cleanup(self):
        attacker = self.card('Thorn Sentinel')
        blocker = Card('Token', 'Creature', 'W', 0, 1, 1)
        self.b.player.board, self.b.enemy.board = [attacker], [blocker]
        plan = self.b.damage_plan(self.b.player, [attacker], {attacker: [blocker]})
        self.assertEqual(plan[self.b.enemy], 3)
        self.cast('Verdant Surge', attacker)
        self.resolve()
        self.assertEqual((attacker.attack, attacker.max_health), (7, 7))
        self.b.end_cleanup()
        self.assertEqual((attacker.attack, attacker.max_health), (4, 4))

    def test_new_creature_effects_and_blink_entry(self):
        self.b.player.hp = 10
        medic = self.cast('Dawn Medic')
        self.resolve()
        self.assertEqual(self.b.player.hp, 13)
        self.cast('Aether Warp', medic)
        self.resolve()
        self.assertEqual(self.b.player.hp, 16)
        drawn = self.run.stats['cards_drawn']
        self.cast('Tide Scholar')
        self.resolve()
        self.assertEqual(self.run.stats['cards_drawn'], drawn + 1)
        duelist = self.cast('Ember Duelist')
        self.resolve()
        self.assertFalse(duelist.sick)

    def test_recall_collector_and_area_damage(self):
        self.cast('Soul Collector')
        self.resolve()
        self.b.enemy.board = [self.card('Grove Sprite'), self.card('Crypt Shambler')]
        hp = self.b.enemy.hp
        self.cast('Cinder Volley')
        self.resolve()
        self.assertEqual(self.b.enemy.board, [])
        # Two Collector triggers, one Shambler death heals its own hero.
        self.assertEqual(self.b.enemy.hp, hp - 1)
        self.b.player.discard.append(self.card('Thorn Sentinel'))
        self.cast('Grave Recall')
        self.resolve()
        self.assertEqual(self.b.player.hand[-1].name, 'Thorn Sentinel')

    def test_reward_take_skip_and_resume_cannot_duplicate(self):
        self.b.enemy.hp = 0
        self.b.check_result()
        self.b.collect_reward()
        self.assertEqual(len(self.run.rewards), 3)
        self.assertTrue(all(c['color'] in self.run.commander.colors for c in self.run.rewards))
        node = next(n for row in self.run.grid for n in row if n.available)
        self.assertFalse(self.run.enter(node))
        size = len(self.run.deck)
        restored = decode_graph(encode_graph(self.payload('REWARD')), self.pool)
        run = restored['run']
        self.assertTrue(run.take_card_reward(0))
        self.assertFalse(run.take_card_reward(0))
        self.assertEqual(len(run.deck), size + 1)
        self.assertEqual(restored['battle'].collect_reward(), 0)
        self.run.take_card_reward()
        self.assertEqual(len(self.run.deck), size)

    def test_services_upgrade_persists_and_battle_buffs_do_not(self):
        self.run.node.node_type = 'Merchant'
        self.run.gold = 100
        card = next(c for c in self.run.deck if c.is_creature)
        base_attack = card.attack
        self.assertTrue(self.run.service(card, 'upgrade'))
        self.assertEqual(card.attack, base_attack + 1)
        self.assertEqual(self.run.gold, 70)
        self.assertFalse(self.run.service(card, 'remove'))
        copy = self.b.base_card(card)
        self.assertTrue(copy.upgraded)
        self.assertEqual(copy.attack, card.attack)
        copy.attack += 10
        self.assertEqual(self.b.base_card(copy).attack, card.attack)

    def test_rest_upgrade_replaces_healing_and_removal_limits(self):
        self.run.node.node_type = 'Rest'
        self.run.hp = 10
        card = next(c for c in self.run.deck if c.is_creature)
        self.assertTrue(self.run.service(card, 'upgrade'))
        self.assertEqual(self.run.hp, 10)
        self.assertIsNone(self.run.node)
        node = next(n for row in self.run.grid for n in row if n.available)
        node.node_type = 'Merchant'
        self.run.enter(node)
        self.run.gold = 100
        land = next(c for c in self.run.deck if c.card_type == 'Land')
        self.run.deck = self.run.deck[:10]
        self.assertFalse(self.run.service(land, 'remove'))

    def test_upgraded_spell_effect_and_counter_draw(self):
        hp = self.b.enemy.hp
        self.cast('Magma Bolt', upgrade=True)
        self.resolve()
        self.assertEqual(self.b.enemy.hp, hp - 3)
        self.b.phase = 'DEFEND_RESPONSE'
        self.cast('Magma Bolt', side=self.b.enemy)
        target = self.b.stack[-1]
        drawn = self.run.stats['cards_drawn']
        self.cast('Null Sigil', target, upgrade=True)
        self.resolve()
        self.assertEqual(self.run.stats['cards_drawn'], drawn + 1)

    def test_enemy_theme_and_boss_phase(self):
        self.b.theme, self.b.elite = 'W', True
        self.b.start_turn(self.b.enemy)
        self.assertTrue(any(c.token for c in self.b.enemy.board))
        self.b.theme = 'G'
        self.b.enemy.creatures_played = 0
        creature = self.card('Grove Sprite')
        self.b.summon(self.b.enemy, creature, played=True)
        self.assertEqual(creature.attack, 2)
        self.b.boss = True
        self.b.enemy.hp = self.b.enemy.max_hp // 2
        self.b.check_result()
        count = len(self.b.enemy.board)
        self.assertTrue(self.b.boss_enraged)
        self.b.check_result()
        self.assertEqual(len(self.b.enemy.board), count)

    def test_save_restores_stack_identity_and_rng(self):
        creature = self.card('Grove Sprite')
        self.b.enemy.board.append(creature)
        self.cast('Overcharge Bolt', creature)
        self.cast('Null Sigil', self.b.stack[-1], self.b.enemy)
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(Path(directory) / 'run.json')
            payload = self.payload()
            payload['ui'] = dict(pending=self.b.player.hand[0], chosen={creature})
            self.assertTrue(store.save(payload), store.error)
            loaded = store.load(self.pool)
            self.assertIsNotNone(loaded, store.error)
            battle = loaded['battle']
            self.assertIs(battle.run, loaded['run'])
            self.assertIs(battle.stack[-1].target, battle.stack[0])
            self.assertIs(battle.stack[0].target, battle.enemy.board[-1])
            self.assertIn(loaded['ui']['pending'], battle.player.hand)
            expected = random.Random()
            expected.setstate(payload['rng'])
            actual = random.Random()
            actual.setstate(loaded['rng'])
            self.assertEqual(expected.random(), actual.random())

    def test_corrupt_and_failed_saves_preserve_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.json'
            store = RunStore(path)
            self.assertTrue(store.save(self.payload()))
            original = path.read_bytes()
            with patch('persistence.os.fsync', side_effect=OSError('disk failure')):
                self.assertFalse(store.save(self.payload()))
            self.assertEqual(path.read_bytes(), original)
            path.write_text('not-json', encoding='utf-8')
            self.assertIsNone(store.load(self.pool))
            self.assertEqual(path.read_text(), 'not-json')


class ExpandedScreens(unittest.TestCase):
    def test_reward_service_stack_save_resume_scaling_and_shortcuts(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(save_path=Path(directory) / 'run.json', progress_path=Path(directory) / 'unlocks.json')
            game.start_builder()
            game.choose(game.commanders['passives'][1])
            game.choose(game.commanders['actives'][3])
            game.enter_node(game.run.grid[0][0])
            game.draw()
            game.keep_hand()
            game.battle.player.colored_mana = dict.fromkeys('WUBRG', 10)
            game.battle.enemy.hand.clear()
            bolt = Card.from_dict(next(c for c in game.pool['cards'] if c['name'] == 'Magma Bolt'))
            game.battle.player.hand.append(bolt)
            game.play_card(bolt)
            for state in ('BATTLE', 'STACK', 'LOG', 'PAUSE', 'SETTINGS'):
                game.state = state
                game.resume_state = 'BATTLE'
                game.draw()
            game.state = 'BATTLE'
            game.inspect('deck')
            original_order = list(game.battle.player.deck)
            game.draw()
            self.assertEqual(game.battle.player.deck, original_order)
            game.state = 'BATTLE'
            self.assertTrue(game.save_run(), game.store.error)
            game.state = 'MENU'
            game.resume_run()
            self.assertEqual(game.battle.phase, 'RESPONSE')
            game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            self.assertEqual(game.battle.phase, 'MAIN')
            game.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=800, h=600))
            viewport = game.viewport()
            pos = (viewport.x + viewport.w // 2, viewport.y + viewport.h // 2)
            logical = game.to_logical(pos)
            self.assertAlmostEqual(logical[0], 640, delta=2)
            self.assertAlmostEqual(logical[1], 450, delta=2)
            game.draw()
            game.present()
            game.battle.enemy.hp = 0
            game.battle.check_result()
            game.end_battle()
            game.draw()
            self.assertTrue(game.save_run(), game.store.error)
            game.resume_run()
            self.assertEqual(game.state, 'REWARD')
            game.take_reward(0)
            next_node = next(n for row in game.run.grid for n in row if n.available)
            next_node.node_type = 'Merchant'
            game.enter_node(next_node)
            game.run.gold = 100
            game.open_service('upgrade')
            game.draw()
            creature = next(c for c in game.run.deck if c.is_creature)
            game.select_service_card(creature)
            game.draw()
            game.finish_service()
            self.assertTrue(creature.upgraded)
            pygame.quit()


if __name__ == '__main__':
    unittest.main()
