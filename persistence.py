"""Versioned JSON saves preserving shared card, stack-target and map-node references.

No pickle or executable payloads. Writes replace the old save only after a complete
temporary file has been flushed. Transient Pygame objects are reconstructed.
"""
import json
import os
import random
from pathlib import Path
import pygame

from engine import Run, Battle, Side, StackItem
from models import Card, Commander, MapNode

TYPES = {cls.__name__: cls for cls in (Run, Battle, Side, StackItem, Card, Commander, MapNode)}
STATES = {'MAP', 'BATTLE', 'MERCHANT', 'REST', 'TREASURE', 'REWARD', 'WIN', 'LOSS'}
PHASES = {'AFTER_PLAYER_COMBAT', 'AFTER_ENEMY_COMBAT', 'ATTACK_TARGET', 'DECLARE_BLOCKS', 'MULLIGAN', 'MAIN', 'MAIN2', 'RESPONSE', 'ENEMY_MAIN', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE', 'FINISHED'}
REQUIRED = {
    'Card': 'name card_type color_code mana_cost attack max_health current_health text tapped sick token upgraded temp_attack temp_health pips width height',
    'Commander': 'name cmd_id colors archetypes passive active passive_name active_name width height',
    'MapNode': 'x y row node_type connections visited available',
    'Run': 'commander deck hp max_hp gold relics stats grid node shop choices won rewards reward_pending service_used',
    'Side': 'name hp max_hp deck hand board lands discard mana colored_mana armor land_played creatures_played fatigue',
    'StackItem': 'card side target',
    'Battle': 'run relics passive active player enemy theme elite boss boss_enraged enemy_turn_number enemy_damage_bonus_used intent phase return_phase stack enemy_queue blocked combat_side mulligan_used events event_serial turn active_used attackers assignments result settled log',
}


def encode_graph(root):
    nodes, seen = [], {}
    def encode(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {'map': [[encode(k), encode(v)] for k, v in value.items()]}
        if isinstance(value, (list, tuple, set)):
            return {type(value).__name__: [encode(v) for v in value]}
        name = type(value).__name__
        if name not in TYPES:
            raise ValueError(f'Unsupported save object: {name}')
        key = id(value)
        if key not in seen:
            seen[key] = len(nodes)
            node = {'type': name, 'attributes': {}}
            nodes.append(node)
            node['attributes'] = {k: encode(v) for k, v in vars(value).items()
                                  if k != 'rect' and not (name == 'Run' and k == 'pool')}
        return {'ref': seen[key]}
    root_data = encode(root)
    return dict(version=1, root=root_data, objects=nodes)


def decode_graph(data, pool):
    if data.get('version') != 1 or not isinstance(data.get('objects'), list) or len(data['objects']) > 20000:
        raise ValueError('Unsupported or malformed run save')
    objects = [TYPES[node['type']].__new__(TYPES[node['type']]) for node in data['objects']]
    for node in data['objects']:
        if not set(REQUIRED[node['type']].split()).issubset(node['attributes']):
            raise ValueError('Incomplete ' + node['type'] + ' in run save')
    def decode(value):
        if not isinstance(value, dict):
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            raise ValueError('Malformed save value')
        if len(value) != 1:
            raise ValueError('Malformed save tag')
        tag, payload = next(iter(value.items()))
        if tag == 'ref':
            if not isinstance(payload, int) or not 0 <= payload < len(objects):
                raise ValueError('Invalid object reference')
            return objects[payload]
        if tag == 'map':
            return {decode(k): decode(v) for k, v in payload}
        if tag in ('list', 'tuple', 'set'):
            return {'list': list, 'tuple': tuple, 'set': set}[tag](decode(v) for v in payload)
        raise ValueError('Unknown save tag')
    for obj, node in zip(objects, data['objects']):
        for key, value in node['attributes'].items():
            if key.startswith('_') or hasattr(type(obj), key):
                raise ValueError('Invalid attribute in save')
            setattr(obj, key, decode(value))
        if isinstance(obj, Card):
            obj.rect = pygame.Rect(0, 0, obj.width, obj.height)
            if not hasattr(obj, 'plus_one_counters'):
                perpetual = getattr(obj, 'perpetual', {})
                obj.plus_one_counters = (sum(perpetual.get(key, 0) for key in
                                             ('chorus', 'insight', 'death_curse', 'hospitality',
                                              'spellflame', 'landgrowth', 'mourning'))
                                         + perpetual.get('mosaic', 0) + perpetual.get('growth_bonus', 0))
            definition = next((c for c in pool['cards'] if c['name'] == obj.name), None)
            if definition and not isinstance(obj, Commander):
                obj.flashback_cost = definition.get('flashback_cost')
                obj.text = definition.get('text', '')
                if obj.upgraded:
                    obj.text += ' [Upgrade: +1/+1.]' if obj.is_creature else ' [Upgrade: +1 to numerical effects; counters also draw 1.]'
                obj.keywords = sorted(set(getattr(obj, 'keywords', [])) | set(definition.get('keywords', [])))
            if not isinstance(obj.name, str) or not isinstance(obj.mana_cost, int) or obj.mana_cost < 0:
                raise ValueError('Invalid card properties')
        elif isinstance(obj, MapNode):
            obj.rect = pygame.Rect(obj.x - 18, obj.y - 18, 36, 36)
        elif isinstance(obj, Run):
            obj.pool = pool
    root = decode(data['root'])
    run, battle = root['run'], root['battle']
    if not isinstance(run, Run) or root['state'] not in STATES:
        raise ValueError('Invalid run state')
    if not isinstance(run.commander, Commander) or not run.grid or not isinstance(run.deck, list):
        raise ValueError('Invalid run data')
    if any(not isinstance(c, Card) for c in run.deck) or run.hp < 0 or run.max_hp <= 0:
        raise ValueError('Invalid cards or health')
    if battle is not None:
        if not isinstance(battle, Battle) or battle.run is not run or battle.phase not in PHASES:
            raise ValueError('Invalid battle data')
        for side in (battle.player, battle.enemy):
            if not isinstance(side, Side):
                raise ValueError('Invalid combatant')
            if not hasattr(side, 'exile'):
                side.exile = []
            for zone in ('deck', 'hand', 'board', 'lands', 'discard', 'exile'):
                if any(not isinstance(c, Card) for c in getattr(side, zone)):
                    raise ValueError('Invalid combat zone')
        if any(not isinstance(item, StackItem) for item in battle.stack):
            raise ValueError('Invalid spell stack')
        battle.init_commander()
    if root['state'] == 'BATTLE' and battle is None:
        raise ValueError('Missing battle')
    random.Random().setstate(root['rng'])  # Validate without changing the live RNG.
    return root


class RunStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).resolve().parent / 'run-save.json'
        self.error = ''

    def exists(self):
        return self.path.is_file()

    def save(self, payload):
        try:
            content = json.dumps(encode_graph(payload), ensure_ascii=False, allow_nan=False)
            temp = self.path.with_suffix('.tmp')
            with temp.open('w', encoding='utf-8') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(self.path)
            self.error = ''
            return True
        except (OSError, ValueError, TypeError) as error:
            self.error = f'Could not save run: {error}'
            return False

    def load(self, pool):
        try:
            if self.path.stat().st_size > 8_000_000:
                raise ValueError('Save file is too large')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            root = decode_graph(data, pool)
            self.error = ''
            return root
        except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError) as error:
            self.error = f'Could not resume run: {error}. Your save has not been changed.'
            return None

    def clear(self):
        try:
            self.path.unlink(missing_ok=True)
            return True
        except OSError as error:
            self.error = f'Could not remove completed run save: {error}'
            return False
