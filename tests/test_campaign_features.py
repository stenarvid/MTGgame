"""Campaign item ownership, opening decisions, and a playable training walkthrough."""
import copy
import time
import unittest
from tactical.session import Session
from tactical.battle import Battle, RuleError
from tactical.content import COMMANDER_MAP, starter, personal_pack, CARD_MAP
from tactical.tutorial import initialize, ai_action, sync


def training():
    s=Session('solo');s.add_member('Student');initialize(s);return s


def play_training(s):
    visited=set()
    for _ in range(1500):
        sync(s);step=s.tutorial['step'];visited.add(step)
        m=s.members[0];b=s.battle
        if step=='complete':return visited
        if step=='stats':s.action(0,'tutorial_next');continue
        if s.stage=='build':
            if m['reward_left']:
                index=next(j for j,id in enumerate(m['reward']) if CARD_MAP[id]['color'] in s.colors(0)+['C'])
                s.action(0,'pick',index=index)
            elif step=='card_upgrade':s.action(0,'upgrade_card',design='w_recruit')
            elif step=='shop':s.action(0,'buy_item',index=0)
            elif step=='equipment':
                uid=s.tutorial['purchased'];slot=m['equipped'].index(uid) if uid in m['equipped'] else 1
                s.action(0,'equip' if s.tutorial['unequipped'] else 'unequip',uid=uid,slot=slot)
            elif step=='item_upgrade':s.action(0,'upgrade_item',uid=s.tutorial['purchased'])
            elif step=='boss_ready':s.action(0,'ready')
            elif m['relic_options']:s.action(0,'relic',relic=m['relic_options'][0])
            else:raise AssertionError((step,s.stage))
            continue
        if s.stage!='battle':raise AssertionError((step,s.stage,b.log[-5:]))
        if b.phase=='opening':
            for i,p in enumerate(b.players):
                if not p['kept']:s.action(i,'keep')
                if p['bottom_remaining']:s.action(i,'bottom',uid=p['hand'][0]['uid'])
            continue
        i=b.priority;p=b.players[i]
        if i:move=ai_action(s,i)
        elif b.phase=='grow':move=dict(action='color',color='W' if step=='opening' else ('U' if p['capacity'].get('U',0)<2 else 'W'))
        elif b.choice:move=dict(action='choose_discard',uid=p['hand'][0]['uid'])
        elif b.phase=='blocks':
            attacks=[a for a in b.attacks if a['defender']==0]
            blockers=[c for c in p['board'] if not c['tapped']]
            move=dict(action='block',blocks={attacks[0]['uid']:[blockers[0]['uid']]} if attacks and blockers else {})
        elif b.phase=='combat' and not b.stack:move=dict(action='attack',attacks=[dict(uid=c['uid'],defender=1) for c in p['board'] if b.attack_ready(c)])
        elif b.phase in ('main','main2') and not b.stack:
            c=next((c for c in p['hand'] if c['id'] in ('w_recruit','u_apprentice','u_scholar') and b.castable(i,c)),None)
            move=dict(action='cast',uid=c['uid']) if c else dict(action='pass')
        else:move=dict(action='pass')
        s.action(i,**move)
    raise AssertionError(('Training stalled',s.tutorial,b.phase,b.log[-8:]))


