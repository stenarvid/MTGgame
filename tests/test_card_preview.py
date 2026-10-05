import unittest
from tactical.preview import fixture
from tactical.battle import RuleError
from tactical.content import CARD_MAP

class ReviewRules(unittest.TestCase):
    def test_timing_and_priority(self):
        b=fixture('combat');c=b.players[0]['board'][0]
        self.assertFalse(b.ability_options(0,c)[0]['available'])
        self.assertFalse(b.ability_options(0,c)[1]['available'])
        recruit=b.players[0]['board'][1]
        self.assertTrue(b.ability_options(0,recruit)[0]['available'])
        with self.assertRaises(RuleError): b.action(0,'ability',uid=c['uid'],ability=0,target=recruit['uid'])
        b=fixture('response');c=b.players[0]['board'][0]
        self.assertTrue(b.ability_options(0,c)[1]['available'])
        self.assertFalse(b.ability_options(1,c)[1]['available'])

    def test_costs_are_paid_before_responses_and_priority_is_not_skipped(self):
        b=fixture();c=b.players[0]['board'][1];amount=sum(b.players[0]['mana'].values())
        b.action(0,'ability',uid=c['uid'],target=c['uid'])
        self.assertTrue(c['tapped']);self.assertFalse(c['protected'])
        self.assertEqual(sum(b.players[0]['mana'].values()),amount-1)
        for i in range(1): b.action(b.priority,'pass');self.assertEqual(len(b.stack),1)
        b.action(b.priority,'pass');self.assertTrue(c['protected']);self.assertEqual(b.priority,b.active)

    def test_source_removal_does_not_remove_pending_ability(self):
        b=fixture('source');source=b.players[0]['board'][1];target=b.players[0]['board'][2]
        b.move_out(b.players[0],source,'exile')
        while b.stack: b.action(b.priority,'pass')
        self.assertTrue(target['protected'])

    def test_invalidated_target_has_no_effect_and_costs_stay_spent(self):
        b=fixture('invalid');source=b.players[1]['board'][2];target=b.players[0]['board'][1]
        mana=b.players[1]['mana'].copy();b.move_out(b.players[0],target,'hand')
        while b.stack: b.action(b.priority,'pass')
        self.assertEqual(target['damage'],0);self.assertTrue(source['tapped']);self.assertEqual(b.players[1]['mana'],mana)
        self.assertTrue(any('fizzles' in entry for entry in b.log))

    def test_counter_can_stop_an_ability(self):
        b=fixture('response');spell=next(c for c in b.players[0]['hand'] if c['id']=='u_counter');target=b.players[0]['board'][1]
        b.action(0,'cast',uid=spell['uid'],target=b.stack[0]['uid'])
        while b.stack: b.action(b.priority,'pass')
        self.assertEqual(target['damage'],0)

    def test_combat_choice_costs_can_remove_attack_option(self):
        b=fixture('combat');c=b.players[0]['board'][1]
        b.action(0,'ability',uid=c['uid'],target=c['uid'])
        while b.stack: b.action(b.priority,'pass')
        with self.assertRaises(RuleError): b.action(0,'attack',attacks=[dict(uid=c['uid'],defender=1)])

    def test_buffs_have_source_duration_and_expire(self):
        b=fixture('buffs');c=b.players[0]['board'][1]
        self.assertEqual(b.stats(c),(5,7))
        self.assertEqual(len(c['buffs']),5)
        self.assertTrue(all(all(k in x for k in ('name','effect','source','duration')) for x in c['buffs']))
        b.start_turn(0)
        self.assertEqual(b.stats(c),(1,3))
        self.assertFalse(any(x['duration']=='Until your next turn' for x in c['buffs']))

    def test_blocker_ability_has_a_response_window_before_block_choice(self):
        b=fixture('blocks');c=b.players[0]['board'][1]
        b.action(0,'ability',uid=c['uid'],target=c['uid'])
        self.assertEqual(b.phase,'block_ability_response')
        for _ in range(2): b.action(b.priority,'pass')
        self.assertEqual(b.priority,b.active)
        for _ in range(2): b.action(b.priority,'pass')
        self.assertEqual(b.phase,'blocks');self.assertEqual(b.priority,0)
        self.assertTrue(c['protected'])

    def test_fixtures_do_not_modify_card_pool(self):
        import copy
        before=copy.deepcopy(CARD_MAP)
        for scenario in ('main','combat','blocks','response','invalid','source','buffs'): fixture(scenario)
        self.assertEqual(CARD_MAP,before)

if __name__=='__main__': unittest.main()

