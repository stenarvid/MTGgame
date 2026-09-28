"""Run persistence, inspection, rewards, services, and scalable-window controls."""
import random
import json
import math
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
            self.animation_speed = preferences.get('animation_speed',
                                                   'normal' if preferences.get('animations', True) else 'off')
            if self.animation_speed not in ('off', 'fast', 'normal', 'cinematic'):
                self.animation_speed = 'normal'
            self.animations = self.animation_speed != 'off'
            self.inspect_key = {'Left Alt': pygame.K_LALT, 'Left Ctrl': pygame.K_LCTRL,
                                'Left Shift': pygame.K_LSHIFT}.get(preferences.get('inspect_key'), pygame.K_LALT)
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save_preferences(self):
        try:
            temp = self.preferences_path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(window_size=self.windowed_size, animations=self.animations,
                                            animation_speed=self.animation_speed,
                                            inspect_key=self.inspect_key_name())), encoding='utf-8')
            temp.replace(self.preferences_path)
        except OSError:
            self.message = 'Display settings apply for this session; preferences could not be saved.'

    def save_run(self, announce=False):
        if not self.run or self.state in ('MENU', 'RUN_SETUP', 'PASSIVE', 'ACTIVE', 'SECOND_PASSIVE', 'ACHIEVEMENTS', 'COLLECTION', 'HELP', 'TUTORIAL', 'NEW_RUN_CONFIRM'):
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
                       ui=dict(chosen=self.chosen, pending=None if self.drag_card else self.pending, blockers=self.blockers,
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
        if not hasattr(self.run, 'area'):
            self.run.area = 1
        if not hasattr(self.run, 'total_areas'):
            self.run.total_areas = 4
        # Convert pre-booster reward saves without losing their offered cards.
        if self.run.reward_pending and self.run.rewards and 'cards' not in self.run.rewards[0]:
            from engine import reward_theme
            migrated = []
            for offered in self.run.rewards:
                theme = reward_theme(offered)
                extras = [c for c in self.run.card_choices()
                          if reward_theme(c) == theme and c['name'] != offered['name']][:2]
                migrated.append(dict(theme=theme, cards=[offered] + extras))
            self.run.rewards = migrated
        random.setstate(payload['rng'])
        ui = payload.get('ui', {})
        self.chosen = ui.get('chosen', set())
        self.pending = ui.get('pending')
        self.blockers = ui.get('blockers', set())
        if not self.blockers and ui.get('blocker') is not None:
            self.blockers = {ui['blocker']}
        self.hand_page = ui.get('hand_page', 0)
        self.recent_unlocks = ui.get('recent_unlocks', [])
        self.page = 0
        self.last_event = self.battle.event_serial if self.battle else 0
        self.effects = []
        self.turn_banner_key = None
        if self.battle and self.battle.phase == 'UPKEEP':
            self.battle.finish_upkeep()
        elif self.battle and self.battle.phase == 'END':
            self.battle.end_turn()
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
        self.button((180, 385, 550, 55), f'Animation speed: {self.animation_speed.title()}', self.cycle_animation_speed)
        self.button((180, 460, 550, 55), f'Inspect card key: {self.inspect_key_name()}', self.cycle_inspect_key)
        self.text('Shortcuts: Enter/Space advance | 1-9 cards | A attack all | B blockers | Ctrl+Z undo | D/G/L/P', 50, 550)
        self.button((180, 600, 280, 55), 'Back', lambda: self.set_state('PAUSE' if self.resume_state != 'MENU' else 'MENU'))

    def open_settings(self):
        self.resume_state = 'MENU'
        self.state = 'SETTINGS'

    def toggle_animations(self):
        self.animation_speed = 'off' if self.animations else 'normal'
        self.animations = self.animation_speed != 'off'
        self.effects.clear()
        self.save_preferences()

    def cycle_animation_speed(self):
        speeds = ('off', 'fast', 'normal', 'cinematic')
        self.animation_speed = speeds[(speeds.index(self.animation_speed) + 1) % len(speeds)]
        self.animations = self.animation_speed != 'off'
        self.effects.clear()
        self.save_preferences()

    def inspect_key_name(self):
        return {pygame.K_LALT: 'Left Alt', pygame.K_LCTRL: 'Left Ctrl',
                pygame.K_LSHIFT: 'Left Shift'}.get(self.inspect_key, 'Left Alt')

    def cycle_inspect_key(self):
        keys = (pygame.K_LALT, pygame.K_LCTRL, pygame.K_LSHIFT)
        self.inspect_key = keys[(keys.index(self.inspect_key) + 1) % len(keys)]
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
        # Continue the scene through letterboxed space instead of showing black bars.
        key = 'arena' if self.state == 'BATTLE' else 'land'
        backdrop = self.artwork.image(key, self.window.get_size()).copy()
        shade = pygame.Surface(self.window.get_size(), pygame.SRCALPHA)
        shade.fill((10, 9, 24, 180))
        backdrop.blit(shade, (0, 0))
        self.window.blit(backdrop, (0, 0))
        self.window.blit(pygame.transform.smoothscale(self.screen, rect.size), rect)
        pygame.display.flip()

    def take_reward(self, index=None):
        if self.run.take_card_reward(index):
            self.message = 'Reward skipped.' if index is None else 'Three-card booster added to your deck.'
            self.state = 'WIN' if self.run.won else 'MAP'
            self.battle = None
            self.pending = None
            self.blockers.clear()
            self.chosen.clear()

    def reward_screen(self):
        self.title('Victory: choose a booster', 'Each pack adds all three cards from one archetype. Your gold is already added.')
        for i, reward in enumerate(self.run.rewards):
            pack = reward.get('cards', [reward])
            archetype = reward.get('theme', reward.get('archetype', 'Mixed'))
            x = 25 + 415 * i
            pygame.draw.rect(self.screen, (25, 29, 38), (x, 115, 390, 535), border_radius=12)
            pygame.draw.rect(self.screen, (192, 164, 108), (x, 115, 390, 535), 2, border_radius=12)
            self.text(f'{archetype} booster', x + 18, 132, (245, 206, 105))
            copies = sum(sum(existing.name == data['name'] for existing in self.run.deck) for data in pack)
            colors = sorted({data.get('color', '?') for data in pack})
            self.text(f'Adds all 3 | {copies} existing copies | Colors {"/".join(colors)}',
                      x + 18, 164, (159, 155, 178), self.small)
            for j, data in enumerate(pack):
                card = Card.from_dict(data)
                self.card(card, (x + 10 + j * 125, 200, 120, 285))
                owned = sum(existing.name == card.name for existing in self.run.deck)
                self.text(f'Owned: {owned}', x + 14 + j * 125, 493, (159, 155, 178), self.small)
            self.button((x + 25, 545, 340, 50), 'Take all 3 cards', lambda index=i: self.take_reward(index))
        self.button((500, 705, 280, 50), 'Skip booster reward', self.take_reward)

    def mulligan_screen(self):
        self.title('Opening hand', 'Select cards to replace once for free. Two lands start in play; the rest stay in your reserve.')
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
        cards = self.filtered_cards(getattr(side, self.inspect_zone))
        self.title('Your ' + ('draw pile' if self.inspect_zone == 'deck' else 'discard pile'),
                   f'{len(cards)} cards. Sorted for inspection; draw order is hidden.')
        self.button((30, 78, 180, 30), f'Filter: {self.deck_filter}', self.cycle_deck_filter)
        self.button((220, 78, 180, 30), f'Sort: {self.deck_sort}', self.cycle_deck_sort)
        self.button((410, 78, 390, 30), 'Search: ' + (self.deck_search or 'click, then type'), self.start_search,
                    selected=self.search_active)
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
            self.message = (f'Card upgraded to level {self.service_card.upgrade_level}.'
                            if self.service_action == 'upgrade' else 'Card removed.')
            self.state = 'MERCHANT' if self.run.node else 'MAP'
        else:
            self.message = 'Service unavailable: check gold, upgrade status, or minimum deck/land counts.'

    def service_screen(self):
        merchant = self.run.node.node_type == 'Merchant'
        price = (40 if self.service_action == 'remove' else 30) if merchant else 0
        self.title(self.service_action.title() + ' a card',
                   f'Cost: {price} gold. Merchant services are repeatable. Removal keeps at least 10 cards and 2 lands of each existing color.')
        if self.state == 'SERVICE_CONFIRM':
            original = self.service_card
            self.card(original, (300, 170, 280, 420))
            if self.service_action == 'upgrade':
                upgraded = original.fresh()
                upgraded.upgrade()
                self.card(upgraded, (700, 170, 280, 420))
                self.text('Before', 300, 125)
                self.text(f'Next: level {upgraded.upgrade_level}', 700, 125)
                self.wrap(original.upgrade_description(), 700, 605, 360)
            self.button((490, 650, 300, 55), 'Confirm ' + self.service_action, self.finish_service)
            self.button((30, 810, 260, 45), 'Choose another card', lambda: self.set_state('SERVICE'))
            return
        for i, card in enumerate(self.run.deck[self.page * 12:self.page * 12 + 12]):
            eligible = self.service_action == 'remove' or card.card_type != 'Land'
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
            if isinstance(target, Card) and getattr(target, 'rect', None):
                x, y = target.rect.center
            if event['kind'] == 'cast':
                x, y = 640, 375
            self.effects.append(dict(x=x, y=y, label=event['label'], kind=event['kind'], born=now))
            self.last_event = event['serial']
        duration = {'fast': 700, 'normal': 1400, 'cinematic': 2200}.get(self.animation_speed, 1)
        self.effects = [e for e in self.effects if now - e['born'] < duration][-12:]
        if self.animations:
            for i, effect in enumerate(self.effects):
                elapsed = min(1, (now - effect['born']) / duration)
                color = (115, 255, 166) if effect['kind'] == 'heal' else (250, 211, 135) if effect['kind'] == 'cast' else (175, 130, 255) if effect['kind'] == 'blink' else (100, 205, 255) if effect['kind'] == 'return' else (255, 130, 130)
                if effect['kind'] == 'blink':
                    radius = int(18 + elapsed * 65)
                    pygame.draw.circle(self.screen, color, (effect['x'], effect['y']), radius,
                                       max(1, int(5 * (1 - elapsed))))
                    ghost = pygame.Surface((90, 120), pygame.SRCALPHA)
                    pygame.draw.rect(ghost, (*color, int(70 * (1 - elapsed))), ghost.get_rect(), 3, border_radius=9)
                    self.screen.blit(ghost, ghost.get_rect(center=(effect['x'], effect['y'] - int(18 * math.sin(elapsed * math.pi)))))
                elif effect['kind'] == 'return':
                    for trail in range(4):
                        offset = int(elapsed * 90 + trail * 13)
                        pygame.draw.circle(self.screen, color,
                                           (effect['x'] - offset, effect['y'] - offset // 3), max(2, 7 - trail))
                elif effect['kind'] == 'death':
                    for drop in range(12):
                        angle = drop * math.tau / 12
                        distance = elapsed * (28 + (drop % 4) * 9)
                        point = (int(effect['x'] + math.cos(angle) * distance),
                                 int(effect['y'] + math.sin(angle) * distance + elapsed * elapsed * 35))
                        pygame.draw.circle(self.screen, (150 + drop % 3 * 22, 18, 35), point,
                                           max(2, int(7 * (1 - elapsed))))
                elif effect['kind'] == 'cast':
                    travel = min(1, elapsed / .42)
                    start, finish = pygame.Vector2(640, 820), pygame.Vector2(1135, 255)
                    pos = start.lerp(finish, 1 - (1 - travel) ** 3)
                    lift = math.sin(travel * math.pi) * 85
                    card_rect = pygame.Rect(0, 0, 62, 88)
                    card_rect.center = (round(pos.x), round(pos.y - lift))
                    pygame.draw.rect(self.screen, (15, 22, 35), card_rect, border_radius=7)
                    pygame.draw.rect(self.screen, color, card_rect, 2, border_radius=7)
                    self.screen.blit(fitted(effect['label'], 54, 9, color), (card_rect.x + 4, card_rect.y + 8))
                    for spark in range(10):
                        angle = spark * math.tau / 10 + elapsed * 2
                        distance = 12 + elapsed * 55
                        point = (int(effect['x'] + math.cos(angle) * distance),
                                 int(effect['y'] + math.sin(angle) * distance))
                        pygame.draw.circle(self.screen, color, point, max(1, int(5 * (1 - elapsed))))
                    pygame.draw.circle(self.screen, color, (effect['x'], effect['y']), int(12 + elapsed * 38), 2)
                elif effect['kind'] in ('damage', 'hit'):
                    for slash in (-1, 1):
                        reach = int(38 * (1 - elapsed))
                        pygame.draw.line(self.screen, color,
                                         (effect['x'] - reach, effect['y'] - slash * reach),
                                         (effect['x'] + reach, effect['y'] + slash * reach), 4)
                elif effect['kind'] == 'heal':
                    for mote in range(8):
                        angle = mote * math.tau / 8
                        radius = 12 + elapsed * 34
                        point = (int(effect['x'] + math.cos(angle) * radius),
                                 int(effect['y'] + math.sin(angle) * radius - elapsed * 25))
                        pygame.draw.circle(self.screen, color, point, max(1, int(5 * (1 - elapsed))))
                label = fitted(effect['label'], 350, 24, color)
                self.screen.blit(label, (effect['x'] - label.get_width() // 2, effect['y'] - elapsed * 48 - i % 3 * 16))
