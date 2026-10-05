"""Compatibility entry point for the shared anime prompt catalog."""
from prepare_anime_art import build_catalog


def prepare():
    return build_catalog()


if __name__ == '__main__':
    print('Anime catalog:', len(prepare()), 'distinct designs')
