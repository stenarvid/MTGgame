"""Multiplayer invariants, draft progression, privacy and network authorization."""
import copy
import json
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from tactical.battle import Battle, RuleError
from tactical.content import (CARDS, COMMANDERS, COMMANDER_MAP, BASICS, starter,
                              draft_pack, CARD_MAP, legal)
from tactical.session import Session
from tactical.server import make_server, Rooms


def builds():
    return [dict(name=f'Player {i}',commander=cmd,package=0,relic='reserves',
                 deck=starter(COMMANDER_MAP[cmd]['colors'])) for i,cmd in enumerate(('dawn','tide','crypt','ember'))]


def battle():
    b = Battle(builds(),seed=7)
    for i,p in enumerate(b.players):
        b.action(i,'keep')
        b.action(i,'color',color=p['colors'][0])
    return b


def opened(b):
    for p in b.players:
        p['completed_turn'] = True
    return b


def resolve_all(b):
    for _ in range(100):
        if not b.stack or b.finished:
            return
        b.action(b.priority,'pass')
    raise AssertionError('Stack failed to finish')


class MultiplayerRules(unittest.TestCase):
    def test_private_hands_and_opening_color(self):
        b = Battle(builds())
        b.action(0,'keep')
        b.action(0,'color',color='W')
        view = b.view(1)
        self.assertIsNone(view['players'][0]['opening_color'])
        self.assertEqual(view['players'][0]['hand'],[])
        self.assertNotIn('deck',view['players'][0])
        self.assertEqual(len(view['players'][1]['hand']),5)

    def test_opening_protection_lasts_through_last_players_turn(self):
        b = battle()
        for p in b.players:
            p['turns'] = 1
        self.assertTrue(b.protected_opening())
        b.damage_player(2,100,0)
        self.assertEqual(b.players[2]['hp'],1)
        opened(b)
        b.damage_player(2,1,0)
        b.check()
        self.assertFalse(b.players[2]['alive'])
        self.assertEqual(b.players[0]['points'],1)

    def test_all_four_passes_then_priority_returns_to_active(self):
        b = battle()
        b.push(0,'draw',amount=1,name='First')
        b.push(0,'heal',amount=1,name='Second')
        for i in range(3):
            b.action(i,'pass')
            self.assertEqual(len(b.stack),2)
        b.action(3,'pass')
        self.assertEqual(len(b.stack),1)
        self.assertEqual(b.priority,0)
        self.assertEqual(b.players[0]['hp'],26)

    def test_counter_chain_and_no_refund(self):
        b = battle()
        p=b.players[1]
        p['mana']={'U':5}
        counter=b.instance('u_counter',1)
        p['hand'].append(counter)
        b.push(0,'tokens',amount=2,name='Muster')
        b.action(0,'pass')
        b.action(1,'cast',uid=counter['uid'],target=b.stack[0]['uid'])
        self.assertEqual(b.priority,1)
        resolve_all(b)
        self.assertEqual(len(b.players[0]['board']),0)
        self.assertEqual(p['mana']['U'],3)

    def test_ward_is_upfront_and_fizzling_does_not_refund(self):
        b=opened(battle());p=b.players[3]
        unit=b.instance('g_beast',2);b.players[2]['board'].append(unit)
        bolt=b.instance('r_bolt',3);p['hand'].append(bolt);p['mana']={'R':2}
        b.priority=3
        with self.assertRaises(RuleError):b.action(3,'cast',uid=bolt['uid'],target=unit['uid'])
        p['mana']['R']=3
        b.action(3,'cast',uid=bolt['uid'],target=unit['uid'])
        b.move_out(b.players[2],unit,'hand')
        resolve_all(b)
        self.assertEqual(p['mana']['R'],0)

    def test_damage_persists_until_controller_turn(self):
        b=battle();unit=b.instance('w_recruit',0);b.players[0]['board'].append(unit)
        unit['damage']=2
        b.start_turn(1)
        self.assertEqual(unit['damage'],2)
        b.start_turn(0)
        self.assertEqual(unit['damage'],0)

    def test_blocker_removed_stays_blocked_and_trample_differs(self):
        for trample,expected in ((False,25),(True,22)):
            b=opened(battle());a=b.instance('g_sentinel',0);blocker=b.instance('w_recruit',1)
            a['keywords']=['Trample'] if trample else []
            b.players[0]['board'].append(a);b.players[1]['board'].append(blocker)
            b.attacks=[dict(uid=a['uid'],defender=1)]
            b.blocks={a['uid']:[blocker['uid']]};b.blocked=[a['uid']]
            b.move_out(b.players[1],blocker,'hand');b.combat_damage()
            self.assertEqual(b.players[1]['hp'],expected)

    def test_simultaneous_damage_lifesteal_and_multiple_blockers(self):
        b=opened(battle());a=b.instance('g_beast',0);a['keywords']=['Trample','Lifesteal']
        b.players[0]['board'].append(a)
        blockers=[b.instance('r_raider',1),b.instance('r_raider',1)]
        b.players[1]['board']=blockers
        b.attacks=[dict(uid=a['uid'],defender=1)];b.blocks={a['uid']:[x['uid'] for x in blockers]};b.blocked=[a['uid']]
        b.combat_damage()
        self.assertEqual(a['damage'],6)
        self.assertEqual(b.players[1]['hp'],21)
        self.assertEqual(b.players[0]['hp'],31)
        self.assertFalse(b.players[1]['board'])

    def test_symmetrical_anthem_uses_printed_values(self):
        b=battle();a=b.instance('r_raider',0);b.players[0]['board'].append(a)
        engine=b.instance('r_anthem',1);b.players[1]['engines'].append(engine)
        a['bonus_attack']=5;a['damage']=1
        self.assertEqual(b.stats(a)[0],10)
        self.assertIn('Haste',b.keywords(a))

    def test_goad_expires_after_controllers_next_turn(self):
        b=battle();a=b.instance('r_duelist',0);b.players[0]['board'].append(a)
        b.resolve(dict(owner=0,effect='goad',amount=0,target=None,card=None,kind='ability',name='Goad'))
        b.phase='combat';b.priority=0
        with self.assertRaises(RuleError):b.action(0,'attack',attacks=[])
        b.action(0,'attack',attacks=[dict(uid=a['uid'],defender=1)])
        b.start_turn(0);b.phase='end';b.advance()
        self.assertIsNone(a['goad'])

    def test_simultaneous_eliminations_score_dead_controller(self):
        b=opened(battle())
        for i in (0,1,2):b.damage_player(i,100,0)
        b.check()
        self.assertEqual(b.players[0]['points'],2)
        self.assertEqual(b.players[3]['points'],1)
        self.assertEqual(b.survivor,3)
        b.check()
        self.assertEqual(b.players[3]['points'],1)

    def test_dead_active_does_not_cancel_other_players_stack(self):
        b=opened(battle());b.push(1,'draw',amount=1,name='Other action')
        b.damage_player(0,100,2);b.check()
        self.assertEqual(len(b.stack),1)
        resolve_all(b)
        self.assertTrue(any('Resolved: Other action' in x for x in b.log))

    def test_tax_first_cast_and_recursion(self):
        b=battle();p=b.players[0];p['mana']={'W':10}
        b.action(0,'cast',uid='commander');resolve_all(b)
        self.assertEqual(p['tax'],2);self.assertEqual(p['mana']['W'],6)
        cmd=p['board'][0];b.move_out(p,cmd)
        b.action(0,'cast',uid='commander');resolve_all(b)
        self.assertEqual(p['mana']['W'],0);self.assertEqual(p['tax'],4)

    def test_fatigue_no_grave_reshuffle(self):
        b=opened(battle());p=b.players[0];p['deck']=[]
        p['grave'].append(b.instance('w_recruit',0));b.draw(0,3)
        self.assertEqual(p['hp'],19);self.assertEqual(p['fatigue'],3)
        self.assertEqual(len(p['grave']),1)

    def test_health_cost_not_subsidized_by_protection(self):
        b=battle();p=b.players[2];p['hp']=2;p['mana']={'B':5};b.priority=2;b.active=2
        c=b.instance('b_bargain',2);p['hand'].append(c)
        with self.assertRaises(RuleError):b.action(2,'cast',uid=c['uid'])

    def test_save_roundtrip_restores_stack_and_rng(self):
        b=battle();b.push(0,'draw',amount=2,name='Pending')
        clone=Battle.from_dict(json.loads(json.dumps(b.to_dict())))
        resolve_all(b);resolve_all(clone)
        self.assertEqual(b.view(0),clone.view(0))
        self.assertEqual(b.rng.random(),clone.rng.random())

    def test_finite_loop_preserves_windows_and_can_stop(self):
        b=opened(battle());p=b.players[0];p['mana']={'W':5}
        broker=b.instance('b_broker',0);broker['sick']=False
        collector=b.instance('b_collector',0)
        token=b.instance('w_recruit',0);token.update(token=True,attack=1,health=1)
        p['board']=[broker,collector,token]
        p['engines']=[b.instance('c_nest',0),b.instance('c_relay',0)]
        b.action(0,'loop',uid=broker['uid'],count=2)
        self.assertTrue(b.loop_step())
        self.assertEqual(b.loop['remaining'],1)
        self.assertTrue(b.stack)
        b.action(0,'pass')
        self.assertEqual(b.priority,1)
        self.assertFalse(b.loop_step())
        # Opponents have not passed, so nothing resolves automatically.
        b.action(0,'stop_loop')
        self.assertIsNone(b.loop)
        resolve_all(b)
        self.assertTrue(any(c['token'] for c in p['board']))
        self.assertFalse(broker['tapped'])
        self.assertEqual(b.players[1]['hp'],24)

    def test_opponent_can_interrupt_declared_loop(self):
        b=battle();p=b.players[0];p['mana']={'W':5}
        broker=b.instance('b_broker',0);broker['sick']=False
        token=b.instance('w_recruit',0);token['token']=True
        p['board']=[broker,token];p['engines']=[b.instance('c_nest',0),b.instance('c_relay',0)]
        b.action(0,'loop',uid=broker['uid'],count=100)
        b.loop_step();b.action(0,'pass')
        opponent=b.players[1];opponent['mana']={'U':5}
        bounce=b.instance('u_return',1);opponent['hand'].append(bounce)
        b.action(1,'cast',uid=bounce['uid'],target=broker['uid'])
        self.assertIsNone(b.loop)
        resolve_all(b)
        self.assertIn(broker,p['hand'])

    def test_filter_requires_a_private_discard_choice(self):
        b=battle();p=b.players[1];p['mana']={'U':5};b.priority=b.active=1
        spell=b.instance('u_insight',1);p['hand'].append(spell)
        b.action(1,'cast',uid=spell['uid']);resolve_all(b)
        self.assertEqual(b.choice,dict(owner=1,kind='discard'))
        with self.assertRaises(RuleError):b.action(1,'pass')
        uid=p['hand'][0]['uid'];b.action(1,'choose_discard',uid=uid)
        self.assertIsNone(b.choice)
        self.assertTrue(any(c['uid']==uid for c in p['grave']))

    def test_concession_during_blocking_does_not_stall(self):
        b=opened(battle());a=b.instance('r_duelist',0);b.players[0]['board'].append(a)
        b.attacks=[dict(uid=a['uid'],defender=1)];b.defenders=[1];b.phase='blocks';b.priority=1
        b.action(1,'concede')
        self.assertEqual(b.phase,'damage_response')
        self.assertFalse(b.players[1]['alive'])
        self.assertEqual(b.players[0]['points'],0)

    def test_simultaneous_deaths_use_last_known_triggers(self):
        b=opened(battle());p=b.players[0]
        collector=b.instance('b_collector',0);token=b.instance('w_recruit',0);token['token']=True
        p['board']=[collector,token]
        collector['damage']=3;token['damage']=3
        b.check();resolve_all(b)
        self.assertEqual(b.players[1]['hp'],24)
        self.assertEqual(p['hp'],28)


