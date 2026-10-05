"""Validate the structured expansion effects with real stack resolution."""
import unittest
import test_expansion as fixtures
from engine import StackItem
from models import Card


class ContentTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.ExpansionRules(); f.setUp()
        f.b.enemy.hp=f.b.enemy.max_hp=100
        f.b.player.hp=10
        return f

    def test_all_fifty_structured_spells_cast_and_resolve(self):
        pool=self.fixture().pool
        spells=[c for c in pool['cards'] if c.get('spell')]
        self.assertGreaterEqual(len(spells),130)
        for data in spells:
            with self.subTest(card=data['name']):
                f=self.fixture(); b=f.b
                friend=f.card('Thorn Sentinel'); foe=f.card('Thorn Sentinel')
                b.player.board=[friend]; b.enemy.board=[foe]
                b.player.discard=[f.card('Citadel Recruit') for _ in range(5)]
                card=Card.from_dict(data); b.player.hand.append(card)
                target=b.ai_target(card,b.player)
                self.assertTrue(b.play(card,target))
                f.resolve()
                self.assertFalse(b.stack)
                self.assertNotIn(card,b.player.hand)
                self.assertTrue(any(c.name==card.name for c in b.player.discard))
                self.assertFalse(any('No implemented effect' in line or 'fizzles' in line for line in b.log))

    def test_target_required_and_fizzle_are_atomic(self):
        f=self.fixture();b=f.b;card=f.card('Grave Sentence');b.player.hand.append(card)
        mana=b.available_mana(b.player)
        self.assertFalse(b.play(card));self.assertEqual(b.available_mana(b.player),mana)
        target=f.card('Citadel Recruit');b.enemy.board=[target]
        self.assertTrue(b.play(card,target));b.enemy.board.remove(target)
        f.resolve()
        self.assertTrue(any('fizzles' in line for line in b.log))

    def test_new_effect_numbers_and_upgrade(self):
        f=self.fixture();b=f.b
        card=f.card('Scorching Arc');card.upgrade();b.player.hand.append(card)
        self.assertTrue(b.play(card,b.enemy));f.resolve()
        self.assertEqual(b.enemy.hp,95)
        card=f.card('Titanic Mantle'); target=f.card('Thorn Sentinel')
        b.player.board=[target];b.player.hand.append(card)
        self.assertTrue(b.play(card,target));f.resolve()
        self.assertEqual((target.attack,target.max_health),(9,9))
        b.end_cleanup();self.assertEqual((target.attack,target.max_health),(4,4))

    def test_red_encounter_bonus_applies_to_entire_area_spell(self):
        f=self.fixture();b=f.b;b.theme='R';b.boss=False
        b.player.board=[f.card('Thorn Sentinel'),f.card('Thorn Sentinel')]
        b.resolve_card(StackItem(f.card('Rain of Embers'),b.enemy,None))
        self.assertEqual([c.current_health for c in b.player.board],[1,1])
        self.assertTrue(b.enemy_damage_bonus_used)

    def test_every_new_creature_trigger_has_a_supported_effect(self):
        supported={'copy','tokens','draw','heal','damage','drain','recall','land','search','team_buff','self_buff',
                   'buff_group','custom_tokens','loot','freeze','mill','reanimate','grant_keyword','recover_spell','armor',
                   'untap_lands','power_damage','morph_self'}
        pool=self.fixture().pool
        creatures=[c for c in pool['cards'] if c.get('trigger')]
        self.assertGreaterEqual(len(creatures),144)
        for data in creatures:
            with self.subTest(card=data['name']):
                f=self.fixture();b=f.b
                card=Card.from_dict(data);b.player.board=[card]
                target=f.card('Citadel Recruit');b.player.board.append(target)
                item=StackItem(card,b.player,target);item.ability=data['trigger']
                self.assertIn(item.ability['effect'],supported)
                b.resolve_trigger(item)
                self.assertTrue(any('ability resolves' in line for line in b.log))

    def test_every_faction_has_fifty_unique_cards(self):
        pool=self.fixture().pool
        for faction in ('Token','Blink','Graveyard','Spells','Ramp','Morph'):
            cards=[card for card in pool['cards'] if card.get('archetype') == faction]
            self.assertEqual(len(cards),50,faction)
            self.assertEqual(len({card['name'] for card in cards}),50,faction)
            designs={(card['type'],card['cost'],card.get('atk',0),card.get('hp',0),
                      str(card.get('trigger')),str(card.get('spell')),card.get('text')) for card in cards}
            self.assertEqual(len(designs),50,f'{faction} contains duplicate card designs')

if __name__=='__main__':unittest.main()