class CampaignFeatures(unittest.TestCase):
    def test_new_rooms_are_strictly_one_v_one(self):
        from tactical.server import Rooms
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            rooms = Rooms(Path(tmp)/'isolated.json')
            for mode in ('solo','human'):
                created = rooms.create(dict(mode=mode,size=4,name='Host'))
                self.assertEqual(rooms.rooms[created['code']]['session'].size,2)
        for mode in ('solo','human'):
            s=Session(mode,size=4);s.add_member('Host')
            self.assertEqual(s.size,2)
            s.action(0,'add_bot')
            with self.assertRaises(RuleError):s.action(0,'add_bot')
            with self.assertRaises(RuleError):s.add_member('Third player')
            s.start(0);self.assertEqual(len(s.members),2)
        s=Session('solo');s.add_member('Host');s.start(0)
        self.assertEqual(len(s.members),2);self.assertTrue(s.members[1]['bot'])

    def test_training_walkthrough_and_isolation(self):
        s=training();untouched=Session('solo');untouched.add_member('Campaign');snapshot=untouched.to_dict()
        steps=play_training(s)
        self.assertTrue({'block','mana','card_upgrade','item_upgrade','boss','boss_rewards','complete'}<=steps)
        self.assertEqual(s.members[0]['card_upgrades']['w_recruit'],1)
        self.assertEqual(s.members[0]['essence'],4)
        self.assertEqual(snapshot,untouched.to_dict())
        restored=Session.from_dict(s.to_dict());self.assertEqual(restored.tutorial,s.tutorial)
        restored.action(0,'tutorial_restart');self.assertEqual(restored.tutorial['step'],'stats');self.assertEqual(restored.members[0]['essence'],0)

    def test_item_copy_ownership_costs_and_maximum(self):
        s=training();s.tutorial=None;s.stage='build';m=s.members[0];m['essence']=20
        a=s.add_item(m,'panharmonicon');b=s.add_item(m,'panharmonicon')
        with self.assertRaises(RuleError):s.action(0,'equip',uid=a['uid'],slot=2)
        s.action(0,'upgrade_item',uid=a['uid']);s.action(0,'upgrade_item',uid=a['uid'])
        self.assertEqual((a['tier'],b['tier'],m['essence']),(2,0,11))
        with self.assertRaises(RuleError):s.action(0,'upgrade_item',uid=a['uid'])
        s.action(0,'unequip',uid=a['uid'],slot=1);self.assertIsNone(m['equipped'][1])
        s.action(0,'equip',uid=a['uid'],slot=1)
        builds=[dict(name=x['name'],commander=x['commander'],package=0,relic=x['relic'],deck=x['deck'],**s.battle_progression(x)) for x in s.members]
        battle=Battle(builds,7);self.assertEqual(battle.effect_strength(0,'entry'),4)
        scholar=battle.instance('u_scholar',0);battle.entry_triggers(0,scholar)
        self.assertEqual(len(battle.stack),5)
        s.action(0,'upgrade_card',design='w_recruit');builds[0].update(s.battle_progression(m));battle=Battle(builds,7)
        self.assertEqual(battle.instance('w_recruit',0)['attack'],2)
        self.assertEqual(battle.instance('w_recruit',1)['attack'],1)

    def test_repeated_mulligan_bottoms_and_untimed_solo(self):
        s=training();s.tutorial=None;b=s.battle;p=b.players[0]
        for _ in range(3):s.action(0,'mulligan');self.assertEqual(len(p['hand']),5)
        s.action(0,'keep');self.assertEqual(p['bottom_remaining'],2)
        with self.assertRaises(RuleError):s.action(0,'color',color='W')
        chosen=[]
        for _ in range(2):
            c=p['hand'][0];chosen.append(c['uid']);s.action(0,'bottom',uid=c['uid'])
        self.assertEqual(len(p['hand']),3);self.assertEqual(p['grave'],[])
        self.assertEqual([c['uid'] for c in p['deck'][:2]],list(reversed(chosen)))
        s.action(1,'keep')
        while b.phase == 'draw':b.action(b.priority,'pass')
        s.action(0,'color',color='W')
        phase=b.phase;future=time.time()+10000;s.members[0]['last_seen']=future;s.tick(future);self.assertEqual(b.phase,phase);self.assertFalse(s.members[0]['bot'])


    def test_first_and_later_main_phases_wait_for_mana_choice(self):
        s=training();s.tutorial=None;b=s.battle
        for i in range(2):
            s.action(i,'keep')
            self.assertEqual(sum(b.players[i]['capacity'].values()),0)
        self.assertEqual(b.phase,'draw')
        while b.phase == 'draw':b.action(b.priority,'pass')
        self.assertEqual(b.phase,'grow')  # Mandatory first-main mana decision.
        with self.assertRaises(RuleError):s.action(0,'pass')
        with self.assertRaises(RuleError):s.action(1,'color',color='R')
        s.action(0,'auto',enabled=True)
        for offset in (1,10000):s.tick(time.time()+offset)
        self.assertEqual(b.phase,'grow')
        s.action(0,'color',color='W')
        self.assertEqual(b.phase,'main')
        self.assertEqual(b.players[0]['mana']['W'],1)
        with self.assertRaises(RuleError):s.action(0,'color',color='U')
        b.start_turn(1)
        while b.phase == 'draw':b.action(b.priority,'pass')
        self.assertEqual(b.phase,'grow')
        s.action(1,'color',color='R')
        self.assertEqual(b.players[1]['capacity']['R'],1)
        b.start_turn(0)
        while b.phase == 'draw':b.action(b.priority,'pass')
        self.assertEqual(b.phase,'grow')
        s.action(0,'color',color='U')
        self.assertEqual(b.players[0]['mana'],{'W':1,'U':1})

    def test_manual_priority_and_mandatory_mana_even_with_auto_enabled(self):
        s=training();s.tutorial=None;b=s.battle
        for i,p in enumerate(b.players):
            s.action(i,'keep')
        while b.phase == 'draw':b.action(b.priority,'pass')
        s.action(0,'color',color='W')
        s.action(0,'respond')
        m=s.members[0];p=b.players[0];p['hand']=[];b.phase='precombat';b.priority=0
        now=time.time();m['last_seen']=now;s.last_decision=now-1000
        s.tick(now)
        self.assertEqual(b.priority,0);self.assertFalse(m['bot'])
        s.action(0,'auto',enabled=True)
        self.assertEqual(b.priority,1)  # Resume passes this opportunity immediately.
        b.start_turn(0)
        while b.phase == 'draw':b.action(b.priority,'pass')
        self.assertEqual(b.phase,'grow')
        capacity=copy.deepcopy(p['capacity']);m['last_seen']=now+2;s.tick(now+2)
        self.assertEqual(b.phase,'grow');self.assertEqual(p['capacity'],capacity)
        s.action(0,'color',color='U');self.assertEqual(b.phase,'main')
        self.assertEqual(p['capacity']['U'],1)

    def test_opening_offers_are_in_identity(self):
        import random
        for colors in (['W'],['U','B']):
            for seed in range(10):
                pack=personal_pack(random.Random(seed),colors,15,5,legal_only=True)
                self.assertEqual(len(pack),15)
                self.assertTrue(all(CARD_MAP[id]['color'] in colors+['C'] for id in pack))


    def test_maximum_entry_stack_revival_and_token_stats(self):
        s=training();s.tutorial=None;m=s.members[0]
        m['items']=[];m['equipped']=[None]*3
        for _ in range(3):s.add_item(m,'panharmonicon')['tier']=2
        m['card_upgrades']={'w_recruit':2,'c_nest':2,'u_scholar':2}
        builds=[dict(name=x['name'],commander=x['commander'],package=0,relic=x['relic'],deck=x['deck'],**s.battle_progression(x)) for x in s.members]
        b=Battle(builds,3)
        foundry=b.instance('c_nest',0);b.entry_triggers(0,foundry)
        self.assertEqual(len(b.stack),10);self.assertTrue(all(t['amount']==3 for t in b.stack))
        while b.stack:b.resolve(b.stack.pop())
        self.assertEqual(len(b.players[0]['board']),30)
        self.assertTrue(all((c['attack'],c['health'],c['upgrade'])==(1,1,0) for c in b.players[0]['board']))
        recruit=b.instance('w_recruit',0);b.entry_triggers(0,recruit);self.assertEqual(b.stack,[])
        scholar=b.instance('u_scholar',0);b.players[0]['grave'].append(scholar)
        b.push(0,'revive',target=scholar['uid'],card=b.instance('b_revive',0))
        b.resolve(b.stack.pop())
        self.assertEqual(len(b.stack),10);self.assertTrue(all(t['amount']==3 for t in b.stack))
        self.assertEqual(sum(c['uid']==scholar['uid'] for c in b.players[0]['board']),1)

    def test_legacy_save_migrates_equipment_without_rewriting_battle(self):
        s=training();s.tutorial=None;data=s.to_dict();data.pop('item_serial');data.pop('tutorial')
        for m in data['members']:
            for key in ('items','equipped','card_upgrades','essence'):m.pop(key)
        data['battle'].pop('card_upgrades')
        for p in data['battle']['players']:
            for key in ('equipment','mulligan_count','bottom_remaining'):p.pop(key)
        old_hand=copy.deepcopy(data['battle']['players'][0]['hand'])
        restored=Session.from_dict(data)
        self.assertEqual(restored.members[0]['items'][0]['design'],'reserves')
        self.assertEqual(restored.members[0]['equipped'][0],restored.members[0]['items'][0]['uid'])
        self.assertEqual(restored.battle.players[0]['hand'],old_hand)
        self.assertEqual(restored.battle.effect_strength(0,'reserves'),1)
        self.assertEqual(restored.battle.players[0]['bottom_remaining'],0)

    def test_mulligan_limit_and_independent_penalties(self):
        s=training();s.tutorial=None;b=s.battle
        for _ in range(6):s.action(0,'mulligan')
        with self.assertRaises(RuleError):s.action(0,'mulligan')
        s.action(0,'keep');s.action(1,'mulligan');s.action(1,'keep')
        self.assertEqual(b.players[0]['bottom_remaining'],5)
        self.assertEqual(b.players[1]['bottom_remaining'],0)
        for _ in range(5):s.action(0,'bottom',uid=b.players[0]['hand'][0]['uid'])
        self.assertEqual(len(b.players[0]['hand']),1)  # Automatic turn-start draw after bottoming.
        self.assertEqual(b.players[0]['grave'],[])
        while b.phase == 'draw':b.action(b.priority,'pass')
        s.action(0,'color',color='W')
        self.assertEqual(b.phase,'main')

if __name__=='__main__':unittest.main()

