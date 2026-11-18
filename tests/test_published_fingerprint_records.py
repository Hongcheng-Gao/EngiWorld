"""Run with python -m unittest discover -s tests -p 'test_published_fingerprint_records.py'."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((Path(__file__).parent / 'fixtures/published_fingerprint_records.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()


class PublishedFingerprintRecords(unittest.TestCase):
    def test_published_files_match_records_and_reject_content_changes(self):
        self.assertEqual(len(CASES), 40)
        for case in CASES:
            with self.subTest(case=case['case_id']):
                module = runpy.run_path(str(ROOT / case['evaluator']))
                compare = module.get('published_sha256_matches')
                for record in case['revisions']:
                    raw = (ROOT / record['path']).read_bytes()
                    actual = sha(raw)
                    self.assertEqual(actual, record['published_sha256'])
                    mutated = sha(raw + b'content revision')
                    if compare:
                        self.assertTrue(compare(actual, record['recorded_sha256']))
                        self.assertTrue(compare(record['recorded_sha256'], actual))
                        self.assertFalse(compare(mutated, record['recorded_sha256']))
                        self.assertFalse(compare(actual, '0' * 64))
                    elif record['reason'] == 'line_endings':
                        pinned = [v for v in module.values() if isinstance(v, str)]
                        pinned += [v for obj in module.values() if isinstance(obj, dict)
                                   for v in obj.values() if isinstance(v, str)]
                        self.assertIn(actual, [value.lower() for value in pinned])
                        self.assertNotIn(mutated, [value.lower() for value in pinned])
                if compare:
                    self.assertFalse(compare('a' * 64, 'b' * 64))
                    self.assertFalse(compare(None, 'a' * 64))
                    self.assertTrue(compare('unchanged', 'unchanged'))
                    self.assertFalse(compare(1, 2))
                if 'published_sha256_chain' in module:
                    record = case['revisions'][0]
                    chain = module['published_sha256_chain']
                    self.assertTrue(chain(record['recorded_sha256'], record['recorded_sha256'], record['published_sha256']))
                    self.assertFalse(chain(record['recorded_sha256'], '0' * 64, record['published_sha256']))
                if 'published_token_in_text' in module:
                    contains = module['published_token_in_text']
                    self.assertTrue(contains('CaseID', 'CaseID'))
                    self.assertFalse(contains('CaseID', 'caseid'))

    def test_recorded_sizes_bind_to_exact_file_bytes(self):
        for case in CASES:
            module = runpy.run_path(str(ROOT / case['evaluator']))
            compare = module.get('published_size_matches')
            if compare is None:
                continue
            for record in case['revisions']:
                with self.subTest(case=case['case_id'], path=record['path']):
                    path = ROOT / record['path']
                    self.assertTrue(compare(path, record['recorded_bytes']))
                    self.assertFalse(compare(path, record['recorded_bytes'] + 1_000_000))
                    with tempfile.TemporaryDirectory() as tmp:
                        altered = Path(tmp) / path.name
                        raw = bytearray(path.read_bytes())
                        raw[len(raw) // 2] ^= 1
                        altered.write_bytes(raw)
                        if record['published_bytes'] != record['recorded_bytes']:
                            self.assertFalse(compare(altered, record['recorded_bytes']))

    def test_recorded_hash_prefixes_remain_bound(self):
        for case in CASES:
            module = runpy.run_path(str(ROOT / case['evaluator']))
            contains = module.get('published_sha256_in_text')
            if contains is None:
                continue
            for record in case['revisions']:
                for length in (12, 64):
                    with self.subTest(case=case['case_id'], path=record['path'], length=length):
                        old, new = record['recorded_sha256'], record['published_sha256']
                        self.assertTrue(contains(new, old[:length].upper(), length))
                        self.assertTrue(contains(old, new[:length].upper(), length))
                        self.assertFalse(contains(new, '0' * length, length))

    def test_png_metadata_and_notes_revisions(self):
        for case in CASES:
            if 'png' not in case:
                continue
            module = runpy.run_path(str(ROOT / case['evaluator']))
            png = case['png']
            path = ROOT / png['path']
            match = module['artifact_sha256_matches']
            self.assertTrue(match(path, png['recorded_sha256']))
            self.assertFalse(match(path, '0' * 64))
            with tempfile.TemporaryDirectory() as tmp:
                altered = Path(tmp) / path.name
                raw = bytearray(path.read_bytes())
                raw[len(raw) // 2] ^= 1
                altered.write_bytes(raw)
                self.assertFalse(match(altered, png['recorded_sha256']))
                altered.write_bytes(path.read_bytes()[:-5])
                self.assertFalse(match(altered, png['recorded_sha256']))
            for record in case['revisions']:
                if record['reason'] != 'published_notes_revision':
                    continue
                path = ROOT / record['path']
                matcher = module['text_sha256_matches']
                self.assertTrue(matcher(path, record['recorded_sha256']))
                with tempfile.TemporaryDirectory() as tmp:
                    altered = Path(tmp) / path.name
                    altered.write_bytes(path.read_bytes() + b'\ncontent revision\n')
                    self.assertFalse(matcher(altered, record['recorded_sha256']))
                    renamed = Path(tmp) / 'unrelated.md'
                    renamed.write_bytes(path.read_bytes())
                    self.assertFalse(matcher(renamed, record['recorded_sha256']))


if __name__ == '__main__':
    unittest.main()
