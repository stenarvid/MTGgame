"""Production-rule regressions for sockets, owned gear, ward and permanent spending."""
import copy
import unittest
from tactical.battle import Battle, RuleError
from tactical.content import starter, CARD_MAP
from tactical.items import compose, validate_sockets, NEW_CARDS, GEAR, NEW_RELICS, CONSUMABLES, GEM_FAMILIES
from tactical.session import Session


def item(design='spiresteel_blade', tier=2, gems=None, uid='testgear'):
    return dict(uid=uid, design=design, tier=tier, gems=gems or {})


def battle(gems=None, relics=None):
    gear = compose(item(gems=gems))
    builds = [dict(name='Player', commander='rg', package=0, relic='reserves', deck=starter('RG'),
                   gear_cards={'gear:testgear':gear}, equipment=relics or [],
                   pouch=[dict(uid='flask',design='ember_flask'),dict(uid='potion',design='healing_draught')]),
              dict(name='Opponent', commander='wu', package=0, relic='reserves', deck=starter('WU'))]
    b = Battle(builds, 3)
    b.active = b.priority = 0; b.phase = 'main'
    for p in b.players:
        p['kept'] = True; p['completed_turn'] = True
        p['mana'] = {c:10 for c in 'WUBRG'}; p['capacity'] = {c:2 for c in p['colors']}
    return b


def settle(b):
    for _ in range(50):
        if not b.stack or b.choice: return
        b.action(b.priority, 'pass')
    raise AssertionError('Stack did not settle')


def campaign():
    s=Session('solo',seed=42);s.add_member('Player');s.start(0)
    s.members[0]['offers']=['rg'];s.choose_commander(0,'rg',0)
    while s.stage=='draft':s.action(0,'pick',index=0)
    s.action(0,'relic',relic=s.members[0]['relic_options'][0]);s.currency=30
    s.members[0]['essence']=30
    return s


