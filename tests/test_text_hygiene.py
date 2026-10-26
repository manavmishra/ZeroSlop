import importlib.util
import json
from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('text_hygiene', ROOT / 'scripts/text_hygiene.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TextHygieneTests(unittest.TestCase):
    def test_local_mcp_cleanup_is_fixed_and_offline(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import mcp_local_tools
        result = mcp_local_tools.call('clean_text', {'text': 'The te\u200bxt is clear.'})
        self.assertEqual(result['text'], 'The text is clear.')
        self.assertEqual(result['statisticalWatermark']['status'], 'not_verified')

    def test_golden_fixtures_and_reversal(self):
        cases = json.loads((ROOT / 'tests/fixtures/text-hygiene.json').read_text())
        for case in cases:
            with self.subTest(case=case['name']):
                result = module.clean_text_hygiene(case['input'])
                self.assertEqual(result['text'], case['expected'])
                self.assertEqual(module.clean_text_hygiene(result['text'])['text'], result['text'])
                self.assertEqual(module.reverse_text_hygiene(result['text'], result['edits']), case['input'])
                self.assertEqual(result['statisticalWatermark']['status'], 'not_verified')

    def test_rejects_stale_undo(self):
        result = module.clean_text_hygiene('The te\u200bxt is clear.')
        with self.assertRaises(ValueError):
            module.reverse_text_hygiene(result['text'] + ' changed', result['edits'])

    def test_undo_rejects_malformed_or_out_of_bounds_edits(self):
        result = module.clean_text_hygiene('The te\u200bxt is clear.')
        valid = result['edits'][0]
        cases = [None, [], 'edit',
                 dict(valid, start=True, end=2, outputStart=True),
                 dict(valid, start=0, end=1, outputStart=0),
                 dict(valid, start=-1, end=0, outputStart=-1),
                 dict(valid, start=1.5, end=2.5, outputStart=1.5),
                 dict(valid, outputStart=float(valid['outputStart'])),
                 dict(valid, start=999999, end=1000000, outputStart=999999),
                 dict(valid, outputStart=-1),
                 dict(valid, outputStart=len(result['text']) + 1),
                 dict(valid, outputBinding='mismatched')]
        for edit in cases:
            with self.subTest(edit=edit):
                with self.assertRaises(ValueError):
                    module.reverse_text_hygiene(result['text'], [edit])

if __name__ == '__main__':
    unittest.main()
