import os
import tarfile
from typing import BinaryIO, Iterable


class MissingArtifactPathsError(FileNotFoundError):
    def __init__(self, paths: list[str]):
        self.paths = paths
        super().__init__(f"Artifact paths not found: {', '.join(paths)}")


class UnsupportedArtifactPathsError(ValueError):
    def __init__(self, paths: list[str]):
        self.paths = paths
        super().__init__(f"Artifact paths must be files or directories: {', '.join(paths)}")


def write_artifact_archive(paths: Iterable[str], output: BinaryIO) -> list[dict[str, str]]:
    """Write files and recursively collected directories to a gzipped tar stream."""
    expanded_paths = []
    for path in paths:
        expanded = os.path.expandvars(os.path.expanduser(str(path)))
        expanded_paths.append(os.path.normpath(expanded) if os.path.exists(expanded) else expanded)
    missing_paths = [path for path in expanded_paths if not os.path.exists(path)]
    if missing_paths:
        raise MissingArtifactPathsError(missing_paths)

    unsupported_paths = [
        path
        for path in expanded_paths
        if not os.path.isfile(path) and not os.path.isdir(path)
    ]
    if unsupported_paths:
        raise UnsupportedArtifactPathsError(unsupported_paths)

    entries = []
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for index, path in enumerate(expanded_paths):
            basename = os.path.basename(os.path.normpath(path)) or "artifact"
            archive_path = f"{index:03d}-{basename}"
            archive.add(path, arcname=archive_path, recursive=True)
            entries.append({
                "source_path": path,
                "archive_path": archive_path,
                "type": "directory" if os.path.isdir(path) else "file",
            })
    return entries
