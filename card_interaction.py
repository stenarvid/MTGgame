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
        self.stack_animation_times = {}
        self.stack_previous = {}
        self.stack_departures = []

    def hand_layout(self):
        cards = self.battle.player.hand[self.hand_page * 9:self.hand_page * 9 + 9]
        step = min(100, 550 / max(1, len(cards) - 1))
        middle = (len(cards) - 1) / 2
        return [(card, (500 + (i - middle) * step, 817 + abs(i - middle) ** 2 * 1.5),
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
            subtitle = ('PLAY LAND' if card.card_type == 'Land' and self.can_drag(card) else
                        'LAND USED' if card.card_type == 'Land' and self.battle.player.land_played else '')
            self.card_painter.draw(face, card, (0, 0, 146, 210),
                                   cost=self.battle.cost(self.battle.player, card),
                                   selected=card in self.chosen,
                                   playable=self.can_drag(card),
                                   subtitle=('SELECTED TO DISCARD' if card in self.chosen and self.battle.phase == 'DISCARD'
                                             else subtitle))
            # rotozoom applies filtered rotation; transform.rotate leaves visibly
            # stair-stepped borders on the shallow angles used by the hand fan.
            face = pygame.transform.rotozoom(face, angle, 1.0)
            rect = face.get_rect(center=center)
            rendered.append((card, face, rect))
        self.hand_hits = [(card, rect, pygame.mask.from_surface(face)) for card, face, rect in rendered]
        hovered = self.hand_at(self.mouse_pos()) if not self.drag_card else None
        if not hovered and not self.drag_card and self.lifted_rect and self.lifted_rect.collidepoint(self.mouse_pos()):
            hovered = self.hand_hover if self.hand_hover in self.battle.player.hand else None
        self.lifted_rect = None
        self.hand_hover = hovered
        zoomed = hovered and pygame.key.get_pressed()[self.inspect_key]
        for visible_index, (card, face, rect) in enumerate(rendered, 1):
            if card is not self.drag_card and card is not hovered:
                if card.card_type == 'Land' and self.can_drag(card):
                    self.glow(rect, (95, 235, 155))
                self.screen.blit(face, rect)
                badge = pygame.Rect(rect.left + 5, rect.top + 5, 22, 22)
                pygame.draw.circle(self.screen, (9, 13, 19), badge.center, 11)
                pygame.draw.circle(self.screen, (224, 193, 117), badge.center, 10, 1)
                key = fitted(str(visible_index), 14, 11, (245, 232, 202))
                self.screen.blit(key, key.get_rect(center=badge.center))
        if zoomed:
            center = next(rect.centerx for card, _, rect in rendered if card is hovered)
            rect = pygame.Rect(center - 90, 658, 180, 252)
            self.lifted_rect = rect
            self.hand_hits.append((hovered, rect, pygame.mask.Mask(rect.size, fill=True)))
            self.glow(rect)
            self.card_painter.draw(self.screen, hovered, rect, selected=True,
                                   cost=self.battle.cost(self.battle.player, hovered))
            self.hover = hovered
        elif hovered:
            face, original = next((face, rect) for card, face, rect in rendered if card is hovered)
            raised = original.move(0, -42)
            if hovered.card_type == 'Land' and self.can_drag(hovered):
                self.glow(raised, (95, 235, 155))
            self.screen.blit(face, raised)
            self.lifted_rect = raised
            self.hand_hits.append((hovered, raised, pygame.mask.from_surface(face)))
            self.hover = hovered
        if hovered and not self.drag_card:
            discarding = self.battle.phase == 'DISCARD'
            legal = self.can_drag(hovered)
            status = 'PLAYABLE — click or drag to play' if legal else self.cannot_play_reason(hovered)
            if discarding:
                status = 'Click to select or deselect this card for discard'
            color = (245, 206, 105) if discarding else (111, 235, 167) if legal else (235, 164, 132)
            panel = pygame.Rect(315, 682, 445, 28)
            pygame.draw.rect(self.screen, (10, 15, 22), panel, border_radius=8)
            pygame.draw.rect(self.screen, color, panel, 1, border_radius=8)
            label = fitted(status, panel.w - 20, 12, color)
            self.screen.blit(label, label.get_rect(center=panel.center))
        start = self.hand_page * 9
        self.button((18, 850, 55, 36), '<', lambda: self.change_hand_page(-1), enabled=self.hand_page > 0)
        self.button((850, 850, 55, 36), '>', lambda: self.change_hand_page(1),
                    enabled=start + 9 < len(self.battle.player.hand))
        self.text(f'HAND  {len(self.battle.player.hand)}  •  PAGE {self.hand_page + 1}', 20, 813,
                  (220, 207, 174), self.small)

    def can_drag(self, card):
        b = self.battle
        command = card is b.commander and b.commander_zone == 'COMMAND'
        if b.result or (card not in b.player.hand and not command and not b.alternate_zone(card)):
            return False
        if b.phase not in ('MAIN', 'MAIN2') and not (card.card_type == 'Instant Spell' and b.phase in
                ('COMBAT', 'RESPONSE', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE')):
            return False
        if card.card_type == 'Land':
            return not b.player.land_played
        return b.can_pay(b.player, card)

    def cannot_play_reason(self, card):
        b = self.battle
        command = card is b.commander and b.commander_zone == 'COMMAND'
        if b.result:
            return 'The battle is already over.'
        if card not in b.player.hand and not command and not b.alternate_zone(card):
            return 'This card is not in a playable zone.'
        instant = card.card_type == 'Instant Spell'
        if b.phase not in ('MAIN', 'MAIN2') and not (instant and b.phase in
                ('COMBAT', 'RESPONSE', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE')):
            return 'This card requires your main phase.' if not instant else 'You do not have priority now.'
        if card.card_type == 'Land' and b.player.land_played:
            return 'You already played a land this turn.'
        if card.card_type != 'Land' and not b.can_pay(b.player, card):
            return f'Not enough mana for {card.mana_label(b.cost(b.player, card))}. Available: {b.mana_summary(b.player)}.'
        return 'There are no legal targets.' if not b.cast_targets(card) and 'target' in card.text.lower() else 'This card cannot be played now.'

    def draw_alternate_hand(self):
        self.alternate_hits = []
        cards = self.battle.alternate_cards()
        reserve = []
        seen_colors = set()
        if self.battle.phase in ('MAIN', 'MAIN2'):
            for card in getattr(self.battle.player, 'land_reserve', []):
                if card.color_code not in seen_colors:
                    seen_colors.add(card.color_code)
                    reserve.append(card)
        cards += reserve
        if not cards:
            self.alternate_page = 0
            return
        per_page = 2
        self.alternate_page = min(self.alternate_page, (len(cards) - 1) // per_page)
        reserve_count = len(getattr(self.battle.player, 'land_reserve', []))
        plays = getattr(self.battle.player, 'land_plays_remaining', int(not self.battle.player.land_played))
        heading = (f'LAND RESERVE  {reserve_count}  /  PLAYS {plays}' if reserve
                   else 'PLAY FROM GRAVEYARD / EXILE')
        self.screen.blit(fitted(heading, 220, 13, (210, 194, 145)), (900, 706))
        visible = cards[self.alternate_page * per_page:self.alternate_page * per_page + per_page]
        for i, card in enumerate(visible):
            rect = pygame.Rect(900 + i * 110, 738, 106, 150)
            zone = self.battle.alternate_zone(card)
            if self.animations and zone != 'LAND RESERVE':
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
                                   playable=self.can_drag(card), subtitle=zone)
            if zone == 'LAND RESERVE':
                copies = sum(other.color_code == card.color_code
                             for other in self.battle.player.land_reserve)
                badge = pygame.Rect(rect.right - 33, rect.top - 8, 34, 24)
                pygame.draw.rect(self.screen, (12, 17, 23), badge, border_radius=7)
                pygame.draw.rect(self.screen, (230, 206, 143), badge, 1, border_radius=7)
                count = fitted(f'x{copies}', 27, 11, (245, 232, 202))
                self.screen.blit(count, count.get_rect(center=badge.center))
            self.alternate_hits.append((card, rect))
            if rect.collidepoint(self.mouse_pos()):
                self.hover = card
        if len(cards) > per_page:
            self.button((900, 674, 35, 27), '<', lambda: self.change_alternate_page(-1), enabled=self.alternate_page > 0)
            self.button((942, 674, 35, 27), '>', lambda: self.change_alternate_page(1), enabled=(self.alternate_page + 1) * per_page < len(cards))

    def change_alternate_page(self, delta):
        self.alternate_page = max(0, self.alternate_page + delta)

    def adaptive_bloom_description(self, choice):
        return {
            'might': 'Warform — Target gets +2/+2 this turn. If already morphed, it gets +3/+3.',
            'insight': 'Mindform — Draw 1 card. If the target is already morphed, Draw 2 instead.',
            'renewal': 'Lifebloom — Gain 2 life. If the target is already morphed, Gain 3 instead.'
        }[choice]

    def draw_commander(self):
        b = self.battle
        rect = pygame.Rect(1130, 686, 120, 150)
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
            for i, (choice, label) in enumerate((('might', 'War'), ('insight', 'Mind'), ('renewal', 'Life'))):
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
        now = pygame.time.get_ticks()
        current_ids = {id(item) for item in b.stack}
        for key, (card, rect) in list(self.stack_previous.items()):
            if key not in current_ids:
                self.stack_departures.append((card, rect.copy(), now))
        self.stack_departures = [row for row in self.stack_departures if now - row[2] < 520]
        for card, old_rect, born in self.stack_departures:
            progress = (now - born) / 520
            ghost = pygame.Surface(old_rect.size, pygame.SRCALPHA)
            ghost.set_alpha(max(0, int(210 * (1 - progress))))
            self.card_painter.draw(ghost, card, ghost.get_rect())
            moved = old_rect.move(int(progress * 75), -int(progress * 95))
            self.screen.blit(ghost, moved)
        if not b.stack:
            self.stack_previous = {}
            return
        pygame.draw.rect(self.screen, (20, 25, 29), panel, border_radius=12)
        visible = b.stack[-4:]
        legal = self.valid_targets()
        for i, item in enumerate(visible):
            rect = pygame.Rect(1060 + i * 5, 190 + i * 30, 170, 205)
            self.stack_animation_times.setdefault(id(item), now)
            progress = min(1, (now - self.stack_animation_times[id(item)]) / 380)
            rect.y += int((1 - (1 - progress) ** 3) * -110 + 110)
            if item in legal:
                self.glow(rect, (105, 232, 255))
            elif item is b.stack[-1]:
                self.glow(rect)
            self.card_painter.draw(self.screen, item.card, rect, selected=item in legal,
                                   subtitle='LEGAL TARGET' if item in legal else '')
            if item is b.stack[-1]:
                pulse = 2 + int((math.sin(now / 150) + 1) * 2)
                pygame.draw.rect(self.screen, (250, 211, 135), rect.inflate(5 + pulse, 5 + pulse),
                                 2, border_radius=12)
            if item in legal:
                pulse = 2 + int((math.sin(pygame.time.get_ticks() / 120) + 1) * 2)
                pygame.draw.rect(self.screen, (105, 232, 255), rect.inflate(8, 8), pulse, border_radius=12)
                badge = pygame.Rect(rect.left - 9, rect.top - 10, 29, 29)
                pygame.draw.ellipse(self.screen, (18, 31, 43), badge)
                pygame.draw.ellipse(self.screen, (105, 232, 255), badge, 2)
                self.text(str(legal.index(item) + 1), badge.x + 9, badge.y + 4, (220, 250, 255), self.small)
            self.stack_hits.append((item, rect))
            if rect.collidepoint(self.mouse_pos()):
                self.hover = item.card
            self.buttons.append((rect, lambda target=item: self.target(target) if self.pending else None))
        self.stack_previous = {id(item): (item.card, rect) for item, rect in self.stack_hits}
        self.stack_animation_times = {key: value for key, value in self.stack_animation_times.items()
                                      if key in current_ids}
        top = b.stack[-1]
        owner = 'You' if top.side is b.player else 'Enemy'
        target = getattr(top.target, 'name', getattr(getattr(top.target, 'card', None), 'name', 'No target'))
        self.screen.blit(fitted(f'NEXT: {owner} / {target}', 190, 13, (115, 225, 250)), (1060, 488))
        self.button((1060, 510, 185, 30), 'Inspect / choose target', lambda: self.set_state('STACK'))

    def draw_targeting_overlay(self):
        targets = self.valid_targets()
        if not targets or not self.pending:
            return
        start = (640, 790)
        if self.pending not in (None, 'ACTIVE'):
            hit = next((rect for card, rect, _ in self.hand_hits if card is self.pending), None)
            if hit:
                start = hit.midtop
        end = self.mouse_pos()
        pulse = 2 + int((math.sin(pygame.time.get_ticks() / 130) + 1) * 2)
        pygame.draw.line(self.screen, (20, 47, 62), start, end, 8)
        pygame.draw.line(self.screen, (105, 232, 255), start, end, pulse)
        pygame.draw.circle(self.screen, (105, 232, 255), end, 11, 2)
        self.screen.blit(fitted(f'{len(targets)} LEGAL TARGETS', 180, 12, (190, 245, 255)),
                         (start[0] - 85, start[1] - 25))

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
            self.message = self.cannot_play_reason(card)
            return
        targets = self.battle.cast_targets(card)
        if targets and self.drag_start is not None and pygame.Vector2(pos).distance_to(self.drag_start) < 8:
            self.pending = card
            self.message = f'{card.name}: click a highlighted target. Right-click to cancel.'
            return
        if from_hand and not moved and not targets:
            if self.battle.play(card):
                self.message = ''
            else:
                self.message = self.cannot_play_reason(card)
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
                    self.message = self.cannot_play_reason(card)
                return True
            pos = self.to_logical(event.pos)
            alternate = next((card for card, rect in reversed(self.alternate_hits) if rect.collidepoint(pos)), None)
            hand_card = None if alternate else self.hand_at(pos)
            card = alternate or hand_card
            if card:
                if hand_card and self.battle.phase == 'DISCARD':
                    if card in self.chosen:
                        self.chosen.remove(card)
                    elif len(self.chosen) < self.battle.required_discards():
                        self.chosen.add(card)
                    return True
                # Every hand card may be picked up for sorting. Cards from other
                # zones still require a legal play before they can be dragged.
                if hand_card or self.can_drag(card):
                    self.drag_card = self.pending = card
                    self.drag_from_hand = bool(hand_card)
                    self.drag_pos = self.to_logical(event.pos)
                    self.drag_start = self.drag_pos
                    self.hover = None
                else:
                    self.message = self.cannot_play_reason(card)
                return True
        return False
