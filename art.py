"""Cached artwork and scalable trading-card frames, drawn with real game data."""
from functools import lru_cache
from pathlib import Path
import json
import pygame

ART_DIR = Path(__file__).resolve().parent / 'assets' / 'art'
ART_FILES = dict(W='white-vanguard.png', U='blue-shifter.png', B='black-necromancer.png',
                 R='red-pyromancer.png', G='green-overseer.png', land='astral-spire.png')
PALETTES = dict(W=(225, 207, 153), U=(101, 182, 240), B=(188, 141, 230),
                R=(244, 133, 102), G=(128, 203, 158))
INK = (18, 22, 35)
GOLD = (192, 164, 108)


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
        for key, filename in dict(ART_FILES, **self.card_files).items():
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
            result = self.image('land', surface.get_size()).copy()
            shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            shade.fill((8, 12, 23, 70 if mode == 'MENU' else 211 if mode == 'BATTLE' else 195))
            result.blit(shade, (0, 0))
            self.backgrounds[key] = result
        surface.blit(self.backgrounds[key], (0, 0))
        if mode == 'BATTLE':
            width = surface.get_width()
            pygame.draw.line(surface, (103, 92, 75), (28, 350), (width - 28, 350))
            pygame.draw.circle(surface, (100, 86, 63), (width // 2, 350), 17, 1)
            pygame.draw.circle(surface, (100, 86, 63), (width // 2, 350), 9, 1)


class CardPainter:
    def __init__(self, artwork):
        self.artwork = artwork

    def draw(self, surface, card, rect, selected=False, subtitle='', cost=None, combat=False, playable=False):
        rect = pygame.Rect(rect)
        x, y, w, h = rect
        accent = PALETTES.get(card.color_code, GOLD)
        # Layered midnight leather, metallic trim, illustrated window, parchment rules.
        pygame.draw.rect(surface, (5, 8, 14), rect.move(3, 5), border_radius=10)
        if selected or playable:
            glow = (116, 237, 198) if selected else (75, 132, 145)
            pygame.draw.rect(surface, glow, rect.inflate(6, 6), 2, border_radius=11)
        pygame.draw.rect(surface, (16, 23, 36), rect, border_radius=9)
        pygame.draw.rect(surface, accent if selected else GOLD, rect, 2, border_radius=9)
        pygame.draw.rect(surface, tuple(max(0, c // 3) for c in accent), rect.inflate(-8, -8), 1, border_radius=6)

        compact = w < 175
        title_h = 35 if compact else 32
        mana_r = 13 if compact else 16
        title_rect = pygame.Rect(x + 9, y + 7, w - 2 * mana_r - 20, title_h)
        paragraph(surface, card.name + (' +' if card.upgraded else ''), title_rect, 12 if compact else 15, (248, 238, 209))
        cx, cy = rect.right - mana_r - 7, y + mana_r + 8
        pygame.draw.circle(surface, (12, 24, 38), (cx, cy), mana_r)
        pygame.draw.circle(surface, accent, (cx, cy), mana_r, 2)
        number = fitted(card.mana_label(cost), mana_r * 2 - 4, 14 if compact else 18, (248, 244, 228))
        surface.blit(number, number.get_rect(center=(cx, cy)))

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

    def preview(self, surface, card, mx, my):
        w, h = 300, 445
        x = mx + 22 if mx + w + 30 < surface.get_width() else mx - w - 22
        x = max(10, min(x, surface.get_width() - w - 10))
        y = max(10, min(my - h // 2, surface.get_height() - h - 10))
        self.draw(surface, card, (x, y, w, h))
