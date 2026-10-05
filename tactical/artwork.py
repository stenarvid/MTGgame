"""Explicit illustration catalog: each design owns a distinct image."""
from functools import lru_cache
from artwork_catalog import anime_catalog
from pathlib import Path

ART_ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'art'


@lru_cache(maxsize=1)
def artwork_catalog():
    return {key:entry for key,entry in anime_catalog().items() if not key.startswith('legacy_')}


def artwork_path(key):
    entry = artwork_catalog().get(key)
    if not entry:
        return None
    path = (ART_ROOT / entry['file']).resolve()
    if not path.is_relative_to(ART_ROOT.resolve()) or not path.is_file():
        return None
    return path
