"""Render review screenshots without opening a desktop window.

Run from the project root: python tests/capture_screens.py
The sample board is deliberately populated to show both sides' card frames.
"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import random
import tempfile
import sys
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import Game
from models import Card


def main():
    random.seed(10)
    temp = tempfile.TemporaryDirectory()
    game = Game(save_path=Path(temp.name) / 'run.json', progress_path=Path(temp.name) / 'unlocks.json')
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)

    def save(name):
        game.draw()
        pygame.image.save(game.screen, str(output / f'{name}.png'))

    save('menu')
    game.start_builder()
    save('builder')
    game.choose(game.commanders['passives'][0])
    game.choose(game.commanders['actives'][3])
    save('map')
    game.enter_node(game.run.grid[0][0])
    b = game.battle
    save('mulligan')
    b.keep_hand()
    for side, names in [(b.player, ['Legion Vanguard', 'Phase Shifter', 'Grove Sprite']),
                        (b.enemy, ['Crypt Ghoul', 'Spellweaver Pyromancer'])]:
        for name in names:
            card = Card.from_dict(next(c for c in game.pool['cards'] if c['name'] == name))
            b.summon(side, card)
    b.player.board[0].sick = False
    game.chosen.add(b.player.board[0])
    save('battle')
    game.card_painter.preview(game.screen, b.player.board[0], 670, 300)
    pygame.image.save(game.screen, str(output / 'card-preview.png'))
    game.state = 'DECK'
    save('deck')
    game.state = 'BATTLE'
    game.chosen.clear()
    game.animations = False
    b.phase = 'BLOCK'
    b.combat_side = b.enemy
    b.attackers = list(b.enemy.board)
    for creature in b.attackers:
        creature.tapped = True
    b.assign_blocker(b.attackers[0], b.player.board[0])
    b.assign_blocker(b.attackers[0], b.player.board[1])
    save('combat-preview')
    b.player.colored_mana['R'] = 2
    bolt = Card.from_dict(next(c for c in game.pool['cards'] if c['name'] == 'Overcharge Bolt'))
    b.player.hand.append(bolt)
    b.play(bolt, b.enemy.board[0])
    save('response')
    game.state = 'STACK'
    save('stack')
    game.state = 'LOG'
    save('combat-log')
    game.state = 'BATTLE_HELP'
    save('help')
    game.state = 'BATTLE'
    b.enemy.hp = 0
    b.check_result()
    game.end_battle()
    save('rewards')
    game.take_reward(0)
    node = next(n for row in game.run.grid for n in row if n.available)
    node.node_type = 'Merchant'
    game.enter_node(node)
    game.run.gold = 100
    save('merchant')
    game.open_service('upgrade')
    game.select_service_card(next(c for c in game.run.deck if c.is_creature))
    save('upgrade')
    game.set_window_scale(0.75)
    game.present()
    pygame.image.save(game.window, str(output / 'scaled-window.png'))
    pygame.quit()
    temp.cleanup()
    print(f'Saved screenshots in {output}')


if __name__ == '__main__':
    main()
