"""Pygame screens and input for the commander roguelike."""
import random
import pygame

from engine import Battle, Progress, Run, UNLOCKS
from models import Card, color_starters, generate_procedural_commander, load_game_data
from rendering import draw_node_icon, draw_wrapped_text
from art import Artwork, CardPainter, fitted, font as art_font
from persistence import RunStore
from ui_panels import QolPanels
from card_interaction import CardInteraction
from battlefield_piles import BattlefieldPiles

BG = (20, 18, 28)
TEXT = (232, 232, 240)
GOLD = (245, 206, 105)
MUTED = (159, 155, 178)
GREEN = (95, 218, 151)


class Game(BattlefieldPiles, CardInteraction, QolPanels):
    def __init__(self, save_path=None, progress_path=None):
        pygame.init()
        art_font.cache_clear()
        self.windowed_size = (1280, 900)
        self.animations = True
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
        self.pending = self.blocker = None
        self.chosen = set()
        self.legend = False
        self.recent_unlocks = []
        self.init_card_interaction()

    def text(self, text, x, y, color=TEXT, font=None):
        self.screen.blit((font or self.font).render(str(text), True, color), (x, y))

    def wrap(self, text, x, y, width, color=TEXT):
        return draw_wrapped_text(self.screen, text, self.small, color, x, y, width)

    def button(self, rect, label, action, enabled=True, selected=False, readable=False):
        rect = pygame.Rect(rect)
        over = rect.collidepoint(self.mouse_pos())
        color = (64, 57, 86) if over and enabled else (38, 33, 52)
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        pygame.draw.rect(self.screen, GREEN if selected else GOLD if enabled else (80, 74, 93),
                         rect, 2, border_radius=7)
        self.screen.blit(fitted(label, rect.w - 24, 18, TEXT if enabled or readable else MUTED), (rect.x + 12, rect.y + 10))
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
        choices = self.commanders['passives'] + [u for u in UNLOCKS if u['name'] in self.progress.unlocked]
        self.choices = random.sample(choices, min(4, len(choices)))
        self.state = 'PASSIVE'
        self.message = ''
        self.passive = None
        self.recent_unlocks = []

    def choose(self, choice):
        if self.state == 'PASSIVE':
            self.passive = choice
            self.choices = random.sample(self.commanders['actives'], 4)
            self.state = 'ACTIVE'
        else:
            commander = generate_procedural_commander(self.commanders, [], [], self.passive, choice)
            self.run = Run(commander, self.pool)
            self.battle = None
            self.state = 'MAP'
            self.message = 'Choose a green node to begin your ascent.'
            self.pending = self.blocker = None
            self.chosen.clear()
            self.save_run()

    def enter_node(self, node):
        if not self.run.enter(node):
            return
        self.message = ''
        if node.node_type in ('Combat', 'Elite', 'Boss'):
            self.battle = Battle(self.run)
            self.state = 'BATTLE'
            self.hand_page = 0
            self.pending = self.blocker = None
            self.chosen.clear()
            self.last_event = 0
            self.effects = []
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
        if self.battle.targets(card.name):
            self.pending = card
            self.message = f'{card.name}: click a highlighted target. Right-click to cancel.'

        else:
            self.battle.play(card)
            self.pending = None

    def active(self):
        if self.battle.active == 'Wild Growth':
            self.battle.use_active()
        else:
            self.pending = 'ACTIVE'
            self.message = f'{self.battle.active}: click a highlighted target. Right-click to cancel.'

    def valid_targets(self):
        if self.battle.phase == 'ATTACK_TARGET':
            return self.battle.copy_targets(self.battle.attack_choices[0])
        if self.pending is None:
            return []
        return self.battle.targets(self.battle.active if self.pending == 'ACTIVE' else self.pending.name)

    def target(self, target):
        if self.battle.phase == 'ATTACK_TARGET':
            self.battle.choose_attack_copy(target)
            return
        if target not in self.valid_targets():
            return
        success = (self.battle.use_active(target) if self.pending == 'ACTIVE'
                   else self.battle.play(self.pending, target))
        if success:
            self.pending = None
            self.message = ''

    def click_creature(self, creature, friendly):
        battle = self.battle
        if self.pending or battle.phase == 'ATTACK_TARGET':
            self.target(creature)
        elif battle.phase == 'BLOCK':
            if friendly and not creature.tapped:
                self.blocker = creature
            elif not friendly and self.blocker:
                battle.assign_blocker(creature, self.blocker)
                self.blocker = None
        elif battle.phase == 'ATTACK_RESPONSE' and not friendly:
            battle.reorder_blocker(creature)
        elif battle.phase == 'MAIN' and friendly and not creature.sick and not creature.tapped:
            if creature in self.chosen:
                self.chosen.remove(creature)
            else:
                self.chosen.add(creature)

    def advance_combat(self):
        if self.battle.phase == 'ATTACK_TARGET':
            self.battle.choose_attack_copy(None)
        elif self.battle.phase == 'MAIN':
            self.battle.attack(self.chosen)
        elif self.battle.phase == 'MAIN2':
            self.battle.end_turn()
        elif self.battle.phase == 'RESPONSE':
            self.battle.pass_priority()
        elif self.battle.phase == 'ATTACK_RESPONSE':
            self.battle.finish_attack()
        elif self.battle.phase in ('BLOCK', 'DEFEND_RESPONSE'):
            self.battle.finish_blocks()
        elif self.battle.phase == 'MULLIGAN':
            self.keep_hand()
        self.chosen.clear()
        self.blocker = self.pending = None
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
        self.title('1. Choose a passive' if self.state == 'PASSIVE' else '2. Choose an active ability',
                   'Each choice adds the cards below. Abilities determine your commander colors and archetypes.')
        for i, choice in enumerate(self.choices):
            x = 25 + i * 313
            pygame.draw.rect(self.screen, (35, 29, 48), (x, 115, 290, 695), border_radius=10)
            self.artwork.paint(self.screen, choice['color'], (x + 10, 125, 270, 175))
            self.text(choice['name'], x + 15, 320, GOLD)
            self.text(f"{choice['color']} / {choice['archetype']}", x + 15, 352, MUTED)
            self.wrap(choice['desc'], x + 15, 392, 260)
            self.text('Starting cards (hover for details)', x + 15, 465, GREEN, self.small)
            for j, card in enumerate(color_starters(self.pool, choice['color'], choice['archetype'])):
                y = 498 + j * 27
                self.text(card.name, x + 15, y, TEXT, self.small)
                if pygame.Rect(x + 10, y - 2, 270, 26).collidepoint(self.mouse_pos()):
                    self.hover = card
            self.button((x + 15, 745, 260, 48), 'Choose', lambda c=choice: self.choose(c))
        self.button((25, 830, 170, 42), 'Back to menu', lambda: self.set_state('MENU'))

    def map_screen(self):
        run = self.run
        self.title(run.commander.name,
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
                color = GREEN if node.available else GOLD if node.visited else (68, 61, 81)
                pygame.draw.circle(self.screen, color, (x, y), 21)
                draw_node_icon(self.screen, node.node_type, x, y)
                self.text(node.node_type, x - 30, y + 24, color if node.available or node.visited else MUTED, self.small)
                if node.available:
                    self.buttons.append((pygame.Rect(x - 23, y - 23, 46, 46), lambda n=node: self.enter_node(n)))
        self.button((30, 625, 175, 42), 'Run details', lambda: self.set_state('DETAILS'))
        self.button((225, 625, 180, 42), 'Save / pause', self.pause)
        self.button((1040, 625, 210, 42), 'Abandon run', lambda: self.set_state('ABANDON'))
        if self.legend:
            pygame.draw.rect(self.screen, (35, 29, 48), (980, 88, 290, 290), border_radius=8)
            for i, label in enumerate(['Green: available', 'Gold: completed', 'Combat: earn gold',
                                       'Elite: harder duel, more gold', 'Rest: heal 10 HP',
                                       'Merchant: buy cards', 'Treasure: choose a power-up', 'Boss: win the run']):
                self.text(label, 995, 102 + i * 32, TEXT, self.small)

    def toggle_legend(self):
        self.legend = not self.legend

    def battle_screen(self):
        b = self.battle
        if b.phase == 'MULLIGAN':
            self.mulligan_screen()
            return
        self.screen.blit(fitted(f'{b.enemy.name} | Turn {b.turn} | {b.phase.replace("_", " ").title()}', 715, 26, GOLD), (25, 15))
        for x, label, callback in [(760, 'Draw [D]', lambda: self.inspect('deck')),
                                    (885, 'Discard [G]', lambda: self.inspect('discard')),
                                    (1010, 'Log [L]', lambda: self.set_state('LOG')),
                                    (1135, 'Pause [P]', self.pause)]:
            self.button((x, 12, 115, 36), label, callback)
        targets = self.valid_targets()
        for side, x in [(b.enemy, 25), (b.player, 650)]:
            label = f'{"Enemy" if side is b.enemy else "You"}: {side.hp}/{side.max_hp} HP | Armor {side.armor}'
            self.button((x, 59, 595, 42), label, lambda s=side: self.target(s),
                        enabled=side in targets, selected=side in targets, readable=True)
        self.screen.blit(fitted(f'Enemy mana {b.mana_summary(b.enemy)} | Hand {len(b.enemy.hand)} | {b.intent}', 1215, 13, MUTED), (25, 108))
        self.text(f'Your lands {len(b.player.lands)} | Mana {b.mana_summary(b.player)} | '
                  f'Land play: {"used" if b.player.land_played else "available"} | '
                  f'Draw {len(b.player.deck)} / Discard {len(b.player.discard)}', 25, 366, GOLD, self.small)
        self.draw_battlefield()
        preview = b.combat_preview()
        if preview:
            lethal = ', '.join(c.name for c in preview['deaths']) or 'none'
            summary = f"Combat preview: you take {preview['player_damage']}, enemy takes {preview['enemy_damage']}. Lethal: {lethal}."
            self.screen.blit(fitted(summary, 935, 14, GREEN), (25, 334))
            self.text('Before later responses and death triggers.', 25, 350, MUTED, self.small)
        self.draw_response_stack()
        if b.result:
            self.button((25, 590, 390, 46), f'{b.result.title()} - continue', self.end_battle)
        else:
            label = {'ATTACK_TARGET': 'Skip copy [Space]', 'MAIN': 'Declare attacks [Space]', 'MAIN2': 'End turn [Space]', 'RESPONSE': 'Pass priority [Space]',
                     'BLOCK': 'Lock blocks [Space]', 'ATTACK_RESPONSE': 'Resolve combat [Space]', 'DEFEND_RESPONSE': 'Resolve combat [Space]'}.get(b.phase, 'Continue')
            self.button((25, 590, 290, 46), label, self.advance_combat)
            self.button((335, 590, 265, 46), b.active + (' (used)' if b.active_used else ''), self.active,
                        enabled=b.phase in ('MAIN', 'MAIN2') and not b.active_used)
            sprite = next((c for c in b.player.board if c.name == 'Grove Sprite' and not c.sick and not c.tapped), None)
            self.button((620, 590, 230, 46), 'Tap Sprite: +1 G', lambda: b.tap_sprite(sprite), enabled=sprite is not None)
            self.button((870, 590, 175, 46), 'Clear selection', self.clear_selection)
        self.button((1065, 590, 185, 46), 'Rules / help', lambda: self.set_state('BATTLE_HELP'))
        instruction = {'ATTACK_TARGET': 'Attack trigger: choose a highlighted creature to copy, or skip.', 'BLOCK': 'Select a blocker, then an attacker. Repeat to assign multiple blockers. Instants are playable.',
                       'MAIN': 'Drag cards to play [1-9 also works]. Select attackers [A = all]. Declaring attacks opens a response window.',
                       'MAIN2': 'Second main phase: play creatures or lands before ending your turn.',
                       'RESPONSE': 'Cast an instant to respond, or pass priority. Newest spell resolves first.',
                       'ATTACK_RESPONSE': 'Review blocks. Click an enemy blocker to move it last in damage order, or cast an instant.',
                       'DEFEND_RESPONSE': 'Blocks locked. Cast instants or resolve damage.'}.get(b.phase, 'Battle finished.')
        self.text(self.message or instruction, 25, 643, GREEN, self.small)
        self.draw_hand()
        self.render_feedback()

    def clear_selection(self):
        self.pending = self.blocker = None
        self.chosen.clear()
        if self.battle and self.battle.phase == 'BLOCK':
            self.battle.assignments.clear()
        self.message = ''

    def shop_screen(self):
        self.title('Merchant', f'Gold: {self.run.gold}. Purchases join your deck for future battles.')
        for i, item in enumerate(self.run.shop):
            card = Card.from_dict(item['card'])
            x = 30 + i * 248
            self.card(card, (x, 140, 225, 345))
            self.button((x, 510, 225, 48), 'Sold' if item['sold'] else f"Buy: {item['price']} gold",
                        lambda index=i: self.run.buy(index), enabled=not item['sold'] and self.run.gold >= item['price'])
        self.button((30, 800, 230, 48), 'Leave merchant', self.leave_shop)
        self.button((30, 625, 340, 50), 'Remove a card: 40 gold', lambda: self.open_service('remove'),
                    enabled=not self.run.service_used and self.run.gold >= 40)
        self.button((395, 625, 340, 50), 'Upgrade a card: 30 gold', lambda: self.open_service('upgrade'),
                    enabled=not self.run.service_used and self.run.gold >= 30)
        self.text('One service per merchant visit. Choose a card and review it before confirming.', 30, 700, MUTED)

    def treasure_screen(self):
        self.title('Treasure: choose one power-up', 'Relics last for this run and combine with your commander abilities.')
        for i, relic in enumerate(self.run.choices):
            x = 35 + i * 415
            pygame.draw.rect(self.screen, (39, 32, 53), (x, 155, 385, 280), border_radius=10)
            self.text(relic['name'], x + 20, 180, GOLD)
            self.text(relic['rarity'], x + 20, 220, MUTED)
            self.wrap(relic['desc'], x + 20, 260, 345)
            self.button((x + 20, 355, 345, 50), 'Take relic', lambda index=i: self.take_relic(index))
        if not self.run.choices:
            self.button((35, 190, 380, 50), 'All relics owned: take 25 gold', lambda: self.take_relic(0))

    def deck_screen(self):
        creatures = sum(c.is_creature for c in self.run.deck)
        lands = sum(c.card_type == 'Land' for c in self.run.deck)
        self.title('Your deck', f'{len(self.run.deck)} cards  |  {creatures} creatures  |  '
                   f'{len(self.run.deck) - creatures - lands} spells  |  {lands} lands. Hover a card to inspect it.')
        start = self.page * 12
        for i, card in enumerate(self.run.deck[start:start + 12]):
            self.card(card, (30 + (i % 6) * 207, 115 + (i // 6) * 335, 190, 290))
        self.button((30, 805, 170, 45), 'Back to map', lambda: self.set_state('MAP'))
        self.button((230, 805, 150, 45), 'Previous', lambda: self.change_page(-1), enabled=self.page > 0)
        self.button((400, 805, 150, 45), 'Next', lambda: self.change_page(1), enabled=start + 12 < len(self.run.deck))

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
                self.text(f'{cmd.passive_name}: {cmd.passive}', 40, y, GREEN)
                self.text(f'{cmd.active_name}: {cmd.active} (once per battle)', 40, y + 38, GOLD)
                y += 95
            relics = self.pool['relics'] if state == 'COLLECTION' else self.run.relics
            for relic in relics:
                self.text(f"{relic['name']}: {relic['desc']}", 40, y)
                y += 43
            if not relics:
                self.text('Visit a Treasure node to choose your first power-up.', 40, y, MUTED)
        else:
            self.title('How to play', 'An MTG-inspired roguelike with a small, explicit ruleset.')
            lines = [
                'Opening: two lands in play, five cards in hand. Replace selected cards once for free, then keep and draw for turn.',
                'Mana: W white, U blue, B black, R red, G green. A cost of 1R needs one red plus one mana of any color.',
                'Lands: play one per turn. They persist and untap each turn. Payment uses matching colors automatically.',
                'Turn: first main phase, declare attacks, combat responses, second main phase, then end turn.',
                'Stack: spells wait for responses. Cast an instant or pass priority; the newest spell resolves first.',
                'Drag a hand card onto the field or its target. Hover to enlarge; hold left mouse to pick up; right-click cancels.',
                'Attack: select ready creatures, then declare. New creatures cannot attack unless they have Haste.',
                'Block: select an untapped blocker and an attacker. Repeat for multiple blockers; each blocker guards one attacker.',
                'Damage order: during your attack, click an enemy blocker to move it last. Block labels show the order.',
                'Preview: hero damage and lethal creatures are shown before damage, excluding later responses and death triggers.',
                'Trample deals excess damage through blockers. Other blocked attackers stay blocked if their blockers disappear.',
                'Damage is simultaneous. Survivors clear damage and temporary buffs at turn end. Tokens vanish when they leave.',
                'Unplayed cards stay in hand. Empty decks reshuffle discards; an empty deck AND discard causes increasing fatigue.',
                'Rewards: choose one of three cards or skip. Treasure offers relics; shops offer purchases and one paid service.',
                'Rest: heal 10 HP OR upgrade a card. Creature upgrades give +1/+1; spell upgrades improve numerical effects.',
                'Save: autosave after decisions, F5 manual save, P pause. Resume from the menu, including mid-combat decisions.',
                'Shortcuts: Space advance, 1-9 hand cards, A attack all, D draw pile, G discard, L log, F11 fullscreen.',
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
        elif state in ('PASSIVE', 'ACTIVE'):
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
        if self.hover and not self.drag_card:
            x, y = self.mouse_pos()
            if self.state == 'BATTLE' and self.hand_hover is self.hover:
                self.card_painter.draw(self.screen, self.hover, (35 if x > 640 else 665, 145, 300, 445),
                                       cost=self.battle.cost(self.battle.player, self.hover))
            else:
                self.card_painter.preview(self.screen, self.hover, x, y)
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
            elif event.key == pygame.K_F5:
                self.save_run(True)
            elif event.key == pygame.K_ESCAPE:
                if self.state == 'BATTLE':
                    if self.pending or self.chosen or self.blocker:
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
                if event.key == pygame.K_SPACE:
                    self.end_battle() if self.battle.result else self.advance_combat()
                elif event.key == pygame.K_a and self.battle.phase == 'MAIN':
                    ready = {c for c in self.battle.player.board if not c.sick and not c.tapped}
                    self.chosen = set() if self.chosen == ready else ready
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    index = self.hand_page * 9 + event.key - pygame.K_1
                    if index < len(self.battle.player.hand):
                        self.play_card(self.battle.player.hand[index])
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
            self.check_unlocks()
            self.present()
            self.clock.tick(60)
        pygame.quit()


def main():
    Game().loop()


if __name__ == '__main__':
    main()
