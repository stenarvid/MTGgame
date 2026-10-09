"""Isolated, deterministic training campaign using production battle and inventory actions."""
import copy
import time
from .battle import Battle, RuleError
from .content import starter

LESSONS = {
 'stats': ('Read your cards', 'Attack is damage dealt; health is damage a creature can survive. Colored symbols must be paid with that color; numbers accept any mana. Inspect a card, then continue.'),
 'opening': ('Keep an opening hand', 'You draw five cards. Your first mulligan is free; later redraws require bottoming more cards when keeping. Keep and finish any bottom choices. At the start of your main phase, select a white mana gem.'),
 'summon': ('Play Citadel Recruit', 'Select Citadel Recruit in your hand. Pay one white mana, then pass priority so Mira can respond. The creature enters only when the action resolves.'),
 'first_turn': ('New creatures wait', 'Your Recruit can block now, but cannot attack until your next turn. Continue to combat, declare no attacks, then pass through the remaining windows.'),
 'block': ('Defend against an attack', 'Mira attacks with a 2/1 Ember Duelist. Assign your 1/3 Recruit as a blocker and confirm. It deals 1 and takes 2 simultaneously; its damage lasts until your next turn.'),
 'mana': ('Choose mana at the start of your main phase', 'At the start of your second turn, mana refreshes. Choose blue to add capacity before playing cards. Unspent mana also pays for responses on opponents’ turns.'),
 'duel': ('Win the practice encounter', 'Attack Mira with ready creatures. Add Tide Apprentice for another attacker; later Tide Scholar draws on entry. Protection and returning creatures are responses. Mira starts this practice at 3 health and stops attacking after the blocking lesson.'),
 'rewards': ('Collect victory rewards', 'A normal victory grants 1 shop currency, 2 Essence, and a pack: keep two legal cards. This tutorial also announces a training bonus of 1 currency and 1 Essence so you can try a purchase and upgrade immediately.'),
 'card_upgrade': ('Spend Essence on a card design', 'In Celestial inventory, select Citadel Recruit, and inspect its +1 preview. Confirm the 3-Essence upgrade. Every owned and future copy of that design improves for this campaign.'),
 'shop': ('Buy equipment', 'The shop sells cards for 1 currency and equipment for 2. Buy the Panharmonicon. Each item is a separately owned copy; buying duplicates can fill different slots.'),
 'equipment': ('Try your equipment slots', 'Your new Panharmonicon was placed in a free slot. Unequip it, then equip that same copy again. There are three flexible slots. Different copies stack; one physical item cannot occupy two slots.'),
 'item_upgrade': ('Upgrade an individual item', 'Training cache: +3 Essence to try an item upgrade. Select your Panharmonicon and confirm +1. Its extra entry triggers increase from one to two. Item tiers are independent; +2 costs another 6 Essence.'),
 'boss_ready': ('Prepare for the boss', 'Your card upgrade and equipped items carry into battle. A boss victory grants 4 Essence and another item choice. Begin the training boss encounter when ready.'),
 'boss': ('Defeat the training boss', 'Use your upgraded creatures and responses. Panharmonicon repeats Tide Scholar and Recruit Foundry entry abilities, not their summons. The training boss starts at 5 health and uses the ordinary boss draw rule.'),
 'boss_rewards': ('Claim the boss spoils', 'You earned 4 Essence and another equipment choice. Choose an item and keep two reward cards. Equipment changes are free between encounters; campaign upgrades reset in a new campaign.'),
 'complete': ('Training complete', 'You played real cards, blocked, grew mana, won battles, collected rewards, bought equipment, and upgraded a design and an item. Return to Rooms to start a fresh campaign, or replay this tutorial.')
}


