"""Unlimited battlefield presentation with homogeneous token piles."""
import math
import time
import pygame


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
        if self.pending or getattr(self.battle, 'pending_entry', None) or self.battle.phase != 'MAIN' or self.battle.result:
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
        b = self.battle
        targets = self.valid_targets()
        for friendly, side, y in [(False, b.enemy, 230), (True, b.player, 420)]:
            groups = self.board_groups(side)
            last_page = max(0, (len(groups) - 1) // 7)
            page = min(self.board_pages.get(friendly, 0), last_page)
            self.board_pages[friendly] = page
            visible = groups[page * 7:page * 7 + 7]
            start_x = 40 + (7 - len(visible)) * 139 // 2
            for i, group in enumerate(visible):
                card = group[0]
                attacking = card in self.chosen or card in b.attackers
                rect = pygame.Rect(start_x + 139 * i, y, 126, 126)
                started = getattr(card, 'attack_animation_started', 0)
                elapsed = time.monotonic() - started if started else 99
                if elapsed < .55:
                    pulse = math.sin(elapsed / .55 * math.pi)
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
                      and not b.active_used and not b.stack):
                    subtitle = 'CLICK: ACTIVE'
                for attacker, blockers in b.assignments.items():
                    if card in blockers:
                        subtitle = f'#{b.attackers.index(attacker) + 1} / order {blockers.index(card) + 1}'
                if card in self.blockers:
                    subtitle = 'SELECTED BLOCKER'
                rect = self.battlefield_card(card, rect, selected=card in targets or attacking or card in self.blockers, subtitle=subtitle)
                self.buttons.append((rect, lambda c=card, f=friendly: self.click_creature(c, f)))
                if attacking:
                    pygame.draw.rect(self.screen, (90, 210, 255) if friendly else (255, 133, 106), rect.inflate(4, 4), 2, border_radius=8)
                self.board_hits.append((card, rect))
                if len(group) > 1:
                    badge = pygame.Rect(rect.right - 49, rect.top - 9, 49, 25)
                    pygame.draw.rect(self.screen, (12, 26, 43), badge, border_radius=6)
                    pygame.draw.rect(self.screen, (115, 211, 255), badge, 1, border_radius=6)
                    self.text(f'x{len(group)}', badge.x + 5, badge.y + 2, font=self.small)
                    if friendly and b.phase == 'MAIN' and not self.pending:
                        self.buttons.append((badge, lambda cards=tuple(group): self.select_pile(cards)))
            if last_page:
                self.button((950, y - 32, 35, 27), '<', lambda f=friendly: self.board_page(f, -1), enabled=page > 0)
                self.button((990, y - 32, 35, 27), '>', lambda f=friendly: self.board_page(f, 1), enabled=page < last_page)
                self.text(f'{len(side.board)} creatures / page {page + 1}', 760, y - 27, font=self.small)
        # Use the actual visible targets, including blocker assignments.
        positions = dict(self.board_hits)
        entry_source = getattr(b, 'pending_entry', None)
        if entry_source in positions:
            start = positions[entry_source].midtop
            end = self.mouse_pos()
            pygame.draw.line(self.screen, (26, 20, 45), start, end, 8)
            pygame.draw.line(self.screen, (210, 115, 255), start, end, 3)
            pygame.draw.circle(self.screen, (235, 155, 255), end, 12, 3)
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
