"""Download and unpack per-run task bundles."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from engiworld.scheduler.storage import create_s3_client

MARKER_FILENAME = ".arena_task_bundle.json"
DEFAULT_TASK_BUCKET = os.getenv("ARENA_TASK_BUCKET", "agent-eval-tasks")
DEFAULT_WAIT_TIMEOUT_SECONDS = 60 * 60
DEFAULT_LOCK_STALE_SECONDS = 60 * 60


def ensure_task_bundle(
    *,
    task_root: str | Path,
    run_id: str,
    task_file_path: str | None,
    task_bucket: str = DEFAULT_TASK_BUCKET,
    wait_timeout_seconds: int = DEFAULT_WAIT_TIMEOUT_SECONDS,
    lock_stale_seconds: int = DEFAULT_LOCK_STALE_SECONDS,
    poll_interval_seconds: float = 2.0,
) -> Path:
    """Return the local task root, downloading the run bundle when a source is given.

    Without a task source, return ``task_root`` directly.
    With ``task_file_path`` the archive is downloaded from the configured task bucket
    and unpacked into
    ``<task_root>/<run_id>``. A local
    lock directory prevents duplicate downloads by sibling worker processes on the
    same machine, while each machine still gets its own copy of the task data.
    """

    base_root = Path(task_root).expanduser().resolve()
    if not task_file_path:
        return base_root
    if not run_id:
        raise ValueError("run_id is required when downloading a task bundle")

    task_file_path = task_file_path.lstrip("/")
    base_root.mkdir(parents=True, exist_ok=True)
    target_root = base_root / _safe_path_component(run_id)
    source_uri = _source_uri(task_bucket, task_file_path)
    source_hash = _source_hash(source_uri)
    completed = _completed_task_root(target_root, source_hash)
    if completed is not None:
        return completed

    lock_dir = base_root / f".{_safe_path_component(run_id)}.download.lock"
    deadline = time.monotonic() + wait_timeout_seconds
    while True:
        try:
            lock_dir.mkdir()
            _touch_path(lock_dir)
            break
        except FileExistsError:
            completed = _completed_task_root(target_root, source_hash)
            if completed is not None:
                return completed
            if _is_stale(lock_dir, lock_stale_seconds):
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for task bundle download lock: {lock_dir}"
                )
            time.sleep(poll_interval_seconds)

    stop_heartbeat, heartbeat_thread = _start_lock_heartbeat(
        lock_dir,
        lock_stale_seconds,
    )
    try:
        completed = _completed_task_root(target_root, source_hash)
        if completed is not None:
            return completed
        return _download_and_unpack(
            task_bucket,
            task_file_path,
            target_root,
            run_id,
            source_hash,
        )
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
        shutil.rmtree(lock_dir, ignore_errors=True)


def task_bundle_target_root(task_root: str | Path, run_id: str) -> Path:
    return Path(task_root).expanduser().resolve() / _safe_path_component(run_id)


def _download_and_unpack(
    task_bucket: str,
    task_file_path: str,
    target_root: Path,
    run_id: str,
    source_hash: str,
) -> Path:
    parent = target_root.parent
    with tempfile.TemporaryDirectory(prefix=f".{target_root.name}.", dir=parent) as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / _archive_filename(task_file_path)
        extract_root = temp_path / "extract"
        extract_root.mkdir()

        _download_from_s3(task_bucket, task_file_path, archive_path)
        _extract_archive(archive_path, extract_root)
        selected_root = _select_task_root(extract_root)

        replacement_root = temp_path / "task-root"
        shutil.move(str(selected_root), replacement_root)
        if target_root.exists():
            shutil.rmtree(target_root)
        shutil.move(str(replacement_root), target_root)
        _write_marker(target_root, run_id, source_hash)
        return target_root


def _download_from_s3(task_bucket: str, task_file_path: str, archive_path: Path) -> None:
    client, settings = create_s3_client(task_bucket)
    try:
        client.download_file(settings.bucket, task_file_path, str(archive_path))
    except Exception as exc:
        raise RuntimeError(
            "Failed to download task bundle "
            f"from s3://{settings.bucket}/{task_file_path} "
            f"using endpoint={settings.endpoint_url!r}, "
            f"region={settings.region!r}, "
            f"addressing_style={settings.addressing_style!r}: {exc}"
        ) from exc


def _extract_archive(archive_path: Path, destination: Path) -> None:
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                _validate_archive_member(destination, member.filename)
            archive.extractall(destination)
        return

    try:
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk():
                    raise ValueError(f"Task archive contains unsupported link: {member.name}")
                _validate_archive_member(destination, member.name)
            archive.extractall(destination)
    except tarfile.TarError as exc:
        raise ValueError(f"Unsupported task bundle archive: {archive_path}") from exc


def _validate_archive_member(destination: Path, member_name: str) -> None:
    target = (destination / member_name).resolve()
    root = destination.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Task archive contains unsafe path: {member_name!r}")


def _select_task_root(extract_root: Path) -> Path:
    child_dirs = [path for path in extract_root.iterdir() if path.is_dir()]
    task_dir = extract_root / "task"
    if task_dir.is_dir() and _contains_task_files(task_dir):
        return task_dir
    if _looks_like_task_root(extract_root):
        return extract_root

    valid_children = [path for path in child_dirs if _contains_task_files(path)]
    if len(valid_children) == 1:
        return valid_children[0]
    if _contains_task_files(extract_root):
        return extract_root
    if not valid_children:
        raise FileNotFoundError(
            "Downloaded task bundle does not contain OSWorld V1 task-*.json or V2 task_*.py files"
        )
    valid_children.sort(key=lambda path: path.name)
    return valid_children[0]


def _contains_task_files(path: Path) -> bool:
    return any(path.glob("**/task-*.json")) or any(path.glob("**/task_*.py"))


def _looks_like_task_root(path: Path) -> bool:
    return any((path / name).exists() for name in ("task-c", "task-v", "open"))


def _completed_task_root(target_root: Path, source_hash: str) -> Path | None:
    marker = target_root / MARKER_FILENAME
    if not marker.is_file():
        return None
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("source_sha256") != source_hash:
        return None
    if not _contains_task_files(target_root):
        return None
    return target_root


def _write_marker(target_root: Path, run_id: str, source_hash: str) -> None:
    payload = {
        "run_id": run_id,
        "source_sha256": source_hash,
        "downloaded_at": int(time.time()),
        "task_root": ".",
    }
    (target_root / MARKER_FILENAME).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _archive_filename(task_file_path: str) -> str:
    filename = Path(task_file_path).name
    return filename or "task-bundle.tgz"


def _source_uri(task_bucket: str, task_file_path: str) -> str:
    return f"s3://{task_bucket}/{task_file_path}"


def _source_hash(source_uri: str) -> str:
    return hashlib.sha256(source_uri.encode("utf-8")).hexdigest()


def _safe_path_component(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")


def _is_stale(path: Path, stale_seconds: int) -> bool:
    if stale_seconds <= 0:
        return False
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    return time.time() - mtime >= stale_seconds


def _start_lock_heartbeat(
    lock_dir: Path,
    stale_seconds: int,
) -> tuple[threading.Event, threading.Thread]:
    stop = threading.Event()
    interval = 30.0
    if stale_seconds > 0:
        interval = max(1.0, min(30.0, stale_seconds / 4))
    thread = threading.Thread(
        target=_heartbeat_lock,
        args=(lock_dir, stop, interval),
        name=f"task-bundle-lock-heartbeat-{lock_dir.name}",
        daemon=True,
    )
    thread.start()
    return stop, thread


def _heartbeat_lock(lock_dir: Path, stop: threading.Event, interval: float) -> None:
    while not stop.wait(interval):
        _touch_path(lock_dir)


def _touch_path(path: Path) -> None:
    try:
        os.utime(path, None)
    except OSError:
        pass
