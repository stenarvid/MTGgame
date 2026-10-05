"""Artwork coverage is a product constraint, not a color-level fallback."""
import hashlib
import threading
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from tactical.artwork import artwork_catalog, artwork_path
from tactical.content import CARDS, COMMANDERS, RELICS
from tactical.server import make_server
from artwork_catalog import ART_ROOT, anime_catalog


class ArtworkTests(unittest.TestCase):
    def test_every_design_has_a_unique_real_illustration(self):
        keys = ([c['id'] for c in CARDS] + ['commander_'+c['id'] for c in COMMANDERS]
                + ['relic_'+r['id'] for r in RELICS] + ['token_recruit', 'environment'])
        self.assertEqual(set(artwork_catalog()), set(keys))
        files, hashes = set(), set()
        for key in keys:
            with self.subTest(design=key):
                path = artwork_path(key)
                self.assertIsNotNone(path)
                self.assertNotIn(path, files)
                data = path.read_bytes()
                self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                digest = hashlib.sha256(data).hexdigest()
                self.assertNotIn(digest, hashes)
                self.assertGreater(len(data), 10000)
                files.add(path)
                hashes.add(digest)
                self.assertIn('lettering', artwork_catalog()[key]['prompt'].lower())

    def test_http_art_and_styles_are_served_without_path_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = make_server(port=0, save_path=Path(tmp)/'save.json')
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_address[1]}'
            try:
                for key in ['w_shield', 'commander_dawn', 'relic_lens', 'token_recruit', 'environment']:
                    with urlopen(base+'/art/'+key+'?v=anime-1') as response:
                        self.assertEqual(response.headers['Content-Type'], 'image/png')
                        self.assertEqual(response.read(), artwork_path(key).read_bytes())
                with urlopen(base+'/style.css') as response:
                    self.assertIn('text/css',response.headers['Content-Type'])
                for key in ['unknown', '../cards.json', 'commander_not-real']:
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(base+'/art/'+key)
                    self.assertEqual(caught.exception.code,404)
                    caught.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                worker.join()


class FullAnimeArtworkTests(unittest.TestCase):
    def test_complete_catalog_has_no_missing_or_reused_images(self):
        files,hashes=set(),set()
        missing=[key for key,entry in anime_catalog().items() if not (ART_ROOT/entry['file']).is_file()]
        self.assertFalse(missing, f'{len(missing)} illustrations still missing: {missing[:5]}')
        for key,entry in anime_catalog().items():
            with self.subTest(design=key):
                path=(ART_ROOT/entry['file']).resolve()
                self.assertTrue(path.is_relative_to(ART_ROOT.resolve()))
                data=path.read_bytes()
                self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertGreater(len(data),10000)
                digest=hashlib.sha256(data).hexdigest()
                self.assertNotIn(path,files)
                self.assertNotIn(digest,hashes)
                files.add(path);hashes.add(digest)

    def test_only_current_five_color_game_designs_are_in_catalog(self):
        self.assertEqual(set(anime_catalog()),set(artwork_catalog()))
        self.assertEqual(len(anime_catalog()),64)
        self.assertFalse(any(key.startswith('legacy_') for key in anime_catalog()))
        self.assertFalse(any('P' in entry['colors'] for entry in anime_catalog().values()))


if __name__ == '__main__':
    unittest.main()
