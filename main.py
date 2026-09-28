"""Pygame screens and input for the commander roguelike."""
import random
import pygame

from engine import Battle, Progress, Run, UNLOCKS
from models import Card, color_starters, generate_procedural_commander, load_game_data
from rendering import draw_node_icon, draw_wrapped_text
from art import Artwork, CardPainter, PALETTES, draw_mana_glyph, fitted, font as art_font
from persistence import RunStore
from ui_panels import QolPanels
from card_interaction import CardInteraction
from battlefield_piles import BattlefieldPiles
from arena_ui import ArenaUI

BG = (20, 18, 28)
TEXT = (232, 232, 240)
GOLD = (245, 206, 105)
MUTED = (159, 155, 178)
GREEN = (95, 218, 151)


class Game(ArenaUI, BattlefieldPiles, CardInteraction, QolPanels):
    def __init__(self, save_path=None, progress_path=None):
        pygame.init()
        art_font.cache_clear()
        self.windowed_size = (1280, 900)
        self.animations = True
        self.animation_speed = 'normal'
        self.inspect_key = pygame.K_LALT
        self.store = RunStore(save_path)
        self.load_preferences()
        if pygame.display.get_driver() != 'dummy':
            desktop = pygame.display.get_desktop_sizes()[0]
            self.windowed_size = (min(self.windowed_size[0], max(640, desktop[0] - 50)),
                                  min(self.windowed_size[1], max(450, desktop[1] - 90)))
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.screen = pygame.Surface((1280, 900)).convert()
        self.fullscreen = False
        self.effects = []
        self.last_event = 0
        self.resume_state = 'MENU'
        pygame.display.set_caption('Commander Spire')
        self.clock = pygame.time.Clock()
        self.large = pygame.font.SysFont('Georgia', 32)
        self.font = pygame.font.SysFont('Segoe UI', 18)
        self.small = pygame.font.SysFont('Segoe UI', 14)
        self.artwork = Artwork()
        self.card_painter = CardPainter(self.artwork)
        _, self.commanders, self.pool = load_game_data()
        self.progress = Progress(progress_path)
        self.state = 'MENU'
        self.running = True
        self.run = self.battle = None
        self.buttons = []
        self.hover = None
        self.message = self.progress.error
        self.page = self.hand_page = 0
        self.pending = None
        self.blockers = set()
        self.chosen = set()
        self.legend = False
        self.morph_choice = None
        self.priority_signature = None
        self.priority_since = 0
        self.recent_unlocks = []
        self.assignment_undo = []
        self.turn_banner_key = None
        self.turn_banner_started = 0
        self.deck_filter = 'All'
        self.deck_sort = 'Mana'
        self.deck_search = ''
        self.search_active = False
        self.tutorial_page = 0
        self.run_bosses = 4
        self.builder_mode = 'active'
        self.init_card_interaction()

    def text(self, text, x, y, color=TEXT, font=None):
        self.screen.blit((font or self.font).render(str(text), True, color), (x, y))

    def wrap(self, text, x, y, width, color=TEXT):
        return draw_wrapped_text(self.screen, text, self.small, color, x, y, width)

    def button(self, rect, label, action, enabled=True, selected=False, readable=False):
        rect = pygame.Rect(rect)
        over = rect.collidepoint(self.mouse_pos())
        shadow = rect.move(0, 3)
        pygame.draw.rect(self.screen, (6, 9, 14), shadow, border_radius=8)
        if selected:
            fill, edge = (29, 73, 66), GREEN
        elif over and enabled:
            fill, edge = (61, 55, 40), (255, 226, 139)
        elif enabled:
            fill, edge = (25, 31, 38), (184, 157, 99)
        else:
            fill, edge = (22, 24, 31), (67, 67, 78)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, edge, rect, 2 if selected or (over and enabled) else 1, border_radius=8)
        pygame.draw.line(self.screen, tuple(min(255, c + 24) for c in fill),
                         (rect.x + 9, rect.y + 2), (rect.right - 9, rect.y + 2), 1)
        label_image = fitted(label, rect.w - 24, 16, TEXT if enabled or readable else MUTED)
        self.screen.blit(label_image, label_image.get_rect(center=rect.center))
        if enabled:
            self.buttons.append((rect, action))

    def card(self, card, rect, action=None, selected=False, subtitle=None, enabled=True):
        rect = pygame.Rect(rect)
        card.rect = rect
        combat = self.state == 'BATTLE'
        side = self.battle.enemy if combat and card in self.battle.enemy.board else self.battle.player if combat else None
        cost = self.battle.cost(side, card) if combat else card.mana_cost
        playable = (combat and enabled and card in self.battle.player.hand
                    and ((card.card_type == 'Land' and not side.land_played)
                         or (card.card_type != 'Land' and self.battle.can_pay(side, card))))
        self.card_painter.draw(self.screen, card, rect, selected=selected, subtitle=subtitle or '',
                               cost=cost, combat=combat and card in side.board, playable=playable)
        if rect.collidepoint(self.mouse_pos()):
            self.hover = card
        if action and enabled:
            self.buttons.append((rect, action))

    def title(self, text, subtitle=''):
        self.text(text, 30, 24, GOLD, self.large)
        if subtitle:
            self.text(subtitle, 30, 64, MUTED)

    def set_state(self, state):
        self.state = state
        self.page = 0

    def start_builder(self):
        self.state = 'RUN_SETUP'
        self.message = ''

    def begin_builder(self):
        choices = self.commanders['passives'] + [u for u in UNLOCKS if u['name'] in self.progress.unlocked]
        self.choices = random.sample(choices, min(4, len(choices)))
        self.state = 'PASSIVE'
        self.message = ''
        self.passive = None
        self.recent_unlocks = []

    def reroll_builder(self):
        passive_pool = self.commanders['passives'] + [u for u in UNLOCKS if u['name'] in self.progress.unlocked]
        if self.state == 'ACTIVE':
            pool = self.commanders['actives']
        elif self.state == 'SECOND_PASSIVE':
            pool = [choice for choice in passive_pool if choice['name'] != self.passive['name']]
        else:
            pool = passive_pool
        self.choices = random.sample(pool, min(4, len(pool)))
        self.message = 'Choices rerolled.'

    def choose(self, choice):
        if self.state == 'PASSIVE':
            self.passive = choice
            if self.builder_mode == 'two_passives':
                passive_pool = self.commanders['passives'] + [u for u in UNLOCKS if u['name'] in self.progress.unlocked]
                pool = [candidate for candidate in passive_pool
                        if candidate['name'] != choice['name']]
                self.choices = random.sample(pool, min(4, len(pool)))
                self.state = 'SECOND_PASSIVE'
            else:
                self.choices = random.sample(self.commanders['actives'], 4)
                self.state = 'ACTIVE'
        else:
            commander = generate_procedural_commander(
                self.commanders, [], [], self.passive,
                choice if self.state == 'ACTIVE' else None,
                choice if self.state == 'SECOND_PASSIVE' else None)
            self.run = Run(commander, self.pool)
            self.run.total_areas = self.run_bosses
            self.battle = None
            self.state = 'MAP'
            self.message = 'Choose a green node to begin your ascent.'
            self.pending = None
            self.blockers.clear()
            self.chosen.clear()
            self.save_run()

    def enter_node(self, node):
        if not self.run.enter(node):
            self.message = ('Finish choosing your battle reward first.' if self.run.reward_pending else
                            'Finish your current encounter first.' if self.run.node is not None else
                            'Choose a green location connected to your completed path.')
            return
        self.message = ''
        if node.node_type in ('Combat', 'Elite', 'Boss'):
            self.battle = Battle(self.run)
            self.state = 'BATTLE'
            self.hand_page = 0
            self.pending = None
            self.blockers.clear()
            self.chosen.clear()
            self.last_event = 0
            self.effects = []
            self.turn_banner_key = None
        else:
            self.state = node.node_type.upper()

    def leave_shop(self):
        self.run.finish()
        self.state = 'MAP'

    def rest(self):
        healed = self.run.rest()
        self.message = f'Restored {healed} HP.'
        self.state = 'MAP'

    def take_relic(self, index):
        name = self.run.choices[index]['name'] if self.run.choices else '25 gold'
        self.run.take_relic(index)
        self.message = f'Gained {name}.'
        self.state = 'MAP'

    def end_battle(self):
        if self.battle.result == 'VICTORY':
            gold = self.battle.collect_reward()
            self.message = f'Battle won! Gained {gold} gold.'
            self.state = 'REWARD'
        else:
            self.state = 'LOSS'

    def play_card(self, card):
        if self.battle.phase == 'MULLIGAN':
            if card in self.chosen:
                self.chosen.remove(card)
            else:
                self.chosen.add(card)
            return
        if self.battle.result:
            return
        if not self.can_drag(card):
            self.message = self.cannot_play_reason(card)
            return
        if self.battle.cast_targets(card):
            self.pending = card
            self.message = f'{card.name}: click a highlighted target. Right-click to cancel.'

        else:
            self.battle.play(card)
            self.pending = None

    def active(self):
        if (self.battle.result or self.battle.phase not in ('MAIN', 'MAIN2')
                or self.battle.active_used or self.battle.stack
                or self.battle.commander_zone != 'BOARD'):
            self.message = 'Commander abilities use sorcery timing: your main phase, an empty stack, and the commander on the battlefield.'
            return
        if not self.battle.targets(self.battle.active):
            self.battle.use_active()
        elif self.battle.active == 'Adaptive Bloom':
            self.pending = 'ACTIVE'
            self.morph_choice = None
            self.message = 'Choose a form under your commander, then choose a friendly creature.'
        else:
            self.pending = 'ACTIVE'
            self.message = f'{self.battle.active}: click a highlighted target. Right-click to cancel.'

    def valid_targets(self):
        if self.battle.phase == 'ATTACK_TARGET':
            return self.battle.copy_targets(self.battle.attack_choices[0])
        if getattr(self.battle, 'pending_entry', None):
            return self.battle.entry_targets(self.battle.player, self.battle.pending_entry)
        if self.pending is None:
            return []
        if self.pending == 'ACTIVE' and self.battle.active == 'Adaptive Bloom' and not self.morph_choice:
            return []
        return self.battle.targets(self.battle.active if self.pending == 'ACTIVE' else self.pending.name)

    def target(self, target):
        if self.battle.phase == 'ATTACK_TARGET':
            self.battle.choose_attack_copy(target)
            return
        if target not in self.valid_targets():
            return
        if getattr(self.battle, 'pending_entry', None):
            success = self.battle.resolve_pending_entry(target)
        else:
            success = (self.battle.use_active(target, self.morph_choice) if self.pending == 'ACTIVE'
                       else self.battle.play(self.pending, target))
        if success:
            self.pending = None
            self.morph_choice = None
            self.message = ''

    def choose_morph(self, choice):
        self.morph_choice = choice
        self.message = f'{choice.title()} form selected. Choose a highlighted friendly creature.'

    def click_creature(self, creature, friendly):
        battle = self.battle
        if self.pending or getattr(battle, 'pending_entry', None) or battle.phase == 'ATTACK_TARGET':
            self.target(creature)
        elif battle.phase == 'BLOCK':
            if friendly and not creature.tapped:
                if creature in self.blockers:
                    self.blockers.remove(creature)
                else:
                    self.blockers.add(creature)
            elif not friendly and self.blockers:
                self.assignment_undo.append({a: list(group) for a, group in battle.assignments.items()})
                for blocker in tuple(self.blockers):
                    battle.assign_blocker(creature, blocker)
                self.blockers.clear()
        elif battle.phase == 'ATTACK_RESPONSE' and not friendly:
            battle.reorder_blocker(creature)
        elif battle.phase == 'COMBAT' and friendly and not creature.sick and not creature.tapped:
            if creature in self.chosen:
                self.chosen.remove(creature)
            else:
                self.chosen.add(creature)

    def advance_combat(self):
        if getattr(self.battle, 'pending_entry', None):
            self.message = 'Choose the highlighted ETB target first.'
            return
        if self.battle.phase == 'ATTACK_TARGET':
            self.battle.choose_attack_copy(None)
        elif self.battle.phase == 'UPKEEP':
            self.battle.finish_upkeep()
        elif self.battle.phase == 'MAIN':
            self.battle.begin_combat()
        elif self.battle.phase == 'COMBAT':
            self.battle.attack(self.chosen)
        elif self.battle.phase == 'MAIN2':
            self.battle.begin_end_step()
        elif self.battle.phase == 'END':
            self.battle.end_turn()
        elif self.battle.phase == 'DISCARD':
            if not self.battle.discard_to_hand_limit(self.chosen):
                self.message = f'Choose exactly {self.battle.required_discards()} card(s) from your hand.'
                return
        elif self.battle.phase == 'RESPONSE':
            self.battle.pass_priority()
        elif self.battle.phase == 'ATTACK_RESPONSE':
            self.battle.finish_attack()
        elif self.battle.phase == 'BLOCK' and self.blockers:
            self.message = f'{len(self.blockers)} selected blocker(s) are not assigned. Click an attacker or deselect them.'
            return
        elif self.battle.phase in ('BLOCK', 'DEFEND_RESPONSE'):
            self.battle.finish_blocks()
        elif self.battle.phase == 'MULLIGAN':
            self.keep_hand()
        self.chosen.clear()
        self.pending = None
        self.blockers.clear()
        self.message = ''

    def change_hand_page(self, delta):
        self.hand_page += delta

    def menu(self):
        self.text('A N   A S T R A L   D E C K B U I L D E R', 65, 95, GOLD, self.small)
        self.text('Commander', 60, 135, TEXT, art_font(58, serif=True))
        self.text('Spire', 60, 200, GOLD, art_font(72, serif=True))
        self.text('Choose your magic. Challenge the spire.', 65, 300, TEXT)
        for y, label, callback in [
            (370, 'Create commander & play', self.request_new_run),
            (435, 'Achievements', lambda: self.set_state('ACHIEVEMENTS')),
            (500, 'Relic collection', lambda: self.set_state('COLLECTION')),
            (565, 'How to play', lambda: self.set_state('HELP')),
            (630, 'Quit', self.quit),
        ]:
            self.button((65, y, 360, 50), label, callback)
        self.button((445, 370, 300, 50), 'Replay tutorial', self.open_tutorial)
        self.button((65, 710, 360, 50), 'Resume saved run', self.resume_run, enabled=self.store.exists())
        self.button((65, 775, 360, 50), 'Display settings', self.open_settings)
        for i, name in enumerate(['Phase Shifter', 'Legion Vanguard', 'Spellweaver Pyromancer']):
            card = Card.from_dict(next(c for c in self.pool['cards'] if c['name'] == name))
            self.card(card, (550 + i * 218, 465 - (35 if i == 1 else 0), 200, 305))
        self.text('Persistent lands  /  Tactical duels  /  Build-defining relics', 570, 805, TEXT, self.small)

    def quit(self):
        if self.save_run():
            self.running = False

    def builder(self):
        heading = ('1. Choose a passive' if self.state == 'PASSIVE' else
                   '2. Choose a second passive' if self.state == 'SECOND_PASSIVE' else
                   '2. Choose an active ability')
        self.title(heading,
                   'Each choice adds the cards below. Abilities determine your commander colors and archetypes.')
        for i, choice in enumerate(self.choices):
            x = 25 + i * 313
            pygame.draw.rect(self.screen, (35, 29, 48), (x, 115, 290, 695), border_radius=10)
            self.artwork.paint(self.screen, choice['color'], (x + 10, 125, 270, 175))
            self.text(choice['name'], x + 15, 320, GOLD)
            pip_center = (x + 28, 363)
            pip_color = PALETTES.get(choice['color'], (190, 180, 160))
            pygame.draw.circle(self.screen, (12, 16, 22), pip_center, 13)
            pygame.draw.circle(self.screen, pip_color, pip_center, 11)
            draw_mana_glyph(self.screen, choice['color'], pip_center, 9)
            self.text(choice['archetype'], x + 48, 352, MUTED)
            self.wrap(choice['desc'], x + 15, 392, 260)
            self.text('Starting cards (hover for details)', x + 15, 465, GREEN, self.small)
            for j, card in enumerate(color_starters(self.pool, choice['color'], choice['archetype'])):
                y = 498 + j * 27
                self.text(card.name, x + 15, y, TEXT, self.small)
                if pygame.Rect(x + 10, y - 2, 270, 26).collidepoint(self.mouse_pos()):
                    self.hover = card
            self.button((x + 15, 745, 260, 48), 'Choose', lambda c=choice: self.choose(c))
        self.button((25, 830, 170, 42), 'Back to menu', lambda: self.set_state('MENU'))
        self.button((215, 830, 190, 42), 'Reroll choices', self.reroll_builder)
        self.button((1040, 830, 215, 42), 'Exit fullscreen [F11]' if self.fullscreen else 'Fullscreen [F11]',
                    self.toggle_fullscreen)

    def run_setup_screen(self):
        self.title('Choose your Spire length', 'Each area ends with a boss. Defeating one adds a basic land of every commander color to your deck.')
        self.text('BOSSES', 565, 205, GOLD, art_font(22, serif=True))
        self.text(str(self.run_bosses), 602, 260, TEXT, art_font(72, serif=True))
        self.button((430, 275, 100, 62), '−', lambda: setattr(self, 'run_bosses', max(1, self.run_bosses - 1)))
        self.button((750, 275, 100, 62), '+', lambda: setattr(self, 'run_bosses', min(12, self.run_bosses + 1)))
        estimates = {1:'Short run',2:'Quick campaign',3:'Standard campaign',4:'Long campaign'}
        self.text(estimates.get(self.run_bosses, 'Endurance campaign'), 555, 365, MUTED)
        self.wrap('Boss reward: +1 permanent land for each of your commander colors. Longer runs grow both your deck and mana base.',
                  430, 420, 420, TEXT)
        mode_label = 'Passive + Active' if self.builder_mode == 'active' else 'Two Passives'
        self.button((430, 510, 420, 48), f'Commander powers: {mode_label}',
                    lambda: setattr(self, 'builder_mode', 'two_passives' if self.builder_mode == 'active' else 'active'),
                    selected=self.builder_mode == 'two_passives')
        self.button((430, 580, 420, 58), f'Climb past {self.run_bosses} boss' + ('es' if self.run_bosses != 1 else ''), self.begin_builder)
        self.button((430, 660, 420, 48), 'Back to menu', lambda: self.set_state('MENU'))

    def map_screen(self):
        run = self.run
        self.title(run.commander.name,
                   f'AREA {getattr(run, "area", 1)} / {getattr(run, "total_areas", 4)}   |   '
                   f'HP {run.hp}/{run.max_hp}   |   Gold {run.gold}   |   Deck {len(run.deck)}   |   Relics {len(run.relics)}')
        self.button((910, 20, 160, 42), 'View deck', lambda: self.set_state('DECK'))
        self.button((1090, 20, 160, 42), 'Map legend', self.toggle_legend)
        for row in run.grid:
            for node in row:
                for connection in node.connections:
                    pygame.draw.line(self.screen, (78, 67, 97), (node.x, node.y + 25),
                                     (connection.x, connection.y + 25), 3)
        for row in run.grid:
            for node in row:
                x, y = node.x, node.y + 25
                # The icon and its label form one target, in logical screen coordinates.
                label = self.small.render(node.node_type, True,
                                          GREEN if node.available else GOLD if node.visited else MUTED)
                label_rect = label.get_rect(midtop=(x, y + 24))
                node.rect = pygame.Rect(x - 25, y - 25, 50, 50).union(label_rect).inflate(12, 8)
                if node.available and node.rect.collidepoint(self.mouse_pos()):
                    pygame.draw.rect(self.screen, (45, 65, 65), node.rect, border_radius=8)
                    pygame.draw.rect(self.screen, GREEN, node.rect, 1, border_radius=8)
                color = GREEN if node.available else GOLD if node.visited else (68, 61, 81)
                pygame.draw.circle(self.screen, color, (x, y), 21)
                draw_node_icon(self.screen, node.node_type, x, y)
                self.screen.blit(label, label_rect)
                self.buttons.append((node.rect, lambda n=node: self.enter_node(n)))
        self.button((30, 625, 175, 42), 'Run details', lambda: self.set_state('DETAILS'))
        self.button((225, 625, 180, 42), 'Save / pause', self.pause)
        self.button((1040, 625, 210, 42), 'Abandon run', lambda: self.set_state('ABANDON'))
        self.text('Choose a green circle or its label. Start at the top; follow the paths downward.',
                  30, 695, GREEN, self.small)
        if self.legend:
            pygame.draw.rect(self.screen, (35, 29, 48), (980, 88, 290, 290), border_radius=8)
            for i, label in enumerate(['Green: available', 'Gold: completed', 'Combat: earn gold',
                                       'Elite: harder duel, more gold', 'Rest: heal 10 HP',
                                       'Merchant: buy cards', 'Treasure: choose a power-up', 'Boss: advance / final boss wins']):
                self.text(label, 995, 102 + i * 32, TEXT, self.small)

    def toggle_legend(self):
        self.legend = not self.legend

    def open_tutorial(self):
        self.tutorial_page = 0
        self.state = 'TUTORIAL'

    def tutorial_screen(self):
        pages = [
            ('1. Play cards and lands', 'Cards with a bright cyan border are legal now. Lands show PLAY LAND when your land play is available. Hold your inspection key over any card for its full text and modifiers.'),
            ('2. Choose targets', 'After choosing a targeted spell or enter ability, every legal target receives a numbered pulsing ring. Click one of those targets. Right-click or Escape cancels targeting.'),
            ('3. Attack and block', 'Click ready creatures, then Attack. While blocking, select several creatures and click one attacker. B selects every blocker and Ctrl+Z restores the previous assignment.'),
            ('4. Commander and stack', 'Cast your commander from the command zone. On the battlefield, its gold A badge activates its sorcery-speed ability. Instant spells can respond while the stack is open.'),
            ('5. Build your run', 'Boosters add three themed cards. Treasure nodes grant relics. Merchants allow repeated upgrades and removals while you can afford them. Rest-site smithing remains one choice for that node.'),
        ]
        title, body = pages[self.tutorial_page]
        self.title('Replayable tutorial', f'Page {self.tutorial_page + 1} of {len(pages)}')
        pygame.draw.rect(self.screen, (25, 29, 42), (180, 150, 920, 470), border_radius=16)
        pygame.draw.rect(self.screen, GOLD, (180, 150, 920, 470), 2, border_radius=16)
        self.text(title, 225, 205, GOLD, self.large)
        self.wrap(body, 225, 285, 830, TEXT)
        self.button((180, 680, 220, 50), 'Previous', lambda: self.change_tutorial(-1), enabled=self.tutorial_page > 0)
        self.button((430, 680, 220, 50), 'Next', lambda: self.change_tutorial(1), enabled=self.tutorial_page + 1 < len(pages))
        self.button((880, 680, 220, 50), 'Back to menu', lambda: self.set_state('MENU'))

    def change_tutorial(self, delta):
        self.tutorial_page = max(0, min(4, self.tutorial_page + delta))

    def battle_screen(self):
        b = self.battle
        if b.phase == 'MULLIGAN':
            self.mulligan_screen()
            return
        self.draw_battle_chrome()
        self.text(f'TURN {b.turn}', 32, 22, GOLD, self.small)
        self.screen.blit(fitted(b.phase.replace('_', ' ').title(), 240, 22, TEXT), (32, 43))
        for x, label, callback in [(914, 'Log [L]', lambda: self.set_state('LOG')),
                                    (1025, 'Help', lambda: self.set_state('BATTLE_HELP')),
                                    (1136, 'Pause [P]', self.pause)]:
            self.button((x, 18, 102, 34), label, callback)
        self.draw_land_row(False)
        self.draw_land_row(True)
        self.draw_battlefield()
        self.draw_hero(False)
        self.draw_hero(True)
        self.draw_response_stack()
        self.draw_phase_track()
        self.draw_turn_indicator()
        self.draw_enemy_intent()
        if b.result:
            self.button((1035, 582, 215, 58), f'{b.result.title()} - continue', self.end_battle)
        else:
            response_window = b.phase in ('RESPONSE', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE')
            can_respond = b.player_has_instant_action() if response_window else True
            choosing_entry = bool(getattr(b, 'pending_entry', None))
            label = {'UPKEEP': 'Resolving upkeep...', 'ATTACK_TARGET': 'Skip copy', 'MAIN': 'Enter Combat',
                     'COMBAT': f'Attack with {len(self.chosen)}' if self.chosen else 'No attackers',
                     'MAIN2': 'End Turn', 'END': 'Ending turn...',
                     'DISCARD': f'Discard selected ({len(self.chosen)}/{b.required_discards()})',
                     'RESPONSE': 'Pass priority' if can_respond else 'Resolving...', 'BLOCK': 'Confirm blocks',
                     'ATTACK_RESPONSE': 'Resolve combat', 'DEFEND_RESPONSE': 'Resolve combat'}.get(b.phase, 'Continue')
            label = 'Choose ETB target' if choosing_entry else label
            discard_ready = b.phase != 'DISCARD' or len(self.chosen) == b.required_discards()
            self.button((1035, 582, 215, 58), label + (' [Space]' if can_respond and not choosing_entry else ''), self.advance_combat,
                        enabled=can_respond and not choosing_entry and discard_ready)
        self.button((25, 657, 132, 32), 'Draw pile [D]', lambda: self.inspect('deck'))
        self.button((166, 657, 132, 32), 'Discard [G]', lambda: self.inspect('discard'))
        self.button((307, 657, 130, 32), 'Clear selection', self.clear_selection)
        if b.phase == 'DISCARD':
            self.button((446, 657, 145, 32), 'Suggest discards', self.suggest_discards)
        if b.phase == 'BLOCK':
            self.button((446, 657, 130, 32), 'Clear blocks', self.clear_blocks,
                        enabled=bool(b.assignments))
        sprite = next((c for c in b.player.board if c.name == 'Grove Sprite' and not c.sick and not c.tapped), None)
        if sprite:
            amount = 1 + getattr(sprite, 'upgrade_level', int(sprite.upgraded))
            self.button((805, 657, 185, 32), f'Tap Sprite: +{amount} G', lambda: b.tap_sprite(sprite))
        self.draw_mana_status()
        preview = b.combat_preview()
        if preview:
            summary = f'COMBAT PREVIEW   You take {preview["player_damage"]} / Enemy takes {preview["enemy_damage"]}'
            self.screen.blit(fitted(summary, 930, 14, TEXT), (45, 379))
        elif b.phase == 'COMBAT':
            self.text(f'{len(self.chosen)} attackers selected. Click your ready creatures, then Attack.', 45, 379, TEXT, self.small)
        instruction = {'UPKEEP': 'Upkeep effects have triggered. Continue to your first main phase.',
                       'MAIN': 'First main: play lands, creatures, and sorceries. Continue to enter combat.',
                       'COMBAT': 'Combat: choose attackers. You may cast instants before declaring attacks.',
                       'MAIN2': 'Second main: play lands, creatures, and sorceries, then enter your end step.',
                       'END': 'End step: until-end-of-turn effects have expired. End your turn when ready.',
                       'DISCARD': f'Cleanup: select exactly {b.required_discards()} card(s) from your hand, then confirm.',
                       'BLOCK': 'Select one or more of your blockers, then click an enemy attacker. Confirm when finished.',
                       'ATTACK_RESPONSE': 'Enemy blockers are assigned. Cast an instant or resolve combat.',
                       'RESPONSE': 'Respond with an instant, or pass priority to resolve the stack.',
                       'ATTACK_TARGET': 'Choose a highlighted creature to copy, or skip.'}.get(b.phase, 'Space advances the phase. Right-click cancels targeting.')
        if getattr(b, 'pending_entry', None):
            instruction = f'{b.pending_entry.name} entered. Click a highlighted enemy to finish its ETB effect.'
        message = fitted(self.message or instruction, 930, 14, GREEN)
        self.screen.blit(message, message.get_rect(center=(640, 709)))
        self.draw_hand()
        self.draw_alternate_hand()
        self.draw_commander()
        self.draw_targeting_overlay()
        self.render_feedback()

    def clear_selection(self):
        self.pending = None
        self.blockers.clear()
        self.morph_choice = None
        self.chosen.clear()
        self.message = ''

    def suggest_discards(self):
        if not self.battle or self.battle.phase != 'DISCARD':
            return
        required = self.battle.required_discards()
        ranked = sorted(self.battle.player.hand,
                        key=lambda card: (card.mana_cost, card.is_creature, card.name), reverse=True)
        self.chosen = set(ranked[:required])
        self.message = 'Suggested the highest-cost cards. Change the selection if you prefer.'

    def clear_blocks(self):
        if self.battle and self.battle.phase == 'BLOCK':
            self.assignment_undo.append({a: list(group) for a, group in self.battle.assignments.items()})
            self.battle.assignments.clear()
            self.blockers.clear()
            self.message = 'All block assignments cleared.'

    def undo_blocks(self):
        if self.battle and self.battle.phase == 'BLOCK' and self.assignment_undo:
            self.battle.assignments = self.assignment_undo.pop()
            self.blockers.clear()
            self.message = 'Restored the previous block assignments.'

    def shop_screen(self):
        self.title('Merchant', f'Gold: {self.run.gold}. Purchases join your deck for future battles.')
        for i, item in enumerate(self.run.shop):
            card = Card.from_dict(item['card'])
            x = 30 + i * 248
            self.card(card, (x, 140, 225, 345))
            owned = sum(existing.name == card.name for existing in self.run.deck)
            self.text(f'Owned: {owned}  |  Cost {card.mana_cost}', x, 490, MUTED, self.small)
            self.button((x, 510, 225, 48), 'Sold' if item['sold'] else f"Buy: {item['price']} gold",
                        lambda index=i: self.run.buy(index), enabled=not item['sold'] and self.run.gold >= item['price'])
        self.button((30, 800, 230, 48), 'Leave merchant', self.leave_shop)
        self.button((30, 625, 340, 50), 'Remove a card: 40 gold', lambda: self.open_service('remove'),
                    enabled=self.run.gold >= 40)
        self.button((395, 625, 340, 50), 'Upgrade a card: 30 gold', lambda: self.open_service('upgrade'),
                    enabled=self.run.gold >= 30)
        self.text('Use services as often as you can afford them. Choose a card and review it before confirming.', 30, 700, MUTED)

    def treasure_screen(self):
        self.title('Treasure: choose one power-up', 'Two offers favor your build. The wildcard can open a new direction.')
        rarity_colors = {'Common': (114, 188, 205), 'Elite': (188, 116, 232), 'Boss': (245, 184, 74)}
        for i, relic in enumerate(self.run.choices):
            x = 35 + i * 415
            panel = pygame.Rect(x, 155, 385, 280)
            edge = rarity_colors.get(relic['rarity'], GOLD)
            pygame.draw.rect(self.screen, (8, 11, 17), panel.move(0, 5), border_radius=14)
            pygame.draw.rect(self.screen, (35, 31, 48), panel, border_radius=14)
            pygame.draw.rect(self.screen, edge, panel, 2, border_radius=14)
            pygame.draw.circle(self.screen, (13, 17, 25), (x + 48, 225), 28)
            pygame.draw.circle(self.screen, edge, (x + 48, 225), 24, 3)
            pygame.draw.polygon(self.screen, edge, [(x + 48, 207), (x + 61, 225),
                                                     (x + 48, 243), (x + 35, 225)])
            self.text(relic['name'], x + 20, 180, GOLD)
            self.text(relic['rarity'].upper(), x + 85, 218, edge, self.small)
            self.wrap(relic['desc'], x + 20, 260, 345)
            identities = set(self.run.commander.archetypes) | set(self.run.commander.colors)
            matches = [tag for tag in relic.get('tags', []) if tag in identities]
            relevant = ('BUILD SYNERGY  •  ' + ' / '.join(matches) if matches else 'WILDCARD RELIC')
            self.text(relevant, x + 20, 325, GREEN if matches else MUTED, self.small)
            self.button((x + 20, 355, 345, 50), 'Take relic', lambda index=i: self.take_relic(index))
        if not self.run.choices:
            self.button((35, 190, 380, 50), 'All relics owned: take 25 gold', lambda: self.take_relic(0))

    def deck_screen(self):
        creatures = sum(c.is_creature for c in self.run.deck)
        lands = sum(c.card_type == 'Land' for c in self.run.deck)
        self.title('Your deck', f'{len(self.run.deck)} cards  |  {creatures} creatures  |  '
                   f'{len(self.run.deck) - creatures - lands} spells  |  {lands} lands.')
        cards = self.filtered_cards(self.run.deck)
        self.button((30, 78, 180, 30), f'Filter: {self.deck_filter}', self.cycle_deck_filter)
        self.button((220, 78, 180, 30), f'Sort: {self.deck_sort}', self.cycle_deck_sort)
        self.button((410, 78, 390, 30), 'Search: ' + (self.deck_search or 'click, then type'), self.start_search,
                    selected=self.search_active)
        self.text(f'Showing {len(cards)}. Hold {self.inspect_key_name()} over a card to inspect.', 820, 83, MUTED, self.small)
        start = self.page * 12
        for i, card in enumerate(cards[start:start + 12]):
            rect = pygame.Rect(30 + (i % 6) * 207, 115 + (i // 6) * 335, 190, 290)
            self.card(card, rect)
            copies = sum(other.name == card.name for other in self.run.deck)
            if copies > 1:
                self.text(f'x{copies}', rect.right - 31, rect.y + 7, GOLD, self.small)
        self.button((30, 805, 170, 45), 'Back to map', lambda: self.set_state('MAP'))
        self.button((230, 805, 150, 45), 'Previous', lambda: self.change_page(-1), enabled=self.page > 0)
        self.button((400, 805, 150, 45), 'Next', lambda: self.change_page(1), enabled=start + 12 < len(cards))

    def filtered_cards(self, source):
        cards = list(source)
        value = self.deck_filter
        if value in 'WUBRGP' and len(value) == 1:
            cards = [c for c in cards if value in c.color_code]
        elif value == 'Creatures':
            cards = [c for c in cards if c.is_creature]
        elif value == 'Spells':
            cards = [c for c in cards if 'Spell' in c.card_type]
        elif value == 'Lands':
            cards = [c for c in cards if c.card_type == 'Land']
        needle = self.deck_search.casefold().strip()
        if needle:
            cards = [c for c in cards if needle in (c.name + ' ' + c.text).casefold()]
        keys = {'Mana': lambda c: (c.mana_cost, c.name), 'Name': lambda c: c.name,
                'Color': lambda c: (c.color_code, c.mana_cost, c.name),
                'Type': lambda c: (c.card_type, c.mana_cost, c.name)}
        return sorted(cards, key=keys[self.deck_sort])

    def cycle_deck_filter(self):
        values = ('All', 'Creatures', 'Spells', 'Lands', 'W', 'U', 'B', 'R', 'G', 'P')
        self.deck_filter = values[(values.index(self.deck_filter) + 1) % len(values)]
        self.page = 0

    def cycle_deck_sort(self):
        values = ('Mana', 'Name', 'Color', 'Type')
        self.deck_sort = values[(values.index(self.deck_sort) + 1) % len(values)]
        self.page = 0

    def start_search(self):
        self.search_active = True
        self.page = 0

    def change_page(self, delta):
        self.page += delta

    def info_screen(self):
        state = self.state
        if state == 'ACHIEVEMENTS':
            self.title('Achievements', 'Progress is earned through actual combat. Unlocks are saved between sessions.')
            for i, unlock in enumerate(UNLOCKS[self.page * 4:self.page * 4 + 4]):
                y = 145 + i * 125
                status = 'UNLOCKED' if unlock['name'] in self.progress.unlocked else 'LOCKED'
                self.text(f"{status} - {unlock['name']}", 40, y, GREEN if status == 'UNLOCKED' else GOLD)
                self.text(unlock['desc'], 40, y + 33)
                count = self.run.stats.get(unlock['stat'], 0) if self.run else 0
                self.text(f"In one run: {unlock['goal']} {unlock['stat'].replace('_', ' ')} | Current run: {count}/{unlock['goal']}", 40, y + 64, MUTED)
            self.button((260, 745, 180, 45), 'Previous', lambda: self.change_page(-1), enabled=self.page > 0)
            self.button((460, 745, 180, 45), 'Next', lambda: self.change_page(1), enabled=(self.page + 1) * 4 < len(UNLOCKS))
            self.text(f'Unlocked {len(self.progress.unlocked.intersection(u["name"] for u in UNLOCKS))}/{len(UNLOCKS)}', 700, 756, GOLD)
        elif state in ('COLLECTION', 'DETAILS'):
            self.title('Relic collection' if state == 'COLLECTION' else 'Your commander & relics')
            y = 115
            if state == 'DETAILS':
                cmd = self.run.commander
                passive_names = getattr(cmd, 'passive_names', [cmd.passive_name])
                self.screen.blit(fitted('PASSIVES: ' + ' + '.join(passive_names), 1160, 16, GREEN), (40, y))
                if cmd.active_name:
                    self.screen.blit(fitted(f'{cmd.active_name}: {cmd.active} (once per battle)', 1160, 16, GOLD), (40, y + 38))
                else:
                    self.text('No active ability — both passive effects are always active.', 40, y + 38, MUTED)
                y += 95
            relics = self.pool['relics'] if state == 'COLLECTION' else self.run.relics
            for relic in relics:
                self.text(f"{relic['name']}: {relic['desc']}", 40, y)
                y += 43
            if not relics:
                self.text('Visit a Treasure node to choose your first power-up.', 40, y, MUTED)
            if state == 'DETAILS':
                deck = self.run.deck
                creatures = sum(c.is_creature for c in deck)
                lands = sum(c.card_type == 'Land' for c in deck)
                spells = len(deck) - creatures - lands
                colors = {color: sum(color in c.color_code for c in deck) for color in 'WUBRGP'}
                curve = {cost: sum(c.mana_cost == cost and c.card_type != 'Land' for c in deck) for cost in range(6)}
                curve['6+'] = sum(c.mana_cost >= 6 and c.card_type != 'Land' for c in deck)
                y = max(y + 20, 360)
                self.text(f'DECK SUMMARY  {len(deck)} cards | {creatures} creatures | {spells} spells | {lands} lands', 40, y, GOLD)
                self.text('Colors: ' + '   '.join(f'{c}:{n}' for c, n in colors.items() if n), 40, y + 35, TEXT)
                self.text('Mana curve', 40, y + 78, GREEN)
                maximum = max(1, max(curve.values()))
                for i, (cost, count) in enumerate(curve.items()):
                    x = 45 + i * 105
                    height = int(120 * count / maximum)
                    pygame.draw.rect(self.screen, (71, 111, 142), (x, y + 225 - height, 70, height), border_radius=5)
                    self.text(str(count), x + 27, y + 201 - height, TEXT, self.small)
                    self.text(str(cost), x + 27, y + 232, GOLD, self.small)
        else:
            self.title('How to play', 'An MTG-inspired roguelike with a small, explicit ruleset.')
            lines = [
                'Opening: two lands in play, five cards in hand. Replace selected cards once for free, then keep and draw for turn.',
                'Mana: W white, U blue, B black, R red, G green. A cost of 1R needs one red plus one mana of any color.',
                'Lands: play one per turn. They persist and untap each turn. Payment uses matching colors automatically.',
                'Turn: upkeep, first main, combat, second main, end step. Damage and until-end effects clear at end step.',
                'Stack: spells wait for responses. Cast an instant or pass priority; the newest spell resolves first.',
                f'Drag a hand card onto the field or its target. Hold {self.inspect_key_name()} while hovering to inspect; right-click cancels.',
                'Attack: select ready creatures, then declare. New creatures cannot attack unless they have Haste.',
                'Block: select any number of untapped creatures, then click one attacker. B selects all; Ctrl+Z undoes an assignment.',
                'Damage order: during your attack, click an enemy blocker to move it last. Block labels show the order.',
                'Preview: hero damage and lethal creatures are shown before damage, excluding later responses and death triggers.',
                'Trample deals excess damage through blockers. Other blocked attackers stay blocked if their blockers disappear.',
                'Damage is simultaneous. Survivors clear damage and temporary buffs at turn end. Tokens vanish when they leave.',
                'Unplayed cards stay in hand. Empty decks reshuffle discards; an empty deck AND discard causes increasing fatigue.',
                'Rewards: choose one of three cards or skip. Treasure offers relics; shops offer purchases and one paid service.',
                'Rest: heal 10 HP OR upgrade a card. Creature upgrades give +1/+1; spell upgrades improve numerical effects.',
                'Save: autosave after decisions, F5 manual save, P pause. Resume from the menu, including mid-combat decisions.',
                'Shortcuts: Enter/Space advance, 1-9 cards, A attack all, Shift+A excludes commander, B blockers, Ctrl+Z undo.',
                'Resize to scale the board. Mouse wheel browses pages. Escape cancels a selection or pauses; right-click clears it.',
                'Keywords: Haste attacks immediately; Guard reduces blocking damage by 1; Vigilance attacks without tapping.',
                'New card triggers use the stack. Legacy card triggers and commander actives resolve immediately. No creature limit; matching tokens share piles.',
            ]
            for i, line in enumerate(lines):
                self.text(line, 35, 112 + i * 33, TEXT, self.small)
        destination = 'BATTLE' if state == 'BATTLE_HELP' else 'MAP' if state == 'DETAILS' else 'MENU'
        self.button((35, 810, 190, 45), 'Back', lambda: self.set_state(destination))

    def check_unlocks(self):
        if not self.run:
            return
        new = self.progress.check(self.run.stats)
        for name in new:
            if name not in self.recent_unlocks:
                self.recent_unlocks.append(name)
        if new:
            self.message = 'Unlocked: ' + ', '.join(new)
            if self.progress.error:
                self.message += '. ' + self.progress.error

    def unlock_results(self):
        """Derive results from this run, retaining unlocks earned before a resume."""
        self.check_unlocks()
        rows = []
        for unlock in UNLOCKS:
            count = self.run.stats.get(unlock['stat'], 0)
            status = ('NEW UNLOCK' if unlock['name'] in self.recent_unlocks else
                      'ALREADY UNLOCKED' if unlock['name'] in self.progress.unlocked else 'LOCKED')
            rows.append(dict(unlock, count=count, status=status,
                             remaining=max(0, unlock['goal'] - count)))
        order = {'NEW UNLOCK': 0, 'LOCKED': 1, 'ALREADY UNLOCKED': 2}
        return sorted(rows, key=lambda row: order[row['status']])

    def run_results(self):
        rows = self.unlock_results()
        earned = sum(row['status'] == 'NEW UNLOCK' for row in rows)
        self.title('Spire conquered!' if self.state == 'WIN' else 'Your run has ended',
                   f'{earned} new unlock(s) this run. Earned passives join future commander choices.')
        self.text('Unlock goals are per run. Partial progress resets next run; earned unlocks are permanent.',
                  30, 105, MUTED, self.small)
        self.text(f"Cards drawn: {self.run.stats.get('cards_drawn', 0)}   |   Kills: {self.run.stats.get('kills', 0)}   |   "
                  f"Spell damage: {self.run.stats.get('spell_damage', 0)}", 30, 135, TEXT)
        for i, row in enumerate(rows):
            x, y = 30 + (i % 2) * 625, 185 + (i // 2) * 146
            color = GREEN if row['status'] == 'NEW UNLOCK' else MUTED if row['status'] == 'ALREADY UNLOCKED' else GOLD
            rect = pygame.Rect(x, y, 595, 132)
            pygame.draw.rect(self.screen, (28, 26, 42), rect, border_radius=9)
            pygame.draw.rect(self.screen, color, rect, 2 if row['status'] == 'NEW UNLOCK' else 1, border_radius=9)
            self.text(row['name'], x + 14, y + 10, color)
            self.text(row['status'], x + 407, y + 13, color, self.small)
            self.screen.blit(fitted(row['desc'], 565, 14, TEXT), (x + 14, y + 40))
            metric = row['stat'].replace('_', ' ')
            self.text(f"This run: {row['count']} / {row['goal']} {metric}", x + 14, y + 68, TEXT, self.small)
            hint = f"{row['remaining']} short of goal" if row['status'] == 'LOCKED' else 'Goal reached!' if row['status'] == 'NEW UNLOCK' else 'Available in commander builder'
            self.screen.blit(fitted(hint, 235, 13, color), (x + 340, y + 70))
            bar = pygame.Rect(x + 14, y + 101, 565, 12)
            pygame.draw.rect(self.screen, (54, 50, 68), bar, border_radius=5)
            width = int(bar.w * min(1, row['count'] / row['goal']))
            if width:
                pygame.draw.rect(self.screen, color, (bar.x, bar.y, width, bar.h), border_radius=5)
        self.button((30, 800, 285, 48), 'New commander', self.start_builder)
        self.button((335, 800, 230, 48), 'Main menu', lambda: self.set_state('MENU'))
        if self.progress.error:
            self.screen.blit(fitted(self.progress.error, 1200, 14, (255, 140, 140)), (30, 856))

    def draw(self):
        self.artwork.background(self.screen, self.state)
        self.buttons = []
        self.hover = None
        state = self.state
        if state == 'MENU':
            self.menu()
        elif state == 'RUN_SETUP':
            self.run_setup_screen()
        elif state in ('PASSIVE', 'ACTIVE', 'SECOND_PASSIVE'):
            self.builder()
        elif state == 'MAP':
            self.map_screen()
        elif state == 'BATTLE':
            self.battle_screen()
        elif state == 'MERCHANT':
            self.shop_screen()
        elif state == 'TREASURE':
            self.treasure_screen()
        elif state == 'REST':
            self.title('Rest site', f'HP {self.run.hp}/{self.run.max_hp}. Recover before the next duel.')
            self.button((420, 280, 440, 60), 'Rest: heal up to 10 HP', self.rest)
            self.button((420, 380, 440, 60), 'Smith: upgrade a card instead', lambda: self.open_service('upgrade'))
        elif state == 'REWARD':
            self.reward_screen()
        elif state in ('SERVICE', 'SERVICE_CONFIRM'):
            self.service_screen()
        elif state == 'PAUSE':
            self.pause_screen()
        elif state == 'SETTINGS':
            self.settings_screen()
        elif state == 'TUTORIAL':
            self.tutorial_screen()
        elif state == 'INSPECT':
            self.inspect_screen()
        elif state == 'LOG':
            self.log_screen()
        elif state == 'STACK':
            self.stack_screen()
        elif state == 'NEW_RUN_CONFIRM':
            self.title('Replace the saved run?', 'Starting a new run will replace your existing run. Achievements are kept.')
            self.button((400, 250, 480, 55), 'Resume existing run', self.resume_run)
            self.button((400, 335, 480, 55), 'Replace and create commander', self.replace_run)
            self.button((400, 420, 480, 55), 'Cancel', lambda: self.set_state('MENU'))
        elif state == 'DECK':
            self.deck_screen()
        elif state in ('WIN', 'LOSS'):
            self.run_results()
        elif state == 'ABANDON':
            self.title('Abandon this run?', 'Achievements remain unlocked. This run cannot be resumed after leaving.')
            self.button((40, 220, 250, 55), 'Continue run', lambda: self.set_state('MAP'))
            self.button((40, 300, 250, 55), 'Abandon to menu', self.abandon)
        else:
            self.info_screen()
        if self.message and state not in ('BATTLE', 'WIN', 'LOSS'):
            self.text(self.message, 30, 876, GREEN, self.small)
        inspect_down = pygame.key.get_pressed()[self.inspect_key]
        if self.hover and not self.drag_card and inspect_down:
            cost = (self.battle.cost(self.battle.player, self.hover)
                    if self.state == 'BATTLE' and (self.hover in self.battle.player.hand
                    or self.hover is self.battle.commander or self.battle.alternate_zone(self.hover)) else None)
            preview_rect = pygame.Rect(360, 145, 300, 445)
            self.card_painter.draw(self.screen, self.hover, preview_rect, cost=cost)
            self.draw_card_modifiers(self.hover, preview_rect)
        elif self.hover and not self.drag_card:
            mx, my = self.mouse_pos()
            hint = fitted(f'Hold {self.inspect_key_name()} to inspect', 205, 13, TEXT)
            box = hint.get_rect(topleft=(min(mx + 16, 1060), min(my + 18, 865))).inflate(12, 8)
            pygame.draw.rect(self.screen, (15, 19, 27), box, border_radius=6)
            pygame.draw.rect(self.screen, GOLD, box, 1, border_radius=6)
            self.screen.blit(hint, hint.get_rect(center=box.center))
        if self.state == 'BATTLE':
            self.draw_drag()
        if self.store.error:
            self.screen.blit(fitted(self.store.error, 1220, 14, (255, 140, 140)), (30, 875))

    def handle_event(self, event):
        if not self.card_input(event):
            self._handle_event(event)
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.KEYDOWN):
            self.save_run()

    def _handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
        elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.windowed_size = (max(640, event.w), max(450, event.h))
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.save_preferences()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif self.search_active and self.state in ('DECK', 'INSPECT'):
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.search_active = False
                elif event.key == pygame.K_BACKSPACE:
                    self.deck_search = self.deck_search[:-1]
                    self.page = 0
                elif event.unicode and event.unicode.isprintable() and len(self.deck_search) < 40:
                    self.deck_search += event.unicode
                    self.page = 0
            elif event.key == pygame.K_F5:
                self.save_run(True)
            elif event.key == pygame.K_ESCAPE:
                if self.state == 'TUTORIAL':
                    self.state = 'MENU'
                elif self.state == 'BATTLE':
                    if self.pending or self.chosen or self.blockers:
                        self.clear_selection()
                    else:
                        self.pause()
                elif self.state in ('BATTLE_HELP', 'INSPECT', 'LOG', 'STACK'):
                    self.state = 'BATTLE'
                elif self.state == 'PAUSE':
                    self.return_from_panel()
                elif self.state in ('DECK', 'DETAILS', 'ABANDON'):
                    self.state = 'MAP'
                elif self.state in ('SERVICE', 'SERVICE_CONFIRM'):
                    self.state = 'MERCHANT' if self.run.node.node_type == 'Merchant' else 'REST'
            elif self.state == 'BATTLE':
                mods = pygame.key.get_mods()
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.end_battle() if self.battle.result else self.advance_combat()
                elif event.key == pygame.K_a and self.battle.phase == 'COMBAT':
                    ready = {c for c in self.battle.player.board if not c.sick and not c.tapped}
                    if mods & pygame.KMOD_SHIFT:
                        ready.discard(self.battle.commander)
                    self.chosen = set() if self.chosen == ready else ready
                elif event.key == pygame.K_b and self.battle.phase == 'BLOCK':
                    ready = {c for c in self.battle.player.board if not c.tapped
                             and all(c not in group for group in self.battle.assignments.values())}
                    self.blockers = set() if self.blockers == ready else ready
                elif event.key == pygame.K_z and mods & pygame.KMOD_CTRL:
                    self.undo_blocks()
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    index = self.hand_page * 9 + event.key - pygame.K_1
                    if index < len(self.battle.player.hand):
                        card = self.battle.player.hand[index]
                        if self.battle.phase == 'DISCARD':
                            if card in self.chosen:
                                self.chosen.remove(card)
                            elif len(self.chosen) < self.battle.required_discards():
                                self.chosen.add(card)
                        else:
                            self.play_card(card)
                elif event.key == pygame.K_d:
                    self.inspect('deck')
                elif event.key == pygame.K_g:
                    self.inspect('discard')
                elif event.key == pygame.K_l:
                    self.set_state('LOG')
                elif event.key == pygame.K_p:
                    self.pause()
            elif event.key == pygame.K_p and self.state in ('MAP', 'REST', 'MERCHANT', 'TREASURE', 'REWARD'):
                self.pause()
        elif event.type == pygame.MOUSEWHEEL:
            if self.state == 'BATTLE':
                self.hand_page = max(0, self.hand_page - event.y)
            elif self.state in ('LOG', 'DECK', 'INSPECT', 'SERVICE', 'STACK'):
                count = len(self.battle.log) if self.state == 'LOG' else len(self.run.deck) if self.state in ('DECK', 'SERVICE') else len(self.battle.stack) if self.state == 'STACK' else len(getattr(self.battle.player, self.inspect_zone))
                page_size = 18 if self.state == 'LOG' else 4 if self.state == 'STACK' else 12
                self.page = max(0, min(max(0, (count - 1) // page_size), self.page - event.y))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3 and self.state == 'BATTLE':
                self.clear_selection()
            elif event.button == 1:
                for rect, action in reversed(self.buttons):
                    if rect.collidepoint(self.to_logical(event.pos)):
                        action()
                        break

    def loop(self):
        while self.running:
            self.draw()
            for event in pygame.event.get():
                self.handle_event(event)
                self.draw()
            self.auto_pass_priority()
            self.check_unlocks()
            self.present()
            self.clock.tick(60)
        pygame.quit()

    def auto_pass_priority(self):
        if self.state != 'BATTLE' or not self.battle or self.battle.result:
            self.priority_signature = None
            return
        b = self.battle
        action = None
        if b.phase == 'RESPONSE' and not b.player_has_instant_action():
            action = b.pass_priority
        elif b.phase == 'ATTACK_RESPONSE' and not b.player_has_instant_action():
            action = b.finish_attack
        elif b.phase == 'DEFEND_RESPONSE' and not b.player_has_instant_action():
            action = b.finish_blocks
        elif b.phase == 'BLOCK':
            blockers = [card for card in b.player.board if not card.tapped]
            if not blockers and not b.player_has_instant_action():
                action = b.finish_blocks
        elif b.phase == 'COMBAT':
            attackers = [card for card in b.player.board if not card.sick and not card.tapped]
            if not attackers and not b.player_has_instant_action():
                action = lambda: b.attack([])
        elif b.phase in ('MAIN', 'MAIN2'):
            candidates = list(b.player.hand) + b.alternate_cards()
            candidates += list(getattr(b.player, 'land_reserve', [])[:1])
            if b.commander_zone == 'COMMAND':
                candidates.append(b.commander)
            active_ready = (b.active and b.commander_zone == 'BOARD' and not b.active_used and not b.stack)
            if not active_ready and not any(self.can_drag(card) for card in candidates):
                action = b.begin_combat if b.phase == 'MAIN' else b.begin_end_step
        if action is None or self.pending or getattr(b, 'pending_entry', None) or self.chosen or self.blockers:
            self.priority_signature = None
            return
        signature = (b.phase, tuple(id(item) for item in b.stack), len(b.player.hand),
                     len(b.player.board), len(b.enemy.board))
        now = pygame.time.get_ticks()
        if signature != self.priority_signature:
            self.priority_signature, self.priority_since = signature, now
        elif now - self.priority_since >= 320:
            action()
            self.priority_signature = None


def main():
    Game().loop()


if __name__ == '__main__':
    main()
