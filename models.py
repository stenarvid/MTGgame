import json
import random
import pygame
from pathlib import Path

COLOR_PIP_MAP = {
    'W': (245, 240, 210), 'U': (60, 160, 240), 'B': (80, 60, 95),
    'R': (240, 65, 80), 'G': (50, 180, 90), 'P': (245, 105, 190),
    'C': (170, 170, 185)
}

class Card:
    def __init__(self, name, card_type, color_code, mana_cost=1, attack=0, health=0, text=""):
        self.name = name
        self.card_type = card_type
        self.color_code = color_code
        self.mana_cost = mana_cost
        self.attack = attack
        self.max_health = health
        self.current_health = health
        self.text = text
        self.tapped = False
        self.sick = True
        self.token = False
        self.keywords = []
        self.upgraded = False
        self.temp_attack = self.temp_health = 0
        self.perpetual = {}
        self.plus_one_counters = 0
        self.pips = {color_code: 1} if mana_cost and card_type != 'Land' and color_code in 'WUBRGP' else {}
        self.width, self.height = 110, 150
        self.rect = pygame.Rect(0, 0, self.width, self.height)

    @classmethod
    def from_dict(cls, data):
        card = cls(
            name=data['name'],
            card_type=data['type'],
            color_code=data['color'],
            mana_cost=data.get('cost', 1),
            attack=data.get('atk', 0),
            health=data.get('hp', 0),
            text=data.get('text', '')
        )
        card.pips = data.get('pips', card.pips).copy()
        card.keywords = list(data.get('keywords', []))
        card.flashback_cost = data.get('flashback_cost')
        return card

    @property
    def is_creature(self):
        return self.max_health > 0 and self.card_type != "Commander"

    def fresh(self):
        card = Card(self.name, self.card_type, self.color_code, self.mana_cost,
                    self.attack - self.temp_attack, self.max_health - self.temp_health, self.text)
        card.keywords = list(getattr(self, 'keywords', []))
        card.upgraded = self.upgraded
        card.pips = self.pips.copy()
        card.flashback_cost = getattr(self, 'flashback_cost', None)
        card.perpetual = dict(getattr(self, 'perpetual', {}))
        card.plus_one_counters = getattr(self, 'plus_one_counters', 0)
        return card

    def upgrade(self):
        if self.upgraded or self.card_type == 'Land':
            return False
        self.upgraded = True
        if self.is_creature:
            self.attack += 1
            self.max_health += 1
            self.current_health += 1
        self.text += ' [Upgrade: +1/+1.]' if self.is_creature else ' [Upgrade: +1 to numerical effects; counters also draw 1.]'
        return True

    def mana_label(self, total=None):
        total = self.mana_cost if total is None else total
        generic = max(0, total - sum(self.pips.values()))
        return (str(generic) if generic else '') + ''.join(c * n for c, n in self.pips.items()) or '0'


class Commander(Card):
    def __init__(self, cmd_id, name, colors, archetypes, passive, active, unlocked=False):
        super().__init__(name, "Commander", colors[0], 1, 3, 5, text=f"Pass: {passive} | Act: {active}")
        self.cmd_id = cmd_id
        self.colors = colors
        self.archetypes = archetypes
        self.passive = passive
        self.active = active
        self.unlocked = unlocked


def generate_procedural_commander(cmd_meta, passives_pool, actives_pool, forced_passive=None, forced_active=None):
    prefix = random.choice(cmd_meta['prefixes'])
    suffix = random.choice(cmd_meta['suffixes'])
    name = f"{prefix} {suffix}"
    
    pass_obj = forced_passive if forced_passive else random.choice(passives_pool)
    act_obj = forced_active if forced_active else random.choice(actives_pool)
    
    colors = [pass_obj["color"], act_obj["color"]]
    archetypes = [pass_obj["archetype"], act_obj["archetype"]]
    
    commander = Commander(
        cmd_id=f"cmd_{random.randint(1000, 9999)}",
        name=name,
        colors=colors,
        archetypes=archetypes,
        passive=pass_obj["desc"],
        active=act_obj["desc"],
        unlocked=False
    )
    commander.passive_name = pass_obj['name']
    commander.active_name = act_obj['name']
    return commander


