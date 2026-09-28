"""Compact battlefield presentation and shared visual/input geometry."""
import math
import time
import pygame
from art import PALETTES, draw_mana_glyph, fitted, font


class ArenaUI:
    def draw_battle_chrome(self):
        """Give every interactive battle region a stable visual home."""
        veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(veil, (6, 10, 18, 150), (0, 0, 1280, 102))
        pygame.draw.rect(veil, (7, 11, 19, 90), (15, 103, 1018, 445), border_radius=18)
        pygame.draw.rect(veil, (7, 11, 19, 185), (15, 551, 1000, 108), border_radius=14)
        pygame.draw.rect(veil, (6, 9, 16, 190), (15, 653, 1000, 45), border_radius=10)
        pygame.draw.rect(veil, (5, 8, 14, 145), (0, 699, 1280, 201))
        pygame.draw.rect(veil, (7, 11, 19, 170), (1037, 105, 228, 458), border_radius=16)
        self.screen.blit(veil, (0, 0))
        # Colored lane lighting makes ownership readable before labels are read.
        lanes = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        for i in range(70):
            strength = int(28 * (1 - i / 70) ** 2)
            pygame.draw.line(lanes, (190, 73, 64, strength), (25, 108 + i), (1022, 108 + i))
            pygame.draw.line(lanes, (65, 154, 190, strength), (25, 542 - i), (1022, 542 - i))
        self.screen.blit(lanes, (0, 0))
        for rect in ((15, 103, 1018, 445), (15, 551, 1000, 108), (1037, 105, 228, 458)):
            pygame.draw.rect(self.screen, (139, 120, 80), rect, 1, border_radius=16)
        self.screen.blit(fitted('OPPONENT FIELD', 170, 11, (205, 145, 129)), (35, 206))
        self.screen.blit(fitted('YOUR FIELD', 170, 11, (130, 199, 219)), (35, 516))
        # Central filigree and a quiet animated dust layer add depth.
        pygame.draw.line(self.screen, (66, 94, 105), (26, 401), (1005, 401), 1)
        pygame.draw.circle(self.screen, (20, 29, 37), (640, 401), 15)
        pygame.draw.circle(self.screen, (179, 153, 93), (640, 401), 14, 2)
        pygame.draw.circle(self.screen, (179, 153, 93), (640, 401), 4)
        if self.animations:
            t = pygame.time.get_ticks() / 1000
            for i in range(14):
                x = 45 + ((i * 89 + int(t * (7 + i % 4))) % 950)
                y = 125 + int((math.sin(t * .7 + i * 1.9) + 1) * 195)
                alpha = 35 + (i % 4) * 12
                pygame.draw.circle(self.screen, (224, 205, 146, alpha), (x, y), 1 + i % 2)
        pygame.draw.line(self.screen, (219, 185, 107), (28, 697), (1000, 697), 1)

    def draw_mana_status(self):
        """Compact, readable mana pool with the same glyphs used on cards."""
        side = self.battle.player
        x, y = 35, 637
        self.text('MANA', x, y - 2, (230, 213, 169), self.small)
        x += 52
        shown = False
        for symbol in 'WUBRGP':
            amount = side.colored_mana.get(symbol, 0)
            if not amount:
                continue
            shown = True
            accent = PALETTES[symbol]
            pygame.draw.circle(self.screen, (7, 10, 14), (x, y + 7), 13)
            pygame.draw.circle(self.screen, accent, (x, y + 7), 11)
            draw_mana_glyph(self.screen, symbol, (x, y + 7), 8)
            count = font(12, bold=True).render(str(amount), True, (246, 239, 219))
            self.screen.blit(count, (x + 13, y))
            x += 39
        if not shown:
            self.text('None', x, y - 2, (135, 132, 145), self.small)
            x += 42
        self.text(f'DECK {len(side.deck)}', x + 12, y - 2, (198, 194, 203), self.small)
        self.text(f'GRAVEYARD {len(side.discard)}', x + 87, y - 2, (198, 194, 203), self.small)

    def player_has_turn(self):
        phase = self.battle.return_phase if self.battle.phase == 'RESPONSE' else self.battle.phase
        return phase not in ('ENEMY_MAIN', 'BLOCK', 'DEFEND_RESPONSE', 'AFTER_ENEMY_COMBAT')

    def draw_turn_indicator(self):
        yours = self.player_has_turn()
        label = 'YOUR TURN' if yours else 'ENEMY TURN'
        color = (255, 220, 108) if yours else (255, 125, 105)
        dark = (63, 48, 20) if yours else (67, 27, 27)
        now = pygame.time.get_ticks()
        key = (yours, self.battle.turn, self.battle.enemy_turn_number)
        if key != self.turn_banner_key:
            self.turn_banner_key = key
            self.turn_banner_started = now

        panel = pygame.Rect(472, 15, 236, 48)
        pygame.draw.rect(self.screen, (15, 19, 26), panel, border_radius=12)
        pygame.draw.rect(self.screen, dark, panel.inflate(-5, -5), border_radius=9)
        pygame.draw.rect(self.screen, color, panel, 3, border_radius=12)
        title = font(22, serif=True, bold=True).render(label, True, color)
        self.screen.blit(title, title.get_rect(center=panel.center))

        elapsed = now - self.turn_banner_started
        if self.animations and elapsed < 1050:
            progress = elapsed / 1050
            alpha = int(235 * (1 - max(0, (progress - .55) / .45)))
            scale = 1 + .12 * math.sin(min(1, progress) * math.pi)
            banner = pygame.Surface((620, 125), pygame.SRCALPHA)
            pygame.draw.rect(banner, (10, 14, 22, int(alpha * .88)), banner.get_rect(), border_radius=22)
            pygame.draw.rect(banner, (*color, alpha), banner.get_rect(), 4, border_radius=22)
            large = font(round(42 * scale), serif=True, bold=True).render(label, True, (*color, alpha))
            banner.blit(large, large.get_rect(center=banner.get_rect().center))
            self.screen.blit(banner, banner.get_rect(center=(640, 360)))

    def draw_enemy_intent(self):
        b = self.battle
        ready = [c for c in b.enemy.board if not c.tapped and c.attack > 0]
        projected_mana = len(b.enemy.lands) + sum(2 for c in b.enemy.board if c.name == 'Titan Overseer')
        playable = [c for c in b.enemy.hand if c.card_type == 'Land' or b.cost(b.enemy, c) <= projected_mana]
        next_card = min(playable, key=lambda c: (c.card_type == 'Land', c.mana_cost), default=None)
        attack = sum(c.attack for c in ready)
        panel = pygame.Rect(710, 18, 195, 78)
        pygame.draw.rect(self.screen, (23, 23, 31), panel, border_radius=9)
        pygame.draw.rect(self.screen, (218, 119, 102), panel, 2, border_radius=9)
        self.text('ENEMY INTENT', panel.x + 10, panel.y + 7, (240, 170, 145), self.small)
        self.screen.blit(fitted(f'Attack: {len(ready)} creature(s), {attack} power', 175, 12, (238, 228, 214)),
                         (panel.x + 10, panel.y + 30))
        action = f'Likely play: {next_card.name}' if next_card else 'Likely play: none'
        self.screen.blit(fitted(action, 175, 12, (190, 187, 202)), (panel.x + 10, panel.y + 51))

    def card_modifier_details(self, card):
        perpetual = getattr(card, 'perpetual', {})
        mutations = {
            'insight': 'Insight Morph: +1/+1; draw a card when this enters.',
            'chorus': 'Chorus Morph: +1/+1; gain 1 life during upkeep.',
            'death_curse': 'Hostile Morph: +1/+1; controller loses 1 life when this dies.',
            'hospitality': 'Welcoming Morph: +1/+1; gain 1 life when another ally enters.',
            'spellflame': 'Cinder Morph: +1/+1; noncreature spells deal 1 hero damage.',
            'landgrowth': 'Rooted Morph: +1/+1; playing a land adds a perpetual +1/+1.',
            'mourning': 'Mourning Morph: +1/+1; gain 1 life when another ally dies.'}
        details = []
        for key, description in mutations.items():
            count = perpetual.get(key, 0)
            if count:
                details.append((f'x{count} ' if count > 1 else '') + description)
        if perpetual.get('mosaic'):
            details.append(f'Living Mosaic: +{perpetual["mosaic"]}/+{perpetual["mosaic"]} perpetual.')
        if perpetual.get('growth_bonus'):
            details.append(f'Rooted growth: +{perpetual["growth_bonus"]}/+{perpetual["growth_bonus"]} perpetual.')
        if getattr(card, 'upgraded', False):
            details.append('Card upgrade applied.')
        if getattr(card, 'temp_attack', 0) or getattr(card, 'temp_health', 0):
            details.append(f'Temporary buff: +{card.temp_attack}/+{card.temp_health} until end of turn.')
        definition = next((data for data in self.pool['cards'] if data['name'] == card.name), None)
        if definition and card.max_health > 0:
            known = (sum(perpetual.get(key, 0) for key in mutations)
                     + perpetual.get('mosaic', 0) + perpetual.get('growth_bonus', 0))
            upgrade = int(getattr(card, 'upgraded', False))
            other_attack = card.attack - card.temp_attack - definition.get('atk', 0) - known - upgrade
            other_health = card.max_health - card.temp_health - definition.get('hp', 0) - known - upgrade
            if other_attack or other_health:
                details.append(f'Other permanent stat changes: {other_attack:+d}/{other_health:+d}.')
        for keyword in getattr(card, 'keywords', []):
            details.append(f'Keyword: {keyword.title()}.')
        if getattr(card, 'frozen', False):
            details.append('Frozen: skips its next untap.')
        return details

    def draw_card_modifiers(self, card, card_rect):
        details = self.card_modifier_details(card)
        perpetual = getattr(card, 'perpetual', {})
        morph_keys = ('insight', 'chorus', 'death_curse', 'hospitality',
                      'spellflame', 'landgrowth', 'mourning')
        morphs = sum(perpetual.get(key, 0) for key in morph_keys)
        counters = getattr(card, 'plus_one_counters', 0)
        left = pygame.Rect(card_rect.left - 245, card_rect.top + 25, 225, 230)
        right = pygame.Rect(card_rect.right + 20, card_rect.top, 385, card_rect.h)
        for panel in (left, right):
            pygame.draw.rect(self.screen, (17, 22, 31), panel, border_radius=10)
            pygame.draw.rect(self.screen, (245, 117, 199), panel, 2, border_radius=10)
        self.text('MODIFIER TOTALS', left.x + 14, left.y + 14, (245, 206, 105), self.small)
        rows = [(f'+1/+1 counters', counters), ('Morph effects', morphs),
                ('Buff sources', len(details)), ('Keywords', len(getattr(card, 'keywords', [])))]
        for i, (label, value) in enumerate(rows):
            y = left.y + 52 + i * 38
            self.text(label, left.x + 14, y, (190, 187, 202), self.small)
            value_text = font(18, bold=True).render(str(value), True, (245, 232, 205))
            self.screen.blit(value_text, value_text.get_rect(midright=(left.right - 16, y + 10)))
        self.text('BUFFS & EFFECTS', right.x + 15, right.y + 14, (245, 206, 105), self.small)
        y = right.y + 47
        if not details:
            self.text('No buffs or additional effects.', right.x + 15, y, (159, 155, 178), self.small)
        for detail in details:
            pygame.draw.circle(self.screen, (245, 117, 199), (right.x + 18, y + 7), 4)
            used = self.wrap(detail, right.x + 31, y, right.w - 46, (232, 226, 238))
            y += used + 10
            if y > right.bottom - 24:
                self.text('More effects…', right.x + 15, right.bottom - 25, (245, 206, 105), self.small)
                break

    def hero_rect(self, friendly):
        return pygame.Rect(578, 594 if friendly else 30, 124, 112)

    def draw_hero(self, friendly):
        side = self.battle.player if friendly else self.battle.enemy
        rect = self.hero_rect(friendly)
        selected = side in self.valid_targets()
        color = (105, 220, 247) if selected else (202, 171, 112)
        phase = self.battle.return_phase if self.battle.phase == 'RESPONSE' else self.battle.phase
        player_turn = phase not in ('ENEMY_MAIN', 'BLOCK', 'DEFEND_RESPONSE', 'AFTER_ENEMY_COMBAT')
        active_turn = friendly == player_turn and not self.battle.result
        if active_turn:
            pulse = (math.sin(time.monotonic() * 4) + 1) / 2
            aura = pygame.Surface((rect.w + 90, rect.h + 90), pygame.SRCALPHA)
            center = (aura.get_width() // 2, aura.get_height() // 2)
            for radius, alpha in ((70, int(20 + pulse * 15)), (58, int(38 + pulse * 22)), (48, 55)):
                pygame.draw.circle(aura, (255, 191, 65, alpha), center, radius, 5)
            self.screen.blit(aura, aura.get_rect(center=rect.center))
        points = [(rect.centerx, rect.top), (rect.right, rect.top + 24),
                  (rect.right - 8, rect.bottom - 16), (rect.centerx, rect.bottom),
                  (rect.left + 8, rect.bottom - 16), (rect.left, rect.top + 24)]
        shadow_points = [(x + 4, y + 6) for x, y in points]
        pygame.draw.polygon(self.screen, (3, 6, 9), shadow_points)
        pygame.draw.circle(self.screen, (8, 12, 16), rect.center, 69)
        pygame.draw.circle(self.screen, tuple(max(0, c // 2) for c in color), rect.center, 65, 3)
        pygame.draw.polygon(self.screen, (18, 22, 22), points)
        portrait = rect.inflate(-24, -24)
        self.artwork.paint(self.screen, self.run.commander.color_code if friendly else self.battle.theme, portrait)
        pygame.draw.polygon(self.screen, color, points, 3)
        for point in (points[0], points[1], points[4]):
            pygame.draw.circle(self.screen, (245, 220, 154), point, 4)
            pygame.draw.circle(self.screen, (55, 42, 25), point, 2)
        badge = pygame.Rect(rect.centerx - 28, rect.bottom - 28, 56, 36)
        pygame.draw.ellipse(self.screen, (20, 22, 22), badge)
        pygame.draw.ellipse(self.screen, color, badge, 2)
        number = font(26, bold=True).render(str(side.hp), True, (250, 241, 215))
        self.screen.blit(number, number.get_rect(center=badge.center))
        if side.armor:
            self.text(f'+{side.armor} armor', rect.right + 10, rect.centery, color, self.small)
        if selected:
            self.glow(rect, color)
            pulse = 2 + int((math.sin(time.monotonic() * 7) + 1) * 2)
            pygame.draw.ellipse(self.screen, (105, 232, 255), rect.inflate(8, 8), pulse)
            self.buttons.append((rect, lambda s=side: self.target(s)))
        name = fitted('YOU' if friendly else side.name, 220, 14, (235, 222, 194))
        self.screen.blit(name, name.get_rect(midbottom=(rect.centerx, rect.top - 5)))

    def draw_land_row(self, friendly):
        side = self.battle.player if friendly else self.battle.enemy
        if not hasattr(self, 'land_hits') or not friendly:
            self.land_hits = {False: [], True: []}
        y = 642 if friendly else 196
        label_y = 563 if friendly else 111
        label = 'MANA BASE' + ('  •  LAND PLAYED' if friendly and side.land_played else '')
        self.text(label, 32, label_y, (230, 213, 169), self.small)
        visible = side.lands[:12]
        start_x = 122 if friendly else 27
        step = min(66, (760 if friendly else 720) / max(1, len(visible) - 1))
        for i, card in enumerate(visible):
            x = start_x + i * step
            surface = pygame.Surface((96, 68), pygame.SRCALPHA)
            surface.fill((15, 18, 16))
            self.artwork.paint(surface, card.color_code, (4, 4, 88, 60))
            accent = PALETTES.get(card.color_code, (190, 180, 160))
            pygame.draw.rect(surface, (8, 10, 10), surface.get_rect(), 5, border_radius=8)
            pygame.draw.rect(surface, accent, surface.get_rect(), 2, border_radius=8)
            pygame.draw.rect(surface, (18, 23, 21, 220), (5, 5, 86, 18), border_radius=4)
            surface.blit(fitted('Mana Conduit', 63, 9, (246, 236, 205)), (8, 8))
            pygame.draw.circle(surface, (12, 16, 18), (81, 14), 10)
            pygame.draw.circle(surface, accent, (81, 14), 9)
            draw_mana_glyph(surface, card.color_code, (81, 14), 7)
            if card.tapped:
                surface = pygame.transform.rotozoom(surface, -12, 1.0)
            rect = surface.get_rect(midbottom=(x + 48, y))
            pygame.draw.rect(self.screen, (4, 7, 11), rect.move(3, 4), border_radius=7)
            self.screen.blit(surface, rect)
            self.land_hits[friendly].append((card, rect))
        if len(side.lands) > 12:
            self.text(f'+{len(side.lands) - 12}', 910 if friendly else 780, y - 24,
                      (230, 213, 169), self.small)

    def battlefield_card(self, card, rect, selected=False, subtitle=''):
        """Art, name and live stats; full rules appear on hover."""
        rect = pygame.Rect(rect)
        accent = PALETTES.get(card.color_code, (194, 177, 140))
        hovered = rect.inflate(8, 8).collidepoint(self.mouse_pos())
        if hovered and not card.tapped:
            rect.y -= 6
        canvas = pygame.Surface(rect.size, pygame.SRCALPHA)
        local = canvas.get_rect()
        pygame.draw.rect(canvas, (18, 23, 21), local, border_radius=7)
        picture = local.inflate(-8, -8)
        key = card.name if card.name in self.artwork.card_files else card.color_code
        self.artwork.paint(canvas, key, picture)
        pygame.draw.rect(canvas, (99, 222, 245) if selected else accent, local, 3 if selected else 2, border_radius=7)
        counters = getattr(card, 'plus_one_counters', 0)
        title = pygame.Rect(4, 4, local.w - 8, 20)
        pygame.draw.rect(canvas, (23, 27, 22), title)
        title_offset = 25 if counters else 0
        canvas.blit(fitted(card.name, title.w - 6 - title_offset, 11, (240, 233, 207)),
                    (title.x + 3 + title_offset, title.y + 3))
        if counters:
            pygame.draw.circle(canvas, (245, 117, 199), (15, 14), 11)
            badge = font(9, bold=True).render(f'+{counters}', True, (24, 18, 26))
            canvas.blit(badge, badge.get_rect(center=(15, 14)))
        badge = pygame.Rect(local.right - 53, local.bottom - 24, 52, 25)
        pygame.draw.rect(canvas, (235, 223, 190), badge, border_radius=4)
        stats = font(19, bold=True).render(f'{card.attack}/{card.current_health}', True, (22, 25, 23))
        canvas.blit(stats, stats.get_rect(center=badge.center))
        status = subtitle or ('TAPPED' if card.tapped else 'SUMMONING' if card.sick else '')
        if status:
            strip = pygame.Rect(0, local.bottom - 20, local.w - 54, 20)
            pygame.draw.rect(canvas, (22, 27, 29), strip)
            canvas.blit(fitted(status, strip.w - 4, 10, accent), (strip.x + 2, strip.y + 3))
        if getattr(card, 'perpetual', {}):
            pygame.draw.circle(canvas, (255, 121, 211), (13, local.bottom - 12), 7)
        if card.tapped:
            canvas = pygame.transform.rotozoom(canvas, -12, 1.0)
        drawn = canvas.get_rect(center=rect.center)
        if hovered:
            halo = pygame.Surface((drawn.w + 28, drawn.h + 28), pygame.SRCALPHA)
            pygame.draw.rect(halo, (*accent, 38), halo.get_rect().inflate(-4, -4), 8, border_radius=13)
            self.screen.blit(halo, halo.get_rect(center=drawn.center))
        pygame.draw.rect(self.screen, (3, 6, 8), drawn.move(5, 7), border_radius=8)
        self.screen.blit(canvas, drawn)
        card.rect = drawn
        if drawn.collidepoint(self.mouse_pos()):
            self.hover = card
        return drawn

    def draw_phase_track(self):
        raw_phase = self.battle.return_phase if self.battle.phase == 'RESPONSE' else self.battle.phase
        combat = raw_phase in ('COMBAT', 'BLOCK', 'ATTACK_RESPONSE', 'DEFEND_RESPONSE', 'ATTACK_TARGET',
                               'AFTER_PLAYER_COMBAT', 'DECLARE_BLOCKS', 'AFTER_ENEMY_COMBAT')
        active_key = ('MAIN1' if raw_phase == 'MAIN' else 'MAIN2' if raw_phase == 'MAIN2' else
                      'COMBAT' if combat else 'END' if raw_phase in ('END', 'ENEMY_MAIN') else 'UPKEEP')
        if raw_phase == 'DISCARD':
            active_key = 'END'
        stages = [('UPKEEP', 'UP', 4), ('MAIN1', 'MAIN I', 10), ('COMBAT', 'COMBAT', 5),
                  ('MAIN2', 'MAIN II', 10), ('END', 'END', 4)]
        y = self.hero_rect(True).centery
        positions = [737, 785, 857, 929, 977]
        center_x = positions[2]
        pygame.draw.line(self.screen, (74, 69, 55), (positions[0], y), (positions[-1], y), 2)
        for (key, label, radius), x in zip(stages, positions):
            active = key == active_key
            if active:
                glow = pygame.Surface((58, 58), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 192, 62, 45), (29, 29), 27)
                pygame.draw.circle(glow, (255, 218, 104, 90), (29, 29), 20)
                self.screen.blit(glow, glow.get_rect(center=(x, y)))
            color = (255, 222, 119) if active else (77, 76, 69)
            pygame.draw.rect(self.screen, (16, 20, 20), (x - radius, y - radius, radius * 2, radius * 2), border_radius=3)
            pygame.draw.rect(self.screen, color, (x - radius, y - radius, radius * 2, radius * 2), 2, border_radius=3)
            if label:
                text = fitted(label, 62, 10 if radius < 10 else 11, color)
                self.screen.blit(text, text.get_rect(midtop=(x, y + 14)))
        player_turn = self.player_has_turn()
        turn_text = 'YOUR TURN' if player_turn else 'OPPONENT TURN'
        color = (255, 222, 119) if turn_text == 'YOUR TURN' else (200, 127, 112)
        text = fitted(turn_text, 180, 13, color)
        self.screen.blit(text, text.get_rect(midbottom=(center_x, y - 15)))
