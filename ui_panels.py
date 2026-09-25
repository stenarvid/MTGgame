"""Run persistence, inspection, rewards, services, and scalable-window controls."""
import random
import json
import pygame
from models import Card
from art import fitted


class QolPanels:
    def load_preferences(self):
        self.preferences_path = self.store.path.with_name('settings.json')
        try:
            preferences = json.loads(self.preferences_path.read_text(encoding='utf-8'))
            size = preferences.get('window_size', [1280, 900])
            if len(size) == 2 and all(isinstance(n, int) for n in size):
                self.windowed_size = (max(640, min(3840, size[0])), max(450, min(2160, size[1])))
            self.animations = preferences.get('animations', True) is not False
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save_preferences(self):
        try:
            temp = self.preferences_path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(window_size=self.windowed_size, animations=self.animations)), encoding='utf-8')
            temp.replace(self.preferences_path)
        except OSError:
            self.message = 'Display settings apply for this session; preferences could not be saved.'

    def save_run(self, announce=False):
        if not self.run or self.state in ('MENU', 'PASSIVE', 'ACTIVE', 'ACHIEVEMENTS', 'COLLECTION', 'HELP', 'NEW_RUN_CONFIRM'):
            return True
        state = self.state
        if state in ('PAUSE', 'SETTINGS'):
            state = self.resume_state
        if state == 'MENU':
            return True
        if state in ('INSPECT', 'LOG', 'STACK', 'BATTLE_HELP'):
            state = 'BATTLE'
        if state in ('DECK', 'DETAILS', 'ABANDON'):
            state = 'MAP'
        if state in ('SERVICE', 'SERVICE_CONFIRM'):
            state = 'MERCHANT' if self.run.node.node_type == 'Merchant' else 'REST'
        if state in ('WIN', 'LOSS'):
            return self.store.clear()
        payload = dict(run=self.run, battle=self.battle, state=state, rng=random.getstate(),
                       ui=dict(chosen=self.chosen, pending=None if self.drag_card else self.pending, blocker=self.blocker,
                               hand_page=self.hand_page, recent_unlocks=self.recent_unlocks))
        saved = self.store.save(payload)
        if not saved:
            self.message = self.store.error
        elif announce:
            self.message = 'Run saved.'
        return saved

    def resume_run(self):
        payload = self.store.load(self.pool)
        if payload is None:
            self.message = self.store.error
            return
        self.run, self.battle, self.state = payload['run'], payload['battle'], payload['state']
        random.setstate(payload['rng'])
        ui = payload.get('ui', {})
        self.chosen = ui.get('chosen', set())
        self.pending, self.blocker = ui.get('pending'), ui.get('blocker')
        self.hand_page = ui.get('hand_page', 0)
        self.recent_unlocks = ui.get('recent_unlocks', [])
        self.page = 0
        self.last_event = self.battle.event_serial if self.battle else 0
        self.effects = []
        self.message = 'Run resumed at your last decision.'

    def request_new_run(self):
        if self.store.exists():
            self.state = 'NEW_RUN_CONFIRM'
        else:
            self.start_builder()

    def replace_run(self):
        if self.store.clear():
            self.run = self.battle = None
            self.start_builder()
        else:
            self.message = self.store.error

    def abandon(self):
        if self.store.clear():
            self.run = self.battle = None
            self.state = 'MENU'
        else:
            self.message = self.store.error

    def pause(self):
        self.resume_state = self.state
        self.state = 'PAUSE'

    def save_to_menu(self):
        if self.save_run(True):
            self.state = 'MENU'

    def return_from_panel(self):
        self.state = self.resume_state
        self.page = 0

    def pause_screen(self):
        self.title('Run paused', 'Your run autosaves after each decision. F5 also saves immediately.')
        self.button((420, 220, 440, 55), 'Continue', self.return_from_panel)
        self.button((420, 295, 440, 55), 'Save and return to menu', self.save_to_menu)
        self.button((420, 370, 440, 55), 'Display / animation settings', lambda: self.set_state('SETTINGS'))

    def settings_screen(self):
        self.title('Display & feedback', 'Resize the window freely. The board scales proportionally and mouse input follows it.')
        for i, scale in enumerate((0.75, 1.0, 1.25)):
            self.button((180 + i * 310, 210, 280, 55), f'Interface size: {int(scale * 100)}%',
                        lambda value=scale: self.set_window_scale(value))
        self.button((180, 300, 360, 55), 'Toggle fullscreen (F11)', self.toggle_fullscreen)
        self.button((180, 385, 550, 55), 'Animations: ' + ('on' if self.animations else 'reduced'), self.toggle_animations)
        self.text('Shortcuts: Space advance | 1-9 cards | A attack all | D draw pile | G discard | L log | P pause', 50, 495)
        self.button((180, 600, 280, 55), 'Back', lambda: self.set_state('PAUSE' if self.resume_state != 'MENU' else 'MENU'))

    def open_settings(self):
        self.resume_state = 'MENU'
        self.state = 'SETTINGS'

    def toggle_animations(self):
        self.animations = not self.animations
        self.effects.clear()
        self.save_preferences()

    def set_window_scale(self, scale):
        self.fullscreen = False
        self.windowed_size = (int(1280 * scale), int(900 * scale))
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.save_preferences()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = self.window.get_size()
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def viewport(self):
        width, height = self.window.get_size()
        factor = min(width / 1280, height / 900)
        size = (max(1, int(1280 * factor)), max(1, int(900 * factor)))
        return pygame.Rect((width - size[0]) // 2, (height - size[1]) // 2, *size)

    def to_logical(self, pos):
        rect = self.viewport()
        if not rect.collidepoint(pos):
            return (-1000, -1000)
        return ((pos[0] - rect.x) * 1280 / rect.w, (pos[1] - rect.y) * 900 / rect.h)

    def mouse_pos(self):
        return self.to_logical(pygame.mouse.get_pos())

    def present(self):
        rect = self.viewport()
        self.window.fill((5, 7, 13))
        self.window.blit(pygame.transform.smoothscale(self.screen, rect.size), rect)
        pygame.display.flip()

    def take_reward(self, index=None):
        if self.run.take_card_reward(index):
            self.message = 'Reward skipped.' if index is None else 'Card added to your deck.'
            self.state = 'WIN' if self.run.won else 'MAP'
            self.battle = None
            self.pending = self.blocker = None
            self.chosen.clear()

    def reward_screen(self):
        self.title('Victory: choose a card', 'Take one card for your deck, or skip. Your gold reward has already been added.')
        for i, data in enumerate(self.run.rewards):
            card = Card.from_dict(data)
            x = 150 + 350 * i
            self.card(card, (x, 150, 275, 410))
            self.button((x, 590, 275, 50), 'Add to deck', lambda index=i: self.take_reward(index))
        self.button((500, 725, 280, 50), 'Skip card reward', self.take_reward)

    def mulligan_screen(self):
        self.title('Opening hand', 'Select cards to replace once for free. Your two starting lands stay in play.')
        for i, card in enumerate(self.battle.player.hand):
            self.card(card, (50 + 240 * i, 180, 220, 330), lambda c=card: self.play_card(c), selected=card in self.chosen)
        self.button((320, 570, 300, 55), 'Replace selected cards', self.replace_hand,
                    enabled=bool(self.chosen) and not self.battle.mulligan_used)
        self.button((660, 570, 300, 55), 'Keep hand / begin', self.keep_hand)
        self.text('Mana costs: W white, U blue, B black, R red, G green. Numbers can use any color.', 125, 680)
        self.text(self.battle.intent, 60, 740)

    def replace_hand(self):
        self.battle.mulligan(self.chosen)
        self.chosen.clear()

    def keep_hand(self):
        self.battle.keep_hand()
        self.chosen.clear()

    def inspect(self, zone):
        self.inspect_zone = zone
        self.state = 'INSPECT'
        self.page = 0

    def inspect_screen(self):
        side = self.battle.player
        cards = sorted(getattr(side, self.inspect_zone), key=lambda c: (c.card_type == 'Land', c.mana_cost, c.name))
        self.title('Your ' + ('draw pile' if self.inspect_zone == 'deck' else 'discard pile'),
                   f'{len(cards)} cards. Sorted for inspection; draw order is hidden.')
        for i, card in enumerate(cards[self.page * 12:self.page * 12 + 12]):
            self.card(card, (30 + i % 6 * 207, 115 + i // 6 * 335, 190, 290))
        self.panel_paging(len(cards), 12)

    def panel_paging(self, count, per_page):
        self.page = min(self.page, max(0, (count - 1) // per_page))
        self.button((30, 815, 200, 45), 'Back to battle', lambda: self.set_state('BATTLE'))
        self.button((250, 815, 180, 45), 'Previous', lambda: self.change_page(-1), enabled=self.page > 0)
        self.button((450, 815, 180, 45), 'Next', lambda: self.change_page(1), enabled=(self.page + 1) * per_page < count)
        self.text(f'Page {self.page + 1}', 670, 825)

    def log_screen(self):
        self.title('Combat history', 'Most recent events first. Scroll or use the arrows to browse earlier actions.')
        lines = list(reversed(self.battle.log))
        for i, line in enumerate(lines[self.page * 18:self.page * 18 + 18]):
            self.screen.blit(fitted(line, 1180, 18, (231, 225, 214)), (40, 120 + 36 * i))
        self.panel_paging(len(lines), 18)

    def stack_screen(self):
        self.title('Stack: newest resolves first', 'Click a spell to target it with Null Sigil; Escape returns to the battlefield.')
        entries = list(reversed(self.battle.stack))
        for i, item in enumerate(entries[self.page * 4:self.page * 4 + 4]):
            x = 35 + i * 310
            self.card(item.card, (x, 140, 280, 420))
            target = getattr(item.target, 'name', getattr(getattr(item.target, 'card', None), 'name', 'none'))
            self.wrap(f'{"Triggered ability" if hasattr(item, "ability") else "Spell"} / {item.side.name}. Target: {target}.', x, 580, 280)
            self.button((x, 660, 280, 45), 'Target this spell', lambda value=item: self.stack_target(value),
                        enabled=item in self.valid_targets())
        self.panel_paging(len(entries), 4)

    def stack_target(self, item):
        self.target(item)
        self.state = 'BATTLE'

    def open_service(self, action):
        self.service_action = action
        self.service_card = None
        self.page = 0
        self.state = 'SERVICE'

    def select_service_card(self, card):
        self.service_card = card
        self.state = 'SERVICE_CONFIRM'

    def finish_service(self):
        if self.run.service(self.service_card, self.service_action):
            self.message = 'Card upgraded.' if self.service_action == 'upgrade' else 'Card removed.'
            self.state = 'MERCHANT' if self.run.node else 'MAP'
        else:
            self.message = 'Service unavailable: check gold, upgrade status, or minimum deck/land counts.'

    def service_screen(self):
        merchant = self.run.node.node_type == 'Merchant'
        price = (40 if self.service_action == 'remove' else 30) if merchant else 0
        self.title(self.service_action.title() + ' a card',
                   f'Cost: {price} gold. One service per node. Removal keeps at least 10 cards and 2 lands of each existing color.')
        if self.state == 'SERVICE_CONFIRM':
            original = self.service_card
            self.card(original, (300, 170, 280, 420))
            if self.service_action == 'upgrade':
                upgraded = original.fresh()
                upgraded.upgrade()
                self.card(upgraded, (700, 170, 280, 420))
                self.text('Before', 300, 125)
                self.text('After', 700, 125)
            self.button((490, 650, 300, 55), 'Confirm ' + self.service_action, self.finish_service)
            self.button((30, 810, 260, 45), 'Choose another card', lambda: self.set_state('SERVICE'))
            return
        for i, card in enumerate(self.run.deck[self.page * 12:self.page * 12 + 12]):
            eligible = self.service_action == 'remove' or (not card.upgraded and card.card_type != 'Land')
            self.card(card, (30 + i % 6 * 207, 115 + i // 6 * 335, 190, 290),
                      lambda c=card: self.select_service_card(c), enabled=eligible)
        destination = 'MERCHANT' if merchant else 'REST'
        self.button((30, 815, 200, 45), 'Cancel', lambda: self.set_state(destination))
        self.button((250, 815, 180, 45), 'Previous', lambda: self.change_page(-1), enabled=self.page > 0)
        self.button((450, 815, 180, 45), 'Next', lambda: self.change_page(1), enabled=(self.page + 1) * 12 < len(self.run.deck))

    def render_feedback(self):
        if not self.battle:
            return
        now = pygame.time.get_ticks()
        for event in self.battle.events:
            if event['serial'] <= self.last_event:
                continue
            target = event['target']
            x, y = (850, 80) if target is self.battle.player else (250, 80)
            for side, top in ((self.battle.enemy, 175), (self.battle.player, 425)):
                if target in side.board:
                    x, y = 91 + side.board.index(target) * 139, top
            if event['kind'] == 'cast':
                x, y = 640, 375
            self.effects.append(dict(x=x, y=y, label=event['label'], kind=event['kind'], born=now))
            self.last_event = event['serial']
        self.effects = [e for e in self.effects if now - e['born'] < 1400][-12:]
        if self.animations:
            for i, effect in enumerate(self.effects):
                elapsed = (now - effect['born']) / 1400
                color = (115, 255, 166) if effect['kind'] == 'heal' else (250, 211, 135) if effect['kind'] == 'cast' else (255, 130, 130)
                label = fitted(effect['label'], 350, 24, color)
                self.screen.blit(label, (effect['x'] - label.get_width() // 2, effect['y'] - elapsed * 48 - i % 3 * 16))