class AutomaticResponses(unittest.TestCase):
    def test_unavailable_responses_resolve_without_spending_resources(self):
        b=fixture('response')
        for p in b.players: p['mana']={};p['temporary']=0
        target=b.players[0]['board'][1]
        self.assertFalse(b.has_legal_response(0))
        self.assertGreater(b.auto_pass_unavailable(),0)
        self.assertFalse(b.stack)
        self.assertEqual(target['damage'],3)
        self.assertEqual(b.phase,'main')

    def test_usable_ability_and_instant_preserve_manual_response(self):
        b=fixture('response')
        self.assertTrue(b.has_legal_response(0))
        self.assertEqual(b.auto_pass_unavailable(),0)
        self.assertEqual(len(b.stack),1)
        for p in b.players: p['board']=[]
        self.assertTrue(b.has_legal_response(0))  # Blue counter can target the pending action.

    def test_mandatory_and_main_decisions_are_never_automatic(self):
        for scenario in ('main','grow','combat','blocks'):
            b=fixture(scenario)
            for p in b.players: p['mana']={};p['temporary']=0
            phase=b.phase
            self.assertEqual(b.auto_pass_unavailable(),0)
            self.assertEqual(b.phase,phase)

    def test_ward_can_make_only_target_unaffordable(self):
        b=fixture('response')
        for p in b.players: p['hand']=[]
        b.players[0]['board']=[]
        source=b.players[1]['board'][2]
        source['abilities'][0]['target']='enemy'
        source['abilities'][0]['cost']=1
        b.players[0]['board']=[b.instance('w_recruit',0)]
        b.players[0]['board'][0]['keywords']=['Ward']
        b.players[1]['board']=[source]
        b.priority=1;b.players[1]['mana']={'U':1};b.players[1]['temporary']=0
        self.assertFalse(b.has_legal_response(1))

class SpellPresentationEvents(unittest.TestCase):
    def test_cast_and_resolution_events_include_public_source(self):
        b=fixture('fire');card=b.players[0]['hand'][0];target=b.players[1]['board'][0]
        b.action(0,'cast',uid=card['uid'],target=target['uid'])
        event=b.view(1)['visual_events'][-1]
        self.assertEqual(event['stage'],'cast');self.assertEqual(event['card_id'],'r_bolt')
        self.assertEqual(event['source_uid'],card['uid'])
        self.assertNotIn('hand',event);self.assertNotIn('deck',event)
        while b.stack:b.action(b.priority,'pass')
        self.assertEqual(b.visual_events[-1]['stage'],'resolve')
        self.assertEqual(b.visual_events[-1]['outcome'],'resolved')

    def test_fizzle_is_never_a_successful_impact(self):
        b=fixture('invalid');target=b.players[0]['board'][1]
        b.move_out(b.players[0],target,'hand')
        while b.stack:b.action(b.priority,'pass')
        self.assertEqual(b.visual_events[-1]['outcome'],'fizzle')

    def test_counter_records_cancelled_spell(self):
        b=fixture('response');original=b.stack[0]['uid']
        counter=next(c for c in b.players[0]['hand'] if c['id']=='u_counter')
        b.action(0,'cast',uid=counter['uid'],target=original)
        while b.stack:b.action(b.priority,'pass')
        cancelled=[e for e in b.visual_events if e['action_uid']==original and e['stage']=='resolve']
        self.assertEqual([e['outcome'] for e in cancelled],['countered'])

    def test_meteor_events_retain_destroyed_creature_positions(self):
        b=fixture('meteors');uids={c['uid'] for p in b.players for c in p['board']}
        b.action(0,'cast',uid=b.players[0]['hand'][0]['uid'])
        while b.stack:b.action(b.priority,'pass')
        self.assertEqual(set(b.visual_events[-1]['affected_uids']),uids)

    def test_every_design_has_a_presentation_profile(self):
        import json
        from pathlib import Path
        from tactical.content import CARDS,COMMANDERS,RELICS
        profiles=json.loads((Path(__file__).parents[1]/'tactical/web/effect-profiles.json').read_text())
        for card in CARDS+COMMANDERS:
            self.assertIn(card['id'],profiles)
        for relic in RELICS:self.assertIn('relic_'+relic['id'],profiles)
        self.assertIn('token_recruit',profiles)

    def test_pending_arrival_is_public_but_does_not_enter_early(self):
        b=fixture('summon');c=b.players[0]['hand'][0];uid=c['uid']
        b.action(0,'cast',uid=uid)
        self.assertFalse(any(x['uid']==uid for x in b.players[0]['board']))
        view=b.view(1)
        self.assertEqual(view['stack'][-1]['public_card']['name'],c['name'])
        self.assertEqual(view['players'][0]['hand'],[])
        while b.stack:b.action(b.priority,'pass')
        self.assertIn(uid,b.visual_events[-1]['results']['entries'])

    def test_combat_visual_event_preserves_block_assignment_after_death(self):
        b=fixture('combatanim');attack=b.attacks[0]['uid'];blocker=b.players[0]['board'][0]['uid']
        b.action(0,'block',blocks={attack:[blocker]})
        for _ in range(8):
            if b.phase=='main2':break
            b.action(b.priority,'pass')
        event=next(e for e in b.visual_events if e['stage']=='combat')
        self.assertEqual(event['attacks'][0]['blockers'],[blocker])
        self.assertIn(attack,event['results']['departures'])
        self.assertNotIn(attack,[c['uid'] for c in b.players[1]['board']])
