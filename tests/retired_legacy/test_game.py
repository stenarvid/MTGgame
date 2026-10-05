"""Headless screen/input coverage and seeded complete-run exercises."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import random
import tempfile
from pathlib import Path
import unittest
import pygame

from engine import Battle, Run, UNLOCKS
from main import Game
from models import Card, generate_procedural_commander, load_game_data


def autoplay(battle):
    """Exercise legal phase transitions, responses and complete fights."""
    b = battle
    for _ in range(1500):
        if b.result:
            return b.result
        if b.phase == 'MULLIGAN':
            b.keep_hand()
        elif b.phase == 'ATTACK_TARGET':
            targets = b.copy_targets(b.attack_choices[0])
            b.choose_attack_copy(targets[0] if targets else None)
        elif b.phase == 'RESPONSE':
            counter = next((c for c in b.player.hand if c.name == 'Null Sigil' and b.can_pay(b.player, c)), None)
            targets = b.targets('Null Sigil')
            if counter and targets:
                b.play(counter, targets[-1])
            else:
                b.pass_priority()
        elif b.phase == 'UPKEEP':
            b.finish_upkeep()
        elif b.phase in ('MAIN', 'MAIN2'):
            if not b.active_used:
                targets = b.targets(b.active)
                target = b.player if b.active == 'Holy Light' else b.enemy if b.active == 'Flame Burst' else next((c for c in targets if c in b.enemy.board), None)
                if target or b.active == 'Wild Growth':
                    b.use_active(target)
            if b.result:
                continue
            played = False
            for card in sorted(list(b.player.hand), key=lambda c: (c.card_type != 'Land', not c.is_creature)):
                target = b.ai_target(card, b.player)
                if b.play(card, target):
                    played = True
                    break
            if not played:
                if b.phase == 'MAIN':
                    b.begin_combat()
                else:
                    b.begin_end_step()
        elif b.phase == 'COMBAT':
            b.attack([c for c in b.player.board if not c.sick and not c.tapped])
        elif b.phase == 'END':
            b.end_turn()
        elif b.phase == 'DISCARD':
            excess = b.required_discards()
            b.discard_to_hand_limit(sorted(b.player.hand, key=lambda c: c.mana_cost)[:excess])
        elif b.phase == 'ATTACK_RESPONSE':
            b.finish_attack()
        elif b.phase == 'BLOCK':
            blockers = [c for c in b.player.board if not c.tapped]
            for attacker, blocker in zip(b.attackers, blockers):
                b.assign_blocker(attacker, blocker)
            b.finish_blocks()
        elif b.phase == 'DEFEND_RESPONSE':
            b.finish_blocks()
        else:
            raise AssertionError('Unexpected phase: ' + b.phase)
        assert len(set(b.player.board)) == len(b.player.board)
        assert len(set(b.enemy.board)) == len(b.enemy.board)
        assert b.player.mana >= 0 and b.enemy.mana >= 0
    raise AssertionError('Battle did not resolve within 1500 phase transitions')


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.save_dir = Path(self.temp.name)

    def map_game(self):
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.addCleanup(pygame.quit)
        game.begin_builder()
        game.choose(game.choices[0])
        game.choose(game.choices[0])
        game.confirm_builder()
        return game

    def click_logical(self, game, x, y):
        viewport = game.viewport()
        position = (round(viewport.x + x * viewport.w / 1280),
                    round(viewport.y + y * viewport.h / 900))
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position))

    def test_mana_cost_is_split_into_arena_style_symbols(self):
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.addCleanup(pygame.quit)
        card = Card('Test Spell', 'Instant Spell', 'W', 4)
        self.assertEqual(game.card_painter.mana_symbols(card), ['3', 'W'])
        card.pips = {'U': 2, 'P': 1}
        self.assertEqual(game.card_painter.mana_symbols(card, 6), ['3', 'U', 'U', 'P'])

    def test_run_setup_controls_boss_count(self):
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.addCleanup(pygame.quit)
        game.start_builder()
        self.assertEqual(game.state, 'RUN_SETUP')
        game.run_bosses = 7
        game.begin_builder()
        game.choose(game.choices[0]); game.choose(game.choices[0])
        game.confirm_builder()
        self.assertEqual(game.run.total_areas, 7)

    def test_builder_reroll_and_two_passive_mode(self):
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.addCleanup(pygame.quit)
        game.builder_mode = 'two_passives'
        game.begin_builder()
        before = [choice['name'] for choice in game.choices]
        game.reroll_builder()
        self.assertEqual(len(game.choices), 4)
        game.choose(game.choices[0])
        self.assertEqual(game.state, 'SECOND_PASSIVE')
        self.assertTrue(all(choice['name'] != game.passive['name'] for choice in game.choices))
        game.choose(game.choices[0])
        self.assertEqual(game.state, 'BUILDER_REVIEW')
        game.confirm_builder()
        self.assertEqual(len(game.run.commander.passive_names), 2)
        self.assertIsNone(game.run.commander.active_name)

    def test_builder_requires_confirmation_and_back_preserves_choices(self):
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.addCleanup(pygame.quit)
        game.begin_builder()
        first_offers = list(game.choices)
        game.choose(first_offers[0])
        second_offers = list(game.choices)
        game.choose(second_offers[0])
        self.assertEqual(game.state, 'BUILDER_REVIEW')
        self.assertIsNone(game.run)
        self.assertFalse(game.store.exists())
        game.draw()
        game.save_run()
        self.assertFalse(game.store.exists())
        game.back_builder()
        self.assertEqual(game.state, 'ACTIVE')
        self.assertEqual(game.choices, second_offers)
        game.back_builder()
        self.assertEqual(game.state, 'PASSIVE')
        self.assertEqual(game.choices, first_offers)
        game.choose(first_offers[1])
        game.choose(game.choices[0])
        self.assertTrue(game.confirm_builder())
        self.assertEqual(game.run.commander.passive_name, first_offers[1]['name'])
        self.assertEqual(game.state, 'MAP')
        self.assertTrue(game.store.exists())
        self.assertFalse(game.confirm_builder())

    def test_pausing_unconfirmed_builder_does_not_overwrite_existing_run(self):
        game = self.map_game()
        saved = game.store.path.read_bytes()
        game.begin_builder()
        game.choose(game.choices[0])
        game.choose(game.choices[0])
        game.resume_state = game.state
        game.state = 'PAUSE'
        self.assertTrue(game.save_run())
        self.assertEqual(game.store.path.read_bytes(), saved)

    def test_builder_fullscreen_toggle_and_scene_filled_letterbox(self):
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.addCleanup(pygame.quit)
        game.begin_builder()
        game.window = pygame.display.set_mode((1000, 500), pygame.RESIZABLE)
        game.windowed_size = (1000, 500)
        game.draw(); game.present()
        viewport = game.viewport()
        self.assertGreater(viewport.x, 0)
        self.assertNotEqual(game.window.get_at((5, 5))[:3], (5, 7, 13))
        game.toggle_fullscreen()
        self.assertTrue(game.fullscreen)
        game.toggle_fullscreen()
        self.assertFalse(game.fullscreen)
        self.assertEqual(game.window.get_size(), (1000, 500))

    def test_map_icons_and_labels_are_clickable_at_window_sizes(self):
        game = self.map_game()
        for size in ((1280, 900), (960, 675), (640, 450), (1400, 700)):
            for label in (False, True):
                with self.subTest(size=size, label=label):
                    game.run = Run(game.run.commander, game.pool)
                    game.battle = None
                    game.state = 'MAP'
                    game.window = pygame.display.set_mode(size, pygame.RESIZABLE)
                    game.draw()
                    node = game.run.grid[0][0]
                    point = (node.x, node.y + (57 if label else 25))
                    self.assertTrue(node.rect.collidepoint(point))
                    self.click_logical(game, *point)
                    self.assertEqual(game.state, 'BATTLE')
                    self.assertIs(game.run.node, node)
                    self.assertEqual(game.battle.phase, 'MULLIGAN')

    def test_map_click_after_resume_and_locked_location_feedback(self):
        game = self.map_game()
        game.resume_run()
        game.draw()
        locked = game.run.grid[1][0]
        self.click_logical(game, locked.x, locked.y + 25)
        self.assertEqual(game.state, 'MAP')
        self.assertIsNone(game.run.node)
        self.assertIn('green', game.message)
        node = game.run.grid[0][0]
        self.click_logical(game, node.x, node.y + 57)
        self.assertEqual(game.state, 'BATTLE')

    def test_map_progression_through_every_encounter_and_boss(self):
        game = self.map_game()
        for row, kind in enumerate(('Combat', 'Merchant', 'Rest', 'Treasure', 'Elite', 'Boss')):
            node = next(n for n in game.run.grid[row] if n.available)
            node.node_type = kind
            game.draw()
            self.click_logical(game, node.x, node.y + 57)
            if kind in ('Combat', 'Elite', 'Boss'):
                game.keep_hand()
                game.battle.enemy.hp = 0
                game.battle.check_result()
                game.end_battle()
                self.assertEqual(game.state, 'REWARD')
                game.take_reward()
            elif kind == 'Merchant':
                game.leave_shop()
            elif kind == 'Rest':
                game.rest()
            else:
                game.take_relic(0)
            self.assertTrue(node.visited)
            self.assertIsNone(game.run.node)
            self.assertFalse(game.run.reward_pending)
            self.assertEqual(game.state, 'MAP')
        self.assertEqual(game.run.area, 2)
        self.assertFalse(game.run.won)

    def test_fourth_area_boss_is_the_run_victory(self):
        game = self.map_game()
        for expected_area in range(1, 5):
            boss = game.run.grid[-1][0]
            for row in game.run.grid:
                for node in row:
                    node.available = False
            boss.available = True
            self.assertTrue(game.run.enter(boss))
            self.assertTrue(game.run.finish())
            if expected_area < 4:
                self.assertEqual(game.run.area, expected_area + 1)
                self.assertFalse(game.run.won)
                self.assertTrue(all(node.available for node in game.run.grid[0]))
            else:
                self.assertTrue(game.run.won)

    def test_all_screens_render_and_mouse_routes_to_new_screen(self):
        random.seed(12)
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.assertEqual(game.artwork.missing, [])
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(900, 560)))
        self.assertEqual(game.state, 'RUN_SETUP')
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 584)))
        self.assertEqual(game.state, 'PASSIVE')
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 770)))
        self.assertEqual(game.state, 'ACTIVE')
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 770)))
        self.assertEqual(game.state, 'BUILDER_REVIEW')
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(900, 810)))
        self.assertEqual(game.state, 'MAP')
        for state in ['MAP', 'DECK', 'DETAILS', 'ACHIEVEMENTS', 'COLLECTION', 'HELP', 'TUTORIAL', 'ABANDON', 'WIN', 'LOSS']:
            game.state = state
            game.draw()
        node = game.run.grid[0][0]
        game.enter_node(node)
        self.assertEqual(game.state, 'BATTLE')
        game.draw()
        game.card_painter.preview(game.screen, game.run.deck[0], 1250, 880)
        for state in ['BATTLE_HELP', 'REST']:
            game.state = state
            game.draw()
        game.run.node = None
        node.node_type = 'Merchant'
        game.enter_node(node)
        game.draw()
        game.run.node = None
        node.node_type = 'Treasure'
        game.enter_node(node)
        game.draw()
        game.state = 'BATTLE'
        game.pending = game.battle.player.hand[0]
        game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsNone(game.pending)
        pygame.quit()

    def test_seeded_full_runs_cover_all_commander_combinations(self):
        _, meta, pool = load_game_data()
        results = {'VICTORY': 0, 'DEFEAT': 0}
        boss_wins = 0
        boss_encounters = 0
        for index, passive in enumerate(meta['passives'] + UNLOCKS):
            for j, active in enumerate(meta['actives']):
                with self.subTest(passive=passive['name'], active=active['name']):
                    random.seed(index * 5 + j)
                    cmd = generate_procedural_commander(meta, [], [], passive, active)
                    run = Run(cmd, pool)
                    run.total_areas = 1
                    for _ in range(6):
                        if run.won:
                            break
                        choices = [n for row in run.grid for n in row if n.available]
                        node = random.choice(choices)
                        self.assertTrue(run.enter(node))
                        if node.node_type in ('Combat', 'Elite', 'Boss'):
                            boss_encounters += node.node_type == 'Boss'
                            battle = Battle(run)
                            result = autoplay(battle)
                            results[result] += 1
                            if result == 'DEFEAT':
                                break
                            self.assertGreater(battle.collect_reward(), 0)
                            run.take_card_reward(0)
                        elif node.node_type == 'Rest':
                            run.rest()
                        elif node.node_type == 'Treasure':
                            run.take_relic(0)
                        else:
                            for k in range(len(run.shop)):
                                run.buy(k)
                            run.finish()
                    if run.won:
                        boss_wins += 1
        self.assertGreater(results['VICTORY'], 0)
        self.assertGreater(results['DEFEAT'], 0)
        self.assertGreater(boss_encounters, 0)


if __name__ == '__main__':
    unittest.main()
