"""Regression tests for distinct card identities and conditional mechanics."""
import json
import unittest
from collections import Counter
import test_expansion as fixtures
from engine import StackItem
from models import Card
from persistence import encode_graph, decode_graph


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ExpansionRules(); self.f.setUp()
        self.b = self.f.b
        self.b.enemy.hp = self.b.enemy.max_hp = 100

    def settle(self):
        self.f.resolve()

    def trigger(self, name, target=None):
        card = self.f.card(name)
        self.b.player.board.append(card)
        item = StackItem(card, self.b.player, target)
        item.ability = self.b.ability(card)
        self.b.resolve_trigger(item)
        return card

    def cast(self, name, target=None):
        card = self.f.card(name); self.b.player.hand.append(card)
        self.assertTrue(self.b.play(card, target))
        self.settle()
        return card

    def test_no_duplicate_structured_ability_definitions(self):
        for field in ('trigger', 'spell'):
            counts = Counter(json.dumps(c[field], sort_keys=True) for c in self.f.pool['cards'] if field in c)
            self.assertTrue(all(n == 1 for n in counts.values()), field)

    def test_special_tokens_double_and_have_different_mechanics(self):
        b = self.b; b.passive = 'Mirror Legion'
        self.trigger('Citadel Envoy')
        shields = [c for c in b.player.board if c.token]
        self.assertEqual(len(shields), 2)
        self.assertTrue(all(c.attack == 0 and c.max_health == 3 and b.has_keyword(c, 'guard') for c in shields))
        self.trigger('Cinder Artificer')
        sparks = [c for c in b.player.board if c.name == 'Cinder Spark']
        self.assertEqual(len(sparks), 2)
        self.assertTrue(all(not c.sick for c in sparks))

    def test_token_buffs_ignore_nontokens_and_are_permanent(self):
        b = self.b; b.tokens(b.player, 2)
        plain = self.f.card('Citadel Recruit'); b.player.board.append(plain)
        self.cast('Shared Resolve')
        self.assertEqual([c.attack for c in b.player.board], [2, 2, 1])
        b.end_cleanup()
        self.assertEqual([c.attack for c in b.player.board], [2, 2, 1])

    def test_freeze_skips_exactly_one_untap(self):
        target = self.f.card('Thorn Sentinel'); self.b.enemy.board = [target]
        self.trigger('Tidal Guardian')
        self.assertTrue(target.tapped)
        self.b.start_turn(self.b.enemy)
        self.assertTrue(target.tapped); self.assertFalse(target.frozen)
        self.b.start_turn(self.b.enemy)
        self.assertFalse(target.tapped)

    def test_once_per_turn_and_spell_count_reset_on_both_turns(self):
        b = self.b
        oracle = self.f.card('Tideglass Oracle'); b.player.board.append(oracle)
        self.cast('Magma Bolt')
        self.assertFalse(any('Tideglass Oracle: spell cast ability triggers' in s for s in b.log))
        self.cast('Magma Bolt'); self.cast('Magma Bolt')
        self.assertEqual(sum('Tideglass Oracle: spell cast ability triggers' in s for s in b.log), 1)
        b.start_turn(b.enemy)
        self.assertEqual(b.player.spells_this_turn, 0)
        b.player.colored_mana = dict.fromkeys('WUBRG', 30)
        self.cast('Magma Bolt'); self.cast('Magma Bolt')
        self.assertEqual(sum('Tideglass Oracle: spell cast ability triggers' in s for s in b.log), 2)

    def test_three_copy_creatures_have_distinct_lifetimes_and_stats(self):
        for name, permanent, small in [('Astra, Echo Conduit', False, False),
                                       ('Mirror Pathfinder', False, True), ('Prism Navigator', True, False)]:
            with self.subTest(name=name):
                self.setUp(); b = self.b
                target = self.f.card('Thorn Sentinel'); b.player.board.append(target)
                hp = b.player.hp
                self.trigger(name, target)
                copy = next(c for c in b.player.board if c.token)
                self.assertEqual(copy.attack, 1 if small else 4)
                self.assertTrue(copy.tapped)
                b.end_cleanup()
                self.assertEqual(copy in b.player.board, permanent)
                self.assertEqual(b.player.hp, hp - (3 if permanent else 0))

    def test_copy_fizzle_cancels_followup_draw_or_life_payment(self):
        for name in ('Mirror Pathfinder', 'Prism Navigator'):
            with self.subTest(name=name):
                self.setUp()
                target = self.f.card('Citadel Recruit')
                hand, hp = len(self.b.player.hand), self.b.player.hp
                self.trigger(name, target)  # Target has already left play.
                self.assertEqual(len(self.b.player.hand), hand)
                self.assertEqual(self.b.player.hp, hp)

    def test_scaling_is_capped_and_counts_live_board(self):
        b = self.b; b.tokens(b.player, 10)
        source = self.trigger('Dawn Procession Leader')
        self.assertEqual(sum(c.token for c in b.player.board), 15)
        b.player.hp = 1
        hp = b.enemy.hp
        self.trigger('Nightfall Harvester')
        self.assertEqual(b.enemy.hp, hp - 6)

    def test_reanimation_runs_entry_effect_and_respects_cost(self):
        b = self.b; b.player.hp = 10
        cheap = self.f.card('Dawn Medic'); costly = self.f.card('Thorn Sentinel')
        b.player.discard = [cheap, costly]
        self.trigger('Night Reclaimer')
        self.assertIn(cheap, b.player.board)
        self.assertIn(costly, b.player.discard)
        self.assertEqual(b.player.hp, 13)

    def test_sacrifice_triggers_death_and_draws(self):
        b = self.b; victim = self.f.card('Crypt Shambler'); b.player.board = [victim]
        size = len(b.player.hand); hp = b.enemy.hp
        self.cast('Funeral Offering', victim)
        self.assertNotIn(victim, b.player.board)
        self.assertEqual(len(b.player.hand), size + 3)
        self.assertEqual(b.enemy.hp, hp - 1)

    def test_loot_discards_highest_cost_after_drawing(self):
        b = self.b
        expensive = Card('Test giant', 'Cyber Fighter', 'G', 99, 9, 9)
        b.player.hand.append(expensive)
        size = len(b.player.hand)
        self.trigger('Mist Courier')
        self.assertEqual(len(b.player.hand), size + 1)
        self.assertNotIn(expensive, b.player.hand)
        self.assertTrue(any(c.name == 'Test giant' for c in b.player.discard))

    def test_vigilance_and_granted_trample_are_real_rules(self):
        b = self.b; attacker = self.f.card('Silverwing Chaplain'); attacker.sick = False
        b.player.board = [attacker]; b.enemy.board = []
        b.attack([attacker]); self.settle()
        self.assertFalse(attacker.tapped)
        b.finish_attack(); self.assertFalse(attacker.tapped)
        b.phase = 'MAIN'; b.player.colored_mana = dict.fromkeys('WUBRG', 30)
        self.cast('Titanic Mantle', attacker)
        defender = self.f.card('Crypt Shambler'); b.enemy.board = [defender]
        plan = b.damage_plan(b.player, [attacker], {attacker: [defender]})
        self.assertGreater(plan.get(b.enemy, 0), 0)

    def test_keyword_and_once_turn_state_survive_save(self):
        b = self.b; source = self.f.card('Spark Savant'); b.player.board = [source]
        self.cast('Magma Bolt')
        source.keywords = ['vigilance']; source.frozen = True
        restored = decode_graph(encode_graph(self.f.payload()), self.f.pool)['battle']
        saved = restored.player.board[0]
        self.assertEqual(saved.trigger_turn, restored.turn_serial)
        self.assertTrue(saved.frozen)
        self.assertTrue(restored.has_keyword(saved, 'vigilance'))

if __name__ == '__main__': unittest.main()
