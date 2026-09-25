"""Unlimited battlefield presentation with homogeneous token piles."""
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
                   card is self.blocker)
            if not card.token or separate:
                key = (id(card),)
            groups.setdefault(key, []).append(card)
        return list(groups.values())

    def select_pile(self, cards):
        if self.pending or self.battle.phase != 'MAIN' or self.battle.result:
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
        arrow = (975, 350)
        for friendly, side, y in [(False, b.enemy, 137), (True, b.player, 387)]:
            groups = self.board_groups(side)
            last_page = max(0, (len(groups) - 1) // 7)
            page = min(self.board_pages.get(friendly, 0), last_page)
            self.board_pages[friendly] = page
            for i, group in enumerate(groups[page * 7:page * 7 + 7]):
                card = group[0]
                attacking = card in self.chosen or card in b.attackers
                rect = pygame.Rect(25 + 139 * i, y, 130, 170)
                if attacking:
                    color = (85, 204, 255) if friendly else (255, 133, 106)
                    self.glow(rect, color)
                    start = (rect.centerx, rect.top if friendly else rect.bottom)
                    bend = ((start[0] + arrow[0]) // 2, 345 if friendly else 335)
                    pygame.draw.lines(self.screen, (22, 76, 105), False, [start, bend, arrow], 7)
                    pygame.draw.lines(self.screen, color, False, [start, bend, arrow], 2)
                    pygame.draw.polygon(self.screen, color, [(arrow[0] - 12, arrow[1] - 7), arrow,
                                                            (arrow[0] - 12, arrow[1] + 7)])
                for layer in range(min(3, len(group) - 1), 0, -1):
                    pygame.draw.rect(self.screen, (18, 30, 47), rect.move(layer * 3, -layer * 3), border_radius=8)
                    pygame.draw.rect(self.screen, (142, 160, 177), rect.move(layer * 3, -layer * 3), 1, border_radius=8)
                subtitle = 'ATTACKING' if attacking else ''
                if card in b.attackers:
                    subtitle = f'Attack #{b.attackers.index(card) + 1}'
                for attacker, blockers in b.assignments.items():
                    if card in blockers:
                        subtitle = f'#{b.attackers.index(attacker) + 1} / order {blockers.index(card) + 1}'
                self.card(card, rect, lambda c=card, f=friendly: self.click_creature(c, f),
                          selected=card in targets or attacking or card is self.blocker, subtitle=subtitle)
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
                self.button((25, y + 175, 75, 27), '<', lambda f=friendly: self.board_page(f, -1), enabled=page > 0)
                self.button((110, y + 175, 75, 27), '>', lambda f=friendly: self.board_page(f, 1), enabled=page < last_page)
                self.text(f'{len(side.board)} creatures / {len(groups)} piles / page {page + 1}', 205, y + 179, font=self.small)