class ItemRules(unittest.TestCase):
    def test_approved_counts_and_colors(self):
        self.assertEqual([len(x) for x in (NEW_CARDS,GEAR,NEW_RELICS,CONSUMABLES,GEM_FAMILIES)], [10,5,3,5,6])
        self.assertEqual({color:sum(c['color']==color for c in NEW_CARDS) for color in 'WUBRG'},dict.fromkeys('WUBRG',2))

    def test_composed_roles_and_reusable_unlocks(self):
        s=campaign();m=s.members[0];m['gem_unlocks']={'might':2,'binding':2,'brood':2,'vitality':2}
        a=s.add_item(m,'spiresteel_blade',2);b=s.add_item(m,'spiresteel_blade',2)
        for x in (a,b):s.action(0,'socket_gem',uid=x['uid'],gem='might',tier=0)
        self.assertEqual(m['gem_unlocks']['might'],2)
        before=copy.deepcopy(a)
        s.action(0,'preview_socket',uid=a['uid'],gem='binding',tier=1)
        self.assertEqual(a,before)
        s.action(0,'socket_gem',uid=a['uid'],gem='binding',tier=1)
        self.assertEqual(compose(a)['cost'],1)
        with self.assertRaises(RuleError):s.action(0,'socket_gem',uid=a['uid'],gem='might',tier=1)
        self.assertEqual(a['gems']['might'],0)
        s.action(0,'clear_socket',uid=a['uid'],gem='binding')
        s.action(0,'socket_gem',uid=a['uid'],gem='might',tier=2)
        self.assertEqual(compose(a)['gear_attack'],3)

    def test_relic_full_combination_and_slot_costs(self):
        r=item('smith_insignia',2,dict(might=0,brood=0,vitality=0))
        validate_sockets(r,dict(might=2,brood=2,vitality=2))
        self.assertEqual(compose(r)['text'],'Whenever a creature token you control attacks, it gets +1/+0 until end of turn and you gain 1 life.')
        r['gems']={'vitality':1,'brood':0};validate_sockets(r,dict(vitality=1,brood=0))
        self.assertEqual(compose(r)['health'],2)
        with self.assertRaises(ValueError):validate_sockets(item(tier=1,gems={'might':1}),dict(might=1))

    def test_item_upgrade_only_unlocks_socket(self):
        s=campaign();m=s.members[0];x=s.add_item(m,'smith_insignia');text=compose(x)['text']
        s.action(0,'upgrade_item',uid=x['uid'])
        self.assertEqual(compose(x)['text'],text);self.assertEqual(len(compose(x)['sockets']),2)

    def test_distinct_copies_shared_limit_and_identity(self):
        s=campaign();m=s.members[0];items=[s.add_item(m,'spiresteel_blade') for _ in range(3)]
        deck=list(m['deck']);deck[-2:]=['gear:'+x['uid'] for x in items[:2]];s.validate_deck(0,deck)
        deck[-3:]=['gear:'+x['uid'] for x in items]
        with self.assertRaises(RuleError):s.validate_deck(0,deck)
        deck=list(m['deck']);deck[-2:]=['gear:'+items[0]['uid']]*2
        with self.assertRaises(RuleError):s.validate_deck(0,deck)
        off=s.add_item(m,'dawnward_shield');deck[-2:]=[m['deck'][-2],'gear:'+off['uid']]
        with self.assertRaises(RuleError):s.validate_deck(0,deck)

    def test_relic_unique_and_gear_not_loadout(self):
        s=campaign();m=s.members[0];m['equipped']=[None]*3
        a=s.add_item(m,'smith_insignia');b=s.add_item(m,'smith_insignia');g=s.add_item(m,'spiresteel_blade')
        with self.assertRaises(RuleError):s.action(0,'equip',uid=b['uid'],slot=1)
        with self.assertRaises(RuleError):s.action(0,'equip',uid=g['uid'],slot=1)

    def test_equip_stack_recruit_and_death_detaches(self):
        b=battle();p=b.players[0];c=b.instance('w_spire_recruit',0);p['board']=[c]
        g=b.instance('gear:testgear',0);p['hand'].append(g)
        b.action(0,'cast',uid=g['uid']);settle(b)
        self.assertIn(g,p['gear']);self.assertFalse(g['attachment'])
        b.action(0,'equip_gear',uid=g['uid'],target=c['uid'])
        self.assertEqual(b.stats(c),(2,2));settle(b)
        self.assertEqual(b.stats(c),(4,3));self.assertIn('Guard',b.keywords(c))
        b.death(p,c);self.assertIn(g,p['gear']);self.assertIsNone(g['attachment'])

    def test_equip_cannot_respond_or_refund_fizzle(self):
        b=battle();p=b.players[0];c=b.instance('w_recruit',0);p['board']=[c]
        g=b.instance('gear:testgear',0);p['gear']=[g]
        b.phase='damage_response'
        with self.assertRaises(RuleError):b.action(0,'equip_gear',uid=g['uid'],target=c['uid'])
        b.phase='main';before=sum(p['mana'].values())
        b.action(0,'equip_gear',uid=g['uid'],target=c['uid']);b.death(p,c);settle(b)
        self.assertIsNone(g['attachment']);self.assertEqual(sum(p['mana'].values()),before-1)

    def test_auto_attachment_is_targeted_counterable_trigger(self):
        b=battle({'binding':0});p=b.players[0];c=b.instance('w_recruit',0);p['board']=[c]
        g=b.instance('gear:testgear',0);p['hand'].append(g);self.assertEqual(g['cost'],2)
        b.action(0,'cast',uid=g['uid']);settle(b)
        self.assertEqual(b.choice['kind'],'attachment_target')
        b.action(0,'choose_item_target',target=c['uid'])
        trigger=b.stack[-1];b.resolve(dict(uid='test',owner=1,effect='counter',target=trigger['uid'],amount=0,card=None,kind='ability',name='Counter'))
        self.assertIsNone(g['attachment']);self.assertIn(g,p['gear'])

    def test_ward_resolves_with_payment_and_can_be_countered(self):
        b=battle({'guardian':0});g=b.instance('gear:testgear',0);c=b.instance('w_recruit',0)
        b.players[0]['gear']=[g];b.players[0]['board']=[c];g['attachment']=c['uid']
        b.priority=1;bolt=b.instance('r_bolt',1);b.players[1]['hand'].append(bolt)
        before=sum(b.players[1]['mana'].values());b.action(1,'cast',uid=bolt['uid'],target=c['uid'])
        self.assertEqual(sum(b.players[1]['mana'].values()),before-2)
        self.assertEqual(b.stack[-1]['effect'],'item_ward');settle(b)
        self.assertEqual(b.choice['cost'],2);b.action(1,'choose_item_payment',pay=False)
        self.assertFalse(b.stack);self.assertEqual(c['damage'],0)

    def test_consume_invalid_target_free_but_counter_and_fizzle_spent(self):
        b=battle();p=b.players[0];mana=copy.deepcopy(p['mana'])
        with self.assertRaises(RuleError):b.action(0,'consume',uid='flask',target='unknown')
        self.assertEqual(p['mana'],mana);self.assertEqual(len(p['pouch']),2)
        c=b.instance('w_recruit',1);b.players[1]['board']=[c]
        b.action(0,'consume',uid='flask',target=c['uid']);b.death(b.players[1],c);settle(b)
        self.assertEqual(p['spent_consumables'],['flask']);self.assertEqual(len(p['pouch']),1)
        b.priority=0;b.action(0,'consume',uid='potion');s=b.stack.pop();b.finish_card(s)
        self.assertFalse(p['pouch']);self.assertEqual(p['hp'],25)

    def test_consumption_persists_reload_defeat_and_retry(self):
        s=campaign();m=s.members[0];potion=s.add_consumable(m,'healing_draught');s.action(0,'pouch',uid=potion['uid'],slot=0)
        s.action(0,'ready');b=s.battle
        b.phase='main';b.active=b.priority=0;b.players[0]['mana']={'R':3}
        s.action(0,'consume',uid=potion['uid'])
        self.assertFalse(m['consumables']);self.assertEqual(m['pouch'],[None,None])
        s=Session.from_dict(s.to_dict());b=s.battle
        b.finished=True;b.survivor=1;s.apply_results();self.assertEqual(s.stage,'retry')
        s.action(0,'retry');self.assertFalse(s.battle.players[0]['pouch'])

    def test_gems_and_pouch_lock_in_battle(self):
        s=campaign();x=s.add_item(s.members[0],'smith_insignia');s.action(0,'ready')
        for action,data in [('socket_gem',dict(uid=x['uid'],gem='might',tier=0)),('pouch',dict(slot=0,uid=None))]:
            with self.assertRaises(RuleError):s.action(0,action,**data)

    def test_attack_relic_uncapped_and_end_turn_expiry(self):
        b=battle(relics=[item('muster_standard',2,{'vitality':2})]);p=b.players[0]
        p['board']=[b.instance('w_recruit',0) for _ in range(6)]
        for c in p['board']:c['sick']=False
        b.phase='combat';b.action(0,'attack',attacks=[dict(uid=c['uid'],defender=1) for c in p['board']]);settle(b)
        self.assertEqual(p['hp'],31);self.assertEqual(b.stats(p['board'][0]),(1,6))
        b.phase='end';b.advance();self.assertEqual(b.stats(p['board'][0]),(1,3))

    def test_control_and_copy_preserve_modifications_not_ownership(self):
        b=battle({'binding':2});p=b.players[0];g=b.instance('gear:testgear',0);p['gear']=[g]
        c=b.instance('w_recruit',0);p['board']=[c];g['attachment']=c['uid']
        b.change_control(g['uid'],1);self.assertEqual(g['attachment'],c['uid']);self.assertIn('Haste',b.keywords(c))
        token=b.copy_equipment(g['uid'],1);self.assertTrue(token['token']);self.assertEqual(token['gems'],g['gems']);self.assertNotIn('item_uid',token)
        b.move_out(b.players[1],g);self.assertIn(g,p['grave']);self.assertNotIn(g,b.players[1]['grave'])

    def test_artifact_removal_and_hexproof(self):
        b=battle();g=b.instance('gear:testgear',0);b.players[0]['gear']=[g]
        self.assertIn(g['uid'],b.targets(1,'artifact'))
        b.resolve(dict(owner=1,effect='destroy_artifact',target=g['uid'],amount=0,card=None,kind='ability',name='Break',target_kind='artifact'))
        self.assertIn(g,b.players[0]['grave'])
        c=b.instance('w_recruit',0);b.players[0]['board']=[c]
        c['end_buffs']=[dict(keywords=['Hexproof'])]
        self.assertNotIn(c['uid'],b.targets(1,'creature'));self.assertIn(c['uid'],b.targets(0,'friendly'))

    def test_cast_triggers_survive_counter_and_optional_draw(self):
        b=battle();p=b.players[0];study=b.instance('u_artificer_study',0);p['engines']=[study]
        tender=b.instance('g_wildsteel_tender',0);p['board']=[tender]
        g=b.instance('gear:testgear',0);p['hand'].append(g);b.action(0,'cast',uid=g['uid'])
        self.assertEqual(b.choice['kind'],'counter_target');b.action(0,'choose_item_target',target=tender['uid'])
        spell=next(s for s in b.stack if s.get('card') is g);b.stack.remove(spell);b.finish_card(spell)
        count=len(p['hand']);settle(b);self.assertEqual(len(p['hand']),count+1);self.assertEqual(tender['attack'],3)

    def test_soft_counter_only_noncreature_spells_and_payment(self):
        b=battle();c=b.instance('u_artificer_study',1);b.push(1,c['effect'],card=c,kind=c['kind'])
        target=b.stack[-1]['uid'];self.assertIn(target,b.targets(0,'noncreature_spell'))
        b.resolve(dict(owner=0,effect='soft_counter',target=target,amount=0,card=None,kind='ability',name='Disrupt',target_kind='noncreature_spell'))
        self.assertEqual(b.choice['owner'],1);b.action(1,'choose_item_payment',pay=True);settle(b)
        self.assertIn(c,b.players[1]['engines'])

    def test_optional_equipped_death_and_attack_choices(self):
        b=battle();p=b.players[0]
        squire=b.instance('b_graveward_squire',0);victim=b.instance('w_recruit',0)
        p['board']=[squire,victim];g=b.instance('gear:testgear',0);p['gear']=[g];g['attachment']=victim['uid']
        count=len(p['hand']);b.death(p,victim);settle(b)
        self.assertEqual(b.choice['kind'],'optional_death_draw')
        b.action(0,'choose_item_payment',pay=True)
        self.assertEqual(len(p['hand']),count+1);self.assertEqual(p['hp'],24)
        raider=b.instance('r_forgefire_raider',0);raider['sick']=False;p['board'].append(raider);g['attachment']=raider['uid']
        b.phase='combat';b.action(0,'attack',attacks=[dict(uid=raider['uid'],defender=1)]);settle(b)
        self.assertEqual(b.choice['kind'],'optional_loot');discard=p['hand'][0];b.action(0,'choose_item_discard',uid=discard['uid'])
        self.assertIn(discard,p['grave']);self.assertEqual(len(p['hand']),count+1)

    def test_ward_payment_counter_and_multiple_instances(self):
        b=battle({'guardian':0});p=b.players[0];c=b.instance('w_recruit',0);p['board']=[c]
        for _ in range(2):
            g=b.instance('gear:testgear',0);g['attachment']=c['uid'];p['gear'].append(g)
        b.priority=1;bolt=b.instance('r_bolt',1);b.players[1]['hand'].append(bolt)
        b.action(1,'cast',uid=bolt['uid'],target=c['uid'])
        self.assertEqual(sum(s['effect']=='item_ward' for s in b.stack),2)
        ward=b.stack[-1]
        b.resolve(dict(owner=1,effect='counter',target=ward['uid'],amount=0,card=None,kind='ability',name='Counter Ward'))
        settle(b);self.assertEqual(b.choice['kind'],'payment')
        b.action(1,'choose_item_payment',pay=True);settle(b)
        self.assertIn(c,p['grave'])

    def test_cleanup_death_triggers_before_next_turn(self):
        b=battle();p=b.players[0];c=b.instance('b_shambler',0);p['board']=[c]
        c['end_buffs']=[dict(attack=0,health=2)];c['damage']=2;b.phase='end'
        b.advance();self.assertEqual(b.phase,'cleanup');self.assertEqual(b.active,0)
        self.assertTrue(b.stack);settle(b)
        b.action(0,'pass');b.action(1,'pass');self.assertEqual(b.active,1)

    def test_consumable_timing_color_and_duplicate_slots(self):
        s=campaign();m=s.members[0];a=s.add_consumable(m,'ember_flask');b=s.add_consumable(m,'ember_flask')
        s.action(0,'pouch',slot=0,uid=a['uid'])
        with self.assertRaises(RuleError):s.action(0,'pouch',slot=1,uid=a['uid'])
        s.action(0,'pouch',slot=1,uid=b['uid'])
        illegal=s.add_consumable(m,'mistveil_vial')
        with self.assertRaises(RuleError):s.action(0,'pouch',slot=0,uid=illegal['uid'])
        duel=battle();duel.players[0]['colors']=['W'];duel.players[0]['pouch']=[dict(uid='beacon',design='militia_beacon')]
        duel.phase='damage_response'
        with self.assertRaises(RuleError):duel.action(0,'consume',uid='beacon')
        self.assertEqual(len(duel.players[0]['pouch']),1)

    def test_separate_supply_rewards_once_and_legal_loot(self):
        from unittest.mock import patch
        s=campaign();m=s.members[0]
        self.assertNotIn('dawnward_shield',s.loot_designs())
        self.assertIn('rootbreaker_maul',s.loot_designs())
        with patch.object(s.rng,'random',return_value=0):s.supply_rewards(m)
        self.assertEqual(len(m['consumables']),1);self.assertEqual(len(m['gem_unlocks']),1)
        m['gem_unlocks']=dict.fromkeys(('might','brood','vitality','binding','guardian','bastion'),2)
        essence=m['essence']
        with patch.object(s.rng,'random',return_value=0):s.supply_rewards(m)
        self.assertEqual(m['essence'],essence+1)
        s.action(0,'ready');s.battle.finished=True;s.battle.survivor=0
        with patch.object(s.rng,'random',return_value=0):s.apply_results()
        snapshot=copy.deepcopy(m)
        s.apply_results();self.assertEqual(m,snapshot)


if __name__=='__main__':unittest.main()