def initialize(s):
    """Reset only this training room, never another saved campaign."""
    from .session import Session
    name = s.members[0]['name'] if s.members else 'Player'
    fresh = Session('solo',seed=2718,size=2)
    fresh.add_member(name)
    fresh.add_member('Mira, Training Rival',True)
    s.__dict__.clear()
    s.__dict__.update(fresh.__dict__)
    for m,cmd in zip(s.members,('wu','ember')):
        m.update(commander=cmd,package=0,relic='reserves')
        m['deck'] = starter(s.colors(m['id']))
        m['owned'] = list(m['deck'])
    s.add_item(s.members[0],'reserves')
    s.tutorial = dict(step='stats',bonus=False,purchased=None,unequipped=False,cache=False)
    s.starting_offset = 0
    s.seating = [0,1]
    training_battle(s,False)


def training_battle(s,boss):
    s.stage = 'battle'
    s.results_applied = False
    builds = []
    for seat,m in enumerate(s.members):
        m['seat'] = seat
        m['ready'] = False
        builds.append(dict(name=m['name'],commander=m['commander'],package=m['package'],
                           relic=m['relic'],deck=m['deck'],**s.battle_progression(m)))
    s.battle_seed = 2718 + int(boss)
    s.battle = Battle(builds,s.battle_seed,0,dict(act=1,battle=4 if boss else 1,
        kind='Training Boss' if boss else 'Practice',rule='insight' if boss else '',coordinated=False,
        description='Announced training setup: rival starts at 5 health.' if boss else 'Announced training setup: rival starts at 3 health.'))
    b = s.battle
    b.players[1]['hp'] = 5 if boss else 3
    # Predetermined legal hands and draw order, without changing any card definition.
    order = ['w_recruit','u_apprentice','u_scholar','w_shield','u_return','c_nest']
    for i,p in enumerate(b.players):
        ids = s.members[i]['deck']
        desired = order if i == 0 else ['r_duelist']
        remaining = list(ids)
        hand = []
        for design in desired[:5]:
            if design in remaining:
                remaining.remove(design)
                hand.append(b.instance(design,i))
        p['hand'] = hand
        p['deck'] = [b.instance(design,i) for design in remaining]
        if i == 0:
            # Support another blue creature on the next draw.
            apprentice = next((c for c in p['deck'] if c['id']=='u_apprentice'),None)
            if apprentice:
                p['deck'].remove(apprentice)
                p['deck'].append(apprentice)
    if boss:
        s.encounter = 3
    b.note(b.encounter['description'])
    s.last_decision = time.time()


def lesson_view(s):
    sync(s)
    step = s.tutorial['step']
    title,text = LESSONS[step]
    keys = list(LESSONS)
    return dict(step=step,title=title,text=text,index=keys.index(step)+1,total=len(keys),
                informational=step=='stats',complete=step=='complete')


def tutorial_action(s,i,action,data):
    if i != 0:
        return False
    sync(s)
    step = s.tutorial['step']
    if action == 'tutorial_restart':
        initialize(s)
        return True
    if action == 'tutorial_exit':
        s.stage = 'complete'
        s.tutorial['step'] = 'complete'
        return True
    if action == 'tutorial_next':
        if step != 'stats':
            raise RuleError('Complete the lesson’s playable action to continue.')
        s.tutorial['step'] = 'opening'
        return True
    if action in ('auto','reclaim','feedback'):
        return False
    if action == 'ready' and step == 'boss_ready':
        training_battle(s,True)
        s.tutorial['step'] = 'boss'
        return True
    if step in ('stats','complete'):
        raise RuleError('Use the tutorial controls to continue or restart.')
    # Gate economy lessons before any mutation or resource deduction.
    restricted = {'rewards':{'pick'},'card_upgrade':{'upgrade_card'},'shop':{'buy_item'},
                  'equipment':{'equip','unequip'},'item_upgrade':{'upgrade_item'},
                  'boss_ready':{'ready'},'boss_rewards':{'pick','relic'}}
    if step in restricted and action not in restricted[step]:
        raise RuleError('Follow the current lesson before continuing: '+LESSONS[step][0])
    if step == 'card_upgrade' and data.get('design') != 'w_recruit':
        raise RuleError('Upgrade Citadel Recruit for this lesson.')
    if step == 'shop' and (data.get('index') != 0 or s.gear_shop[0] != 'panharmonicon'):
        raise RuleError('Buy the offered Panharmonicon for this lesson.')
    if step in ('equipment','item_upgrade') and data.get('uid') != s.tutorial['purchased']:
        raise RuleError('Use your newly purchased Panharmonicon for this lesson.')
    if step == 'summon' and action == 'cast':
        c = next((c for c in s.battle.players[0]['hand'] if c['uid']==data.get('uid')),None)
        if not c or c['id'] != 'w_recruit':
            raise RuleError('Play Citadel Recruit for this lesson.')
    if step == 'block' and action == 'block':
        recruit = next((c for c in s.battle.players[0]['board'] if c['id'] == 'w_recruit'),None)
        assigned = [uid for group in data.get('blocks',{}).values() for uid in group]
        if not recruit or recruit['uid'] not in assigned:
            raise RuleError('Assign Citadel Recruit to block the attacking Ember Duelist.')
    if step == 'opening' and action == 'color' and data.get('color') != 'W':
        raise RuleError('Choose white to cast Citadel Recruit in the next lesson.')
    if step == 'mana' and action == 'color' and data.get('color') != 'U':
        raise RuleError('Choose blue to learn your commander’s second color.')
    return False


