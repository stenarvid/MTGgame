"""Route reachability, challenge rules, and persistent once-only treasure awards."""
import copy
import json
import unittest
from tactical.battle import Battle, RuleError
from tactical.campaign import make_map, bonus, MODIFIERS
from tactical.content import starter, legal, CARDS
from tactical.session import Session


def campaign(seed=9):
    s=Session('solo',seed=seed)
    s.add_member('Explorer');s.start(0)
    s.choose_commander(0,s.members[0]['offers'][0],0)
    while s.stage=='draft':
        s.action(0,'pick',index=0)
    s.action(0,'relic',relic=s.members[0]['relic_options'][0])
    return s


def win(s):
    s.battle.finished=True;s.battle.survivor=0;s.battle.phase='finished'
    s.apply_results()


class Routes(unittest.TestCase):
    def test_counts_edges_and_determinism(self):
        for seed in range(30):
            for difficulty in ('normal','hard','custom'):
                for count in range(5):
                    graph=make_map(seed,1,difficulty,count)
                    self.assertEqual(graph,make_map(seed,1,difficulty,count))
                    marked=[n for n in graph['nodes'] if n['modifiers']]
                    self.assertTrue((1<=len(marked)<=2) if difficulty=='normal' else (3<=len(marked)<=4) if difficulty=='hard' else len(marked)==count)
                    for n in graph['nodes']:
                        self.assertLessEqual(n['bonus'],4)
                        self.assertEqual(len(n['modifiers']),len(set(n['modifiers'])))
                        if n['modifiers']:self.assertTrue(1<=len(n['modifiers'])<=3)
                        for target in n['next']:
                            other=next(x for x in graph['nodes'] if x['id']==target)
                            self.assertEqual(other['column'],n['column']+1)
                            self.assertTrue(other['column']==3 or abs(other['lane']-n['lane'])<=1)

    def test_route_validation_reward_and_retry_freeze(self):
        s=campaign();s.ensure_map()
        first=s.campaign_map['reachable'][0]
        s.action(0,'route',node=first)
        with self.assertRaises(RuleError):s.action(0,'route',node='1:2:0')
        node=s.route_node();node['modifiers']=list(MODIFIERS);node['bonus']=4
        s.action(0,'ready');frozen=copy.deepcopy(s.battle.encounter)
        self.assertEqual(frozen['bonus_essence'],4)
        s.battle.finished=True;s.battle.survivor=1;s.apply_results()
        self.assertEqual(s.stage,'retry');self.assertEqual(s.currency,0);self.assertEqual(s.treasures,[])
        with self.assertRaises(RuleError):s.action(0,'route',node=first)
        s.action(0,'retry');self.assertEqual(s.battle.encounter,frozen)
        win(s);self.assertEqual(s.members[0]['essence'],6)
        self.assertEqual(s.campaign_map['reachable'],node['next'])
        before=copy.deepcopy(s.to_dict());s.apply_results();self.assertEqual(s.to_dict(),before)

    def test_boss_loot_roundtrip_and_ack_never_rerolls(self):
        s=campaign();s.encounter=3;s.ensure_map();s.action(0,'ready');win(s)
        self.assertEqual(len(s.treasures),1);t=s.treasures[0]
        self.assertTrue(1<=len(t['items'])<=3);self.assertTrue(1<=t['currency']<=3)
        self.assertTrue(all(0<=x['tier']<=2 for x in t['items']))
        self.assertTrue(all(x in s.members[0]['items'] for x in t['items']))
        self.assertEqual(len(s.members[0]['relic_options']),3)
        restored=Session.from_dict(json.loads(json.dumps(s.to_dict())))
        self.assertEqual(restored.treasures,s.treasures)
        before=copy.deepcopy(restored.members[0]['items']);currency=restored.currency
        restored.action(0,'treasure_revealed',id=t['id']);restored.action(0,'treasure_revealed',id=t['id'])
        self.assertEqual(restored.members[0]['items'],before);self.assertEqual(restored.currency,currency)

    def test_old_save_continuation_and_custom_zero(self):
        s=campaign();data=s.to_dict()
        for key in ('campaign_map','selected_node','route_seed','difficulty','modifier_nodes','treasures'):data.pop(key)
        data['encounter']=6
        restored=Session.from_dict(data);view=restored.view(0)
        self.assertEqual(view['campaign_map']['act'],2)
        self.assertTrue(all(n.startswith('2:2:') for n in view['campaign_map']['reachable']))
        s.configure_run('custom',0);s.campaign_map=None;s.ensure_map()
        self.assertFalse(any(n['modifiers'] for n in s.campaign_map['nodes']))
        for value in (-1,5,True,'2'):
            with self.assertRaises(RuleError):s.configure_run('custom',value)

    def test_item_validation(self):
        s=campaign()
        for tier in (-1,3,True):
            with self.assertRaises(RuleError):s.add_item(s.members[0],'roots',tier)

    def test_preview_matches_selected_opponent(self):
        for lane in range(3):
            s=campaign();s.ensure_map();s.action(0,'route',node=s.campaign_map['reachable'][lane])
            preview=s.view(0)['upcoming'][0]
            s.action(0,'ready')
            actual=s.battle.players[1]
            self.assertEqual(preview,{key:actual[key] for key in ('commander','package','relic')})


class Challenges(unittest.TestCase):
    def battle(self,modifiers):
        builds=[dict(name=n,commander='',package=0,relic='roots',deck=[]) for n in ('You','Enemy')]
        # Use a real catalog commander without binding this test to a roster name.
        from tactical.content import COMMANDERS
        for build in builds:
            build['commander']=COMMANDERS[0]['id'];build['deck']=starter(COMMANDERS[0]['colors'])
        return Battle(builds,encounter=dict(modifiers=modifiers))

    def test_penalties_are_player_only_and_temporary(self):
        b=self.battle(list(MODIFIERS));color=b.players[1]['colors'][0]
        self.assertEqual(b.players[1]['capacity'],{color:1});self.assertEqual(b.players[0]['capacity'],{})
        for i in (0,1):
            c=b.instance('w_recruit',i);b.players[i]['board'].append(c)
            self.assertEqual(b.stats(c)[0],max(0,c['attack']-(i==0)))
        for i in (0,1):
            c=b.instance(next(c['id'] for c in CARDS if c['kind']=='creature' and c['effect']=='draw'),i)
            before=len(b.stack);b.entry_triggers(i,c);self.assertEqual(len(b.stack)-before,0 if i==0 else 1)
        b.stack=[];b.phase='main';b.active=b.priority=0;b.players[0]['mana']={c:10 for c in ('W','U','B','R','G')}
        spell=b.instance(next(c['id'] for c in CARDS if c['kind']!='creature' and not c.get('target') and c['effect']!='bargain'),0)
        self.assertFalse(b.castable(0,spell))
        b.encounter['modifiers']=[];self.assertTrue(b.castable(0,spell))
        self.assertEqual(bonus(list(MODIFIERS)),4)


if __name__=='__main__':unittest.main()
