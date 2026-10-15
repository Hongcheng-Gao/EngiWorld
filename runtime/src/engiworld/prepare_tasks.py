"""Download complete task data before evaluation, or verify local resources offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

TASK_ROOT = Path(__file__).resolve().parents[3] / "task"
RELEASE_CONFIG = Path(__file__).with_name("data_sources.json")


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


def asset_path(root: Path, relative: str, *, cached_source: bool = False) -> Path:
    base = root.resolve()
    lexical = Path(os.path.abspath(base / relative))
    if not lexical.is_relative_to(base):
        raise ValueError(f"Asset path is outside the task root: {relative}")
    path = lexical.resolve()
    # Hub snapshots link files to their sibling blob cache. Only downloaded
    # sources may follow these links; local output paths stay within their root.
    if not cached_source and not path.is_relative_to(base):
        raise ValueError(f"Asset path is outside the task root: {relative}")
    return path


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    if algorithm == "sha1":
        digest.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_asset(path: Path, entry: dict) -> bool:
    if not path.is_file() or path.stat().st_size != entry["size"]:
        return False
    if entry.get("sha256"):
        return file_hash(path) == entry["sha256"]
    return file_hash(path, "sha1") == entry["git_blob"]


def download_snapshot(source: str, kind: str, patterns: list[str] | None = None) -> Path:
    config = json.loads(RELEASE_CONFIG.read_text(encoding="utf-8"))[source][kind]
    if source == "modelscope":
        repo = os.getenv(f"ENGIWORLD_MODELSCOPE_{kind.upper()}_REPO") or config["repo_id"]
        config = {**config, "repo_id": repo}
        if not repo:
            raise ValueError("The ModelScope mirror is not configured for this release. "
                             f"Set ENGIWORLD_MODELSCOPE_{kind.upper()}_REPO to its published dataset ID.")
    if source == "hf":
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError('Install the downloader: pip install -e ".[download]"') from exc
        return Path(snapshot_download(config["repo_id"], repo_type="dataset",
                                      revision=config["revision"], allow_patterns=patterns,
                                      token=False,
                                      headers={"Accept-Encoding": "identity"}))
    try:
        from modelscope_hub import HubApi
    except ImportError as exc:
        raise RuntimeError('Install the downloader: pip install -e ".[download]"') from exc
    return Path(HubApi(token="", endpoint=config.get("endpoint", "https://modelscope.cn")).download_repo(config["repo_id"], "dataset",
                                      revision=config["revision"], allow_patterns=patterns))


def copy_verified(source: Path, target: Path, expected: dict | None = None) -> str:
    """Preserve local edits; publish a completed copy only after checksum validation."""
    if expected and not verify_asset(source, expected):
        raise ValueError(f"Downloaded resource checksum mismatch: {source.name}")
    if target.exists():
        if (target.is_file() and source.stat().st_size == target.stat().st_size
                and file_hash(source) == file_hash(target)):
            return "present"
        raise ValueError(f"Modified local file; refusing to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".download")
    shutil.copyfile(source, partial)
    if file_hash(partial) != file_hash(source):
        raise ValueError(f"Copied resource checksum mismatch: {target}")
    partial.replace(target)
    return "downloaded"


def task_upload_paths(task_id: str, definition: dict) -> set[str]:
    """Resolve task input and evaluator uploads relative to their software directory."""
    base = Path(task_id).parent
    paths = set()
    items = [*definition.get("config", []),
             *definition.get("evaluator", {}).get("postconfig", [])]
    for item in items:
        if item.get("type") != "upload_file":
            continue
        for resource in item.get("parameters", {}).get("files", []):
            raw = resource.get("local_path")
            if not raw:
                continue
            relative = Path(os.path.normpath(base / raw))
            if relative.is_absolute() or str(relative).startswith("../") or str(relative) == "..":
                raise ValueError(f"Task resource is outside the task root: {raw}")
            paths.add(relative.as_posix())
    return paths


def prepare(root: Path, source: str, task_id: str | None = None) -> dict:
    patterns = ["task/*"]
    if task_id:
        metadata = download_snapshot(source, "tasks", ["task/aliases.json"])
        task_id = canonical_task(metadata / "task", task_id)
        patterns = ["task/aliases.json", "task/assets-manifest.json", "task/taxonomy.json",
                    "task/resources-integrity.json", "task/splits/*", f"task/{task_id}/*"]
    snapshot = download_snapshot(source, "tasks", patterns) / "task"
    _, entries = asset_entries(snapshot, task_id)
    required_paths = set()
    if task_id:
        folder = asset_path(snapshot, task_id)
        if not (folder / f"{folder.name}.json").is_file():
            raise ValueError(f"Unknown task: {task_id}")
        definition = json.loads((folder / f"{folder.name}.json").read_text())
        required_paths = task_upload_paths(task_id, definition)
        shared = sorted(path for path in required_paths if not path.startswith(task_id + "/"))
        if shared:
            patterns += ["task/" + path for path in shared]
            snapshot = download_snapshot(source, "tasks", patterns) / "task"
            _, all_entries = asset_entries(snapshot)
            entries += [e for e in all_entries if e["path"] in shared]
        for path in required_paths:
            if not asset_path(snapshot, path, cached_source=True).is_file():
                raise ValueError(f"Downloaded task resource is missing: {path}")
    expected = {entry["path"]: entry for entry in entries}
    invalid = [entry["path"] for entry in entries
               if not verify_asset(asset_path(snapshot, entry["path"], cached_source=True), entry)]
    if invalid:
        raise ValueError(f"Downloaded dataset is incomplete or corrupt: {invalid[:10]}")
    counts: dict[str, int] = {}
    for path in sorted(snapshot.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(snapshot).as_posix()
        # The code repository keeps its own ignore policy for large local resources.
        if relative == ".gitignore" and (root / relative).exists():
            continue
        if task_id and relative not in required_paths and relative not in {"aliases.json", "assets-manifest.json", "taxonomy.json",
                                       "resources-integrity.json"} and not relative.startswith((task_id + "/", "splits/")):
            continue
        status = copy_verified(path, asset_path(root, relative), expected.get(relative))
        counts[status] = counts.get(status, 0) + 1
    return {"source": source, "task_root": str(root), "resources_verified": len(entries), **counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", type=Path, default=TASK_ROOT)
    parser.add_argument("--source", choices=("hf", "modelscope"), default="hf")
    parser.add_argument("--task", help="Optional task directory or JSON ID; default: all 1,301 tasks")
    parser.add_argument("--check", action="store_true", help="Verify local files without network access")
    args = parser.parse_args(argv)
    root = args.task_root.resolve()
    if args.check:
        _, entries = asset_entries(root, args.task)
        if args.task:
            folder = asset_path(root, canonical_task(root, args.task))
            if not (folder / f"{folder.name}.json").is_file():
                parser.error(f"Unknown task: {args.task}")
        invalid = [entry["path"] for entry in entries
                   if not verify_asset(asset_path(root, entry["path"]), entry)]
        print(json.dumps({"checked": len(entries), "missing_or_modified": invalid}, indent=2))
        return int(bool(invalid))
    print(json.dumps(prepare(root, args.source, args.task), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
