"""Unlimited battlefield presentation with homogeneous token piles."""
import math
import time
import pygame
from art import fitted


class BattlefieldPiles:
    def board_groups(self, side):
        groups = {}
        b = self.battle
        for card in side.board:
            assignment = next(((id(a), group.index(card)) for a, group in b.assignments.items() if card in group), None)
            # Assigned attackers/blockers are individual so combat ordering stays explicit.
            in_combat = card in b.attackers
            separate = assignment is not None or bool(b.assignments.get(card))
            key = (card.name, card.card_type, card.color_code, card.mana_cost, card.text,
                   card.attack, card.max_health, card.current_health, card.upgraded,
                   card.temp_attack, card.temp_health, card.tapped, card.sick,
                   tuple(sorted(getattr(card, 'keywords', []))), getattr(card, 'frozen', False),
                   getattr(card, 'exile_at_end', False), card in self.chosen, in_combat,
                   card in self.blockers)
            if not card.token or separate:
                key = (id(card),)
            groups.setdefault(key, []).append(card)
        return list(groups.values())

    def select_pile(self, cards):
        if self.pending or getattr(self.battle, 'pending_entry', None) or self.battle.phase != 'COMBAT' or self.battle.result:
            return
        ready = {c for c in cards if c in self.battle.player.board and not c.tapped and not c.sick}
        if ready and ready.issubset(self.chosen):
            self.chosen.difference_update(ready)
        else:
            self.chosen.update(ready)

    def board_page(self, friendly, delta):
        self.board_pages[friendly] = max(0, self.board_pages.get(friendly, 0) + delta)

    def draw_battlefield(self):
        if not hasattr(self, 'board_pages'):
            self.board_pages = {}
        self.board_hits = []
        self.commander_active_rect = None
        b = self.battle
        targets = self.valid_targets()
        for friendly, side, y in [(False, b.enemy, 230), (True, b.player, 420)]:
            groups = self.board_groups(side)
            per_page = 14
            last_page = max(0, (len(groups) - 1) // per_page)
            page = min(self.board_pages.get(friendly, 0), last_page)
            self.board_pages[friendly] = page
            visible = groups[page * per_page:page * per_page + per_page]
            compact = len(visible) > 7
            columns = min(7, len(visible))
            card_size = 94 if compact else 126
            column_step = 112 if compact else 139
            row_step = 96
            # Two compact rows fit inside each half of the arena. A normal
            # seven-card row stays at the larger, more readable size.
            base_y = (193 if not friendly else 386) if compact else y
            start_x = (1280 - (columns - 1) * column_step - card_size) // 2
            for i, group in enumerate(visible):
                card = group[0]
                attacking = card in self.chosen or card in b.attackers
                row, column = divmod(i, 7)
                row_count = min(7, len(visible) - row * 7)
                row_x = (1280 - (row_count - 1) * column_step - card_size) // 2
                rect = pygame.Rect(row_x + column_step * column, base_y + row * row_step,
                                   card_size, card_size)
                started = getattr(card, 'attack_animation_started', 0)
                elapsed = time.monotonic() - started if started else 99
                attack_time = {'fast': .3, 'normal': .55, 'cinematic': .9}.get(self.animation_speed, 0)
                if attack_time and elapsed < attack_time:
                    pulse = math.sin(elapsed / attack_time * math.pi)
                    rect.y += round((-55 if friendly else 55) * pulse)
                if attacking:
                    color = (85, 204, 255) if friendly else (255, 133, 106)
                    self.glow(rect, color)
                for layer in range(min(3, len(group) - 1), 0, -1):
                    pygame.draw.rect(self.screen, (18, 30, 47), rect.move(layer * 3, -layer * 3), border_radius=8)
                    pygame.draw.rect(self.screen, (142, 160, 177), rect.move(layer * 3, -layer * 3), 1, border_radius=8)
                subtitle = 'SELECTED' if card in self.chosen and card not in b.attackers else 'ATTACKING' if attacking else ''
                if card in b.attackers:
                    subtitle = f'Attack #{b.attackers.index(card) + 1}'
                elif (card is b.commander and friendly and b.phase in ('MAIN', 'MAIN2')
                      and b.active and not b.active_used and not b.stack):
                    subtitle = 'ABILITY READY'
                for attacker, blockers in b.assignments.items():
                    if card in blockers:
                        subtitle = f'#{b.attackers.index(attacker) + 1} / order {blockers.index(card) + 1}'
                if card in self.blockers:
                    subtitle = 'SELECTED BLOCKER'
                rect = self.battlefield_card(card, rect, selected=card in targets or attacking or card in self.blockers, subtitle=subtitle)
                if card in targets:
                    number = targets.index(card) + 1
                    pulse = 3 + int((math.sin(time.monotonic() * 7) + 1) * 2)
                    pygame.draw.rect(self.screen, (105, 232, 255), rect.inflate(8, 8), pulse, border_radius=11)
                    badge = pygame.Rect(rect.left - 8, rect.top - 10, 27, 27)
                    pygame.draw.ellipse(self.screen, (18, 31, 43), badge)
                    pygame.draw.ellipse(self.screen, (105, 232, 255), badge, 2)
                    self.text(str(number), badge.x + 9, badge.y + 3, (220, 250, 255), self.small)
                self.buttons.append((rect, lambda c=card, f=friendly: self.click_creature(c, f)))
                if (card is b.commander and friendly and b.phase in ('MAIN', 'MAIN2')
                        and b.active and not b.active_used and not b.stack and b.commander_zone == 'BOARD'):
                    ability = pygame.Rect(rect.right - 30, rect.top + 24, 27, 27)
                    self.commander_active_rect = ability
                    pygame.draw.circle(self.screen, (16, 20, 27), ability.center, 14)
                    pygame.draw.circle(self.screen, (245, 206, 105), ability.center, 13, 2)
                    self.text('A', ability.x + 8, ability.y + 3, (245, 206, 105), self.small)
                    self.buttons.append((ability, self.active))
                    if ability.collidepoint(self.mouse_pos()):
                        self.message = f'{b.active}: {b.run.commander.active}'
                if attacking:
                    pygame.draw.rect(self.screen, (90, 210, 255) if friendly else (255, 133, 106), rect.inflate(4, 4), 2, border_radius=8)
                self.board_hits.append((card, rect))
                if len(group) > 1:
                    badge = pygame.Rect(rect.right - 49, rect.top - 9, 49, 25)
                    pygame.draw.rect(self.screen, (12, 26, 43), badge, border_radius=6)
                    pygame.draw.rect(self.screen, (115, 211, 255), badge, 1, border_radius=6)
                    self.text(f'x{len(group)}', badge.x + 5, badge.y + 2, font=self.small)
                    if friendly and b.phase == 'COMBAT' and not self.pending:
                        self.buttons.append((badge, lambda cards=tuple(group): self.select_pile(cards)))
            if last_page:
                pager_y = (base_y - 30) if not friendly else (base_y + (row_step if compact else 0) + card_size + 3)
                self.button((950, pager_y, 35, 27), '<', lambda f=friendly: self.board_page(f, -1), enabled=page > 0)
                self.button((990, pager_y, 35, 27), '>', lambda f=friendly: self.board_page(f, 1), enabled=page < last_page)
                self.text(f'{len(side.board)} creatures / page {page + 1}', 760, pager_y + 4, font=self.small)
        # Use the actual visible targets, including blocker assignments.
        positions = dict(self.board_hits)
        entry_source = getattr(b, 'pending_entry', None)
        if entry_source in positions:
            start = positions[entry_source].midtop
            end = self.mouse_pos()
            pygame.draw.line(self.screen, (26, 20, 45), start, end, 8)
            pygame.draw.line(self.screen, (210, 115, 255), start, end, 3)
            pygame.draw.circle(self.screen, (235, 155, 255), end, 12, 3)
            direction = pygame.Vector2(end) - pygame.Vector2(start)
            if direction.length_squared() > 1:
                direction.scale_to_length(14)
                normal = pygame.Vector2(-direction.y, direction.x) * .5
                pygame.draw.polygon(self.screen, (235, 155, 255),
                                    [end, pygame.Vector2(end) - direction + normal,
                                     pygame.Vector2(end) - direction - normal])
            self.screen.blit(fitted(f'{entry_source.name} ETB: CHOOSE TARGET', 270, 12, (238, 178, 255)),
                             (start[0] - 100, start[1] - 26))
        for card, rect in self.board_hits:
            if card not in self.chosen and card not in b.attackers:
                continue
            friendly = card in b.player.board
            start = rect.midtop if friendly else rect.midbottom
            blockers = b.assignments.get(card, [])
            ends = [(positions[c].midbottom if friendly else positions[c].midtop)
                    for c in blockers if c in positions]
            if not blockers and (card in self.chosen or card not in b.blocked or b.has_keyword(card, 'trample')):
                hero = self.hero_rect(not friendly)
                ends.append(hero.midbottom if friendly else hero.midtop)
            color = (85, 204, 255) if friendly else (255, 133, 106)
            for end in ends:
                pygame.draw.line(self.screen, (22, 48, 55), start, end, 6)
                pygame.draw.line(self.screen, color, start, end, 2)
                direction = pygame.Vector2(end) - pygame.Vector2(start)
                direction.scale_to_length(12)
                normal = pygame.Vector2(-direction.y, direction.x) * 0.5
                pygame.draw.polygon(self.screen, color, [end, pygame.Vector2(end) - direction + normal,
                                                        pygame.Vector2(end) - direction - normal])
