"""Render the fanned hand, hover zoom, drag, and stack using a sample battle."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_expansion import ExpansionRules
from main import Game
from engine import StackItem
import pygame

with tempfile.TemporaryDirectory() as directory:
    game = Game(Path(directory) / 'run.json', Path(directory) / 'progress.json')
    fixture = ExpansionRules(); fixture.setUp()
    game.run = fixture.run; game.battle = fixture.b; game.state = 'BATTLE'; game.animations = False
    battle = game.battle
    battle.player.hand = [fixture.card(n) for n in ['Astra, Echo Conduit', 'Magma Bolt', 'Radiant Aegis',
                          'Null Sigil', 'Dawn Musterer', 'Rootbound Sage', 'Aether Warp']]
    battle.player.board = [fixture.card('Legion Vanguard'), fixture.card('Thorn Sentinel')]
    battle.enemy.board = [fixture.card('Crypt Ghoul'), fixture.card('Ember Duelist')]
    first = StackItem(fixture.card('Overcharge Bolt'), battle.enemy, battle.player)
    battle.stack = [first, StackItem(fixture.card('Null Sigil'), battle.player, first)]
    battle.phase = 'RESPONSE'; game.mouse_pos = lambda: (0, 0)
    output = Path(__file__).resolve().parents[1] / 'artifacts'
    output.mkdir(exist_ok=True)
    game.draw(); pygame.image.save(game.screen, output / 'arena-hand-stack.png')
    position = game.hand_hits[3][1].center; game.mouse_pos = lambda: position
    game.draw(); pygame.image.save(game.screen, output / 'arena-hover.png')
    game.drag_card = game.pending = battle.player.hand[1]; game.drag_pos = (500, 440)
    game.draw(); pygame.image.save(game.screen, output / 'arena-drag.png')
    game.drag_card = game.pending = None
    battle.stack = []; battle.phase = 'MAIN'; game.mouse_pos = lambda: (0, 0)
    battle.player.board = []; battle.tokens(battle.player, 30)
    for card in battle.player.board:
        card.sick = False
    for card in battle.player.board[:3]:
        card.attack += 1; card.max_health += 1; card.current_health += 1
    game.chosen = {battle.player.board[3]}
    game.draw(); pygame.image.save(game.screen, output / 'arena-token-piles.png')
    pygame.quit()
