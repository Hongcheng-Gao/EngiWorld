"""Artifact storage adapter for OSWorld task outputs."""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

from engiworld.scheduler.schemas import EvalConfig, TaskSpec


def task_artifact_object_key(eval_config: EvalConfig, task: TaskSpec, attempt: int) -> str:
    return "/".join(
        [
            _safe_path_component(_task_batch_suffix(eval_config, task)),
            _safe_path_component(eval_config.run_id),
            _archive_filename(task, attempt),
        ]
    )


def upload_task_artifacts(
    eval_config: EvalConfig,
    task: TaskSpec,
    attempt: int,
    local_result_dir: str,
) -> str | None:
    result_path = Path(local_result_dir)
    if not result_path.exists():
        return None

    write_artifact_manifest(result_path, eval_config, task, attempt)
    if not eval_config.s3_upload:
        return None

    object_key = task_artifact_object_key(eval_config, task, attempt)
    with tempfile.TemporaryDirectory(prefix="arena-artifact-") as temp_dir:
        archive_path = Path(temp_dir) / _archive_filename(task, attempt)
        create_result_archive(result_path, archive_path)
        remote_uri = upload_file_to_s3(
            archive_path,
            object_key,
            bucket_name=eval_config.s3_bucket,
        )

    if not eval_config.keep_local_results:
        delete_local_directory(result_path)
        prune_empty_parents(result_path.parent, Path(eval_config.result_dir).resolve())

    return remote_uri


def create_result_archive(result_path: Path, archive_path: Path) -> None:
    if not result_path.is_dir():
        raise NotADirectoryError(f"Local result directory not found: {result_path}")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(result_path, arcname=result_path.name)


def write_artifact_manifest(
    result_path: Path,
    eval_config: EvalConfig,
    task: TaskSpec,
    attempt: int,
) -> None:
    files = [
        {
            "path": path.relative_to(result_path).as_posix(),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(result_path.rglob("*"))
        if path.is_file() and path.name != "artifact_manifest.json"
    ]
    payload = {
        "run_id": eval_config.run_id,
        "task_id": task.task_id,
        "base_task_id": task.metadata.get("base_task_id", task.task_id),
        "attempt": attempt,
        "created_at": int(time.time()),
        "files": files,
    }
    (result_path / "artifact_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upload_file_to_s3(
    local_file: Path,
    object_key: str,
    bucket_name: str | None = None,
) -> str:
    client, settings = create_s3_client(bucket_name)
    try:
        client.upload_file(str(local_file), settings.bucket, object_key)
    except Exception as exc:
        raise RuntimeError(
            "Failed to upload "
            f"{local_file} to s3://{settings.bucket}/{object_key} "
            f"using endpoint={settings.endpoint_url!r}, "
            f"region={settings.region!r}, "
            f"addressing_style={settings.addressing_style!r}: {exc}"
        ) from exc
    return f"s3://{settings.bucket}/{object_key}"


def create_s3_client(bucket_name: str | None = None):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise ImportError(
            "boto3 is required for S3 artifact upload/download. Install worker "
            'dependencies with: pip install -e ".[worker-api]"'
        ) from exc

    settings = _s3_settings(bucket_name)
    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.region,
        "endpoint_url": settings.endpoint_url,
        "config": Config(
            signature_version=settings.signature_version,
            s3={"addressing_style": settings.addressing_style},
        ),
    }
    if settings.access_key_id and settings.secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.access_key_id
        client_kwargs["aws_secret_access_key"] = settings.secret_access_key
    if settings.session_token:
        client_kwargs["aws_session_token"] = settings.session_token

    return boto3.client(**client_kwargs), settings


def delete_local_directory(local_dir: Path) -> None:
    if local_dir.exists():
        shutil.rmtree(local_dir)


def prune_empty_parents(path: Path, stop_at: Path) -> None:
    current = path.resolve()
    stop_at = stop_at.resolve()
    while current != stop_at and str(current).startswith(str(stop_at)):
        if current.is_dir() and not any(current.iterdir()):
            current.rmdir()
            current = current.parent
            continue
        break


class S3Settings:
    def __init__(
        self,
        *,
        access_key_id: str | None,
        secret_access_key: str | None,
        session_token: str | None,
        endpoint_url: str | None,
        region: str,
        bucket: str,
        addressing_style: str,
        signature_version: str,
    ) -> None:
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.endpoint_url = endpoint_url
        self.region = region
        self.bucket = bucket
        self.addressing_style = addressing_style
        self.signature_version = signature_version


def _s3_settings(bucket_name: str | None) -> S3Settings:
    access_key_id = os.getenv("VOLCENGINE_ACCESS_KEY_ID")
    secret_access_key = os.getenv("VOLCENGINE_SECRET_ACCESS_KEY")
    session_token = os.getenv("VOLCENGINE_SESSION_TOKEN")
    endpoint_url = os.getenv("VOLCENGINE_S3_ENDPOINT_URL")
    region = os.getenv("VOLCENGINE_REGION")
    bucket = bucket_name or os.getenv("VOLCENGINE_S3_BUCKET")
    addressing_style = os.getenv("VOLCENGINE_S3_ADDRESSING_STYLE", "virtual")
    signature_version = os.getenv("VOLCENGINE_S3_SIGNATURE_VERSION", "s3v4")

    missing = [
        name
        for name, value in [
            ("VOLCENGINE_ACCESS_KEY_ID", access_key_id),
            ("VOLCENGINE_SECRET_ACCESS_KEY", secret_access_key),
            ("VOLCENGINE_S3_ENDPOINT_URL", endpoint_url),
            ("VOLCENGINE_REGION", region),
            ("VOLCENGINE_S3_BUCKET / --s3-bucket", bucket),
        ]
        if not value
    ]
    if missing:
        raise EnvironmentError("Missing S3 configuration: " + ", ".join(missing))
    return S3Settings(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=session_token,
        endpoint_url=endpoint_url,
        region=region or "",
        bucket=bucket or "",
        addressing_style=addressing_style,
        signature_version=signature_version,
    )


def _archive_filename(task: TaskSpec, attempt: int) -> str:
    base_task_id = str(task.metadata.get("base_task_id") or task.task_id)
    if "@" in base_task_id:
        base_task_id = base_task_id.rsplit("@", 1)[0]
    return f"{_safe_path_component(base_task_id)}-attempt-{attempt}.tgz"


def _task_batch_suffix(eval_config: EvalConfig, task: TaskSpec) -> str:
    suffix = str(task.metadata.get("task_id_suffix") or "")
    if not suffix and "@" in task.task_id:
        suffix = task.task_id.rsplit("@", 1)[1]
    return suffix or eval_config.run_id


def _safe_path_component(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")