def after_action(s,action,data):
    t = s.tutorial
    if not t:
        return
    if t['step']=='card_upgrade' and action=='upgrade_card':
        t['step']='shop'
    elif t['step']=='shop' and action=='buy_item':
        t['purchased']=s.members[0]['items'][-1]['uid']
        t['step']='equipment'
    elif t['step']=='equipment':
        if action=='unequip':
            t['unequipped']=True
        elif action=='equip' and t['unequipped']:
            t['step']='item_upgrade'
            if not t['cache']:
                s.members[0]['essence'] += 3
                t['cache']=True
    elif t['step']=='item_upgrade' and action=='upgrade_item':
        t['step']='boss_ready'
    sync(s)


def sync(s):
    if not s.tutorial:
        return
    t,m,b = s.tutorial,s.members[0],s.battle
    if s.stage in ('retry','defeat'):
        return
    step = t['step']
    if step=='opening' and b.phase=='main':
        t['step']='summon'
    elif step=='summon' and any(c['id']=='w_recruit' for c in b.players[0]['board']):
        t['step']='first_turn'
    elif step=='first_turn' and b.phase=='blocks' and b.priority==0:
        t['step']='block'
    elif step=='block' and b.active==0 and b.phase=='grow':
        t['step']='mana'
    elif step=='mana' and b.active==0 and b.phase=='main':
        t['step']='duel'
    if s.stage=='build' and not t['bonus'] and b.survivor==0:
        s.currency += 1
        m['essence'] += 1
        s.gear_shop=['panharmonicon','edge']
        t['bonus']=True
        t['step']='rewards'
    elif t['step']=='rewards' and not m['reward_left']:
        t['step']='card_upgrade'
    elif t['step']=='boss' and s.stage=='build':
        t['step']='boss_rewards'
    elif t['step']=='boss_rewards' and not m['reward_left'] and not m['relic_options']:
        t['step']='complete'
        s.stage='complete'


def ai_action(s,seat):
    """Script choices only; costs, timing, targets and combat still use Battle.action."""
    b,p = s.battle,s.battle.players[seat]
    if b.phase in ('opening','grow') or b.choice:
        return b.ai_action(seat)
    if b.phase in ('main','main2') and not b.stack and s.tutorial['step'] in ('first_turn','block','boss'):
        c = next((c for c in p['hand'] if c['id']=='r_duelist' and b.castable(seat,c)),None)
        if c:
            return dict(action='cast',uid=c['uid'])
    if b.phase=='combat' and not b.stack:
        attack = s.tutorial['step'] in ('first_turn','block','boss')
        return dict(action='attack',attacks=[dict(uid=c['uid'],defender=0) for c in p['board'] if attack and b.attack_ready(c)])
    if b.phase=='blocks':
        return dict(action='block',blocks={})
    return dict(action='pass')
