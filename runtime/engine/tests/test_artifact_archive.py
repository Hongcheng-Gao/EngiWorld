import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from desktop_env.server.artifact_archive import (
    MissingArtifactPathsError,
    write_artifact_archive,
)


class ArtifactArchiveTests(unittest.TestCase):
    def test_recursively_archives_directory_and_preserves_empty_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "final-project"
            nested = project / "nested"
            empty = project / "empty"
            nested.mkdir(parents=True)
            empty.mkdir()
            (project / ".metadata").write_text("meta", encoding="utf-8")
            (nested / "result.txt").write_text("done", encoding="utf-8")

            output = io.BytesIO()
            entries = write_artifact_archive([str(project)], output)

            self.assertEqual(entries, [{
                "source_path": str(project),
                "archive_path": "000-final-project",
                "type": "directory",
            }])
            output.seek(0)
            with tarfile.open(fileobj=output, mode="r:gz") as archive:
                names = set(archive.getnames())
                self.assertIn("000-final-project", names)
                self.assertIn("000-final-project/.metadata", names)
                self.assertIn("000-final-project/empty", names)
                self.assertIn("000-final-project/nested/result.txt", names)
                result = archive.extractfile("000-final-project/nested/result.txt")
                self.assertIsNotNone(result)
                self.assertEqual(result.read(), b"done")

    def test_files_and_same_named_directories_get_distinct_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first" / "output"
            second = root / "second" / "output"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "first.txt").write_text("first", encoding="utf-8")
            (second / "second.txt").write_text("second", encoding="utf-8")
            summary = root / "summary.txt"
            summary.write_text("summary", encoding="utf-8")

            output = io.BytesIO()
            write_artifact_archive([str(first), str(second), str(summary)], output)

            output.seek(0)
            with tarfile.open(fileobj=output, mode="r:gz") as archive:
                names = set(archive.getnames())
                self.assertIn("000-output/first.txt", names)
                self.assertIn("001-output/second.txt", names)
                self.assertIn("002-summary.txt", names)

    def test_expands_environment_variables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            old_value = os.environ.get("OSWORLD_ARTIFACT_TEST_ROOT")
            os.environ["OSWORLD_ARTIFACT_TEST_ROOT"] = temp_dir
            try:
                output = io.BytesIO()
                entries = write_artifact_archive(
                    ["$OSWORLD_ARTIFACT_TEST_ROOT/project"],
                    output,
                )
            finally:
                if old_value is None:
                    os.environ.pop("OSWORLD_ARTIFACT_TEST_ROOT", None)
                else:
                    os.environ["OSWORLD_ARTIFACT_TEST_ROOT"] = old_value

            self.assertEqual(entries[0]["source_path"], str(project))

    def test_missing_path_fails_instead_of_creating_partial_archive(self):
        output = io.BytesIO()
        with self.assertRaises(MissingArtifactPathsError) as context:
            write_artifact_archive(["/path/that/does/not/exist"], output)

        self.assertEqual(context.exception.paths, ["/path/that/does/not/exist"])
        self.assertEqual(output.getvalue(), b"")


if __name__ == "__main__":
    unittest.main()
