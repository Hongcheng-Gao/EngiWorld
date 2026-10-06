#!/usr/bin/env python3
"""Cross-platform, dependency-free updater for the OSWorld VM server."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any


RELEASE_MARKER = ".arena-osworld-release.json"
IGNORED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
IGNORED_FILES = {RELEASE_MARKER, ".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".swp"}
PRESERVED_RUNTIME_FILES = {"_launcher.py"}


def _posix_install_identity(path: Path) -> tuple[int, int, int] | None:
    if os.name == "nt" or not path.is_dir():
        return None
    details = path.stat()
    return details.st_uid, details.st_gid, stat.S_IMODE(details.st_mode)


def _apply_posix_install_identity(
    root: Path,
    identity: tuple[int, int, int] | None,
) -> None:
    if identity is None or os.name == "nt":
        return
    uid, gid, root_mode = identity
    for current_root, directories, files in os.walk(root):
        current = Path(current_root)
        os.chown(current, uid, gid)
        for name in directories:
            os.chown(current / name, uid, gid)
        for name in files:
            os.chown(current / name, uid, gid)
    os.chmod(root, root_mode)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(
    root: Path,
    *,
    extra_ignored_files: set[str] | frozenset[str] = frozenset(),
) -> str:
    """Hash stable relative paths and file contents, excluding runtime caches."""
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"OSWorld directory not found: {root}")

    digest = hashlib.sha256()
    for current_root, directories, files in os.walk(root):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
        )
        for filename in sorted(files):
            if (
                filename in IGNORED_FILES
                or filename in extra_ignored_files
                or Path(filename).suffix in IGNORED_SUFFIXES
            ):
                continue
            path = Path(current_root) / filename
            if path.is_symlink():
                raise ValueError(f"Symbolic links are not supported in OSWorld bundles: {path}")
            relative = path.relative_to(root).as_posix()
            digest.update(b"file\0")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()


def build_manifest(
    archive_path: Path,
    content_dir: Path,
    version: str,
    root_dir: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "bundle_type": "osworld-vm-server",
        "version": version,
        "root_dir": root_dir,
        "archive_sha256": file_sha256(archive_path),
        "content_sha256": tree_sha256(content_dir),
        "archive_size_bytes": archive_path.stat().st_size,
        "created_at": int(time.time()),
    }


def _validate_sha256(value: str, name: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ValueError(f"{name} must be a lowercase or uppercase SHA256 hex digest")
    return normalized


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "arena-osworld-updater/1"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def _safe_extract(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"Unsafe archive member type: {member.name}")
            target = (destination / member.name).resolve()
            if os.path.commonpath([str(destination), str(target)]) != str(destination):
                raise ValueError(f"Archive member escapes staging directory: {member.name}")
        archive.extractall(destination, members=members)


def _resolve_staging_root(staging_dir: Path, root_dir: str) -> Path:
    if not root_dir or Path(root_dir).is_absolute():
        raise ValueError(f"Bundle root_dir must be a relative path: {root_dir!r}")
    staging_dir = staging_dir.resolve()
    extracted_root = (staging_dir / root_dir).resolve()
    if os.path.commonpath([str(staging_dir), str(extracted_root)]) != str(staging_dir):
        raise ValueError(f"Bundle root_dir escapes staging directory: {root_dir!r}")
    return extracted_root


def _run_command(command: list[str], label: str, *, tolerate_failure: bool = False) -> None:
    if not command:
        return
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode == 0 or tolerate_failure:
        return
    output = (result.stderr or result.stdout or "").strip()
    raise RuntimeError(f"{label} failed with exit code {result.returncode}: {output}")


def _listener_port(config: dict[str, Any]) -> int | None:
    raw_port = config.get("listener_port")
    if raw_port in {None, "", 0, "0"}:
        return None
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"listener_port must be an integer: {raw_port!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"listener_port must be between 1 and 65535: {port}")
    return port


def _windows_stop_listener_command(port: int, timeout_seconds: int = 30) -> list[str]:
    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$Port = {port}; $Deadline = (Get-Date).AddSeconds({timeout_seconds}); "
        "do { "
        "$Connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen "
        "-ErrorAction SilentlyContinue); "
        "$Owners = @($Connections | Select-Object -ExpandProperty OwningProcess -Unique); "
        "foreach ($OwnerProcessId in $Owners) { "
        "if ($OwnerProcessId -gt 0) { "
        "& taskkill.exe /PID $OwnerProcessId /T /F 2>$null | Out-Null "
        "} }; "
        "if ($Connections.Count -eq 0) { exit 0 }; "
        "Start-Sleep -Milliseconds 500 "
        "} while ((Get-Date) -lt $Deadline); "
        "$Remaining = @(Get-NetTCPConnection -LocalPort $Port -State Listen "
        "-ErrorAction SilentlyContinue); "
        "if ($Remaining.Count -gt 0) { "
        "throw \"Timed out waiting for TCP port $Port to be released; owning PIDs: "
        "$($Remaining.OwningProcess -join ',')\" "
        "}"
    )
    return [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]


def _stop_configured_listener(
    config: dict[str, Any],
    *,
    tolerate_failure: bool = False,
) -> None:
    port = _listener_port(config)
    if port is None or os.name != "nt":
        return
    _run_command(
        _windows_stop_listener_command(port),
        f"stop listener on TCP port {port}",
        tolerate_failure=tolerate_failure,
    )


def _wait_for_health(url: str, expected_content_sha256: str, timeout_seconds: int) -> None:
    if not url:
        return
    deadline = time.time() + timeout_seconds
    last_error = "no response"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            actual = str(payload.get("content_sha256") or "").lower()
            if payload.get("status") == "ok" and actual == expected_content_sha256:
                return
            last_error = f"unexpected health payload: {payload}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(2)
    raise TimeoutError(f"OSWorld health check timed out: {last_error}")


def _load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Updater config must be a JSON object: {path}")
    if not payload.get("current_dir"):
        raise ValueError(f"Updater config is missing current_dir: {path}")
    return payload


def _rename_with_retry(source: Path, destination: Path, attempts: int = 10) -> None:
    for attempt in range(1, attempts + 1):
        try:
            source.rename(destination)
            return
        except OSError:
            if attempt >= attempts:
                raise
            time.sleep(1)


def _remove_tree_with_retry(path: Path, attempts: int = 10) -> None:
    for attempt in range(1, attempts + 1):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            if attempt >= attempts:
                raise
            time.sleep(1)


def _write_marker(
    root: Path,
    *,
    version: str,
    archive_sha256: str,
    content_sha256: str,
) -> None:
    payload = {
        "version": version,
        "archive_sha256": archive_sha256,
        "content_sha256": content_sha256,
        "installed_at": int(time.time()),
    }
    (root / RELEASE_MARKER).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _preserve_runtime_files(current_dir: Path, replacement_dir: Path) -> list[str]:
    preserved: list[str] = []
    if not current_dir.is_dir():
        return preserved
    for filename in sorted(PRESERVED_RUNTIME_FILES):
        source = current_dir / filename
        destination = replacement_dir / filename
        if not source.is_file() or source.is_symlink() or destination.exists():
            continue
        shutil.copy2(source, destination)
        preserved.append(filename)
    return preserved


@contextmanager
def _update_lock(lock_path: Path, stale_seconds: int = 1800):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        age = time.time() - lock_path.stat().st_mtime
        if age <= stale_seconds:
            raise RuntimeError(f"Another OSWorld update is in progress: {lock_path}")
        lock_path.unlink()
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def apply_update(
    *,
    config_path: Path,
    url: str,
    archive_sha256: str,
    content_sha256: str,
    version: str,
    root_dir: str,
    skip_health: bool = False,
) -> dict[str, Any]:
    archive_sha256 = _validate_sha256(archive_sha256, "archive_sha256")
    content_sha256 = _validate_sha256(content_sha256, "content_sha256")
    config = _load_config(config_path)
    current_dir = Path(os.path.expandvars(os.path.expanduser(config["current_dir"]))).resolve()
    install_identity = _posix_install_identity(current_dir)
    parent_dir = current_dir.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    lock_path = parent_dir / ".arena-osworld-update.lock"

    with _update_lock(lock_path):
        stop_command = [str(item) for item in config.get("stop_command") or []]
        start_command = [str(item) for item in config.get("start_command") or []]
        if current_dir.is_dir():
            local_content_sha256 = tree_sha256(
                current_dir,
                extra_ignored_files=PRESERVED_RUNTIME_FILES,
            )
            if local_content_sha256 == content_sha256:
                _write_marker(
                    current_dir,
                    version=version,
                    archive_sha256=archive_sha256,
                    content_sha256=content_sha256,
                )
                if not skip_health:
                    health_url = str(config.get("health_url") or "")
                    health_timeout = int(config.get("health_timeout_seconds") or 90)
                    try:
                        _wait_for_health(health_url, content_sha256, min(5, health_timeout))
                    except Exception:
                        _run_command(stop_command, "restart stop command")
                        _stop_configured_listener(config)
                        _run_command(start_command, "restart start command")
                        _wait_for_health(health_url, content_sha256, health_timeout)
                return {
                    "status": "unchanged",
                    "version": version,
                    "content_sha256": content_sha256,
                    "downloaded": False,
                }

        token = uuid.uuid4().hex
        archive_path = parent_dir / f".arena-osworld-{token}.tgz"
        staging_dir = parent_dir / f".arena-osworld-staging-{token}"
        backup_dir = parent_dir / ".arena-osworld-backup"
        failed_dir = parent_dir / f".arena-osworld-failed-{token}"
        switched = False
        old_installation = current_dir.exists()
        try:
            _download(url, archive_path)
            actual_archive_sha256 = file_sha256(archive_path)
            if actual_archive_sha256 != archive_sha256:
                raise ValueError(
                    "Downloaded archive SHA256 mismatch: "
                    f"expected={archive_sha256}, actual={actual_archive_sha256}"
                )

            staging_dir.mkdir()
            _safe_extract(archive_path, staging_dir)
            extracted_root = _resolve_staging_root(staging_dir, root_dir)
            actual_content_sha256 = tree_sha256(extracted_root)
            if actual_content_sha256 != content_sha256:
                raise ValueError(
                    "Extracted OSWorld SHA256 mismatch: "
                    f"expected={content_sha256}, actual={actual_content_sha256}"
                )
            _write_marker(
                extracted_root,
                version=version,
                archive_sha256=archive_sha256,
                content_sha256=content_sha256,
            )
            preserved_runtime_files = _preserve_runtime_files(
                current_dir,
                extracted_root,
            )
            _apply_posix_install_identity(extracted_root, install_identity)

            _run_command(stop_command, "stop command")
            _stop_configured_listener(config)
            if backup_dir.exists():
                _remove_tree_with_retry(backup_dir)
            if old_installation:
                _rename_with_retry(current_dir, backup_dir)
            _rename_with_retry(extracted_root, current_dir)
            switched = True

            _run_command(start_command, "start command")
            if not skip_health:
                _wait_for_health(
                    str(config.get("health_url") or ""),
                    content_sha256,
                    int(config.get("health_timeout_seconds") or 90),
                )
            if backup_dir.exists():
                _remove_tree_with_retry(backup_dir)
            return {
                "status": "updated",
                "version": version,
                "content_sha256": content_sha256,
                "archive_sha256": archive_sha256,
                "downloaded": True,
                "preserved_runtime_files": preserved_runtime_files,
            }
        except Exception:
            if switched:
                _run_command(stop_command, "rollback stop command", tolerate_failure=True)
                _stop_configured_listener(config, tolerate_failure=True)
                if current_dir.exists():
                    _rename_with_retry(current_dir, failed_dir)
                if backup_dir.exists():
                    _rename_with_retry(backup_dir, current_dir)
                _run_command(start_command, "rollback start command", tolerate_failure=True)
            raise
        finally:
            if archive_path.exists():
                archive_path.unlink()
            if staging_dir.exists():
                _remove_tree_with_retry(staging_dir)
            if failed_dir.exists():
                _remove_tree_with_retry(failed_dir)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--config", required=True)
    apply_parser.add_argument("--url", required=True)
    apply_parser.add_argument("--archive-sha256", required=True)
    apply_parser.add_argument("--content-sha256", required=True)
    apply_parser.add_argument("--version", required=True)
    apply_parser.add_argument("--root-dir", default="osworld")
    apply_parser.add_argument("--skip-health", action="store_true")

    hash_parser = subparsers.add_parser("hash-tree")
    hash_parser.add_argument("path")

    manifest_parser = subparsers.add_parser("build-manifest")
    manifest_parser.add_argument("--archive", required=True)
    manifest_parser.add_argument("--content-dir", required=True)
    manifest_parser.add_argument("--version", required=True)
    manifest_parser.add_argument("--root-dir", default="osworld")
    manifest_parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "hash-tree":
            print(tree_sha256(Path(args.path)))
            return 0
        if args.command == "build-manifest":
            manifest = build_manifest(
                Path(args.archive),
                Path(args.content_dir),
                args.version,
                args.root_dir,
            )
            Path(args.output).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(json.dumps(manifest, ensure_ascii=False))
            return 0

        result = apply_update(
            config_path=Path(args.config),
            url=args.url,
            archive_sha256=args.archive_sha256,
            content_sha256=args.content_sha256,
            version=args.version,
            root_dir=args.root_dir,
            skip_health=args.skip_health,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "failed", "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