class MapNode:
    def __init__(self, x, y, row, node_type):
        self.x = x
        self.y = y
        self.row = row
        self.node_type = node_type
        self.connections = []
        self.visited = False
        self.available = False
        self.rect = pygame.Rect(x - 18, y - 18, 36, 36)


def generate_spire_map():
    rows, cols = 6, 4
    grid = []
    for r in range(rows):
        row_nodes = []
        y_pos = 100 + (r * 95)
        for c in range(1 if r == rows - 1 else cols):
            x_pos = 280 + (c * 200) + random.randint(-20, 20)
            if r == 0:
                ntype = "Combat"
            elif r == rows - 1:
                ntype = "Boss"
                x_pos = 580
            else:
                ntype = random.choice(["Combat", "Combat", "Elite", "Rest", "Merchant", "Treasure"])
            row_nodes.append(MapNode(x_pos, y_pos, r, ntype))
        grid.append(row_nodes)
        
    for r in range(rows - 1):
        for node in grid[r]:
            next_row = grid[r+1]
            sorted_next = sorted(next_row, key=lambda n: abs(n.x - node.x))
            node.connections.append(sorted_next[0])
            if len(sorted_next) > 1 and random.random() < 0.6:
                node.connections.append(sorted_next[1])
                
    for node in grid[0]:
        node.available = True
    return grid


def load_game_data():
    data_dir = Path(__file__).resolve().parent / "data"
    with (data_dir / "cards.json").open(encoding="utf-8") as f:
        card_data = json.load(f)
    with (data_dir / "relics.json").open(encoding="utf-8") as f:
        relics_data = json.load(f)
    with (data_dir / "commanders.json").open(encoding="utf-8") as f:
        cmd_data = json.load(f)
    with (data_dir / "commander_passives.json").open(encoding="utf-8") as f:
        passives_data = json.load(f)
    with (data_dir / "commander_actives.json").open(encoding="utf-8") as f:
        actives_data = json.load(f)
        
    commander_pool = {
        "prefixes": cmd_data["prefixes"],
        "suffixes": cmd_data["suffixes"],
        "passives": passives_data,
        "actives": actives_data
    }
    
    card_pool = {
        "relics": relics_data,
        "archetype_boosters": card_data["archetype_boosters"],
        "starter_cards": card_data["starter_cards"]
    }
    card_pool['cards'] = [dict(card, archetype=archetype)
                          for archetype, cards in card_data['archetype_boosters'].items()
                          for card in cards] + list(card_data['starter_cards'].values()) + card_data.get('expansion_cards', [])

    initial_commanders = [generate_procedural_commander(cmd_data, passives_data, actives_data) for _ in range(4)]
    for cmd in initial_commanders:
        cmd.unlocked = True
        
    return initial_commanders, commander_pool, card_pool


def complete_node(grid, node):
    if not node.available or node.visited:
        return False
    for row in grid:
        for other in row:
            other.available = False
    node.visited = True
    for connection in node.connections:
        connection.available = True
    return True


def color_starters(pool, color, archetype):
    """Stable previews; all archetype cards plus enough basics for a playable deck."""
    # Every commander choice contributes the same package: two signature cards,
    # two copies of its basic starter, and four lands. Additional archetype cards
    # remain in the reward/shop pool instead of inflating the opening deck.
    cards = [Card.from_dict(c) for c in pool['archetype_boosters'].get(archetype, [])[:2]]
    if not cards:
        cards = [Card.from_dict(c) for c in pool['cards']
                 if c['color'] == color and c.get('archetype')][:2]
    cards += [Card.from_dict(pool['starter_cards'][color]) for _ in range(2)]
    cards += [Card(f'{color} Mana Conduit', 'Land', color, 0,
                   text=f'Permanent. Tap for {color} mana. One land play perlaun turn.') for _ in range(4)]
    return cards
