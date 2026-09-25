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
                    b.attack([c for c in b.player.board if not c.sick and not c.tapped])
                else:
                    b.end_turn()
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

    def test_all_screens_render_and_mouse_routes_to_new_screen(self):
        random.seed(12)
        game = Game(save_path=self.save_dir / 'run.json', progress_path=self.save_dir / 'unlocks.json')
        self.assertEqual(game.artwork.missing, [])
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 390)))
        self.assertEqual(game.state, 'PASSIVE')
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 770)))
        self.assertEqual(game.state, 'ACTIVE')
        game.draw()
        game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 770)))
        self.assertEqual(game.state, 'MAP')
        for state in ['MAP', 'DECK', 'DETAILS', 'ACHIEVEMENTS', 'COLLECTION', 'HELP', 'ABANDON', 'WIN', 'LOSS']:
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
        for index, passive in enumerate(meta['passives'] + UNLOCKS):
            for j, active in enumerate(meta['actives']):
                with self.subTest(passive=passive['name'], active=active['name']):
                    random.seed(index * 5 + j)
                    cmd = generate_procedural_commander(meta, [], [], passive, active)
                    run = Run(cmd, pool)
                    for _ in range(6):
                        choices = [n for row in run.grid for n in row if n.available]
                        node = random.choice(choices)
                        self.assertTrue(run.enter(node))
                        if node.node_type in ('Combat', 'Elite', 'Boss'):
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
        self.assertGreater(boss_wins, 0)


if __name__ == '__main__':
    unittest.main()
