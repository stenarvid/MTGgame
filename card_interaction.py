"""Fanned hand, drag casting, and an in-battle response stack."""
import pygame
from art import fitted


class CardInteraction:
    def init_card_interaction(self):
        self.drag_card = None
        self.drag_pos = (0, 0)
        self.hand_hits = []
        self.stack_hits = []
        self.hand_hover = None
        self.lifted_rect = None

    def hand_layout(self):
        cards = self.battle.player.hand[self.hand_page * 9:self.hand_page * 9 + 9]
        step = min(115, 780 / max(1, len(cards) - 1))
        middle = (len(cards) - 1) / 2
        return [(card, (640 + (i - middle) * step, 790 + abs(i - middle) ** 2 * 2),
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
        self.button((1207, 850, 55, 36), '>', lambda: self.change_hand_page(1),
                    enabled=start + 9 < len(self.battle.player.hand))
        self.text(f'Hand {len(self.battle.player.hand)} / page {self.hand_page + 1}', 20, 818, font=self.small)

    def can_drag(self, card):
        b = self.battle
        if b.result or card not in b.player.hand:
            return False
        if b.phase not in ('MAIN', 'MAIN2') and not (card.card_type == 'Instant Spell' and b.phase in
                ('RESPONSE', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE')):
            return False
        if card.card_type == 'Land':
            return not b.player.land_played
        return b.can_pay(b.player, card)

    def draw_response_stack(self):
        self.stack_hits = []
        b = self.battle
        panel = pygame.Rect(1008, 132, 255, 440)
        pygame.draw.rect(self.screen, (20, 25, 39), panel, border_radius=12)
        self.text(f'STACK  /  {len(b.stack)}', 1022, 140, (245, 206, 105), self.small)
        if not b.stack:
            self.wrap('Spells appear here. Newest resolves first.', 1030, 207, 207)
            return
        visible = b.stack[-4:]
        for i, item in enumerate(visible):
            rect = pygame.Rect(1022 + i * 10, 173 + i * 38, 194, 220)
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
        self.screen.blit(fitted(f'NEXT: {owner} / {"Ability" if hasattr(top, "ability") else "Spell"} / {target}', 226, 13, (115, 225, 250)), (1022, 515))
        self.button((1020, 540, 230, 32), 'Inspect all / choose target', lambda: self.set_state('STACK'))

    def drop_target(self, pos):
        # Only exposed stack cards can be targeted; the full inspector handles deeper stacks.
        for item, rect in reversed(self.stack_hits):
            if rect.collidepoint(pos):
                return item
        for side, rect in [(self.battle.enemy, pygame.Rect(25, 59, 595, 42)),
                           (self.battle.player, pygame.Rect(650, 59, 595, 42))]:
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
        if not card or not self.can_drag(card):
            return
        targets = self.battle.targets(card.name)
        target = self.drop_target(pos)
        if targets:
            valid = target in targets
        else:
            valid = pygame.Rect(20, 128, 978, 449).collidepoint(pos)
        if valid and self.battle.play(card, target if targets else None):
            self.message = ''
        else:
            self.message = 'Card returned to hand. Drop onto a highlighted target or the battlefield.'

    def draw_drag(self):
        if not self.drag_card:
            return
        pos = self.drag_pos
        if not self.battle.targets(self.drag_card.name):
            pygame.draw.rect(self.screen, (100, 220, 240), (20, 128, 978, 449), 3, border_radius=12)
        else:
            pygame.draw.line(self.screen, (110, 230, 255), (640, 805), pos, 3)
            pygame.draw.circle(self.screen, (110, 230, 255), pos, 12, 2)
        rect = pygame.Rect(pos[0] + 18, pos[1] - 80, 125, 180)
        self.card_painter.draw(self.screen, self.drag_card, rect, selected=True,
                               cost=self.battle.cost(self.battle.player, self.drag_card))

    def card_input(self, event):
        if self.drag_card and (event.type == pygame.WINDOWFOCUSLOST or self.state != 'BATTLE'):
            self.drag_card = None
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
                return True
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            card = self.hand_at(self.to_logical(event.pos))
            if card:
                if self.can_drag(card):
                    self.drag_card = self.pending = card
                    self.drag_pos = self.to_logical(event.pos)
                    self.hover = None
                else:
                    self.message = 'Cannot play this card now: check mana, phase, or land play.'
                return True
        return False
