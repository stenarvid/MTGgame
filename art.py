"""Cached artwork and scalable trading-card frames, drawn with real game data."""
from functools import lru_cache
from pathlib import Path
import json
import math
import pygame

ART_DIR = Path(__file__).resolve().parent / 'assets' / 'art'
ART_FILES = dict(W='white-vanguard.png', U='blue-shifter.png', B='black-necromancer.png',
                 R='red-pyromancer.png', G='green-overseer.png', P='blue-shifter.png', land='astral-spire.png')
PALETTES = dict(W=(225, 207, 153), U=(101, 182, 240), B=(188, 141, 230),
                R=(244, 133, 102), G=(128, 203, 158), P=(245, 117, 199))
INK = (18, 22, 35)
GOLD = (192, 164, 108)


def draw_mana_glyph(surface, symbol, center, radius, color=INK):
    """Draw compact original glyphs for the six colored mana types."""
    cx, cy = map(int, center)
    r = max(5, int(radius))
    line = max(1, r // 5)
    if symbol == 'W':
        pygame.draw.circle(surface, color, (cx, cy), max(2, r // 3))
        for i in range(8):
            angle = i * math.tau / 8
            inner, outer = r * .52, r * .82
            pygame.draw.line(surface, color,
                             (cx + math.cos(angle) * inner, cy + math.sin(angle) * inner),
                             (cx + math.cos(angle) * outer, cy + math.sin(angle) * outer), line)
    elif symbol == 'U':
        points = [(cx, cy - r + 1), (cx - int(r * .64), cy + int(r * .25)),
                  (cx - int(r * .45), cy + int(r * .7)), (cx, cy + int(r * .82)),
                  (cx + int(r * .45), cy + int(r * .7)), (cx + int(r * .64), cy + int(r * .25))]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, color, (cx, cy + r // 4), int(r * .58))
    elif symbol == 'B':
        pygame.draw.circle(surface, color, (cx, cy - r // 5), int(r * .65))
        pygame.draw.rect(surface, color, (cx - r // 2, cy, r, int(r * .62)), border_radius=2)
        eye = max(1, r // 5)
        hole = PALETTES['B']
        pygame.draw.circle(surface, hole, (cx - r // 4, cy - r // 5), eye)
        pygame.draw.circle(surface, hole, (cx + r // 4, cy - r // 5), eye)
        pygame.draw.polygon(surface, hole, [(cx, cy), (cx - eye, cy + eye), (cx + eye, cy + eye)])
        for dx in (-r // 3, 0, r // 3):
            pygame.draw.line(surface, hole, (cx + dx, cy + r // 4), (cx + dx, cy + r // 2), 1)
    elif symbol == 'R':
        outer = [(cx, cy - r), (cx + r // 4, cy - r // 3), (cx + int(r * .7), cy - r // 2),
                 (cx + int(r * .62), cy + r // 3), (cx, cy + r),
                 (cx - int(r * .68), cy + r // 3), (cx - r // 3, cy - r // 4)]
        pygame.draw.polygon(surface, color, outer)
        pygame.draw.polygon(surface, PALETTES['R'], [(cx, cy - r // 3), (cx + r // 3, cy + r // 3),
                                                    (cx, cy + int(r * .7)), (cx - r // 4, cy + r // 4)])
    elif symbol == 'G':
        leaf = [(cx - r // 5, cy + int(r * .75)), (cx - int(r * .72), cy),
                (cx - r // 3, cy - int(r * .72)), (cx + int(r * .72), cy - int(r * .65)),
                (cx + int(r * .58), cy + r // 4)]
        pygame.draw.polygon(surface, color, leaf)
        pygame.draw.line(surface, PALETTES['G'], (cx - r // 3, cy + r // 2),
                         (cx + r // 3, cy - r // 3), line)
    elif symbol == 'P':
        box = pygame.Rect(cx - int(r * .72), cy - int(r * .72), int(r * 1.44), int(r * 1.44))
        pygame.draw.arc(surface, color, box, .25, math.tau * .92, line + 1)
        pygame.draw.circle(surface, color, (cx, cy), max(2, r // 5))
        pygame.draw.polygon(surface, color, [(cx + int(r * .7), cy - r // 5),
                                             (cx + r, cy), (cx + int(r * .67), cy + r // 5)])


@lru_cache(maxsize=40)
def font(size, serif=False, bold=False):
    return pygame.font.SysFont('Georgia' if serif else 'Segoe UI', size, bold=bold)


def fitted(text, width, size, color, serif=False):
    chosen = font(size, serif)
    while chosen.size(text)[0] > width and size > 9:
        size -= 1
        chosen = font(size, serif)
    if chosen.size(text)[0] > width:
        while text and chosen.size(text + '...')[0] > width:
            text = text[:-1]
        text += '...'
    return chosen.render(text, True, color)


def text_lines(text, width, text_font):
    lines, current = [], ''
    for word in text.split():
        candidate = f'{current} {word}'.strip()
        if current and text_font.size(candidate)[0] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def paragraph(surface, text, rect, size=14, color=INK):
    rect = pygame.Rect(rect)
    chosen = font(size)
    lines = text_lines(text, rect.w, chosen)
    while len(lines) * chosen.get_linesize() > rect.h and size > 10:
        size -= 1
        chosen = font(size)
        lines = text_lines(text, rect.w, chosen)
    limit = max(1, rect.h // chosen.get_linesize())
    for i, line in enumerate(lines[:limit]):
        if i == limit - 1 and len(lines) > limit:
            line = line.rstrip('.') + '...'
        surface.blit(fitted(line, rect.w, size, color), (rect.x, rect.y + i * chosen.get_linesize()))


class Artwork:
    def __init__(self):
        self.originals = {}
        self.scaled = {}
        self.backgrounds = {}
        self.missing = []
        manifest_path = ART_DIR / 'cards.json'
        self.card_files = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
        loaded = {}
        for key, filename in dict(ART_FILES, arena='arena-board.png', **self.card_files).items():
            try:
                if filename not in loaded:
                    loaded[filename] = pygame.image.load(str(ART_DIR / filename)).convert()
                self.originals[key] = loaded[filename]
            except (FileNotFoundError, pygame.error):
                self.missing.append(filename)

    def image(self, key, size):
        cache_key = (key, tuple(size))
        if cache_key not in self.scaled:
            source = self.originals.get(key)
            if source is None:
                result = pygame.Surface(size)
                result.fill((35, 45, 65))
            else:
                width, height = size
                factor = max(width / source.get_width(), height / source.get_height())
                crop_w, crop_h = round(width / factor), round(height / factor)
                # Favor the upper portion to preserve faces when wide card windows crop art.
                crop = pygame.Rect((source.get_width() - crop_w) // 2,
                                   int((source.get_height() - crop_h) * 0.30), crop_w, crop_h)
                result = pygame.transform.smoothscale(source.subsurface(crop), size)
            self.scaled[cache_key] = result
        return self.scaled[cache_key]

    def paint(self, surface, key, rect):
        rect = pygame.Rect(rect)
        surface.blit(self.image(key, rect.size), rect)

    def background(self, surface, mode):
        key = (surface.get_size(), mode)
        if key not in self.backgrounds:
            result = self.image('arena' if mode == 'BATTLE' else 'land', surface.get_size()).copy()
            shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            shade.fill((8, 12, 23, 70 if mode == 'MENU' else 85 if mode == 'BATTLE' else 195))
            result.blit(shade, (0, 0))
            # Soft cinematic vignette keeps attention on the play space without
            # adding bitmap UI assets that blur at unusual resolutions.
            vignette = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            w, h = surface.get_size()
            for i in range(48):
                alpha = int(2 + i * 1.35)
                pygame.draw.rect(vignette, (2, 4, 10, alpha),
                                 (i, i, w - i * 2, h - i * 2), 2, border_radius=max(0, 34 - i // 2))
            for i in range(70):
                alpha = int(72 * (1 - i / 70) ** 2)
                pygame.draw.line(vignette, (3, 6, 13, alpha), (0, i), (w, i))
                pygame.draw.line(vignette, (3, 6, 13, alpha), (0, h - i - 1), (w, h - i - 1))
            result.blit(vignette, (0, 0))
            self.backgrounds[key] = result
        surface.blit(self.backgrounds[key], (0, 0))
        if mode == 'BATTLE':
            width = surface.get_width()
            pygame.draw.line(surface, (122, 111, 84), (28, 401), (1030, 401))


class CardPainter:
    def __init__(self, artwork):
        self.artwork = artwork

    def mana_symbols(self, card, cost=None):
        total = card.mana_cost if cost is None else cost
        colored = []
        for color in 'WUBRGP':
            colored.extend([color] * card.pips.get(color, 0))
        generic = max(0, total - len(colored))
        return ([str(generic)] if generic else []) + colored

    def draw_mana_symbols(self, surface, card, rect, cost=None, compact=False):
        symbols = self.mana_symbols(card, cost)
        radius = 10 if compact else 13
        gap = radius * 2 + 2
        right = rect.right - 7
        cy = rect.top + radius + 8
        for i, symbol in enumerate(reversed(symbols)):
            cx = right - radius - i * gap
            fill = PALETTES.get(symbol, (210, 205, 190)) if symbol != '0' else (205, 205, 195)
            pygame.draw.circle(surface, (5, 8, 12), (cx + 2, cy + 2), radius + 1)
            pygame.draw.circle(surface, fill, (cx, cy), radius)
            pygame.draw.circle(surface, (235, 225, 195), (cx, cy), radius, 1)
            if symbol in 'WUBRGP':
                draw_mana_glyph(surface, symbol, (cx, cy), radius - 2)
            else:
                glyph = font(11 if compact else 14, serif=True, bold=True).render(symbol, True, (18, 20, 22))
                surface.blit(glyph, glyph.get_rect(center=(cx, cy)))
        return len(symbols) * gap

    def draw(self, surface, card, rect, selected=False, subtitle='', cost=None, combat=False, playable=False):
        rect = pygame.Rect(rect)
        x, y, w, h = rect
        accent = PALETTES.get(card.color_code, GOLD)
        # Layered midnight leather, metallic trim, illustrated window, parchment rules.
        pygame.draw.rect(surface, (2, 4, 8), rect.move(4, 7), border_radius=11)
        if selected or playable:
            glow = (116, 237, 198) if selected else (82, 190, 210)
            pygame.draw.rect(surface, tuple(max(0, c // 3) for c in glow), rect.inflate(9, 9), 3, border_radius=13)
            pygame.draw.rect(surface, glow, rect.inflate(5, 5), 2, border_radius=11)
        pygame.draw.rect(surface, (16, 23, 36), rect, border_radius=9)
        pygame.draw.rect(surface, accent if selected else GOLD, rect, 2, border_radius=9)
        pygame.draw.rect(surface, tuple(max(0, c // 3) for c in accent), rect.inflate(-8, -8), 1, border_radius=6)
        # Small metallic corner brackets give the frame definition after rotation.
        corner = 12 if w >= 150 else 8
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            cx = rect.left + 5 if sx > 0 else rect.right - 5
            cy = rect.top + 5 if sy > 0 else rect.bottom - 5
            pygame.draw.line(surface, (248, 224, 158), (cx, cy), (cx + sx * corner, cy), 1)
            pygame.draw.line(surface, (248, 224, 158), (cx, cy), (cx, cy + sy * corner), 1)

        compact = w < 175
        title_h = 35 if compact else 32
        mana_width = max(26, len(self.mana_symbols(card, cost)) * (22 if compact else 28))
        counters = getattr(card, 'plus_one_counters', 0)
        counter_space = 30 if counters else 0
        title_rect = pygame.Rect(x + 9 + counter_space, y + 7,
                                 max(20, w - mana_width - 16 - counter_space), title_h)
        level = getattr(card, 'upgrade_level', int(card.upgraded))
        paragraph(surface, card.name + (f' +{level}' if level else ''), title_rect, 12 if compact else 15, (248, 238, 209))
        if counters:
            badge_center = (x + 17, y + 18)
            pygame.draw.circle(surface, (12, 16, 20), badge_center, 13)
            pygame.draw.circle(surface, (245, 117, 199), badge_center, 12)
            label = font(10 if compact else 11, bold=True).render(f'+{counters}', True, (24, 18, 26))
            surface.blit(label, label.get_rect(center=badge_center))
        self.draw_mana_symbols(surface, card, rect, cost, compact)

        art_top = y + title_h + 10
        art_height = int(h * (0.35 if compact else 0.47))
        art_rect = pygame.Rect(x + 9, art_top, w - 18, art_height)
        key = 'land' if card.card_type == 'Land' else card.name if card.name in self.artwork.card_files else card.color_code
        self.artwork.paint(surface, key, art_rect)
        pygame.draw.rect(surface, accent, art_rect, 1)
        # Colored corner flourishes remain readable even on bright art.
        for left in (True, False):
            px = art_rect.left if left else art_rect.right - 1
            dx = 9 if left else -9
            pygame.draw.line(surface, GOLD, (px, art_rect.top), (px + dx, art_rect.top), 2)
            pygame.draw.line(surface, GOLD, (px, art_rect.top), (px, art_rect.top + 9), 2)

        type_y = art_rect.bottom + 4
        type_name = 'Creature' if card.is_creature else 'Spell' if card.card_type == 'Instant Spell' else card.card_type
        label = fitted(f'{card.color_code}  /  {type_name}', w - 20, 11 if compact else 13, accent)
        surface.blit(label, (x + 10, type_y))
        rules_y = type_y + (18 if compact else 23)
        bottom_h = 25 if compact else 32
        rules_rect = pygame.Rect(x + 9, rules_y, w - 18, max(0, rect.bottom - bottom_h - rules_y - 5))
        if rules_rect.h >= 16:
            pygame.draw.rect(surface, (227, 219, 197), rules_rect, border_radius=3)
            rules = card.text
            descriptions = {'haste': 'Haste: can attack immediately.', 'guard': 'Guard: takes 1 less blocking damage.',
                            'trample': 'Trample: excess combat damage hits the enemy hero.',
                            'vigilance': 'Vigilance: attacking does not tap this creature.'}
            for keyword in getattr(card, 'keywords', []):
                if keyword not in rules.lower():
                    rules += ' ' + descriptions.get(keyword, keyword.title())
            paragraph(surface, rules, rules_rect.inflate(-10, -6), 11 if compact else 14)

        status = subtitle
        if not status and combat and card.is_creature:
            status = 'TAPPED' if card.tapped else 'SUMMONING' if card.sick else 'READY'
        if status:
            max_width = w - (63 if card.is_creature else 20)
            surface.blit(fitted(status, max_width, 10 if compact else 12, accent),
                         (x + 10, rect.bottom - bottom_h + 5))
        elif not card.is_creature:
            surface.blit(fitted('COMMANDER SPIRE', w - 20, 9, (144, 146, 157)),
                         (x + 10, rect.bottom - bottom_h + 5))
        if card.is_creature:
            badge = pygame.Rect(rect.right - 59, rect.bottom - bottom_h, 51, bottom_h - 6)
            pygame.draw.rect(surface, (36, 34, 36), badge, border_radius=5)
            pygame.draw.rect(surface, accent, badge, 1, border_radius=5)
            stats = font(14 if compact else 18, bold=True).render(f'{card.attack}/{card.current_health}', True, (250, 238, 214))
            surface.blit(stats, stats.get_rect(center=badge.center))
        if combat and card.tapped:
            tag = pygame.Rect(art_rect.x + 3, art_rect.bottom - 20, art_rect.w - 6, 17)
            pygame.draw.rect(surface, (24, 23, 37), tag)
            surface.blit(fitted('TAPPED', tag.w - 6, 11, accent), (tag.x + 4, tag.y))

    def preview(self, surface, card, mx, my, cost=None):
        w, h = 300, 445
        x = mx + 22 if mx + w + 30 < surface.get_width() else mx - w - 22
        x = max(10, min(x, surface.get_width() - w - 10))
        y = max(10, min(my - h // 2, surface.get_height() - h - 10))
        self.draw(surface, card, (x, y, w, h), cost=cost)
        return pygame.Rect(x, y, w, h)
