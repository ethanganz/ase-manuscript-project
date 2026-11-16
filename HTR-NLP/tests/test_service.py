"""The web service's place assembly and HTTP layer, without any neural model."""
import io
import json
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from service.pipeline import assemble_places, upright_page  # noqa: E402
from historical_aliases import HistoricalAliases  # noqa: E402  (path added by service.pipeline)

try:
    from fastapi.testclient import TestClient
except ImportError:  # CI installs only the light dependencies
    TestClient = None


def matchers():
    config = json.loads((ROOT / 'configs/place_inference.json').read_text(encoding='utf-8'))
    return [HistoricalAliases(json.loads((ROOT / path).read_text(encoding='utf-8')))
            for path in config['lexicons']]


class AssemblePlaces(unittest.TestCase):
    def test_neural_span_gets_official_candidates(self):
        text = 'Basileę ultimo iulii 1549.'
        span = dict(start=0, end=7, text='Basileę', score=0.97)
        places = assemble_places(text, 'line_0001', [span], matchers())
        self.assertEqual([(p['start'], p['end'], p['text']) for p in places], [(0, 7, 'Basileę')])
        self.assertEqual(places[0]['place_link_status'], 'candidate_for_review')
        self.assertEqual(places[0]['official_place_candidates'][0]['canonical_name'], 'Basel')
        self.assertIn('mbert', places[0]['sources'])
        self.assertIn('official_source_variant', places[0]['sources'])

    def test_alias_match_without_neural_span(self):
        places = assemble_places('Basileę ultimo iulii 1549.', 'line_0001', [], matchers())
        self.assertEqual([p['text'] for p in places], ['Basileę'])

    def test_unknown_name_is_kept_as_unmatched(self):
        span = dict(start=3, end=9, text='Xyqzzk', score=0.9)
        places = assemble_places('in Xyqzzk misi', 'line_0001', [span], matchers())
        self.assertEqual(places[0]['place_link_status'], 'unmatched')
        self.assertEqual(places[0]['official_place_candidates'], [])

    def test_span_inside_a_word_is_dropped(self):
        span = dict(start=1, end=5, text='asil', score=0.9)
        self.assertEqual(assemble_places('Basileę', 'line_0001', [span], []), [])

    def test_blank_line_has_no_places(self):
        self.assertEqual(assemble_places('  ', 'line_0001', [], matchers()), [])


class UprightPage(unittest.TestCase):
    def test_transparent_pixels_become_white(self):
        page = upright_page(Image.new('RGBA', (4, 4), (0, 0, 0, 0)))
        self.assertEqual(page.mode, 'RGB')
        self.assertEqual(page.getpixel((0, 0)), (255, 255, 255))


@unittest.skipIf(TestClient is None, 'fastapi is not installed')
class Http(unittest.TestCase):
    def setUp(self):
        import service.app as app_module
        self.module = app_module
        outer = self

        class Fake:
            device = 'cpu'

            def __init__(self, **_):
                pass

            def recognize(self, image):
                if outer.empty:
                    raise app_module.NoLinesFound('No text lines found on this page')
                return {'page': {'width': image.width, 'height': image.height},
                        'lines': [{'line_id': 'line_0001', 'text': 'x', 'places': []}]}

        self.empty = False
        self.original = app_module.Pipeline
        app_module.Pipeline = Fake

    def tearDown(self):
        self.module.Pipeline = self.original

    @staticmethod
    def png():
        buffer = io.BytesIO()
        Image.new('RGB', (30, 20), 'white').save(buffer, 'PNG')
        return buffer.getvalue()

    def test_transcribe_returns_lines(self):
        with TestClient(self.module.app) as client:
            self.assertEqual(client.get('/health').json()['status'], 'ok')
            r = client.post('/transcribe', files={'image': ('page.png', self.png(), 'image/png')})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['page'], {'width': 30, 'height': 20})

    def test_page_without_lines_is_422(self):
        self.empty = True
        with TestClient(self.module.app) as client:
            r = client.post('/transcribe', files={'image': ('page.png', self.png(), 'image/png')})
        self.assertEqual(r.status_code, 422)
        self.assertIn('No text lines', r.json()['detail'])

    def test_corrupt_image_is_400(self):
        with TestClient(self.module.app) as client:
            r = client.post('/transcribe', files={'image': ('page.png', b'not an image', 'image/png')})
        self.assertEqual(r.status_code, 400)


if __name__ == '__main__':
    unittest.main()
