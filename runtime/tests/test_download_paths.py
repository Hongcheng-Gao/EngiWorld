import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engiworld.prepare_tasks import asset_path, copy_verified, prepare, task_upload_paths


class DownloadPathTests(unittest.TestCase):
    def test_hub_blob_link_can_be_verified_and_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshots" / "revision"
            (snapshot / "images").mkdir(parents=True)
            blob = root / "blobs" / "content"
            blob.parent.mkdir()
            blob.write_bytes(b"image archive")
            (snapshot / "images" / "example.zst").symlink_to(blob)
            output = root / "output"
            output.mkdir()
            source = asset_path(snapshot, "images/example.zst", cached_source=True)
            target = asset_path(output, "images/example.zst")
            copy_verified(source, target, {"size": 13, "sha256": hashlib.sha256(blob.read_bytes()).hexdigest()})
            self.assertEqual(target.read_bytes(), blob.read_bytes())

    def test_output_symlink_cannot_write_outside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "output").mkdir()
            (root / "outside").mkdir()
            (root / "output" / "images").symlink_to(root / "outside")
            with self.assertRaises(ValueError):
                asset_path(root / "output", "images/example.zst")

    def test_source_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("../outside", "/etc/passwd"):
                with self.assertRaises(ValueError):
                    asset_path(root, relative, cached_source=True)

    def test_single_task_download_includes_shared_evaluator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / 'snapshot'
            task_id = 'single-software-execution/cli/floris/task-01'
            folder = snapshot / 'task' / task_id
            folder.mkdir(parents=True)
            helper = folder.parent / 'eval_utils.py'
            helper.write_text('VALUE = 1\n')
            definition = {'evaluator': {'postconfig': [{'type': 'upload_file',
                'parameters': {'files': [{'local_path': 'eval_utils.py'}]}}]}}
            (folder / 'task-01.json').write_text(json.dumps(definition))
            (snapshot / 'task/aliases.json').write_text('{}')
            (snapshot / 'task/assets-manifest.json').write_text(json.dumps({'assets': []}))
            output = root / 'output'
            with patch('engiworld.prepare_tasks.download_snapshot', return_value=snapshot) as download:
                prepare(output, 'hf', task_id)
            self.assertEqual((output / task_id).parent.joinpath('eval_utils.py').read_text(), 'VALUE = 1\n')
            self.assertIn('task/single-software-execution/cli/floris/eval_utils.py',
                          download.call_args.args[2])

    def test_shared_resource_cannot_escape_task_root(self):
        definition = {'config': [{'type': 'upload_file', 'parameters': {
            'files': [{'local_path': '../../../../../outside'}]}}]}
        with self.assertRaises(ValueError):
            task_upload_paths('category/cli/software/task-01', definition)


if __name__ == "__main__":
    unittest.main()
