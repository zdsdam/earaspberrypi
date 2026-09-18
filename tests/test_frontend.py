import tempfile
import unittest
from pathlib import Path

from client import create_app


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'index.html').write_text('<html>EASound</html>')
        (self.root / 'assets').mkdir()
        (self.root / 'assets/app.js').write_text('console.log("local")')
        (self.root / 'trap.mp3').write_bytes(b'audio')
        app, _ = create_app(self.root)
        self.http = app.test_client()

    def test_index_and_spa_route(self):
        for url in ('/', '/rooms/armoury'):
            with self.http.get(url) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'EASound', response.data)

    def test_local_assets(self):
        for url, content in (('/assets/app.js', b'console.log("local")'), ('/trap.mp3', b'audio')):
            with self.http.get(url) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, content)
        with self.http.get('/trap.mp3', headers={'Range': 'bytes=0-1'}) as response:
            self.assertEqual(response.status_code, 206)

    def test_missing_assets_and_traversal(self):
        for url in ('/missing.mp3', '/assets/missing.js', '/../client.py', '/message', '/health/missing'):
            self.assertEqual(self.http.get(url).status_code, 404)
        self.assertEqual(self.http.get('/health').json, {'status': 'ok'})

    def test_missing_build(self):
        app, _ = create_app(self.root / 'not-built')
        self.assertEqual(app.test_client().get('/').status_code, 503)
