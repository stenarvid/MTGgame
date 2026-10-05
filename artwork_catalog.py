"""Stable illustration identities for Commander Spire's five-color card pool."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ART_ROOT = ROOT / 'assets/art'


def design_filename(key):
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', key.lower()).strip('-')[:90]
    return 'anime/' + slug + '-' + hashlib.sha256(key.encode()).hexdigest()[:10] + '.png'


@lru_cache(maxsize=1)
def anime_catalog():
    return json.loads((ART_ROOT / 'anime/manifest.json').read_text(encoding='utf-8'))
