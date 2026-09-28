"""Regression coverage for drag casting, attack triggers and token replacement."""
import unittest
from unittest import mock
import tempfile
from pathlib import Path
from collections import Counter
import pygame
import test_expansion as fixtures
from engine import StackItem
from models import Card
from persistence import encode_graph, decode_graph
from main import Game


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExpansionRules()
        self.fixture.setUp()
        self.b = self.fixture.b
        self.card = self.fixture.card

    def settle(self):
        for _ in range(100):
            if self.b.phase != 'RESPONSE':
                return
            self.b.pass_priority()
        self.fail('Trigger chain did not settle')

    def put(self, name, side=None):
        c = self.card(name); c.sick = False
        (side or self.b.player).board.append(c)
        return c

    def test_new_unlock_passives_and_stats(self):
        b = self.b
        b.passive = 'Radiant Foundry'
        b.tokens(b.player, 2)
        self.assertEqual([(c.attack, c.max_health) for c in b.player.board], [(2, 2), (2, 2)])
        self.assertEqual(b.run.stats['tokens_created'], 2)
        b.passive = 'Graveplate'
        b.player.board[0].current_health = 0
        before = b.player.armor
        b.cleanup_deaths()
        self.assertEqual(b.player.armor, before + 1)
        self.assertEqual(b.run.stats['friendly_deaths'], 1)
        b.passive = 'Rift Sanctuary'; b.player.hp = 10
        b.return_unit(b.player, b.player.board[0])
        self.assertEqual(b.player.hp, 12)
        self.assertEqual(b.run.stats['blink_returns'], 1)
        b.passive = 'Living Roots'
        land = b.player.land_reserve[0]
        self.assertTrue(b.play(land))
        self.assertEqual(b.player.hp, 14)
        self.assertEqual(b.run.stats['lands_played'], 1)
        b.passive = 'Runic Ward'
        spell = self.card('Magma Bolt'); b.player.hand.append(spell)
        self.assertTrue(b.play(spell))
        self.assertEqual(b.player.armor, before + 2)
        self.assertEqual(b.run.stats['spells_cast'], 1)
        self.assertFalse(b.play(spell))
        self.assertEqual(b.run.stats['spells_cast'], 1)

    def test_fifty_cards_per_faction(self):
        counts=Counter(c['archetype'] for c in self.fixture.pool['cards'])
        factions=['Token','Blink','Graveyard','Spells','Ramp','Morph']
        self.assertEqual({key: counts[key] for key in factions},dict.fromkeys(factions,50))

    def test_attack_copy_choice_stack_entry_and_exile(self):
        source=self.put('Astra, Echo Conduit'); target=self.put('Tide Scholar')
        self.b.enemy.board=[]
        before=len(self.b.player.hand)
        self.b.attack([source])
        self.assertEqual(self.b.phase,'ATTACK_TARGET')
        self.assertFalse(self.b.choose_attack_copy(source))
        self.assertTrue(self.b.choose_attack_copy(target))
        self.assertEqual(self.b.phase,'RESPONSE')
        self.assertEqual(self.b.targets('Null Sigil',self.b.enemy),[])
        self.settle()
        copies=[c for c in self.b.player.board if c.token]
        self.assertEqual(len(copies),1)
        self.assertIn(copies[0],self.b.attackers)
        self.assertTrue(copies[0].tapped)
        self.assertEqual(len(self.b.player.hand),before+1)
        self.b.finish_attack(); self.b.end_cleanup()
        self.assertNotIn(copies[0],self.b.player.board)
        self.assertNotIn(copies[0],self.b.player.discard)

    def test_doubler_recruits_copies_and_unlimited_board(self):
        self.b.passive='Mirror Legion'
        self.b.tokens(self.b.player,2)
        self.assertEqual(len(self.b.player.board),4)
        self.b.player.board=[]
        source=self.put('Astra, Echo Conduit'); target=self.put('Citadel Recruit')
        self.b.attack([source]); self.b.choose_attack_copy(target); self.settle()
        self.assertEqual(sum(c.token for c in self.b.player.board),2)
        self.b.tokens(self.b.player,20)
        self.assertEqual(len(self.b.player.board),44)
        self.b.enemy.board=[]; self.b.tokens(self.b.enemy,1)
        self.assertEqual(len(self.b.enemy.board),1)

    def test_copy_target_removed_fizzles(self):
        source=self.put('Mirror Pathfinder'); target=self.put('Citadel Recruit')
        self.b.attack([source]); self.b.choose_attack_copy(target)
        self.b.player.board.remove(target); self.settle()
        self.assertFalse(any(c.token for c in self.b.player.board))

    def test_attack_trigger_save_preserves_target_identity(self):
        source=self.put('Astra, Echo Conduit'); target=self.put('Citadel Recruit')
        self.b.attack([source])
        choice = decode_graph(encode_graph(self.fixture.payload()), self.fixture.pool)['battle']
        self.assertEqual(choice.phase, 'ATTACK_TARGET')
        self.assertIs(choice.attack_choices[0], choice.player.board[0])
        self.b.choose_attack_copy(target)
        restored=decode_graph(encode_graph(self.fixture.payload()), self.fixture.pool)['battle']
        self.assertIs(restored.stack[-1].target,restored.player.board[1])
        self.assertEqual(restored.stack[-1].ability['effect'],'copy')

    def test_spell_cast_ability_resolves_before_spell(self):
        self.put('Spark Savant'); card=self.card('Magma Bolt')
        self.b.player.hand.append(card)
        count=len(self.b.player.hand)
        self.assertTrue(self.b.play(card))
        self.assertEqual(len(self.b.stack),2)
        self.assertEqual(self.b.stack[-1].ability['effect'],'draw')
        self.b.pass_priority()
        self.assertEqual(len(self.b.player.hand),count)
        self.assertEqual(self.b.stack[-1].card.name,'Magma Bolt')

    def test_land_and_enter_triggers(self):
        source=self.put('Rootbound Sage')
        land=self.b.player.land_reserve[0]
        self.assertTrue(self.b.play(land))
        self.assertIs(self.b.stack[-1].card,source)
        self.settle()
        count=len(self.b.player.lands)
        before_plays = self.b.player.land_plays_remaining
        self.b.resolve_card(StackItem(self.card('Grove Tender'),self.b.player,None))
        self.settle()
        self.assertEqual(len(self.b.player.lands), count)
        self.assertEqual(self.b.player.land_plays_remaining, before_plays + 1)

    def test_death_triggers_finish_before_next_phase(self):
        self.put('Mourning Priest')
        dead=self.put('Citadel Recruit'); dead.attack=1; dead.current_health=1
        blocker=self.put('Thorn Sentinel',self.b.enemy)
        self.b.attack([dead]); self.b.finish_attack()
        self.assertEqual(self.b.phase,'RESPONSE')
        self.assertEqual(self.b.return_phase,'AFTER_PLAYER_COMBAT')
        self.settle(); self.assertEqual(self.b.phase,'MAIN2')

    def test_simultaneous_collector_death_still_drains(self):
        source=self.put('Soul Collector'); victim=self.put('Thorn Sentinel',self.b.enemy)
        before=self.b.enemy.hp
        source.current_health=victim.current_health=0
        self.b.cleanup_deaths()
        self.assertEqual(self.b.enemy.hp,before-1)


class DragTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.game=Game(Path(self.temp.name)/'run.json',Path(self.temp.name)/'progress.json')
        f=fixtures.ExpansionRules(); f.setUp()
        self.game.run=f.run; self.game.battle=f.b; self.game.state='BATTLE'
        self.card=f.card
        self.game.mouse_pos=lambda:(0,0)
        self.game.to_logical=lambda p:p

    def tearDown(self):
        pygame.quit(); self.temp.cleanup()

    def event(self,kind,**args):
        self.game.handle_event(pygame.event.Event(kind,args))

    def grab(self,card):
        self.game.battle.player.hand=[card]; self.game.draw()
        pos=self.game.hand_hits[0][1].center
        self.event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos)
        self.assertIs(self.game.drag_card,card)

    def test_release_casts_not_press_and_saves(self):
        card=self.card('Magma Bolt'); self.grab(card)
        self.assertIn(card,self.game.battle.player.hand)
        self.assertFalse(self.game.battle.stack)
        self.event(pygame.MOUSEBUTTONUP,button=1,pos=(500,450))
        self.assertIsNone(self.game.drag_card)
        self.assertIs(self.game.battle.stack[-1].card,card)
        self.assertTrue(self.game.store.exists())

    def test_invalid_drop_and_escape_preserve_mana(self):
        card=self.card('Magma Bolt'); self.grab(card)
        before=self.game.battle.available_mana(self.game.battle.player)
        self.event(pygame.MOUSEBUTTONUP,button=1,pos=(600,820))
        self.assertIn(card,self.game.battle.player.hand)
        self.assertEqual(before,self.game.battle.available_mana(self.game.battle.player))
        self.grab(card); self.event(pygame.KEYDOWN,key=pygame.K_ESCAPE)
        self.assertIsNone(self.game.drag_card)
        self.assertEqual(self.game.state,'BATTLE')

    def test_click_plays_untargeted_card_without_dragging(self):
        card = self.card('Citadel Recruit')
        self.game.battle.player.hand = [card]
        self.game.draw()
        pos = self.game.hand_hits[0][1].center
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=pos)
        self.assertNotIn(card, self.game.battle.player.hand)
        self.assertIs(self.game.battle.stack[-1].card, card)

    def test_keyboard_does_not_target_an_unplayable_card(self):
        card = self.card('Overcharge Bolt')
        self.game.battle.player.hand = [card]
        self.game.battle.phase = 'UPKEEP'
        self.game.play_card(card)
        self.assertIsNone(self.game.pending)
        self.assertIn('priority', self.game.message.lower())

    def test_cleanup_cards_are_selected_instead_of_dragged(self):
        while len(self.game.battle.player.hand) < 9:
            self.game.battle.player.hand.append(self.card('Citadel Recruit'))
        self.game.battle.phase = 'DISCARD'
        self.game.draw()
        _, rect, _ = self.game.hand_hits[len(self.game.hand_hits) // 2]
        card = self.game.hand_at(rect.center)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        self.assertIn(card, self.game.chosen)
        self.assertIsNone(self.game.drag_card)

    def test_number_keys_select_cleanup_discards(self):
        while len(self.game.battle.player.hand) < 9:
            self.game.battle.player.hand.append(self.card('Citadel Recruit'))
        self.game.battle.phase = 'DISCARD'
        card = self.game.battle.player.hand[0]
        self.event(pygame.KEYDOWN, key=pygame.K_1, unicode='1')
        self.assertIn(card, self.game.chosen)
        self.event(pygame.KEYDOWN, key=pygame.K_1, unicode='1')
        self.assertNotIn(card, self.game.chosen)

    def test_cleanup_selection_survives_save_and_resume(self):
        while len(self.game.battle.player.hand) < 9:
            self.game.battle.player.hand.append(self.card('Citadel Recruit'))
        self.game.battle.phase = 'DISCARD'
        selected = set(self.game.battle.player.hand[:2])
        selected_names = {card.name for card in selected}
        self.game.chosen = selected
        self.assertTrue(self.game.save_run())
        self.game.chosen.clear()
        self.game.resume_run()
        self.assertEqual(self.game.battle.phase, 'DISCARD')
        self.assertEqual({card.name for card in self.game.chosen}, selected_names)
        self.assertEqual(len(self.game.chosen), 2)

    def test_discard_suggestion_selects_exact_required_count(self):
        while len(self.game.battle.player.hand) < 10:
            self.game.battle.player.hand.append(self.card('Citadel Recruit'))
        self.game.battle.phase = 'DISCARD'
        self.game.suggest_discards()
        self.assertEqual(len(self.game.chosen), self.game.battle.required_discards())
        self.assertTrue(self.game.chosen.issubset(set(self.game.battle.player.hand)))

    def test_dragging_sixth_card_onto_third_reorders_hand(self):
        hand = [self.card(name) for name in ('Magma Bolt', 'Citadel Recruit', 'Null Sigil',
                'Thorn Sentinel', 'Dawn Medic', 'Overcharge Bolt')]
        self.game.battle.player.hand = hand[:]
        self.game.draw()
        positions = {card: rect.center for card, rect, _ in self.game.hand_hits}
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=positions[hand[5]])
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=positions[hand[2]])
        self.assertEqual(self.game.battle.player.hand,
                         [hand[0], hand[1], hand[5], hand[2], hand[3], hand[4]])
        self.assertIn('position 3', self.game.message)

    def test_unplayable_card_can_still_be_reordered(self):
        hand = [self.card('Citadel Recruit'), self.card('Thorn Sentinel'), self.card('Dawn Medic')]
        self.game.battle.player.hand = hand[:]
        self.game.battle.player.colored_mana = dict.fromkeys('WUBRGP', 0)
        self.game.draw()
        positions = {card: rect.center for card, rect, _ in self.game.hand_hits}
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=positions[hand[2]])
        self.assertIs(self.game.drag_card, hand[2])
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=positions[hand[0]])
        self.assertEqual(self.game.battle.player.hand, [hand[2], hand[0], hand[1]])

    def test_targeted_drop_and_counter_on_stack(self):
        target=self.card('Thorn Sentinel'); self.game.battle.enemy.board=[target]
        bolt=self.card('Overcharge Bolt'); self.grab(bolt)
        self.event(pygame.MOUSEBUTTONUP,button=1,pos=target.rect.center)
        self.assertIs(self.game.battle.stack[-1].target,target)
        self.game.battle.stack[-1].side=self.game.battle.enemy
        counter=self.card('Null Sigil'); self.grab(counter)
        item,rect=self.game.stack_hits[-1]
        self.event(pygame.MOUSEBUTTONUP,button=1,pos=rect.center)
        self.assertIs(self.game.battle.stack[-1].target,item)

    def test_click_spell_then_creature_keeps_target_selection(self):
        target = self.card('Thorn Sentinel')
        self.game.battle.enemy.board = [target]
        bolt = self.card('Overcharge Bolt')
        self.grab(bolt)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=self.game.drag_start)
        self.assertIs(self.game.pending, bolt)
        self.assertIsNone(self.game.drag_card)
        self.game.draw()
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=target.rect.center)
        self.assertIs(self.game.battle.stack[-1].target, target)
        self.assertIsNone(self.game.pending)

    def test_run_results_distinguish_new_old_and_partial_unlocks(self):
        g = self.game
        g.progress.unlocked.add('Mind Vault')
        g.run.stats.update(cards_drawn=6, kills=10, tokens_created=7)
        g.state = 'LOSS'
        rows = {r['name']: r for r in g.unlock_results()}
        self.assertEqual(rows['Mind Vault']['status'], 'ALREADY UNLOCKED')
        self.assertEqual(rows['Endless Horde']['status'], 'NEW UNLOCK')
        self.assertEqual(rows['Radiant Foundry']['count'], 7)
        self.assertEqual(rows['Radiant Foundry']['remaining'], 13)
        g.draw()
        g.state = 'WIN'; g.draw()
        g.unlock_results()
        self.assertEqual(g.recent_unlocks.count('Endless Horde'), 1)
        g.state = 'BATTLE'; g.save_run(); g.resume_run()
        self.assertEqual(next(r for r in g.unlock_results() if r['name'] == 'Endless Horde')['status'], 'NEW UNLOCK')

    def test_token_piles_regroup_by_live_stats_not_buff_history(self):
        b = self.game.battle
        b.tokens(b.player, 6)
        first, second, third = b.player.board[:3]
        first.attack += 1; first.max_health += 1; first.current_health += 1
        groups = self.game.board_groups(b.player)
        self.assertEqual(sorted(map(len, groups)), [1, 5])
        # A later turn buffs two more tokens to the same permanent stats.
        b.end_cleanup()
        for c in (second, third):
            c.attack += 1; c.max_health += 1; c.current_health += 1
        groups = self.game.board_groups(b.player)
        self.assertEqual(sorted(map(len, groups)), [3, 3])
        merged = next(g for g in groups if first in g)
        self.assertEqual(set(merged), {first, second, third})
        first.tapped = True
        self.assertEqual(sorted(map(len, self.game.board_groups(b.player))), [1, 2, 3])
        first.tapped = False; first.current_health -= 1
        self.assertEqual(sorted(map(len, self.game.board_groups(b.player))), [1, 2, 3])
        first.current_health = first.max_health
        self.assertEqual(sorted(map(len, self.game.board_groups(b.player))), [3, 3])

    def test_pile_single_attack_and_count_select_all(self):
        b = self.game.battle
        b.phase = 'COMBAT'
        b.tokens(b.player, 30)
        for c in b.player.board:
            c.sick = False
        self.game.draw()
        top, rect = self.game.board_hits[0]
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        self.assertEqual(len(self.game.chosen), 1)
        self.game.draw()
        groups = self.game.board_groups(b.player)
        remaining = next(g for g in groups if len(g) == 29)
        _, rect = next((c, r) for c, r in self.game.board_hits if c in remaining)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(rect.right - 20, rect.top))
        self.assertEqual(len(self.game.chosen), 30)
        self.game.draw()
        self.assertEqual(len(self.game.board_groups(b.player)), 1)
        self.game.select_pile(b.player.board)
        self.assertFalse(self.game.chosen)

    def test_large_unique_board_paging_and_visible_targets(self):
        b = self.game.battle
        for i in range(24):
            card = self.card('Thorn Sentinel')
            b.summon(b.player, card)
        self.game.draw()
        self.assertEqual(len(self.game.board_groups(b.player)), 24)
        self.assertEqual(len(self.game.board_hits), 14)
        self.assertEqual(len({rect.y for _, rect in self.game.board_hits}), 2)
        self.game.board_page(True, 3); self.game.draw()
        self.assertEqual(len(self.game.board_hits), 10)
        self.assertIs(self.game.drop_target(self.game.board_hits[-1][1].center), b.player.board[-1])

    def test_hover_lift_disappears_on_grab(self):
        card=self.card('Magma Bolt'); self.game.battle.player.hand=[card]; self.game.draw()
        pos=self.game.hand_hits[0][1].center
        self.game.mouse_pos=lambda:pos
        self.game.draw()
        self.assertIs(self.game.hand_hover,card)
        self.assertIsNotNone(self.game.lifted_rect)
        keys = {pygame.K_LALT: True}
        with mock.patch('pygame.key.get_pressed', return_value=keys):
            self.game.draw()
            self.assertIsNotNone(self.game.lifted_rect)
        self.event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos)
        self.game.draw()
        self.assertIsNone(self.game.hand_hover)
        self.assertIsNone(self.game.lifted_rect)

    def test_hover_modifier_lists_morph_counters_and_temporary_buffs(self):
        card = self.card('Citadel Recruit')
        self.game.battle.player.board = [card]
        self.game.battle.morph(self.game.battle.player, card, 'insight')
        card.attack += 2; card.max_health += 1; card.current_health += 1
        card.temp_attack = 2; card.temp_health = 1
        details = self.game.card_modifier_details(card)
        self.assertTrue(any('Insight Morph' in item for item in details))
        self.assertTrue(any('Temporary buff: +2/+1' in item for item in details))
        self.assertEqual(card.plus_one_counters, 1)

if __name__=='__main__': unittest.main()
