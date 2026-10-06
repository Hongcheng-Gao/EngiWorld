"""Restore released task assets from the immutable final-branch source version."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

TASK_ROOT = Path(__file__).resolve().parents[3] / "task"
_FETCH_LOCK = threading.Lock()


def authenticated_git_asset(root: Path, manifest: dict, entry: dict) -> bytes:
    """Use the same Git credential setup as clone for non-public raw URLs."""
    with _FETCH_LOCK:
        available = subprocess.run(
            ["git", "cat-file", "-e", entry["git_blob"]], cwd=root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if available.returncode:
            print("Fetching the pinned task source with Git credentials; "
                  "this can download more than the selected task's assets.", flush=True)
            subprocess.run(
                ["git", "fetch", "--no-tags", "--depth=1", manifest["source_repository"],
                 manifest["revision"]], cwd=root, check=True,
            )
    return subprocess.check_output(["git", "cat-file", "blob", entry["git_blob"]], cwd=root)


def canonical_task(root: Path, task_id: str) -> str:
    aliases_path = root / "aliases.json"
    aliases = json.loads(aliases_path.read_text(encoding="utf-8")) if aliases_path.exists() else {}
    return aliases.get(task_id.strip("/"), task_id.strip("/"))


def asset_entries(root: Path, task_id: str | None = None) -> tuple[dict, list[dict]]:
    manifest = json.loads((root / "assets-manifest.json").read_text(encoding="utf-8"))
    entries = manifest["assets"]
    if task_id:
        prefix = canonical_task(root, task_id) + "/"
        entries = [entry for entry in entries if entry["path"].startswith(prefix)]
    return manifest, entries


def blob_hash(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def asset_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Asset path is outside the task root: {relative}")
    return path


def verify_asset(path: Path, entry: dict) -> bool:
    return (path.is_file() and path.stat().st_size == entry["size"]
            and blob_hash(path.read_bytes()) == entry["git_blob"])


def restore_asset(root: Path, manifest: dict, entry: dict) -> str:
    target = asset_path(root, entry["path"])
    if target.exists():
        if verify_asset(target, entry):
            return "present"
        raise ValueError(f"Modified asset; refusing to overwrite: {target}")
    data = None
    # Developers with the final branch already fetched can use its verified blobs.
    try:
        cached = subprocess.run(
            ["git", "cat-file", "blob", entry["git_blob"]], cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if cached.returncode == 0:
            data = cached.stdout
    except FileNotFoundError:
        pass
    if data is None:
        repository = manifest["source_repository"].removeprefix("https://github.com/")
        url = (f"https://raw.githubusercontent.com/{repository}/{manifest['revision']}/"
               + quote(entry["source"], safe="/"))
        for attempt in range(3):
            try:
                with urlopen(url, timeout=120) as response:
                    data = response.read()
                break
            except HTTPError as exc:
                if exc.code in {401, 403, 404}:
                    data = authenticated_git_asset(root, manifest, entry)
                    break
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    if len(data) != entry["size"] or blob_hash(data) != entry["git_blob"]:
        raise ValueError(f"Asset checksum mismatch: {entry['path']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".download")
    partial.write_bytes(data)
    partial.replace(target)
    return "restored"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", type=Path, default=TASK_ROOT)
    parser.add_argument("--task", help="Optional exact task directory ID; defaults to all 1,301 tasks")
    parser.add_argument("--check", action="store_true", help="Verify files without downloading")
    args = parser.parse_args(argv)
    root = args.task_root.resolve()
    if args.task:
        task_id = canonical_task(root, args.task)
        task_dir = asset_path(root, task_id)
        if not (task_dir / f"{task_dir.name}.json").is_file():
            parser.error(f"Unknown task: {args.task}")
    manifest, entries = asset_entries(root, args.task)
    if args.check:
        invalid = [entry["path"] for entry in entries
                   if not verify_asset(asset_path(root, entry["path"]), entry)]
        print(json.dumps({"checked": len(entries), "missing_or_modified": invalid}, indent=2))
        return int(bool(invalid))
    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, status in enumerate(pool.map(lambda item: restore_asset(root, manifest, item), entries), 1):
            counts[status] = counts.get(status, 0) + 1
            if index % 50 == 0:
                print(f"Task assets: {index}/{len(entries)}", flush=True)
    print(json.dumps({"revision": manifest["revision"], **counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
