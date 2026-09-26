"""Fanned hand, drag casting, and an in-battle response stack."""
import math
import pygame
from art import fitted


class CardInteraction:
    def init_card_interaction(self):
        self.drag_card = None
        self.drag_pos = (0, 0)
        self.drag_start = None
        self.drag_from_hand = False
        self.alternate_hits = []
        self.alternate_page = 0
        self.hand_hits = []
        self.stack_hits = []
        self.hand_hover = None
        self.lifted_rect = None

    def hand_layout(self):
        cards = self.battle.player.hand[self.hand_page * 9:self.hand_page * 9 + 9]
        step = min(100, 550 / max(1, len(cards) - 1))
        middle = (len(cards) - 1) / 2
        return [(card, (495 + (i - middle) * step, 810 + abs(i - middle) ** 2 * 2),
                 -(i - middle) * 3.5) for i, card in enumerate(cards)]

    def hand_at(self, pos):
        for card, rect, mask in reversed(self.hand_hits):
            if rect.collidepoint(pos) and mask.get_at((int(pos[0] - rect.x), int(pos[1] - rect.y))):
                return card
        return None

    def glow(self, rect, color=(85, 220, 255)):
        layer = pygame.Surface((rect.w + 44, rect.h + 44), pygame.SRCALPHA)
        for spread in range(20, 0, -2):
            pygame.draw.rect(layer, (*color, 85 - spread * 3),
                             pygame.Rect(22, 22, rect.w, rect.h).inflate(spread * 2, spread * 2),
                             border_radius=14)
        self.screen.blit(layer, (rect.x - 22, rect.y - 22))

    def draw_hand(self):
        self.hand_page = max(0, min(self.hand_page, max(0, (len(self.battle.player.hand) - 1) // 9)))
        rendered = []
        for card, center, angle in self.hand_layout():
            face = pygame.Surface((150, 215), pygame.SRCALPHA)
            self.card_painter.draw(face, card, (0, 0, 146, 210),
                                   cost=self.battle.cost(self.battle.player, card),
                                   playable=self.can_drag(card))
            face = pygame.transform.rotate(face, angle)
            rect = face.get_rect(center=center)
            rendered.append((card, face, rect))
        self.hand_hits = [(card, rect, pygame.mask.from_surface(face)) for card, face, rect in rendered]
        hovered = self.hand_at(self.mouse_pos()) if not self.drag_card else None
        if not hovered and not self.drag_card and self.lifted_rect and self.lifted_rect.collidepoint(self.mouse_pos()):
            hovered = self.hand_hover if self.hand_hover in self.battle.player.hand else None
        self.lifted_rect = None
        self.hand_hover = hovered
        for card, face, rect in rendered:
            if card is not self.drag_card and card is not hovered:
                self.screen.blit(face, rect)
        if hovered:
            center = next(rect.centerx for card, _, rect in rendered if card is hovered)
            rect = pygame.Rect(center - 90, 658, 180, 252)
            self.lifted_rect = rect
            self.hand_hits.append((hovered, rect, pygame.mask.Mask(rect.size, fill=True)))
            self.glow(rect)
            self.card_painter.draw(self.screen, hovered, rect, selected=True,
                                   cost=self.battle.cost(self.battle.player, hovered))
            self.hover = hovered
        start = self.hand_page * 9
        self.button((18, 850, 55, 36), '<', lambda: self.change_hand_page(-1), enabled=self.hand_page > 0)
        self.button((820, 850, 55, 36), '>', lambda: self.change_hand_page(1),
                    enabled=start + 9 < len(self.battle.player.hand))
        self.text(f'Hand {len(self.battle.player.hand)} / page {self.hand_page + 1}', 20, 818, font=self.small)

    def can_drag(self, card):
        b = self.battle
        command = card is b.commander and b.commander_zone == 'COMMAND'
        if b.result or (card not in b.player.hand and not command and not b.alternate_zone(card)):
            return False
        if b.phase not in ('MAIN', 'MAIN2') and not (card.card_type == 'Instant Spell' and b.phase in
                ('RESPONSE', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE')):
            return False
        if card.card_type == 'Land':
            return not b.player.land_played
        return b.can_pay(b.player, card)

    def draw_alternate_hand(self):
        self.alternate_hits = []
        cards = self.battle.alternate_cards()
        if not cards:
            self.alternate_page = 0
            return
        self.alternate_page = min(self.alternate_page, (len(cards) - 1) // 3)
        self.text('PLAY FROM ZONE', 899, 706, (171, 211, 224), self.small)
        for i, card in enumerate(cards[self.alternate_page * 3:self.alternate_page * 3 + 3]):
            rect = pygame.Rect(900 + i * 31, 740 - i * 7, 106, 150)
            if self.animations:
                smoke = pygame.Surface((146, 190), pygame.SRCALPHA)
                time = pygame.time.get_ticks() / 1000
                for particle in range(12):
                    phase = (time * 0.32 + particle / 12) % 1
                    x = int(73 + math.sin(time + particle * 2.3) * (42 + phase * 15))
                    y = int(180 - phase * 170)
                    pygame.draw.circle(smoke, (135, 193, 224, int(60 * (1 - phase))), (x, y), int(9 + phase * 9))
                self.screen.blit(smoke, rect.move(-20, -20))
            else:
                self.glow(rect, (130, 170, 200))
            self.card_painter.draw(self.screen, card, rect, cost=self.battle.cost(self.battle.player, card),
                                   playable=self.can_drag(card), subtitle=self.battle.alternate_zone(card))
            self.alternate_hits.append((card, rect))
            if rect.collidepoint(self.mouse_pos()):
                self.hover = card
        if len(cards) > 3:
            self.button((900, 674, 35, 27), '<', lambda: self.change_alternate_page(-1), enabled=self.alternate_page > 0)
            self.button((942, 674, 35, 27), '>', lambda: self.change_alternate_page(1), enabled=(self.alternate_page + 1) * 3 < len(cards))

    def change_alternate_page(self, delta):
        self.alternate_page = max(0, self.alternate_page + delta)

    def adaptive_bloom_description(self, choice):
        return {
            'might': 'Might: +2/+2 this turn. An already morphed creature gets +3/+3 instead.',
            'insight': 'Insight: draw 1 card. Draw 2 instead if the target is already morphed.',
            'renewal': 'Renewal: gain 2 life. Gain 3 instead if the target is already morphed.'
        }[choice]

    def draw_commander(self):
        b = self.battle
        rect = pygame.Rect(1090, 686, 130, 150)
        self.commander_rect = rect if b.commander_zone == 'COMMAND' else None
        card = b.commander
        if b.commander_zone == 'COMMAND':
            self.text('COMMANDER', rect.x, rect.y - 22, (245, 206, 105), self.small)
            self.card_painter.draw(self.screen, card, rect, cost=b.cost(b.player, card),
                                   playable=self.can_drag(card), subtitle='CLICK TO CAST')
        elif b.commander_zone == 'STACK':
            self.text('COMMANDER', rect.x, rect.y - 22, (245, 206, 105), self.small)
            pygame.draw.rect(self.screen, (20, 25, 39), rect, border_radius=10)
            pygame.draw.rect(self.screen, (110, 100, 130), rect, 1, border_radius=10)
            self.wrap('On stack', rect.x + 10, rect.y + 65, rect.w - 20)
        if rect.collidepoint(self.mouse_pos()) and b.commander_zone == 'COMMAND':
            self.hover = card
        active_y = 844
        if b.active == 'Adaptive Bloom' and self.pending == 'ACTIVE':
            hovered = None
            for i, (choice, label) in enumerate((('might', 'Might'), ('insight', 'Insight'), ('renewal', 'Renew'))):
                choice_rect = pygame.Rect(1020 + i * 78, active_y, 72, 38)
                self.button(choice_rect, label, lambda value=choice: self.choose_morph(value),
                            selected=self.morph_choice == choice)
                if choice_rect.collidepoint(self.mouse_pos()):
                    hovered = self.adaptive_bloom_description(choice)
            if hovered:
                tip = pygame.Rect(720, 742, 285, 90)
                pygame.draw.rect(self.screen, (17, 22, 31), tip, border_radius=8)
                pygame.draw.rect(self.screen, (245, 117, 199), tip, 2, border_radius=8)
                self.wrap(hovered, tip.x + 12, tip.y + 11, tip.w - 24, (238, 232, 242))

    def draw_response_stack(self):
        self.stack_hits = []
        b = self.battle
        panel = pygame.Rect(1050, 180, 205, 360)
        self.text(f'STACK  /  {len(b.stack)}', 1080, 158, (245, 206, 105), self.small)
        if not b.stack:
            return
        pygame.draw.rect(self.screen, (20, 25, 29), panel, border_radius=12)
        visible = b.stack[-4:]
        for i, item in enumerate(visible):
            rect = pygame.Rect(1060 + i * 5, 190 + i * 30, 170, 205)
            if item is b.stack[-1]:
                self.glow(rect)
            self.card_painter.draw(self.screen, item.card, rect, selected=item in self.valid_targets())
            self.stack_hits.append((item, rect))
            if rect.collidepoint(self.mouse_pos()):
                self.hover = item.card
            self.buttons.append((rect, lambda target=item: self.target(target) if self.pending else None))
        top = b.stack[-1]
        owner = 'You' if top.side is b.player else 'Enemy'
        target = getattr(top.target, 'name', getattr(getattr(top.target, 'card', None), 'name', 'No target'))
        self.screen.blit(fitted(f'NEXT: {owner} / {target}', 190, 13, (115, 225, 250)), (1060, 488))
        self.button((1060, 510, 185, 30), 'Inspect / choose target', lambda: self.set_state('STACK'))

    def drop_target(self, pos):
        # Only exposed stack cards can be targeted; the full inspector handles deeper stacks.
        for item, rect in reversed(self.stack_hits):
            if rect.collidepoint(pos):
                return item
        for side, rect in [(self.battle.enemy, self.hero_rect(False)),
                           (self.battle.player, self.hero_rect(True))]:
            if rect.collidepoint(pos):
                return side
        for card, rect in self.board_hits:
            if rect.collidepoint(pos):
                return card
        return None

    def finish_drag(self, pos):
        card = self.drag_card
        self.drag_card = None
        self.pending = None
        from_hand = self.drag_from_hand
        self.drag_from_hand = False
        if not card:
            return
        moved = self.drag_start is not None and pygame.Vector2(pos).distance_to(self.drag_start) >= 8
        if from_hand and moved:
            target = self.hand_at(pos)
            if target in self.battle.player.hand:
                if target is not card:
                    hand = self.battle.player.hand
                    target_index = hand.index(target)
                    hand.remove(card)
                    hand.insert(target_index, card)
                    self.message = f'Moved {card.name} to hand position {target_index + 1}.'
                return
        if not self.can_drag(card):
            self.message = 'Cannot play this card now: check mana, phase, or land play.'
            return
        targets = self.battle.cast_targets(card)
        if targets and self.drag_start is not None and pygame.Vector2(pos).distance_to(self.drag_start) < 8:
            self.pending = card
            self.message = f'{card.name}: click a highlighted target. Right-click to cancel.'
            return
        if self.battle.alternate_zone(card) and self.drag_start is not None and pygame.Vector2(pos).distance_to(self.drag_start) < 8:
            self.battle.play(card)
            return
        target = self.drop_target(pos)
        if targets:
            valid = target in targets
        else:
            valid = pygame.Rect(20, 145, 1005, 435).collidepoint(pos)
        if valid and self.battle.play(card, target if targets else None):
            self.message = ''
        else:
            self.message = 'Card returned to hand. Drop onto a highlighted target or the battlefield.'

    def draw_drag(self):
        if not self.drag_card:
            return
        pos = self.drag_pos
        if not self.battle.cast_targets(self.drag_card):
            pygame.draw.rect(self.screen, (100, 220, 240), (20, 145, 1005, 435), 3, border_radius=12)
        else:
            pygame.draw.line(self.screen, (110, 230, 255), (640, 805), pos, 3)
            pygame.draw.circle(self.screen, (110, 230, 255), pos, 12, 2)
        rect = pygame.Rect(pos[0] + 18, pos[1] - 80, 125, 180)
        self.card_painter.draw(self.screen, self.drag_card, rect, selected=True,
                               cost=self.battle.cost(self.battle.player, self.drag_card))

    def card_input(self, event):
        if self.drag_card and (event.type == pygame.WINDOWFOCUSLOST or self.state != 'BATTLE'):
            self.drag_card = None
            self.drag_from_hand = False
            self.pending = None
        if self.state != 'BATTLE' or self.battle.phase == 'MULLIGAN':
            return False
        if self.drag_card:
            if event.type == pygame.MOUSEMOTION:
                self.drag_pos = self.to_logical(event.pos)
                return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.finish_drag(self.to_logical(event.pos))
                return True
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
                self.drag_card = self.pending = None
                self.drag_from_hand = False
                return True
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (getattr(self, 'commander_rect', None) and self.commander_rect.collidepoint(self.to_logical(event.pos))
                    and self.battle.commander_zone == 'COMMAND'):
                card = self.battle.commander
                if self.can_drag(card):
                    self.battle.play(card)
                    self.message = ''
                else:
                    self.message = f'Commander needs {card.mana_label(self.battle.cost(self.battle.player, card))} and your main phase.'
                return True
            pos = self.to_logical(event.pos)
            alternate = next((card for card, rect in reversed(self.alternate_hits) if rect.collidepoint(pos)), None)
            hand_card = None if alternate else self.hand_at(pos)
            card = alternate or hand_card
            if card:
                # Every hand card may be picked up for sorting. Cards from other
                # zones still require a legal play before they can be dragged.
                if hand_card or self.can_drag(card):
                    self.drag_card = self.pending = card
                    self.drag_from_hand = bool(hand_card)
                    self.drag_pos = self.to_logical(event.pos)
                    self.drag_start = self.drag_pos
                    self.hover = None
                else:
                    self.message = 'Cannot play this card now: check mana, phase, or land play.'
                return True
        return False