class Progression(unittest.TestCase):
    def solo(self):
        s=Session('solo',seed=5);s.add_member('Human');s.start(0)
        s.choose_commander(0,s.members[0]['offers'][0],0)
        while s.stage=='draft':
            m=s.members[0];j=next(i for i,c in enumerate(m['reward']) if legal(c,s.colors(0)))
            s.action(0,'pick',index=j)
        s.action(0,'relic',relic=s.members[0]['relic_options'][0])
        return s

    def test_every_starter_is_legal_and_30_cards(self):
        s=Session()
        for cmd in COMMANDERS:
            s.members=[dict(commander=cmd['id'],owned=starter(cmd['colors']))]
            s.validate_deck(0,starter(cmd['colors']))
            self.assertEqual(len(starter(cmd['colors'])),30)

    def test_pack_color_coverage(self):
        s=Session(seed=2)
        for _ in range(20):
            pack=draft_pack(s.rng);counts=Counter(CARD_MAP[c]['color'] for c in pack)
            self.assertEqual(len(pack),15)
            for c in 'WUBRGC':self.assertGreaterEqual(counts[c],2)

    def test_human_three_round_pick_and_pass(self):
        s=Session('human',seed=2)
        for i in range(4):s.add_member(str(i))
        s.start(0)
        for m in s.members:s.choose_commander(m['id'],m['offers'][0],0)
        first=s.packs[0][0]
        for _ in range(45):
            for i in range(4):s.draft_pick(i,0)
        self.assertEqual(s.stage,'build')
        self.assertIn(first,s.members[0]['owned'])
        self.assertTrue(all(len(m['owned'])==75 for m in s.members))

    def test_solo_draft_shop_and_boss_relic(self):
        s=self.solo();self.assertEqual(len(s.members[0]['owned']),45)
        s.encounter=3;s.action(0,'ready');opened(s.battle)
        for i in (1,2,3):s.battle.damage_player(i,100,0)
        s.battle.check();s.apply_results()
        self.assertEqual(s.encounter,4);self.assertEqual(s.currency,1)
        self.assertEqual(s.members[0]['reward_left'],2)
        self.assertEqual(len(s.members[0]['relic_options']),3)
        self.assertNotIn(s.members[0]['relic'],s.members[0]['relic_options'])
        s.action(0,'buy',index=0);self.assertEqual(s.currency,0)
        s.apply_results();self.assertEqual(s.currency,0)

    def test_one_retry_no_reward_for_defeat(self):
        s=self.solo();s.action(0,'ready');opened(s.battle)
        s.battle.damage_player(0,100,1);s.battle.check()
        for i in (2,3):s.battle.damage_player(i,100,1)
        s.battle.check();s.apply_results()
        self.assertEqual(s.stage,'retry');self.assertEqual(s.currency,0)
        s.action(0,'retry');self.assertEqual(s.retry,0)
        self.assertEqual(s.stage,'battle')

    def test_vote_extension_uses_highest_score_and_runoff(self):
        s=Session('human')
        for i in range(4):s.add_member(str(i))
        s.stage='vote';s.members[0]['score']=7
        for i,c in enumerate(('extend','extend','quit','restart')):s.vote(i,c)
        self.assertEqual(s.stage,'vote');self.assertEqual(len(s.vote_options),2)
        for i in range(4):s.vote(i,'extend')
        self.assertEqual(s.target,10);self.assertEqual(s.stage,'build')

    def test_save_draft_integer_picks_and_private_view(self):
        s=Session('human',seed=2)
        for i in range(2):s.add_member(str(i))
        s.start(0)
        for m in s.members:s.choose_commander(m['id'],m['offers'][0],0)
        s.draft_pick(0,0)
        clone=Session.from_dict(json.loads(json.dumps(s.to_dict())))
        self.assertIn(0,clone.picks)
        clone.draft_pick(1,0)
        self.assertEqual(clone.pick_number,1)
        self.assertNotIn('owned',clone.view(0)['members'][1])

    def test_seeded_all_ai_battle_completes(self):
        b=battle()
        for _ in range(18000):
            if b.finished:break
            b.action(b.priority,**b.ai_action(b.priority))
        self.assertTrue(b.finished, f'AI stalled in {b.phase}: {b.log[-10:]}')

    def test_full_four_act_campaign_progression(self):
        s=self.solo()
        for encounter in range(16):
            self.assertEqual(s.encounter,encounter)
            m=s.members[0]
            while m['reward_left']:
                index=next(j for j,c in enumerate(m['reward']) if legal(c,s.colors(0)))
                s.action(0,'pick',index=index)
            if m['relic_options']:s.action(0,'relic',relic=m['relic'])
            s.action(0,'ready');opened(s.battle)
            for i in (1,2,3):s.battle.damage_player(i,100,0)
            s.battle.check();s.apply_results()
        self.assertEqual(s.stage,'victory');self.assertEqual(s.currency,16)
        self.assertEqual(len(s.reports),16)

    def test_rewards_cap_and_every_nonsurvivor_gets_a_loss(self):
        s=Session('human',seed=2)
        for i in range(4):s.add_member(str(i))
        for i,m in enumerate(s.members):
            m.update(commander=builds()[i]['commander'],deck=builds()[i]['deck'],package=0,relic='reserves')
        s.begin_battle();opened(s.battle)
        killer=s.members[0]['seat'];survivor=s.members[3]['seat']
        for i in range(4):
            if i!=survivor:s.battle.damage_player(i,100,killer)
        s.battle.check();s.apply_results()
        self.assertEqual(s.members[0]['score'],2)
        self.assertEqual(s.members[0]['reward_left'],2)
        self.assertEqual(len(s.members[0]['reward']),5)
        self.assertEqual(s.members[0]['losses'],1)
        self.assertEqual(s.members[3]['losses'],0)

    def test_closed_solo_browser_pauses_ai_and_timers(self):
        s=self.solo();s.action(0,'ready')
        s.members[0]['last_seen']=0
        before=s.battle.to_dict();s.tick(now=500)
        self.assertEqual(before,s.battle.to_dict())

    def test_ai_uses_no_hidden_opponent_cards(self):
        b=opened(battle());other=copy.deepcopy(b)
        for p in other.players[1:]:
            p['hand']=[other.instance('g_beast',p['id']) for _ in p['hand']]
            p['deck'].reverse()
        self.assertEqual(b.ai_action(0),other.ai_action(0))

    def test_all_twenty_packages_complete_seeded_battles(self):
        for index,cmd in enumerate(COMMANDERS):
            for package in (0,1):
                with self.subTest(commander=cmd['id'],package=package):
                    seats=builds()
                    seats[0].update(commander=cmd['id'],package=package,deck=starter(cmd['colors']))
                    b=Battle(seats,seed=index*2+package)
                    for i,p in enumerate(b.players):
                        b.action(i,'keep');b.action(i,'color',color=p['colors'][0])
                    for _ in range(18000):
                        if b.finished:break
                        b.action(b.priority,**b.ai_action(b.priority))
                    self.assertTrue(b.finished,f'Stalled in {b.phase}: {b.log[-5:]}')

    def test_solo_defeat_ends_when_human_dies(self):
        s=self.solo();s.action(0,'ready');opened(s.battle)
        s.battle.damage_player(0,100,1);s.battle.check()
        self.assertFalse(s.battle.finished)
        s.apply_results()
        self.assertEqual(s.stage,'retry')
        self.assertTrue(s.battle.finished)

    def test_departure_then_restart_draft_has_no_ghost_seat(self):
        s=Session('human',seed=12)
        for i in range(4):s.add_member(str(i))
        s.stage='build'
        s.action(1,'leave')
        s.stage='vote'
        for i in (0,2,3):s.vote(i,'restart')
        s.start(0)
        for i in (0,2,3):s.choose_commander(i,s.members[i]['offers'][0],0)
        for _ in range(45):
            for i in (0,2,3):s.draft_pick(i,0)
        self.assertEqual(s.stage,'build')
        for i in (0,2,3):
            s.action(i,'relic',relic=s.members[i]['relic_options'][0]);s.action(i,'ready')
        self.assertEqual(len(s.battle.players),3)
        view=s.view(1)
        self.assertTrue(all(p['hand']==[] for p in view['battle']['players']))

    def test_restart_accepts_replacement_without_reusing_private_token_seat(self):
        s=Session('human',seed=4)
        for i in range(4):s.add_member(str(i))
        s.stage='build';s.action(1,'leave');s.stage='vote'
        for i in (0,2,3):s.vote(i,'restart')
        replacement=s.add_member('New friend')
        self.assertEqual(replacement,4)
        s.start(0)
        for i in (0,2,3,4):s.choose_commander(i,s.members[i]['offers'][0],0)
        for _ in range(45):
            for i in (0,2,3,4):s.draft_pick(i,0)
        self.assertEqual(s.stage,'build')
        self.assertTrue(all(len(s.members[i]['owned'])==75 for i in (0,2,3,4)))


class Network(unittest.TestCase):
    def test_authenticated_private_views_and_persistent_room(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'save.json';server=make_server(port=0,save_path=path)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_address[1]}'
            def post(endpoint,data,token=None):
                return json.loads(urlopen(Request(base+endpoint,json.dumps(data).encode(),{'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})).read())
            try:
                first=post('/api/create',dict(mode='human',name='A',size=2))
                second=post('/api/join',dict(code=first['code'],name='B'))
                with self.assertRaises(HTTPError) as caught:urlopen(base+'/api/state?code='+first['code'])
                caught.exception.close()
                request=Request(base+'/api/state?code='+first['code'],headers={'Authorization':'Bearer '+second['token']})
                view=json.loads(urlopen(request).read())
                self.assertEqual(view['me']['name'],'B')
                with self.assertRaises(HTTPError) as caught:post('/api/action',dict(code=first['code'],action='start'),second['token'])
                caught.exception.close()
                self.assertTrue(path.exists())
                rooms=Rooms(path);session,seat=rooms.authenticate(first['code'],first['token'])
                self.assertEqual(seat,0);self.assertEqual(len(session.members),2)
            finally:
                server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
