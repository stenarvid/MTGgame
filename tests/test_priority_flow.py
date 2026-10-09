"""Priority convenience controls must preserve authoritative rules and clocks."""
import copy
import json
import time
import unittest
from unittest.mock import patch
from tactical.battle import Battle, RuleError
from tactical.content import COMMANDER_MAP, starter
from tactical.session import Session
from tactical.priority import preferences
from tactical.items import compose


def session(mode='human'):
    s = Session(mode, seed=17)
    for i, cmd in enumerate(('tide', 'ember')):
        s.add_member('Player '+str(i))
        s.members[i].update(seat=i, commander=cmd, package=0, relic=None)
    builds = [dict(name=m['name'], commander=m['commander'], package=0,
                   relic=None, deck=starter(COMMANDER_MAP[m['commander']]['colors'])) for m in s.members]
    s.battle = Battle(builds, 17)
    s.stage = 'battle'
    s.results_applied = False
    b = s.battle
    b.phase = 'precombat'
    b.active = b.priority = 0
    for m, p in zip(s.members, b.players):
        preferences(m)
        p.update(kept=True, hand=[], mana={'U':4, 'R':4}, capacity={'U':4}, turns=1)
    return s


class PriorityFlow(unittest.TestCase):
    def test_defaults_and_polling_do_not_renew_response_window(self):
        s=session();b=s.battle
        b.players[0]['hand']=[b.instance('u_counter',0)]
        b.push(1,'tokens',amount=1,name='Opponent spell')
        now=time.time()
        s.tick(now);deadline=s.response_deadline
        self.assertTrue(s.members[0]['auto'])
        s.view(0);s.view(1);s.tick(now+2.9)
        self.assertEqual(s.response_deadline,deadline)
        self.assertEqual(b.priority,0)
        s.tick(now+3)
        self.assertEqual(b.priority,1)

    def test_no_response_passes_without_a_countdown(self):
        s=session();s.tick(time.time())
        self.assertEqual(s.battle.priority,1)

    def test_action_response_publishes_new_deadline_before_the_next_tick(self):
        s=session();b=s.battle;b.phase='main'
        c=b.instance('u_scholar',0);b.players[0]['hand']=[c]
        b.players[1]['hand']=[b.instance('u_counter',1)]
        with patch('tactical.priority.time.time',return_value=100):
            s.priority_view(s.members[0])
        with patch('tactical.priority.time.time',return_value=101):
            s.action(0,'cast',uid=c['uid'])
            self.assertEqual(s.priority_view(s.members[1])['deadline'],104)
        with patch('tactical.priority.time.time',return_value=102):
            self.assertEqual(s.priority_view(s.members[1])['deadline'],104)

    def test_mana_alone_does_not_open_window_but_affordable_response_does(self):
        s=session();b=s.battle;p=b.players[0]
        mana=b.instance('g_sprite',0)
        mana.update(effect='mana',sick=False);p['board']=[mana];p['mana']={'U':1}
        self.assertFalse(b.meaningful_response(0))
        card=b.instance('u_counter',0);p['hand']=[card]
        b.push(1,'tokens',amount=1,name='Opponent spell')
        self.assertTrue(b.meaningful_response(0))
        self.assertFalse(mana['tapped'])
        self.assertEqual(p['mana'],{'U':1})

    def test_respond_can_arm_without_stealing_priority_and_never_resets_clock(self):
        s=session();b=s.battle;b.priority=1
        s.members[1]['auto']=False
        now=time.time();s.tick(now);clock=s.last_decision
        s.action(0,'respond');s.action(0,'respond');s.action(0,'hold_priority',enabled=True)
        s.tick(now+2)
        self.assertEqual(b.priority,1)
        self.assertEqual(s.last_decision,clock)
        self.assertFalse(s.members[0]['auto'])

    def test_manual_no_response_still_waits_and_pass_once_stays_paused(self):
        s=session();b=s.battle;s.action(0,'respond')
        s.tick(time.time()+10)
        self.assertEqual(b.priority,0)
        s.action(0,'pass_once')
        self.assertEqual(b.priority,1)
        self.assertFalse(s.members[0]['auto'])

    def test_resume_passes_immediately_and_clears_hold(self):
        s=session();s.action(0,'hold_priority',enabled=True)
        s.action(0,'resume_auto')
        self.assertEqual(s.battle.priority,1)
        self.assertTrue(s.members[0]['auto'])
        self.assertFalse(s.members[0]['hold_priority'])

    def test_resume_does_not_skip_main_without_separate_setting(self):
        s=session();b=s.battle;b.phase='main'
        s.action(0,'respond');s.action(0,'resume_auto');s.tick(time.time())
        self.assertEqual((b.phase,b.priority),('main',0))
        s.action(0,'priority_settings',auto_advance=True)
        s.tick(time.time()+1)
        self.assertEqual(b.priority,1)
        b.phase='main';b.priority=0;b.passes=0
        s.action(0,'respond');s.action(0,'resume_auto')
        self.assertEqual((b.phase,b.priority),('precombat',1))

    def test_cast_passes_immediately_unless_hold_was_armed(self):
        for hold in (False,True):
            s=session();b=s.battle;b.phase='main'
            c=b.instance('u_scholar',0);b.players[0]['hand']=[c]
            if hold:s.action(0,'hold_priority',enabled=True)
            s.action(0,'cast',uid=c['uid'])
            self.assertEqual(b.priority,0 if hold else 1)
            self.assertEqual(b.passes,0 if hold else 1)
            if hold:
                s.action(0,'pass_once')
                self.assertFalse(s.members[0]['auto'])

    def test_each_resolved_action_gets_new_window(self):
        s=session();b=s.battle
        c=b.instance('u_counter',0);b.players[0]['hand']=[c]
        b.push(1,'tokens',amount=1,name='First');b.push(1,'tokens',amount=1,name='Second')
        now=time.time();s.tick(now)
        first=s.response_deadline;s.action(0,'respond');s.action(0,'pass_once')
        s.action(1,'respond');s.action(1,'pass_once')
        self.assertEqual(len(b.stack),1)
        # Resuming explicitly passes the current opportunity; the following
        # resolution then creates a genuinely new decision.
        s.members[0]['auto']=True;s.tick(now+1)
        self.assertGreater(s.response_deadline,first)
        self.assertEqual(b.priority,0)

    def test_draw_stop_fires_after_draw_and_before_mana(self):
        s=session();b=s.battle
        s.action(0,'phase_stop',phase='draw',side='own')
        hand=len(b.players[0]['hand']);b.start_turn(0)
        self.assertEqual(len(b.players[0]['hand']),hand+1)
        s.tick(time.time())
        self.assertEqual(b.phase,'draw')
        self.assertFalse(s.members[0]['auto'])
        self.assertEqual(s.members[0]['phase_stops'],[])

    def test_repeating_stop_retained_and_removable(self):
        s=session();b=s.battle
        s.action(0,'phase_stop',phase='combat',side='opponent',repeat=True)
        b.active=b.priority=1;b.phase='precombat'
        s.tick(time.time())
        self.assertFalse(s.members[0]['auto'])
        self.assertEqual(len(s.members[0]['phase_stops']),1)
        s.action(0,'phase_stop',phase='combat',side='opponent')
        self.assertEqual(s.members[0]['phase_stops'],[])

    def test_main_stop_waits_until_required_mana_is_chosen(self):
        s=session();b=s.battle;b.phase='grow'
        s.action(0,'phase_stop',phase='main',side='own')
        s.tick(time.time());self.assertTrue(s.members[0]['auto'])
        s.action(0,'color',color='U');s.tick(time.time()+1)
        self.assertFalse(s.members[0]['auto'])
        self.assertEqual(b.phase,'main')

    def test_end_trigger_is_stacked_before_stop_and_can_be_countered(self):
        s=session();b=s.battle;b.phase='main2';b.players[0]['relic']='reserves'
        s.action(0,'phase_stop',phase='end',side='own')
        b.advance()
        self.assertEqual(b.stack[-1]['name'],'Patient Reserves')
        s.tick(time.time())
        self.assertFalse(s.members[0]['auto'])
        self.assertEqual(b.players[0]['hp'],25)

    def test_combat_damage_waits_for_end_combat(self):
        s=session();b=s.battle;b.phase='damage_response'
        b.advance();self.assertEqual(b.phase,'combat_end')
        s.tick(time.time());self.assertEqual(b.phase,'combat_end')
        b.advance();self.assertEqual(b.phase,'main2')

    def test_phase_buttons_enter_the_next_checkpoint_without_extra_main_passes(self):
        s=session();b=s.battle;b.phase='main'
        s.action(0,'enter_combat')
        self.assertEqual((b.phase,b.priority,b.passes),('precombat',1,1))
        b.action(1,'pass')
        self.assertEqual((b.phase,b.priority),('combat',0))
        b.phase='combat_end'
        s.action(0,'end_combat')
        self.assertEqual((b.phase,b.priority),('main2',0))
        s.action(0,'end_turn')
        self.assertEqual((b.phase,b.priority),('end',0))

    def test_selected_combat_stop_precedes_enter_combat_implicit_pass(self):
        s=session();b=s.battle;b.phase='main'
        s.action(0,'phase_stop',phase='combat',side='own')
        s.action(0,'enter_combat')
        self.assertEqual((b.phase,b.priority,b.passes),('precombat',0,0))
        self.assertFalse(s.members[0]['auto'])
        self.assertEqual(s.members[0]['phase_stops'],[])

    def test_flash_changes_casting_but_not_sorcery_abilities(self):
        s=session();b=s.battle;b.active=1
        c=b.instance('u_scholar',0);c['keywords'].append('Flash')
        self.assertTrue(b.castable(0,c))
        c.update(sick=False,abilities=[dict(name='Setup',effect='draw',timing='main',cost=0)])
        b.players[0]['board']=[c]
        self.assertFalse(b.ability_options(0,c)[0]['available'])

    def test_permission_categories_and_costs_stay_separate(self):
        s=session();b=s.battle;b.active=1;p=b.players[0]
        creature=b.instance('u_scholar',0)
        spell=b.instance('g_ramp',0)
        p['instant_actions']=['creature_cast']
        self.assertTrue(b.instant_card(0,creature))
        self.assertFalse(b.instant_card(0,spell))
        p['mana']={}
        self.assertFalse(b.castable(0,creature))

    def test_pure_explicit_mana_is_immediate(self):
        s=session();b=s.battle;c=b.instance('u_scholar',0)
        c.update(sick=False,abilities=[dict(name='Mana',effect='mana',timing='instant',cost=0,exhaust=True,amount=2,mana_color='U')])
        b.players[0]['board']=[c];before=b.players[0]['mana']['U']
        b.action(0,'ability',uid=c['uid'])
        self.assertEqual(b.stack,[])
        self.assertEqual(b.priority,0)
        self.assertEqual(b.players[0]['mana']['U'],before+2)

    def test_alternative_mana_modes_and_repeatable_generators_are_reachable(self):
        s=session();b=s.battle;p=b.players[0]
        c=b.instance('g_sprite',0)
        c.update(sick=False,abilities=[dict(name=color,effect='mana',timing='instant',cost=0,
                 exhaust=True,amount=2,mana_color=color) for color in ('G','U')])
        p.update(board=[c],mana={})
        p['hand']=[b.instance('u_counter',0)];b.push(1,'tokens',amount=1,name='Opponent spell')
        self.assertTrue(b.meaningful_response(0))
        c['abilities']=[dict(name='Repeatable',effect='mana',timing='instant',cost=0,amount=1,mana_color='U')]
        self.assertTrue(b.meaningful_response(0))
        self.assertFalse(c['tapped']);self.assertEqual(p['mana'],{})
        p['hand']=[]
        self.assertFalse(b.meaningful_response(0))  # Search terminates even with infinite mana.

    def test_targeted_triggers_join_the_cast_batch_before_priority_passes(self):
        for hold in (False,True):
            s=session();b=s.battle;p=b.players[0];b.phase='main'
            tender=b.instance('g_wildsteel_tender',0)
            engine=b.instance('u_artificer_study',0)
            # Entry order deliberately differs from the instance UID order.
            b.mark_entry(engine);b.mark_entry(tender)
            p.update(board=[tender],engines=[engine])
            b.gear_cards[0]['gear:test']=compose(dict(uid='test',design='spiresteel_blade',tier=0,gems={}))
            gear=b.instance('gear:test',0);p['hand']=[gear]
            if hold:s.action(0,'hold_priority',enabled=True)
            s.action(0,'cast',uid=gear['uid'])
            self.assertEqual(b.choice['kind'],'counter_target')
            s.action(0,'choose_item_target',target=tender['uid'])
            self.assertIsNone(b.choice)
            self.assertEqual([x['effect'] for x in b.stack],['equipment','draw','item_counter'])
            self.assertEqual(b.priority,0 if hold else 1)
            self.assertEqual(b.passes,0 if hold else 1)

    def test_manual_order_waits_for_required_targets_and_then_honors_hold(self):
        s=session();b=s.battle;p=b.players[0];b.phase='main'
        tender=b.instance('g_wildsteel_tender',0);engine=b.instance('u_artificer_study',0)
        b.mark_entry(tender);b.mark_entry(engine)
        p.update(board=[tender],engines=[engine])
        b.gear_cards[0]['gear:test']=compose(dict(uid='test',design='spiresteel_blade',tier=0,gems={}))
        gear=b.instance('gear:test',0);p['hand']=[gear]
        s.action(0,'priority_settings',auto_order=False);s.action(0,'hold_priority',enabled=True)
        s.action(0,'cast',uid=gear['uid'])
        self.assertEqual(b.choice['kind'],'counter_target')
        s.action(0,'choose_item_target',target=tender['uid'])
        self.assertEqual(b.choice['kind'],'trigger_order')
        self.assertEqual(len(b.choice['uids']),2)
        s.action(0,'order_triggers',order=b.choice['uids'])
        self.assertEqual((b.priority,b.passes),(0,0))

    def test_instant_equip_grant_does_not_change_consumable_speed(self):
        s=session();b=s.battle;p=b.players[0];b.active=1
        p['instant_actions']=['equip']
        c=b.instance('w_recruit',0);p['board']=[c]
        b.gear_cards[0]['gear:test']=compose(dict(uid='test',design='spiresteel_blade',tier=0,gems={}))
        gear=b.instance('gear:test',0);p['gear']=[gear]
        b.action(0,'equip_gear',uid=gear['uid'],target=c['uid'])
        self.assertEqual(b.stack[-1]['effect'],'attach')
        b.priority=0;p['pouch']=[dict(uid='beacon',design='militia_beacon')]
        with self.assertRaises(RuleError):b.action(0,'consume',uid='beacon')
        self.assertEqual(len(p['pouch']),1)

    def test_serialization_preserves_deadline_paused_state_and_preferences(self):
        s=session();b=s.battle;b.players[0]['hand']=[b.instance('u_counter',0)]
        b.push(1,'tokens',amount=1,name='Opponent spell');s.tick(time.time())
        s.action(0,'phase_stop',phase='end',side='opponent',repeat=True)
        saved=json.loads(json.dumps(s.to_dict()));loaded=Session.from_dict(saved)
        self.assertEqual(loaded.response_deadline,s.response_deadline)
        loaded.tick(s.response_deadline-.1)
        self.assertEqual(loaded.response_deadline,s.response_deadline)
        self.assertEqual(loaded.last_decision,s.last_decision)
        loaded.action(0,'respond')
        again=Session.from_dict(json.loads(json.dumps(loaded.to_dict())))
        self.assertFalse(again.members[0]['auto'])
        self.assertTrue(again.members[0]['phase_stops'][0]['repeat'])

    def test_simultaneous_triggers_are_apnap_then_visible_source_order(self):
        s=session();b=s.battle
        for i,p in enumerate(b.players):
            p['relic']='ashes'
            a=b.instance('b_collector',i);victim=b.instance('w_recruit',i)
            victim['damage']=victim['health'];p['board']=[a,victim]
        b.push(0,'heal',amount=1,name='Cause')
        b.action(0,'pass');b.action(1,'pass')
        owners=[s['owner'] for s in b.stack]
        self.assertEqual(owners,sorted(owners))
        for owner in (0,1):
            batch=[s for s in b.stack if s['owner']==owner]
            self.assertEqual(batch[0]['name'],'Ash Ledger')
            self.assertIsNotNone(batch[-1]['source_uid'])
        self.assertEqual(b.stack[-1]['owner'],1)

    def test_manual_trigger_order_is_resolution_order_for_own_batch_only(self):
        s=session();b=s.battle
        p=b.players[0];p['relic']='ashes'
        victim=b.instance('b_shambler',0)
        victim.update(effect='death_drain',damage=victim['health']);p['board']=[victim]
        s.action(0,'priority_settings',auto_order=False)
        b.push(0,'heal',amount=1,name='Cause');b.action(0,'pass');b.action(1,'pass')
        self.assertEqual(b.choice['kind'],'trigger_order')
        intended=list(reversed(b.choice['uids']))
        with self.assertRaises(RuleError):b.action(1,'order_triggers',order=intended)
        with self.assertRaises(RuleError):b.action(0,'order_triggers',order=[])
        b.action(0,'order_triggers',order=intended)
        self.assertEqual([s['uid'] for s in reversed(b.stack)],intended)

    def test_timeout_ai_can_complete_manual_trigger_order(self):
        s=session();b=s.battle
        b.push(0,'draw',amount=1,name='First');b.push(0,'heal',amount=1,name='Second')
        b.choice=dict(owner=0,kind='trigger_order',uids=[x['uid'] for x in reversed(b.stack)])
        move=b.ai_action(0)
        self.assertEqual(move['action'],'order_triggers')
        b.action(0,**move)
        self.assertIsNone(b.choice)

    def test_ward_trigger_does_not_take_the_activation_target_metadata(self):
        s=session();b=s.battle
        source=b.instance('u_scholar',0);target=b.instance('r_duelist',1)
        source.update(sick=False,abilities=[dict(name='Strike',effect='damage',timing='instant',
                      target='creature',cost=0,requires_source=True,amount=1)])
        target['ward']=2
        b.players[0]['board']=[source];b.players[1]['board']=[target]
        b.action(0,'ability',uid=source['uid'],target=target['uid'])
        pending=next(x for x in b.stack if x['effect']=='damage')
        ward=next(x for x in b.stack if x['effect']=='item_ward')
        self.assertTrue(pending['requires_source'])
        self.assertEqual(pending['target_kind'],'creature')
        self.assertNotIn('requires_source',ward)
        self.assertNotIn('target_kind',ward)


if __name__=='__main__':
    unittest.main()
