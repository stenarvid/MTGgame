"""Public campaign routes, encounter challenges, and earned treasure odds."""
import random

MODIFIERS = {
    'head_start': dict(name='Enemy extra mana', text='Enemy starts with 1 extra mana gem.', essence=1),
    'weak_army': dict(name='Weaker creatures', text='Your creatures have 1 less attack.', essence=1),
    'silent_entry': dict(name='No arrival effects', text="Your cards' arrival effects do not trigger.", essence=2),
    'creatures_only': dict(name='Creatures only', text='Only cast creatures. Abilities still work.', essence=2),
}
TERRAINS = ('temple', 'field', 'town')
TREASURE_ODDS = dict(ordinary_chance=.25, boss_chance=1, item_counts=[1, 2, 3],
                     currency=[1, 2, 3], tiers=[75, 20, 5])


def bonus(modifiers):
    return min(4, sum(MODIFIERS[key]['essence'] for key in set(modifiers)))


def make_map(seed, act, difficulty='normal', marked=2, depth=0):
    rng = random.Random(f'{seed}:{act}')
    nodes = []
    for column in range(4):
        for lane in range(1 if column == 3 else 3):
            nodes.append(dict(id=f'{act}:{column}:{lane}', column=column, lane=lane,
                              kind='Boss' if column == 3 else 'Elite' if column == 2 else 'Encounter',
                              terrain=rng.choice(TERRAINS), modifiers=[], completed=False))
    candidates = [n for n in nodes if depth <= n['column'] < 3]
    count = rng.randint(1, 2) if difficulty == 'normal' else rng.randint(3, 4) if difficulty == 'hard' else marked
    for node in rng.sample(candidates, min(count, len(candidates))):
        node['modifiers'] = rng.sample(list(MODIFIERS), rng.randint(1, 3))
    for node in nodes:
        node['next'] = [n['id'] for n in nodes if n['column'] == node['column']+1
                        and (n['column'] == 3 or abs(n['lane']-node['lane']) <= 1)]
        node['bonus'] = bonus(node['modifiers'])
        node['essence'] = (4 if node['kind'] == 'Boss' else 2) + node['bonus']
    return dict(act=act, nodes=nodes, reachable=[n['id'] for n in nodes if n['column'] == depth])
