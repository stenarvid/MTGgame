"""Drafting, fixed-size builds, competition scoring and four-act solo campaign."""
import copy
import random
import time
from collections import Counter
from .battle import Battle, RuleError
from .content import (COLORS, CARDS, CARD_MAP, COMMANDERS, COMMANDER_MAP, RELICS,
                      BASICS, starter, legal, draft_pack, personal_pack)
from .progression import (EQUIPMENT, EQUIPMENT_MAP, equipment_view, upgraded_card,
                          upgrade_preview, UPGRADE_COSTS, MAX_TIER, SLOTS)
from .campaign import MODIFIERS, TREASURE_ODDS, make_map, bonus


from .item_session import ItemSession
from .items import ITEM_MAP, GEM_FAMILIES, GEM_MAP, CONSUMABLES, CONSUMABLE_MAP, compose, compatible, occupied


from .priority import PrioritySession, preferences


class Session(PrioritySession, ItemSession):
    def __init__(self, mode='human', seed=None, target=5, size=2):
        if mode not in ('human','solo') or size not in (2,3,4) or not 1 <= target <= 50:
            raise RuleError('Choose a supported mode, 2–4 seats, and a target of 1–50.')
        self.rng = random.Random(seed)
        self.mode, self.size, self.target = mode, 2, target
        self.initial_target = target
        self.host = 0
        self.seating = []
        self.starting_offset = 0
        self.members = []
        self.stage = 'lobby'
        self.battle = None
        self.battle_number = 0
        self.encounter = 0
        self.currency = 0
        self.retry = 1
        self.pending_retry = False
        self.votes = {}
        self.vote_options = ['extend','quit','restart']
        self.vote_message = ''
        self.last_decision = time.time()
        self.time_signature = None
        self.pick_number = 0
        self.draft_round = 0
        self.packs = []
        self.picks = {}
        self.results_applied = False
        self.ai_since = 0
        self.battle_seed = 0
        self.last_tick = time.time()
        self.reports = []
        self.feedback = {}
        self.item_serial = 0
        self.tutorial = None
        self.difficulty = 'normal'
        self.modifier_nodes = 2
        self.route_seed = None
        self.campaign_map = None
        self.selected_node = None
        self.treasures = []

    def configure_run(self, difficulty='normal', modifier_nodes=2):
        if difficulty not in ('normal', 'hard', 'custom'):
            raise RuleError('Choose normal, hard, or custom difficulty.')
        if type(modifier_nodes) is not int or not 0 <= modifier_nodes <= 4:
            raise RuleError('Custom maps allow 0 to 4 challenge nodes.')
        self.difficulty, self.modifier_nodes = difficulty, modifier_nodes

    def ensure_map(self):
        if self.mode != 'solo' or self.tutorial or self.encounter >= 16:
            return
        act, depth = self.encounter//4+1, self.encounter%4
        if self.campaign_map and self.campaign_map['act'] == act:
            return
        if self.route_seed is None:
            self.route_seed = self.rng.randrange(2**30)
        self.campaign_map = make_map(self.route_seed, act, self.difficulty, self.modifier_nodes, depth)
        self.selected_node = self.campaign_map['reachable'][0]

    def route_node(self):
        if not self.campaign_map:
            return None
        return next((n for n in self.campaign_map['nodes'] if n['id'] == self.selected_node), None)

    def rival_info(self, i=1):
        if self.stage == 'retry':
            m = self.members[i]
            return dict(commander=m['commander'], package=m['package'], relic=m['relic'])
        node = self.route_node() if not self.tutorial else None
        return dict(commander=COMMANDERS[(self.encounter+i+(node['lane']*3 if node else 0))%len(COMMANDERS)]['id'],
                    package=(self.encounter//4)%2, relic=RELICS[(self.encounter+i)%len(RELICS)]['id'])

    def award_treasure(self, boss=False):
        if self.tutorial or (not boss and self.rng.random() >= .25):
            return
        m = self.members[0]
        items = []
        for _ in range(self.rng.randint(1, 3)):
            tier = self.rng.choices([0, 1, 2], weights=[75, 20, 5])[0]
            items.append(copy.deepcopy(self.add_item(m, self.rng.choice(self.loot_designs()), tier)))
        currency = self.rng.randint(1, 3)
        self.currency += currency
        self.treasures.append(dict(id=f'treasure:{self.battle_number}', items=items, currency=currency, revealed=False))

    def add_member(self, name, bot=False):
        if self.stage != 'lobby' or len([m for m in self.members if not m['departed']]) >= self.size:
            raise RuleError('The group is full or has already started.')
        if not isinstance(name,str) or not name.strip() or len(name) > 32:
            raise RuleError('Choose a name of 1–32 characters.')
        i = len(self.members)
        self.members.append(dict(id=i,name=name.strip(),bot=bot,commander=None,package=0,
            offers=self.rng.sample([c['id'] for c in COMMANDERS],3),deck=[],owned=[],
            relic=None,relic_options=[],ready=False,score=0,losses=0,reward=[],reward_left=0,
            timeout_count=0,time_bank=60,auto=True,departed=False,last_seen=time.time(),
            solo_packs=0,items=[],equipped=[None]*SLOTS,card_upgrades={},essence=0))
        return i

    def start(self, i):
        if i != self.host or self.stage != 'lobby':
            raise RuleError('The host starts the lobby.')
        if self.mode == 'solo':
            while len(self.members) < 2:
                self.add_member(f"Spire rival {len(self.members)}",True)
        if len([m for m in self.members if not m['departed']]) < 2:
            raise RuleError('At least two players are required.')
        self.size = len([m for m in self.members if not m['departed']])
        self.stage = 'commanders'
        for m in self.members:
            if m['bot'] and not m['departed']:
                self.choose_commander(m['id'],m['offers'][0],0)

    def choose_commander(self, i, commander, package):
        m = self.members[i]
        if self.stage != 'commanders' or commander not in m['offers'] or package not in (0,1) or m['commander']:
            raise RuleError('Choose one offered commander and one of its two packages.')
        m['commander'],m['package'] = commander,package
        m['deck'] = starter(COMMANDER_MAP[commander]['colors'])
        m['owned'] = list(m['deck'])
        if all(m['commander'] for m in self.members if not m['departed']):
            self.stage = 'draft'
            if self.mode == 'human':
                self.begin_draft_round()
            else:
                self.members[0]['reward'] = personal_pack(self.rng,self.colors(0),15,5,legal_only=True)
                self.members[0]['reward_left'] = 5

    def colors(self, i):
        return COMMANDER_MAP[self.members[i]['commander']]['colors']

    def begin_draft_round(self):
        self.packs = [draft_pack(self.rng) if not m['departed'] else [] for m in self.members]
        self.picks = {}

    def draft_pick(self, i, index):
        if self.stage != 'draft':
            raise RuleError('No draft is active.')
        if self.mode == 'solo':
            self.reward_pick(i,index)
            return
        if i in self.picks or not isinstance(index,int) or not 0 <= index < len(self.packs[i]):
            raise RuleError('Choose one card from your current pack.')
        self.picks[i] = index
        participants = [m for m in self.members if not m['departed']]
        if len(self.picks) == len(participants):
            for j,m in enumerate(self.members):
                if not m['departed']:
                    m['owned'].append(self.packs[j].pop(self.picks[j]))
            self.pick_number += 1
            self.picks = {}
            if not self.packs[participants[0]['id']]:
                self.draft_round += 1
                if self.draft_round == 3:
                    self.finish_draft()
                else:
                    self.begin_draft_round()
            else:
                # Alternate passing direction for successive packs.
                direction = 1 if self.draft_round % 2 == 0 else -1
                active_ids = [m['id'] for m in participants]
                old = self.packs
                self.packs = [[] for _ in self.members]
                for j,seat in enumerate(active_ids):
                    self.packs[seat] = old[active_ids[(j-direction)%len(active_ids)]]

    def alternatives(self, current=None):
        return self.rng.sample([r['id'] for r in RELICS if r['id'] != current],3)

    def finish_draft(self):
        self.stage = 'build'
        for m in self.members:
            m['relic_options'] = self.rng.sample(self.loot_designs(),3) if self.mode == 'solo' and m['id'] == 0 else self.alternatives()
            m['ready'] = False

    def reward_pick(self, i, index):
        m = self.members[i]
        if self.stage not in ('draft','build') or m['reward_left'] <= 0 or not isinstance(index,int) or not 0 <= index < len(m['reward']):
            raise RuleError('No such reward choice.')
        card = m['reward'][index]
        if not legal(card,self.colors(i)):
            raise RuleError('Choose a card matching your identity or a neutral card.')
        m['owned'].append(m['reward'].pop(index))
        m['reward_left'] -= 1
        if m['reward_left'] == 0:
            m['reward'] = []
            if self.stage == 'draft' and self.mode == 'solo':
                m['solo_packs'] += 1
                if m['solo_packs'] < 3:
                    m['reward'] = personal_pack(self.rng,self.colors(i),15,5,legal_only=True)
                    m['reward_left'] = 5
                else:
                    self.finish_draft()

    def validate_deck(self, i, deck):
        m = self.members[i]
        if not isinstance(deck,list) or len(deck) != 30 or any(not isinstance(c, str) or (c not in CARD_MAP and not self.item_card(m, c)) for c in deck):
            raise RuleError('The deck must contain exactly 30 known cards.')
        if any((self.item_card(m, c) or CARD_MAP.get(c, {})).get('color') not in self.colors(i)+['C'] for c in deck):
            raise RuleError('All cards must fit commander color identity.')
        counts = Counter(deck)
        if any(n > 1 for ref,n in counts.items() if ref.startswith('gear:')):
            raise RuleError('Each Equipment card needs a separate owned item.')
        if counts-Counter(self.members[i]['owned']):
            raise RuleError('You can only use cards you own.')
        basics = {BASICS[c] for c in self.colors(i)}
        identities = Counter(self.card_identity(m, ref) for ref in deck)
        if any(n > 2 and c not in basics for c,n in identities.items()):
            raise RuleError('At most two copies per design, except starter basics.')

    def begin_battle(self):
        self.ensure_map()
        self.stage = 'battle'
        self.results_applied = False
        self.pending_retry = False
        self.battle_seed = self.rng.randrange(2**30)
        builds = []
        if self.mode == 'solo':
            self.size = 2
            for m in self.members[2:]:
                m['departed'] = True
        active_members = [m for m in self.members if not m['departed']]
        if not self.seating:
            self.seating = [m['id'] for m in active_members]
            if self.mode == 'human':
                self.rng.shuffle(self.seating)
            self.starting_offset = self.rng.randrange(len(active_members))
        active_members.sort(key=lambda m:self.seating.index(m['id']))
        if self.mode == 'solo':
            for m in self.members[1:]:
                spec = self.rival_info(m['id'])
                cmd = COMMANDER_MAP[spec['commander']]
                m.update(spec)
                m['deck'] = self.rival_deck(cmd,self.encounter//4)
        for seat,m in enumerate(active_members):
            m['seat'] = seat
            m['timeout_count'] = 0
            m['time_bank'] = 60
            builds.append(dict(name=m['name'],commander=m['commander'],package=m['package'],
                               relic=m['relic'],**(dict(deck=m['deck']) | self.battle_progression(m))))
        self.battle = Battle(builds,self.battle_seed,(self.starting_offset+self.battle_number)%len(builds),self.encounter_info())
        self.last_decision = time.time()
        self.time_signature = None

    def rival_deck(self, cmd, act):
        deck = starter(cmd['colors'])
        # Later acts replace filler with existing synergy pieces, never buff cards.
        preferred = [c['id'] for c in CARDS if legal(c['id'],cmd['colors']) and
                     (c.get('effect') in ('spell_damage','spell_draw','death_ping','death_grow','formation','relay','foundry') or c.get('cost',0)>=4)]
        for card in preferred[:act*3]:
            if deck.count(card) >= 2:
                continue
            basic = next((b for b in deck if b in BASICS.values() and deck.count(b)>1),None)
            if basic:
                deck[deck.index(basic)] = card
        return deck

    def encounter_info(self):
        if self.mode != 'solo':
            return {}
        boss = self.encounter%4 == 3
        elite = self.encounter%4 == 2
        rule = 'insight' if boss else 'reinforcements' if elite else ''
        node = self.route_node() if not self.tutorial else None
        return dict(act=self.encounter//4+1, battle=self.encounter%4+1,
                    node=node['id'] if node else None, terrain=node['terrain'] if node else 'temple',
                    modifiers=list(node['modifiers']) if node else [], bonus_essence=bonus(node['modifiers']) if node else 0,
                    kind='Boss' if boss else 'Elite' if elite else 'Encounter',
                    rule=rule,coordinated=boss or elite,
                    description='Coordinated rivals; each draws an extra card on even turns.' if boss else
                    'Coordinated rivals; each creates a Recruit at turn start.' if elite else
                    'Every rival pursues its own survival.')

    def setup_shop(self):
        self.gear_shop = self.rng.choices(self.loot_designs(),k=2)
        self.shop = self.rng.sample([c['id'] for c in CARDS if legal(c['id'],self.colors(0))],3)

    def apply_results(self):
        self.sync_consumables()
        if self.battle and self.mode == 'solo' and not self.battle.players[0]['alive'] and not self.battle.finished:
            self.battle.finished = True
            self.battle.phase = 'finished'
            self.battle.loop = None
            self.battle.note('Campaign player eliminated; encounter failed.')
        if not self.battle or not self.battle.finished or self.results_applied:
            return
        self.results_applied = True
        self.reports.append(dict(battle=self.battle_number+1,seconds=round(self.battle.elapsed),
            turns=[p['turns'] for p in self.battle.players],
            spectator_seconds=[round(self.battle.elapsed-p['eliminated_elapsed']) if p['eliminated_elapsed'] is not None else 0 for p in self.battle.players],
            points=[p['points'] for p in self.battle.players],
            concessions=sum('concedes;' in message for message in self.battle.log),
            counterplays=sum('Resolved: Null Sigil' in message for message in self.battle.log)))
        self.battle_number += 1
        self.stage = 'build'
        for m in self.members:
            m['ready'] = False
        if self.mode == 'solo':
            if self.battle.survivor != 0:
                self.stage = 'retry' if self.retry else 'defeat'
                return
            self.currency += 1
            m = self.members[0]
            boss = self.encounter%4 == 3
            m['essence'] += (4 if boss else 2) + self.battle.encounter.get('bonus_essence',0)
            self.award_treasure(boss)
            if not self.tutorial:
                self.supply_rewards(m)
            m['reward'] = personal_pack(self.rng,self.colors(0))
            m['reward_left'] = 2
            if self.encounter%4 == 3:
                m['relic_options'] = self.rng.sample(self.loot_designs(),3)
            node = self.route_node()
            if node and not self.tutorial:
                node['completed'] = True
                self.campaign_map['reachable'] = list(node['next'])
                self.selected_node = node['next'][0] if node['next'] else None
            self.encounter += 1
            self.ensure_map()
            if self.encounter == 16:
                self.stage = 'victory'
            self.setup_shop()
        else:
            for m in self.members:
                if m['departed']:
                    continue
                p = self.battle.players[m['seat']]
                m['score'] += p['points']
                if p['points']:
                    m['reward'] = personal_pack(self.rng,self.colors(m['id']))
                    m['reward_left'] = 2
                if not p['alive']:
                    m['losses'] += 1
                    if m['losses'] % 2 == 0:
                        m['relic_options'] = self.alternatives(m['relic'])
            if max(m['score'] for m in self.members if not m['departed']) >= self.target:
                self.stage = 'vote'
                self.votes = {}
                self.vote_options = ['extend','quit','restart']
                self.vote_message = 'Target reached. Vote to extend, quit, or restart.'

    def vote(self, i, choice):
        if self.stage != 'vote' or choice not in self.vote_options or self.members[i]['departed']:
            raise RuleError('No such vote option.')
        self.votes[i] = choice
        participants = [m for m in self.members if not m['departed']]
        if len(self.votes) < len(participants):
            return
        counts = Counter(self.votes.values())
        winners = [c for c,n in counts.items() if n > len(participants)/2]
        if not winners:
            if len(self.vote_options) == 2:
                self.stage = 'complete'
                self.vote_message = 'Tied runoff. Competition ended.'
            else:
                # Stable tie order is published, avoiding an invisible random tiebreak.
                self.vote_options = sorted(self.vote_options,key=lambda c:(-counts[c],['quit','extend','restart'].index(c)))[:2]
                self.votes = {}
                self.vote_message = 'Runoff. Equal option counts use quit, extend, restart order.'
            return
        winner = winners[0]
        if winner == 'extend':
            self.target = max(m['score'] for m in participants)+3
            self.stage = 'build'
            self.vote_message = f'Extended to {self.target} victory points.'
        elif winner == 'quit':
            self.stage = 'complete'
        else:
            self.battle = None
            self.battle_number = self.pick_number = self.draft_round = 0
            self.stage = 'lobby'
            self.host = participants[0]['id']
            self.seating = []
            self.target = self.initial_target
            self.votes = {}
            for m in participants:
                m.update(commander=None,package=0,deck=[],owned=[],relic=None,relic_options=[],
                         ready=False,score=0,losses=0,reward=[],reward_left=0,
                         offers=self.rng.sample([c['id'] for c in COMMANDERS],3))

    def battle_progression(self, m):
        if self.mode != 'solo':
            return {}
        self.item_defaults(m)
        if m['id'] != 0:
            if self.tutorial:
                return {}
            prepared = self.curated_items(m)
            m['deck'][:] = prepared.pop('deck')
            return prepared
        items = {item['uid']:item for item in m['items']}
        return dict(equipment=[copy.deepcopy(items[uid]) for uid in m['equipped'] if uid],
                    card_upgrades=copy.deepcopy(m['card_upgrades']),
                    gear_cards={ref:self.item_card(m, ref) for ref in m['deck'] if ref.startswith('gear:')},
                    pouch=[copy.deepcopy(x) for x in m['consumables'] if x['uid'] in m['pouch']])

    def add_item(self, m, design, tier=0):
        if design not in EQUIPMENT_MAP or type(tier) is not int or not 0 <= tier <= MAX_TIER:
            raise RuleError('Choose a known item and tier 0 to 2.')
        self.item_serial += 1
        item = dict(uid='item'+str(self.item_serial),design=design,tier=tier)
        m['items'].append(item)
        if design in ITEM_MAP and ITEM_MAP[design]['category'] == 'equipment':
            m['owned'].append('gear:'+item['uid'])
            return item
        if None in m['equipped'] and not any(x['uid'] in m['equipped'] and x['design'] == design for x in m['items'] if design in ITEM_MAP):
            m['equipped'][m['equipped'].index(None)] = item['uid']
        return item

    def inventory_action(self, i, action, data):
        m = self.members[i]
        if self.mode != 'solo' or i != 0 or self.stage not in ('build','retry') or m['ready']:
            raise RuleError('Equipment and upgrades are available between solo encounters.')
        if action == 'buy_item':
            index = data.get('index')
            if self.stage != 'build' or not isinstance(index,int) or isinstance(index,bool) or not 0 <= index < len(getattr(self,'gear_shop',[])):
                raise RuleError('Choose an available shop item.')
            if self.currency < 2:
                raise RuleError('Equipment costs 2 currency.')
            item = self.add_item(m,self.gear_shop.pop(index))
            self.currency -= 2
            return item
        if action == 'upgrade_card':
            design = data.get('design')
            if design not in m['owned'] or design not in CARD_MAP or CARD_MAP[design].get('art_style') == 'sigil':
                raise RuleError('Choose a card design you own.')
            tier = m['card_upgrades'].get(design,0)
        else:
            item = next((item for item in m['items'] if item['uid'] == data.get('uid')),None)
            if not item:
                raise RuleError('Choose an item you own.')
            if action in ('equip','unequip'):
                if item['design'] in ITEM_MAP and ITEM_MAP[item['design']]['category'] == 'equipment':
                    raise RuleError('Add Equipment to your deck; it is not a loadout Relic.')
                if action == 'equip' and any(x['design'] == item['design'] and x['uid'] != item['uid'] and x['uid'] in m['equipped'] for x in m['items']):
                    if item['design'] in ITEM_MAP:
                        raise RuleError('Only one Relic of each name may be active.')
                slot = data.get('slot')
                if not isinstance(slot,int) or isinstance(slot,bool) or not 0 <= slot < SLOTS:
                    raise RuleError('Choose one of the three equipment slots.')
                if action == 'unequip':
                    if m['equipped'][slot] != item['uid']:
                        raise RuleError('That item is not in this slot.')
                    m['equipped'][slot] = None
                else:
                    if item['uid'] in m['equipped'] and m['equipped'][slot] != item['uid']:
                        raise RuleError('Each slot needs a separately owned item copy.')
                    m['equipped'][slot] = item['uid']
                return
            tier = item['tier']
        if tier >= MAX_TIER:
            raise RuleError('This upgrade is already at the +2 maximum.')
        cost = UPGRADE_COSTS[tier]
        if m['essence'] < cost:
            raise RuleError(f'This upgrade requires {cost} Essence.')
        if action == 'upgrade_card':
            m['card_upgrades'][design] = tier+1
        else:
            item['tier'] += 1
        m['essence'] -= cost

    def action(self, i, action, **data):
        m = self.members[i]
        if m['departed']:
            raise RuleError('You have left this competition.')
        m['last_seen'] = time.time()
        if action == 'treasure_revealed' and self.mode == 'solo' and i == 0:
            treasure = next((t for t in self.treasures if t['id'] == data.get('id')), None)
            if not treasure:
                raise RuleError('No such earned treasure.')
            treasure['revealed'] = True
            return
        if action == 'route' and self.mode == 'solo' and i == 0 and self.stage == 'build' and not self.tutorial:
            self.ensure_map()
            if data.get('node') not in self.campaign_map['reachable']:
                raise RuleError('Choose a connected battle on the current path.')
            self.selected_node = data['node']
            return
        if self.tutorial:
            from .tutorial import tutorial_action
            handled = tutorial_action(self,i,action,data)
            if handled:
                return
        if action in ('socket_gem', 'preview_socket', 'clear_socket', 'upgrade_gem', 'buy_gem', 'buy_consumable', 'pouch'):
            return self.new_item_action(i, action, data)
        if action in ('equip','unequip','upgrade_item','upgrade_card','buy_item'):
            result = self.inventory_action(i,action,data)
            if self.tutorial:
                from .tutorial import after_action
                after_action(self,action,data)
            return result
        if action == 'feedback' and self.stage in ('build','retry','complete','victory','defeat'):
            text = data.get('text','')
            if not isinstance(text,str) or len(text)>500:
                raise RuleError('Feedback is limited to 500 characters.')
            self.feedback[f'{self.battle_number}:{i}'] = text
            return
        if action == 'start':
            return self.start(i)
        if action == 'add_bot' and i == self.host:
            return self.add_member(f'AI rival {len(self.members)}',True)
        if action == 'commander':
            return self.choose_commander(i,data.get('commander'),data.get('package'))
        if action == 'pick':
            return self.draft_pick(i,data.get('index')) if self.stage == 'draft' else self.reward_pick(i,data.get('index'))
        if action == 'relic' and self.stage == 'build':
            choice = data.get('relic')
            if (self.mode == 'solo' and choice not in m['relic_options']) or (choice != m['relic'] and choice not in m['relic_options']):
                raise RuleError('Choose an offered relic or keep the current one.')
            if not choice:
                raise RuleError('An initial relic is required.')
            m['relic'],m['relic_options'] = choice,[]
            if self.mode == 'solo' and i == 0:
                self.add_item(m,choice)
            return
        if action == 'deck' and self.stage in ('build','retry') and not m['ready']:
            deck = data.get('deck')
            self.validate_deck(i,deck)
            m['deck'] = list(deck)
            return
        if action in ('buy','refresh') and self.stage == 'build' and self.mode == 'solo' and i == 0:
            if self.currency < 1:
                raise RuleError('You need one currency.')
            if action == 'buy':
                index = data.get('index')
                if not isinstance(index,int) or not 0 <= index < len(self.shop):
                    raise RuleError('No such shop card.')
                m['owned'].append(self.shop.pop(index))
            else:
                self.setup_shop()
            self.currency -= 1
            return
        if action == 'ready' and self.stage == 'build':
            self.validate_deck(i,m['deck'])
            if not m['relic'] or m['reward_left'] or m['relic_options']:
                raise RuleError('Finish reward and relic choices first.')
            m['ready'] = True
            participants = self.members[:1] if self.mode == 'solo' else [x for x in self.members if not x['departed']]
            if all(x['ready'] for x in participants):
                if len([x for x in self.members if not x['departed']]) < 2:
                    raise RuleError('At least two participants must remain.')
                self.begin_battle()
            return
        if action == 'vote':
            return self.vote(i,data.get('choice'))
        if action == 'leave' and self.stage in ('build','vote','complete') and self.mode == 'human':
            m['departed'] = True
            self.votes.pop(i,None)
            if len([x for x in self.members if not x['departed']]) < 2:
                self.stage = 'complete'
            elif self.stage == 'vote' and self.votes:
                voter,choice = next(iter(self.votes.items()))
                self.vote(voter,choice)
            return
        if action == 'retry' and self.stage == 'retry' and i == 0 and self.retry:
            self.retry -= 1
            if self.mode == 'solo':
                self.size = 2
                for rival in self.members[2:]:
                    rival['departed'] = True
            builds = [dict(name=x['name'],commander=x['commander'],package=x['package'],relic=x['relic'],**(dict(deck=x['deck']) | self.battle_progression(x))) for x in self.members if not x['departed']]
            frozen = copy.deepcopy(self.battle.encounter)
            self.battle = Battle(builds,self.battle_seed,(self.starting_offset+self.battle_number-1)%len(builds),frozen)
            self.results_applied = False
            self.stage = 'battle'
            self.last_decision = time.time()
            return
        if action == 'end_run' and self.stage == 'retry':
            self.stage = 'defeat'
            return
        if self.priority_control(m, action, data):
            return
        if action == 'reclaim':
            if self.mode == 'solo' and i != 0:
                raise RuleError('Cannot claim a campaign rival.')
            m['bot'] = False
            m['timeout_count'] = 0
            return
        if self.stage == 'battle':
            preferences(m)
            self.battle.auto_order = {str(x.get('seat', 0)):x.get('auto_order', True) for x in self.members}
            if action in ('cast', 'ability', 'consume', 'equip_gear'):
                data['hold_priority'] = m['hold_priority']
            self.battle.action(m['seat'],action,**data)
            if action in ('enter_combat', 'end_combat', 'end_turn'):
                self.after_phase_action(m, action)
            m['timeout_count'] = 0
            self.last_decision = time.time()
            self.apply_results()
            if self.tutorial:
                from .tutorial import after_action
                after_action(self,action,data)
            return
        raise RuleError('That action is unavailable on this screen.')

    def tick(self, now=None):
        self._tick(now)
        if self.tutorial:
            from .tutorial import sync
            sync(self)

    def _tick(self, now=None):
        now = time.time() if now is None else now
        delta = max(0,now-self.last_tick)
        self.last_tick = now
        if self.mode == 'solo' and self.members and now-self.members[0]['last_seen'] > 5:
            # A closed browser pauses solo play, including priority clocks.
            self.last_decision = now
            return
        if self.stage == 'battle':
            self.battle.elapsed += delta
        for m in self.members:
            if self.mode != 'solo' and not m['bot'] and not m['departed'] and now-m['last_seen'] > 90 and self.stage not in ('lobby','complete','victory','defeat','retry'):
                m['bot'] = True
                if self.battle:
                    self.battle.note(f"{m['name']} disconnected; AI temporarily controls the seat. Reclaim to resume.")
        # Limit one AI battle action per tick so humans can inspect each public event.
        for m in self.members:
            if not m['bot'] or m['departed']:
                continue
            i = m['id']
            if self.stage == 'commanders' and not m['commander']:
                self.choose_commander(i,m['offers'][0],0)
            if self.stage == 'draft' and self.mode == 'human' and i not in self.picks:
                choices = self.packs[i]
                index = max(range(len(choices)),key=lambda j:(legal(choices[j],self.colors(i)), CARD_MAP[choices[j]]['kind']=='creature'))
                self.draft_pick(i,index)
            if self.stage == 'build' and (self.mode == 'human' or i == 0) and not m['ready']:
                if m['reward_left']:
                    index = next(j for j,c in enumerate(m['reward']) if legal(c,self.colors(i)))
                    self.reward_pick(i,index)
                elif m['relic_options']:
                    m['relic'] = m['relic_options'][0]
                    m['relic_options'] = []
                else:
                    self.action(i,'ready')
            if self.stage == 'vote' and i not in self.votes:
                self.vote(i,'quit' if 'quit' in self.vote_options else self.vote_options[0])
        if self.stage != 'battle':
            return
        b = self.battle
        if b.finished:
            self.apply_results()
            return
        if b.phase == 'opening':
            for m in self.members:
                if m['bot'] and not m['departed']:
                    seat = m['seat']
                    p = b.players[seat]
                    if b.phase == 'opening' and (not p['kept'] or p.get('bottom_remaining',0)):
                        act = b.ai_action(seat)
                        b.action(seat,**act)
            return
        seat = b.priority
        m = next(m for m in self.members if not m['departed'] and m['seat'] == seat)
        signature = b.decision_key()
        if signature != self.time_signature:
            self.time_signature = signature
            self.last_decision = now
        self.apply_phase_stops(b)
        preferences(m)
        if (m['bot'] or m['auto']) and b.loop_step():
            self.apply_results()
            return
        if m['bot'] and now-self.ai_since >= .45:
            if self.tutorial:
                from .tutorial import ai_action
                move = ai_action(self,seat)
            else:
                move = b.ai_action(seat)
            b.action(seat,**move)
            self.ai_since = now
            self.apply_results()
            return
        if self.automation_tick(b, m, now):
            return
        if self.mode == 'solo' and not m['bot']:
            return
        timeout = 30 if b.stack or b.phase in ('attack_response','damage_response') else 60
        elapsed = now-self.last_decision
        if elapsed >= timeout:
            if m['time_bank'] > 0:
                extra = min(30,m['time_bank'])
                m['time_bank'] -= extra
                self.last_decision += extra
                return
            m['timeout_count'] += 1
            b.note(f"{m['name']} timed out ({m['timeout_count']}/3); AI takes over after three timeouts.")
            self.last_decision = now
            if m['timeout_count'] >= 3 or now-m['last_seen'] > 90:
                m['bot'] = True
            elif b.choice:
                b.action(seat,**b.ai_action(seat))
            elif b.phase == 'combat':
                mandatory = [c for c in b.players[seat]['board'] if c['goad'] and b.attack_ready(c)]
                if mandatory:
                    m['bot'] = True
                else:
                    b.action(seat,'attack',attacks=[])
            elif b.phase == 'blocks':
                b.action(seat,'block',blocks={})
            elif b.phase == 'grow':
                b.action(seat,'color',color=b.players[seat]['colors'][0])
            else:
                b.action(seat,'pass')
            self.apply_results()

    def view(self, i):
        self.ensure_map()
        if self.tutorial:
            from .tutorial import sync
            sync(self)
        m = self.members[i]
        self.item_defaults(m)
        public = []
        for x in self.members:
            public.append({k:copy.deepcopy(v) for k,v in x.items() if k in
                ('id','name','bot','commander','package','relic','ready','score','losses','departed','timeout_count','time_bank','seat')})
        mine = copy.deepcopy(m)
        mine.pop('last_seen',None)
        seat = -1 if m['departed'] else m.get('seat',0)
        out = dict(mode=self.mode,stage=self.stage,members=public,me=mine,size=self.size,target=self.target,host=self.host,
            cards=[upgraded_card(c['id'],m.get('card_upgrades',{}).get(c['id'],0)) for c in CARDS] if self.mode == 'solo' and i == 0 else CARDS,commanders=COMMANDERS,relics=RELICS,draft_round=self.draft_round+1,
            draft_pick=self.pick_number%15+1,pack=self.packs[i] if self.stage == 'draft' and self.mode == 'human' else [],
            picked=i in self.picks,currency=self.currency,retry=self.retry,encounter=self.encounter_info(),
            shop=getattr(self,'shop',[]),votes={str(k):v for k,v in self.votes.items()},vote_options=self.vote_options,
            vote_message=self.vote_message,battle_number=self.battle_number,
            reports=copy.deepcopy(self.reports[-4:]),feedback=self.feedback.get(f'{self.battle_number}:{i}',''),
            upcoming=[self.rival_info()] if self.mode == 'solo' else [],
            timer=max(0,round((30 if self.battle and (self.battle.stack or self.battle.phase in ('attack_response','damage_response')) else 60)-(time.time()-self.last_decision))))
        out['untimed'] = self.mode == 'solo'
        if self.stage == 'battle':
            out['priority_flow'] = self.priority_view(m)
        out['cards'] += [self.item_card(m, ref) for ref in m['owned'] if ref.startswith('gear:') and self.item_card(m, ref)]
        out['gems'] = copy.deepcopy(GEM_FAMILIES)
        out['consumable_catalog'] = copy.deepcopy(CONSUMABLES)
        out['socket_options'] = {x['uid']:[dict(gem=g, tier=t, preview=compose(dict(x, gems=dict(x.get('gems', {}), **{g:t})))) for g, top in m['gem_unlocks'].items() for t in range(top+1) if compatible(x['design'],g) and self.socket_fits(x,g,t)] for x in m['items'] if x['design'] in ITEM_MAP}
        if self.mode == 'solo' and not self.tutorial and m['commander'] and len(self.members) > 1:
            rival = dict(self.members[1], **self.rival_info())
            self.item_defaults(rival)
            loadout = self.curated_items(rival)
            out['upcoming_loadout'] = dict(relics=[equipment_view(x) for x in loadout['equipment']], pouch=[CONSUMABLE_MAP[x['design']] for x in loadout['pouch']])
        out['equipment_catalog'] = [equipment_view(dict(uid='',design=e['id'],tier=0)) for e in EQUIPMENT]
        out['inventory'] = [dict(equipment_view(item),next=equipment_view(dict(item,tier=item['tier']+1)) if item['tier'] < 2 else None) for item in m.get('items',[])]
        out['upgrade_previews'] = [upgrade_preview(design,m.get('card_upgrades',{}).get(design,0)) for design in sorted(set(m['owned'])) if design in CARD_MAP and not CARD_MAP[design].get('art_style')] if self.mode == 'solo' and i == 0 else []
        out['gear_shop'] = getattr(self,'gear_shop',[]) if self.mode == 'solo' else []
        out['tutorial'] = copy.deepcopy(self.tutorial)
        out['campaign_map'] = copy.deepcopy(self.campaign_map) if self.mode == 'solo' and i == 0 and not self.tutorial else None
        out['selected_node'] = self.selected_node
        out['difficulty'] = self.difficulty
        out['modifiers'] = MODIFIERS
        out['treasure_odds'] = TREASURE_ODDS
        out['treasures'] = [dict(t, items=[equipment_view(item) for item in t['items']]) for t in self.treasures] if self.mode == 'solo' and i == 0 else []
        out['basics'] = [BASICS[c] for c in self.colors(i)] if m['commander'] else []
        if self.tutorial:
            from .tutorial import lesson_view
            out['lesson'] = lesson_view(self)
        if self.battle:
            out['battle'] = self.battle.view(seat)
        return out

    def to_dict(self):
        data = {k:copy.deepcopy(v) for k,v in self.__dict__.items() if k not in ('rng','battle')}
        data['battle'] = self.battle.to_dict() if self.battle else None
        data['random_state'] = self.rng.getstate()
        return data

    @classmethod
    def from_dict(cls,data):
        s = cls.__new__(cls)
        s.__dict__.update({k:v for k,v in data.items() if k not in ('random_state','battle')})
        if s.stage == 'lobby':
            s.size = 2
            if s.mode == 'solo':
                s.members = s.members[:2]
        s.tutorial = getattr(s,'tutorial',None)
        for key, default in dict(difficulty='normal', modifier_nodes=2, route_seed=None, campaign_map=None, selected_node=None, treasures=[]).items():
            if not hasattr(s, key):
                setattr(s, key, copy.deepcopy(default))
        s.item_serial = getattr(s,'item_serial',0)
        for m in s.members:
            s.item_defaults(m)
            legacy = 'items' not in m
            m.setdefault('items',[])
            m.setdefault('equipped',[None]*SLOTS)
            m.setdefault('essence',0)
            m.setdefault('card_upgrades',{})
            if s.mode == 'solo' and m['id'] == 0:
                m['bot'] = False
                if legacy and m.get('relic') in EQUIPMENT_MAP:
                    s.add_item(m,m['relic'])
        s.picks = {int(k):v for k,v in s.picks.items()}
        s.votes = {int(k):v for k,v in s.votes.items()}
        s.battle = Battle.from_dict(data['battle']) if data.get('battle') else None
        s.rng = random.Random()
        def tuples(x):
            return tuple(tuples(v) for v in x) if isinstance(x,list) else x
        s.rng.setstate(tuples(data['random_state']))
        if s.mode == 'solo' and s.stage == 'draft' and s.members[0].get('commander'):
            m = s.members[0]
            choices = [c['id'] for c in CARDS if legal(c['id'],s.colors(0))]
            m['reward'] = [design if legal(design,s.colors(0)) else choices[j % len(choices)]
                           for j,design in enumerate(m['reward'])]
        s.last_decision = data.get('last_decision', time.time())
        s.last_tick = time.time()
        s.time_signature = data.get('time_signature')
        return s
