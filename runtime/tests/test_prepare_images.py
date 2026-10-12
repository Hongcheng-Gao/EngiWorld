import json
from pathlib import Path

import pytest

from engiworld import prepare_images, prepare_tasks


@pytest.mark.parametrize("source", ["hf", "modelscope"])
def test_selected_archive_is_verified_and_offline_check_uses_local_files(tmp_path, monkeypatch, source):
    snapshot = tmp_path / "snapshot"
    archive = snapshot / "images/example.qcow2.zst"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"compressed image")
    manifest = {"images": [{"name": "Example", "path_in_repo": "images/example.qcow2.zst",
                           "package_bytes": archive.stat().st_size,
                           "package_sha256": prepare_tasks.file_hash(archive)}]}
    (snapshot / "manifest.json").write_text(json.dumps(manifest))
    (snapshot / "SHA256SUMS").write_text("checksums")
    (snapshot / "README.md").write_text("images")
    monkeypatch.setattr(prepare_images, "download_snapshot", lambda *args: snapshot)
    root = tmp_path / "local"
    arguments = ["--source", source, "--image", "Example", "--image-root", str(root)]
    assert prepare_images.main(arguments) == 0
    monkeypatch.setattr(prepare_images, "download_snapshot", lambda *args: pytest.fail("offline check accessed Hub"))
    assert prepare_images.main(arguments + ["--check"]) == 0
    (root / "images/example.qcow2.zst").write_bytes(b"corrupt")
    assert prepare_images.main(arguments + ["--check"]) == 1


def test_unknown_snapshot_is_reported_before_downloading_archive():
    with pytest.raises(ValueError, match="unavailable"):
        prepare_images.image_entries({"images": []}, ["Unavailable"])
