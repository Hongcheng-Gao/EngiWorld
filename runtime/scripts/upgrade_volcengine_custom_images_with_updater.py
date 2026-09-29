#!/usr/bin/env python3
"""Bake the arena OSWorld updater into existing Volcengine custom images.

Custom images are immutable, so every selected image is upgraded through a
disposable ECS instance and captured as a replacement image. By default the
old image is retained and the replacement gets an updater-version suffix.
Use --promote to move the original name to the replacement, and combine it
with --delete-replaced-images only after reviewing a dry run.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from engiworld.scheduler.schemas import InstanceRecord
from engiworld.scheduler.volcengine_ecs import (
    CloudAssistantCommandResult,
    SharedImage,
    VolcengineEcsClient,
    VolcengineLaunchConfig,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UPDATER_SOURCE = REPO_ROOT / "deploy" / "vm-updater" / "osworld_updater.py"
DEFAULT_UPDATER_VERSION_FILE = REPO_ROOT / "deploy" / "vm-updater" / "version.txt"
AVAILABLE_IMAGE_STATUSES = {"", "available", "ok"}
MANAGED_BY_TAG = "arena-osworld"
SOURCE_UPGRADE_TAG = "custom-image-updater-upgrade"
WINDOWS_STARTUP_POLICY_VERSION = "7"
EXECUTE_READY_MARKER = "arena-osworld-execute-ready"
EXECUTE_UPLOAD_CHUNK_BYTES = 6 * 1024


@dataclass(frozen=True)
class UpdaterPayload:
    source: bytes
    version: str
    sha256: str


@dataclass(frozen=True)
class UpgradeRequest:
    source: SharedImage
    original_name: str
    target_name: str
    existing_replacement: SharedImage | None = None


@dataclass(frozen=True)
class GuestUpdaterConfig:
    linux_current_dir: str
    linux_service_name: str
    windows_current_dir: str
    windows_scheduled_task_name: str
    windows_python_executable: str
    health_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_argument_group("source custom images")
    sources.add_argument(
        "--all-managed-images",
        "--all-managed-copies",
        dest="all_managed_copies",
        action="store_true",
        help=(
            "Select canonical custom images in the project with "
            "managed_by=arena-osworld."
        ),
    )
    sources.add_argument(
        "--image-id",
        action="append",
        default=[],
        help="Custom image ID to upgrade. Repeat for multiple images.",
    )
    sources.add_argument(
        "--image-id-file",
        action="append",
        default=[],
        type=Path,
        help="Text file containing one custom image ID per line.",
    )
    sources.add_argument(
        "--image-name",
        action="append",
        default=[],
        help="Exact custom image name to upgrade. Repeat for multiple images.",
    )

    parser.add_argument(
        "--project-name",
        default=None,
        help="Custom image project. Defaults to VOLCENGINE_PROJECT_NAME or agent-eval.",
    )
    parser.add_argument("--updater-source", type=Path, default=DEFAULT_UPDATER_SOURCE)
    parser.add_argument(
        "--updater-version-file",
        type=Path,
        default=DEFAULT_UPDATER_VERSION_FILE,
    )
    parser.add_argument(
        "--target-name-suffix",
        help="Replacement suffix. Defaults to -updater-v<updater version>.",
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Rename the replacement to the old image's original name.",
    )
    parser.add_argument(
        "--delete-replaced-images",
        action="store_true",
        help="After successful promotion, delete the old image.",
    )
    parser.add_argument(
        "--delete-bound-snapshots",
        "--delete-binded-snapshots",
        dest="delete_binded_snapshots",
        action="store_true",
        help="Also request deletion of snapshots bound to replaced images.",
    )
    parser.add_argument(
        "--auto-install-cloud-assistant",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Call InstallCloudAssistant when the guest agent does not come online.",
    )
    parser.add_argument(
        "--bootstrap-transport",
        choices=("auto", "execute", "cloud-assistant"),
        default="auto",
        help=(
            "How to install the updater in the guest. auto tries the OSWorld "
            "/execute endpoint first and falls back to Cloud Assistant."
        ),
    )
    parser.add_argument(
        "--vm-server-port",
        type=int,
        default=5000,
        help="OSWorld VM server port used by the /execute transport.",
    )
    parser.add_argument(
        "--cleanup-on-error",
        action="store_true",
        help="Delete a disposable ECS after failure. Default retains it for diagnosis.",
    )
    parser.add_argument(
        "--keep-build-instance",
        action="store_true",
        help="Keep disposable ECS instances after successful image creation.",
    )
    parser.add_argument(
        "--pause-before-capture",
        action="store_true",
        help=(
            "After automated guest setup, pause before stopping the instance so an "
            "operator can finish interactive image preparation. Requires one Windows "
            "image and an interactive terminal. This also forces a fresh rebuild."
        ),
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Rebuild even when the source or a replacement already has matching tags.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with later images when one upgrade fails.",
    )
    parser.add_argument("--force-stop", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    guest = parser.add_argument_group("guest updater settings")
    guest.add_argument("--linux-current-dir", default="/home/user/server")
    guest.add_argument("--linux-service-name", default="osworld_server.service")
    guest.add_argument(
        "--windows-current-dir",
        default="auto",
        help=(
            "Existing Windows OSWorld server directory. The default auto discovers "
            "the directory from the /execute working directory, scheduled task, and "
            "standard user-profile locations."
        ),
    )
    guest.add_argument("--windows-scheduled-task-name", default="OSWorldServer")
    guest.add_argument("--windows-python-executable", default="")
    guest.add_argument("--health-url", default="http://127.0.0.1:5000/health")

    timeouts = parser.add_argument_group("timeouts")
    timeouts.add_argument("--instance-ready-timeout-seconds", type=int, default=900)
    timeouts.add_argument("--instance-stop-timeout-seconds", type=int, default=900)
    timeouts.add_argument("--image-timeout-seconds", type=int, default=3600)
    timeouts.add_argument("--image-delete-timeout-seconds", type=int, default=900)
    timeouts.add_argument("--cloud-assistant-initial-wait-seconds", type=int, default=60)
    timeouts.add_argument("--cloud-assistant-timeout-seconds", type=int, default=600)
    timeouts.add_argument("--execute-wait-timeout-seconds", type=int, default=300)
    timeouts.add_argument("--execute-request-timeout-seconds", type=int, default=180)
    timeouts.add_argument("--bootstrap-timeout-seconds", type=int, default=300)
    return parser.parse_args()


def load_image_ids(paths: Iterable[Path]) -> list[str]:
    image_ids: list[str] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Custom image ID file not found: {path}")
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            image_id = raw_line.split("#", 1)[0].strip()
            if not image_id:
                continue
            if any(character.isspace() for character in image_id):
                raise ValueError(
                    f"Invalid custom image ID at {path}:{line_number}: {image_id!r}"
                )
            image_ids.append(image_id)
    return image_ids


def load_updater_payload(source_path: Path, version_path: Path) -> UpdaterPayload:
    if not source_path.is_file():
        raise FileNotFoundError(f"Updater source not found: {source_path}")
    if not version_path.is_file():
        raise FileNotFoundError(f"Updater version file not found: {version_path}")
    source = source_path.read_bytes()
    version = version_path.read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError(f"Updater version is empty: {version_path}")
    return UpdaterPayload(
        source=source,
        version=version,
        sha256=hashlib.sha256(source).hexdigest(),
    )


def custom_image_config(
    config: VolcengineLaunchConfig,
    project_name: str,
    *,
    install_run_command_agent: bool = False,
) -> VolcengineLaunchConfig:
    changes: dict[str, Any] = {
        "project_name": project_name,
        "image_visibility": "private",
        "image_project_name": project_name,
    }
    # Source bundles can reuse an older installed master environment. The
    # /execute transport does not need this newer launch option, so only set
    # it when the loaded scheduler model supports it.
    if hasattr(config, "install_run_command_agent"):
        changes["install_run_command_agent"] = install_run_command_agent
    return replace(config, **changes)


def resolve_source_images(
    images: Iterable[SharedImage],
    *,
    all_managed_copies: bool,
    image_ids: list[str],
    image_names: list[str],
) -> list[SharedImage]:
    available = [
        image
        for image in images
        if str(image.status or "").strip().lower() in AVAILABLE_IMAGE_STATUSES
    ]
    by_id = {image.image_id: image for image in available}
    by_name: dict[str, list[SharedImage]] = {}
    for image in available:
        by_name.setdefault(image.image_name, []).append(image)

    selected: list[SharedImage] = []
    if all_managed_copies:
        selected.extend(
            image
            for image in available
            if _is_managed_upgrade_candidate(image)
        )

    missing_ids = [image_id for image_id in image_ids if image_id not in by_id]
    if missing_ids:
        raise ValueError(
            "Custom image IDs not found or unavailable: " + ", ".join(missing_ids)
        )
    selected.extend(by_id[image_id] for image_id in image_ids)

    for image_name in image_names:
        matches = by_name.get(image_name, [])
        if not matches:
            raise ValueError(
                f"Custom image name not found or unavailable: {image_name!r}"
            )
        if len(matches) > 1:
            ids = ", ".join(sorted(image.image_id for image in matches))
            raise ValueError(
                f"Custom image name {image_name!r} is ambiguous; use --image-id: {ids}"
            )
        selected.append(matches[0])

    result = []
    seen = set()
    for image in sorted(selected, key=lambda item: (item.image_name, item.image_id)):
        if image.image_id in seen:
            continue
        seen.add(image.image_id)
        result.append(image)
    return result


def build_upgrade_requests(
    selected: Iterable[SharedImage],
    all_images: Iterable[SharedImage],
    *,
    updater: UpdaterPayload,
    target_suffix: str,
    force_rebuild: bool = False,
) -> list[UpgradeRequest]:
    images = list(all_images)
    replacements: dict[str, list[SharedImage]] = {}
    for image in images:
        tags = image_tags(image)
        replaced_id = tags.get("replaces_image_id")
        if (
            tags.get("managed_by") == MANAGED_BY_TAG
            and tags.get("source") == SOURCE_UPGRADE_TAG
            and tags.get("updater_sha256") == updater.sha256
            and _startup_policy_is_current(image, tags)
            and replaced_id
            and str(image.status or "").strip().lower() in AVAILABLE_IMAGE_STATUSES
        ):
            replacements.setdefault(replaced_id, []).append(image)

    requests = []
    for source in selected:
        original_name = original_image_name(source)
        source_tags = image_tags(source)
        source_already_current = (
            source_tags.get("managed_by") == MANAGED_BY_TAG
            and source_tags.get("source") == SOURCE_UPGRADE_TAG
            and source_tags.get("updater_sha256") == updater.sha256
            and _startup_policy_is_current(source, source_tags)
        )
        candidates = sorted(
            replacements.get(source.image_id, []),
            key=lambda item: (item.image_name, item.image_id),
        )
        if len(candidates) > 1:
            ids = ", ".join(item.image_id for item in candidates)
            raise ValueError(
                f"Multiple updater replacements exist for {source.image_id}: {ids}"
            )
        target_name = image_name_with_suffix(original_name, target_suffix)
        requests.append(
            UpgradeRequest(
                source=source,
                original_name=original_name,
                target_name=target_name,
                existing_replacement=(
                    None
                    if force_rebuild
                    else source
                    if source_already_current
                    else candidates[0] if candidates else None
                ),
            )
        )
    return requests


def image_tags(image: SharedImage) -> dict[str, str]:
    tags: dict[str, str] = {}
    for tag in getattr(image.raw, "tags", None) or []:
        key = str(getattr(tag, "key", "") or "")
        if key:
            tags[key] = str(getattr(tag, "value", "") or "")
    return tags


def _startup_policy_is_current(image: SharedImage, tags: dict[str, str]) -> bool:
    if "windows" not in str(image.os_type or "").lower():
        return True
    return tags.get("windows_startup_policy") == WINDOWS_STARTUP_POLICY_VERSION


def original_image_name(image: SharedImage) -> str:
    tags = image_tags(image)
    return (
        tags.get("original_image_name")
        or tags.get("source_image_name")
        or image.image_name
    )


def image_name_with_suffix(name: str, suffix: str, limit: int = 128) -> str:
    suffix = suffix.strip()
    if not suffix:
        raise ValueError("Image name suffix cannot be empty")
    if len(suffix) >= limit:
        raise ValueError(f"Image name suffix is too long: {suffix!r}")
    return name[: limit - len(suffix)] + suffix


def _is_managed_upgrade_candidate(image: SharedImage) -> bool:
    tags = image_tags(image)
    if tags.get("managed_by") != MANAGED_BY_TAG:
        return False

    # Images produced by older tooling may only carry managed_by. Include
    # those directly. When provenance names are available, use them to exclude
    # pre-updater backups and unpromoted replacement images from bulk runs.
    canonical_name = tags.get("original_image_name") or tags.get("source_image_name")
    return not canonical_name or image.image_name == canonical_name


def guest_config_from_args(args: argparse.Namespace) -> GuestUpdaterConfig:
    return GuestUpdaterConfig(
        linux_current_dir=args.linux_current_dir,
        linux_service_name=args.linux_service_name,
        windows_current_dir=args.windows_current_dir,
        windows_scheduled_task_name=args.windows_scheduled_task_name,
        windows_python_executable=args.windows_python_executable,
        health_url=args.health_url,
    )


def build_bootstrap_script(
    platform: str,
    updater: UpdaterPayload,
    config: GuestUpdaterConfig,
) -> str:
    if platform == "windows":
        return build_windows_bootstrap_script(updater, config)
    if platform == "linux":
        return build_linux_bootstrap_script(updater, config)
    raise ValueError(f"Unsupported updater platform: {platform!r}")


def build_linux_bootstrap_script(
    updater: UpdaterPayload,
    config: GuestUpdaterConfig,
) -> str:
    variables = "\n".join(
        [
            f"UPDATER_B64 = {base64.b64encode(updater.source).decode('ascii')!r}",
            f"EXPECTED_SHA256 = {updater.sha256!r}",
            f"UPDATER_VERSION = {updater.version!r}",
            f"CURRENT_DIR = {config.linux_current_dir!r}",
            f"SERVICE_NAME = {config.linux_service_name!r}",
            f"HEALTH_URL = {config.health_url!r}",
        ]
    )
    body = r'''
import base64
import hashlib
import json
import os
import pathlib
import subprocess
import sys

install_dir = pathlib.Path("/opt/arena-osworld-updater")
updater_path = install_dir / "osworld_updater.py"
wrapper_path = install_dir / "update-osworld"
config_path = pathlib.Path("/etc/arena-osworld-updater.json")
release_path = install_dir / "updater-release.json"
current_dir = pathlib.Path(CURRENT_DIR)

if not current_dir.is_dir():
    raise RuntimeError(f"OSWorld server directory does not exist: {current_dir}")
service_check = subprocess.run(
    ["systemctl", "cat", SERVICE_NAME],
    capture_output=True,
    text=True,
)
if service_check.returncode != 0:
    detail = (service_check.stderr or service_check.stdout or "").strip()
    raise RuntimeError(f"systemd service {SERVICE_NAME!r} was not found: {detail}")

source = base64.b64decode(UPDATER_B64)
actual_sha256 = hashlib.sha256(source).hexdigest()
if actual_sha256 != EXPECTED_SHA256:
    raise RuntimeError(
        f"Embedded updater SHA256 mismatch: expected={EXPECTED_SHA256}, actual={actual_sha256}"
    )

config = {
    "current_dir": str(current_dir),
    "stop_command": ["systemctl", "stop", SERVICE_NAME],
    "start_command": ["systemctl", "start", SERVICE_NAME],
    "health_url": HEALTH_URL,
    "health_timeout_seconds": 90,
}
config_bytes = (json.dumps(config, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
wrapper_bytes = (
    "#!/usr/bin/env bash\n"
    f"exec {sys.executable!r} {str(updater_path)!r} apply --config {str(config_path)!r} \"$@\"\n"
).encode("utf-8")
release_bytes = (
    json.dumps(
        {"version": UPDATER_VERSION, "sha256": EXPECTED_SHA256},
        ensure_ascii=True,
        indent=2,
    )
    + "\n"
).encode("utf-8")

def same(path, content):
    try:
        return path.read_bytes() == content
    except FileNotFoundError:
        return False

unchanged = (
    same(updater_path, source)
    and same(config_path, config_bytes)
    and same(wrapper_path, wrapper_bytes)
)

def atomic_write(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.chmod(temporary, mode)
    os.replace(temporary, path)

atomic_write(updater_path, source, 0o755)
atomic_write(config_path, config_bytes, 0o644)
atomic_write(wrapper_path, wrapper_bytes, 0o755)
atomic_write(release_path, release_bytes, 0o644)

check = subprocess.run(
    [sys.executable, str(updater_path), "--help"],
    capture_output=True,
    text=True,
)
if check.returncode != 0:
    detail = (check.stderr or check.stdout or "").strip()
    raise RuntimeError(f"Updater self-check failed: {detail}")

print(json.dumps({
    "status": "unchanged" if unchanged else "installed",
    "platform": "linux",
    "updater_sha256": EXPECTED_SHA256,
    "updater_version": UPDATER_VERSION,
    "current_dir": str(current_dir),
    "service_name": SERVICE_NAME,
}, ensure_ascii=True))
'''
    return "#!/usr/bin/env bash\nset -euo pipefail\npython3 - <<'PY'\n" + variables + body + "\nPY\n"


def build_windows_bootstrap_script(
    updater: UpdaterPayload,
    config: GuestUpdaterConfig,
) -> str:
    updater_b64 = base64.b64encode(updater.source).decode("ascii")
    python_resolution = (
        f"$PythonExecutable = {_powershell_quote(config.windows_python_executable)}"
        if config.windows_python_executable
        else (
            "$PythonCommand = Get-Command python.exe -ErrorAction Stop\n"
            "$PythonExecutable = $PythonCommand.Source"
        )
    )
    return textwrap.dedent(
        f"""
        $ErrorActionPreference = 'Stop'
        $InstallDir = "$env:ProgramData\\ArenaOSWorldUpdater"
        $UpdaterPath = Join-Path $InstallDir 'osworld_updater.py'
        $ConfigPath = Join-Path $InstallDir 'config.json'
        $WrapperPath = Join-Path $InstallDir 'update-osworld.ps1'
        $ReleasePath = Join-Path $InstallDir 'updater-release.json'
        $StartupScriptPath = Join-Path $InstallDir 'start-osworld-server.ps1'
        $WatchdogScriptPath = Join-Path $InstallDir 'watch-osworld-server.ps1'
        $StartupConfigPath = Join-Path $InstallDir 'server-startup.json'
        $StartupLogDir = Join-Path $InstallDir 'logs'
        $WatchdogTaskName = 'ArenaOSWorldServerWatchdog'
        $RequestedCurrentDir = {_powershell_quote(config.windows_current_dir)}
        $ScheduledTaskName = {_powershell_quote(config.windows_scheduled_task_name)}
        $HealthUrl = {_powershell_quote(config.health_url)}
        $ListenerPort = ([Uri]$HealthUrl).Port
        $EscapedScheduledTaskName = $ScheduledTaskName.Replace("'", "''")
        $StopTaskScript = "Stop-ScheduledTask -TaskName '$EscapedScheduledTaskName' -ErrorAction SilentlyContinue"
        $StartTaskScript = "Start-ScheduledTask -TaskName '$EscapedScheduledTaskName' -ErrorAction Stop"
        $ExpectedSha256 = '{updater.sha256}'
        $UpdaterVersion = {_powershell_quote(updater.version)}

        $ServerCandidates = [System.Collections.Generic.List[object]]::new()
        $SeenServerCandidates = @{{}}
        function Add-ServerCandidate {{
            param([string]$Path, [string]$Source)
            if ([string]::IsNullOrWhiteSpace($Path) -or $Path -eq 'auto') {{ return }}
            $ExpandedPath = [Environment]::ExpandEnvironmentVariables($Path)
            try {{
                $ResolvedPath = (Resolve-Path -LiteralPath $ExpandedPath -ErrorAction Stop).Path
            }} catch {{
                return
            }}
            if (-not (Test-Path -LiteralPath (Join-Path $ResolvedPath 'main.py') -PathType Leaf)) {{
                return
            }}
            $Key = $ResolvedPath.TrimEnd('\\').ToLowerInvariant()
            if (-not $SeenServerCandidates.ContainsKey($Key)) {{
                $SeenServerCandidates[$Key] = $true
                $ServerCandidates.Add([pscustomobject]@{{Path=$ResolvedPath; Source=$Source}})
            }}
        }}

        Add-ServerCandidate $RequestedCurrentDir 'explicit'
        Add-ServerCandidate (Get-Location).Path 'execute-working-directory'
        Add-ServerCandidate (Join-Path (Get-Location).Path 'server') 'execute-working-directory-child'
        Add-ServerCandidate (Join-Path $env:USERPROFILE 'server') 'user-profile'

        $ScheduledTask = Get-ScheduledTask -TaskName $ScheduledTaskName -ErrorAction SilentlyContinue
        $WatchdogTask = Get-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
        $WatchdogAction = $null
        if ($WatchdogTask) {{ $WatchdogAction = @($WatchdogTask.Actions)[0] }}
        if ($ScheduledTask) {{
            foreach ($Action in $ScheduledTask.Actions) {{
                Add-ServerCandidate ([string]$Action.WorkingDirectory) 'scheduled-task-working-directory'
            }}
        }}

        $UsersRoot = Join-Path $env:SystemDrive 'Users'
        if (Test-Path -LiteralPath $UsersRoot -PathType Container) {{
            foreach ($UserDirectory in Get-ChildItem -LiteralPath $UsersRoot -Directory -ErrorAction SilentlyContinue) {{
                Add-ServerCandidate (Join-Path $UserDirectory.FullName 'server') 'user-directory'
                Add-ServerCandidate (Join-Path $UserDirectory.FullName 'Desktop\\server') 'user-desktop'
                Add-ServerCandidate (Join-Path $UserDirectory.FullName 'OSWorld\\server') 'user-osworld-directory'
                Add-ServerCandidate (Join-Path $UserDirectory.FullName 'Desktop\\OSWorld\\server') 'user-desktop-osworld-directory'
            }}
        }}
        Add-ServerCandidate (Join-Path $env:SystemDrive 'server') 'system-drive'
        Add-ServerCandidate (Join-Path $env:SystemDrive 'OSWorld\\server') 'system-drive-osworld-directory'

        if ($ServerCandidates.Count -eq 0 -and (Test-Path -LiteralPath $UsersRoot -PathType Container)) {{
            $FallbackPatterns = @(
                '*\\server\\main.py',
                '*\\*\\server\\main.py',
                '*\\*\\*\\server\\main.py',
                '*\\*\\*\\*\\server\\main.py'
            )
            foreach ($Pattern in $FallbackPatterns) {{
                foreach ($MainFile in Get-Item -Path (Join-Path $UsersRoot $Pattern) -ErrorAction SilentlyContinue) {{
                    Add-ServerCandidate $MainFile.Directory.FullName 'user-directory-fallback-scan'
                }}
            }}
        }}

        if ($ServerCandidates.Count -eq 0) {{
            throw "Unable to discover the OSWorld server directory containing main.py; requested=$RequestedCurrentDir cwd=$((Get-Location).Path) user_profile=$env:USERPROFILE"
        }}
        $CurrentDir = $ServerCandidates[0].Path
        $CurrentDirSource = $ServerCandidates[0].Source
        & schtasks.exe /Query /TN $ScheduledTaskName | Out-Null
        if ($LASTEXITCODE -ne 0) {{
            throw "Scheduled task was not found: $ScheduledTaskName"
        }}
        {python_resolution}
        if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {{
            throw "Python executable was not found: $PythonExecutable"
        }}

        $OriginalAction = @($ScheduledTask.Actions)[0]
        if (-not $OriginalAction) {{
            throw "Scheduled task has no action: $ScheduledTaskName"
        }}
        $ServerExecute = [string]$OriginalAction.Execute
        $ServerArguments = [string]$OriginalAction.Arguments
        $ServerWorkingDirectory = [string]$OriginalAction.WorkingDirectory
        $StartupPolicyWasCurrent = $false
        if ($ServerArguments -like "*$StartupScriptPath*" -and
            (Test-Path -LiteralPath $StartupConfigPath -PathType Leaf)) {{
            $ExistingStartupConfig = Get-Content -LiteralPath $StartupConfigPath -Raw |
                ConvertFrom-Json
            $StartupPolicyWasCurrent = (
                [string]$ExistingStartupConfig.startup_policy_version -eq
                    '{WINDOWS_STARTUP_POLICY_VERSION}' -and
                (Test-Path -LiteralPath $StartupScriptPath -PathType Leaf) -and
                (Test-Path -LiteralPath $WatchdogScriptPath -PathType Leaf) -and
                $WatchdogAction -and
                [string]$WatchdogAction.Arguments -like "*$WatchdogScriptPath*"
            )
            $ServerExecute = [string]$ExistingStartupConfig.execute
            $ServerArguments = [string]$ExistingStartupConfig.arguments
            $ServerWorkingDirectory = [string]$ExistingStartupConfig.working_directory
        }}
        if ([string]::IsNullOrWhiteSpace($ServerWorkingDirectory)) {{
            $ServerWorkingDirectory = $CurrentDir
        }}
        if ([IO.Path]::GetFileName($ServerExecute) -ieq 'python.exe') {{
            $WindowlessPython = Join-Path (Split-Path -Parent $ServerExecute) 'pythonw.exe'
            if (-not (Test-Path -LiteralPath $WindowlessPython -PathType Leaf)) {{
                throw "Windowless Python executable was not found: $WindowlessPython"
            }}
            $ServerExecute = $WindowlessPython
        }}
        if (-not (Test-Path -LiteralPath $ServerExecute -PathType Leaf)) {{
            throw "OSWorld server task executable was not found: $ServerExecute"
        }}

        New-Item -ItemType Directory -Path $StartupLogDir -Force | Out-Null
        [ordered]@{{
            execute = $ServerExecute
            arguments = $ServerArguments
            working_directory = $ServerWorkingDirectory
            startup_policy_version = '{WINDOWS_STARTUP_POLICY_VERSION}'
        }} | ConvertTo-Json -Depth 4 |
            Set-Content -LiteralPath $StartupConfigPath -Encoding UTF8
        $StartupWrapper = @'
$ErrorActionPreference = 'Continue'
$InstallDir = Join-Path $env:ProgramData 'ArenaOSWorldUpdater'
$Config = Get-Content (Join-Path $InstallDir 'server-startup.json') -Raw |
    ConvertFrom-Json
$LogDir = Join-Path $InstallDir 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$EventLog = Join-Path $LogDir 'server-startup-events.log'
while ($true) {{
    $Timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss-fff')
    $StdoutLog = Join-Path $LogDir "server-$Timestamp.stdout.log"
    $StderrLog = Join-Path $LogDir "server-$Timestamp.stderr.log"
    Add-Content -LiteralPath $EventLog -Value "$(Get-Date -Format o) starting $($Config.execute) $($Config.arguments) cwd=$($Config.working_directory)"
    try {{
        $StartParameters = @{{
            FilePath = [string]$Config.execute
            WorkingDirectory = [string]$Config.working_directory
            PassThru = $true
            Wait = $true
            RedirectStandardOutput = $StdoutLog
            RedirectStandardError = $StderrLog
        }}
        if (-not [string]::IsNullOrWhiteSpace([string]$Config.arguments)) {{
            $StartParameters.ArgumentList = [string]$Config.arguments
        }}
        $Process = Start-Process @StartParameters
        Add-Content -LiteralPath $EventLog -Value "$(Get-Date -Format o) exited pid=$($Process.Id) code=$($Process.ExitCode)"
    }} catch {{
        Add-Content -LiteralPath $EventLog -Value "$(Get-Date -Format o) failed: $($_ | Out-String)"
    }}
    Start-Sleep -Seconds 5
}}
'@
        $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($StartupScriptPath, $StartupWrapper, $Utf8NoBom)

        $WatchdogWrapper = @'
$ErrorActionPreference = 'Continue'
$TaskName = '__TASK_NAME__'
$InstallDir = Join-Path $env:ProgramData 'ArenaOSWorldUpdater'
$UpdaterConfigPath = Join-Path $InstallDir 'config.json'
$UpdateLockPath = $null
$LogDir = Join-Path $InstallDir 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$WatchdogLog = Join-Path $LogDir 'server-watchdog-events.log'
$ConsecutiveMisses = 0
Start-Sleep -Seconds 30
while ($true) {{
    if ([string]::IsNullOrWhiteSpace([string]$UpdateLockPath)) {{
        try {{
            if (Test-Path -LiteralPath $UpdaterConfigPath -PathType Leaf) {{
                $UpdaterConfig = Get-Content -LiteralPath $UpdaterConfigPath -Raw |
                    ConvertFrom-Json
                $ConfiguredCurrentDir = [string]$UpdaterConfig.current_dir
                if (-not [string]::IsNullOrWhiteSpace($ConfiguredCurrentDir)) {{
                    $UpdateParent = Split-Path -Parent $ConfiguredCurrentDir
                    $UpdateLockPath = Join-Path $UpdateParent '.arena-osworld-update.lock'
                }}
            }}
        }} catch {{
            $UpdateLockPath = $null
        }}
        if ([string]::IsNullOrWhiteSpace([string]$UpdateLockPath)) {{
            $ConsecutiveMisses = 0
            Start-Sleep -Seconds 10
            continue
        }}
    }}
    if (Test-Path -LiteralPath $UpdateLockPath -PathType Leaf) {{
        $ConsecutiveMisses = 0
        Start-Sleep -Seconds 10
        continue
    }}
    $Listening = @(
        Get-NetTCPConnection -LocalPort __LISTENER_PORT__ -State Listen -ErrorAction SilentlyContinue
    ).Count -gt 0
    if ($Listening) {{
        $ConsecutiveMisses = 0
    }} else {{
        $ConsecutiveMisses += 1
    }}
    if ($ConsecutiveMisses -ge 3) {{
        Add-Content -LiteralPath $WatchdogLog -Value "$(Get-Date -Format o) restarting $TaskName after $ConsecutiveMisses closed-port probes"
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        $ConsecutiveMisses = 0
        Start-Sleep -Seconds 15
    }}
    Start-Sleep -Seconds 10
}}
'@
        $WatchdogWrapper = $WatchdogWrapper.Replace(
            '__TASK_NAME__',
            $ScheduledTaskName.Replace("'", "''")
        ).Replace(
            '__LISTENER_PORT__',
            [string]$ListenerPort
        )
        [IO.File]::WriteAllText($WatchdogScriptPath, $WatchdogWrapper, $Utf8NoBom)

        $TaskUser = [string]$ScheduledTask.Principal.UserId
        if ([string]::IsNullOrWhiteSpace($TaskUser)) {{
            throw "Scheduled task has no principal user: $ScheduledTaskName"
        }}
        $StartupTrigger = New-ScheduledTaskTrigger -AtStartup
        $StartupTrigger.Delay = 'PT30S'
        $LoginTrigger = New-ScheduledTaskTrigger -AtLogOn -User $TaskUser
        $LoginTrigger.Delay = 'PT15S'
        $TaskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
            -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        $TaskPowerShell = Join-Path $PSHOME 'powershell.exe'
        $TaskArguments = '-NoProfile -NonInteractive -WindowStyle Hidden ' +
            '-ExecutionPolicy Bypass -File "' + $StartupScriptPath + '"'
        $ManagedAction = New-ScheduledTaskAction -Execute $TaskPowerShell `
            -Argument $TaskArguments -WorkingDirectory $InstallDir
        Set-ScheduledTask -TaskName $ScheduledTaskName `
            -TaskPath $ScheduledTask.TaskPath -Action $ManagedAction `
            -Trigger @($StartupTrigger, $LoginTrigger) `
            -Settings $TaskSettings | Out-Null

        $WatchdogTrigger = New-ScheduledTaskTrigger -AtStartup
        $WatchdogTrigger.Delay = 'PT20S'
        $WatchdogArguments = '-NoProfile -NonInteractive -WindowStyle Hidden ' +
            '-ExecutionPolicy Bypass -File "' + $WatchdogScriptPath + '"'
        $ManagedWatchdogAction = New-ScheduledTaskAction -Execute $TaskPowerShell `
            -Argument $WatchdogArguments -WorkingDirectory $InstallDir
        $WatchdogPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' `
            -LogonType ServiceAccount -RunLevel Highest
        $WatchdogSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        Stop-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
        Register-ScheduledTask -TaskName $WatchdogTaskName `
            -Action $ManagedWatchdogAction -Trigger $WatchdogTrigger `
            -Principal $WatchdogPrincipal -Settings $WatchdogSettings `
            -Force | Out-Null
        Start-ScheduledTask -TaskName $WatchdogTaskName

        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        $UpdaterBytes = [Convert]::FromBase64String('{updater_b64}')
        $Hasher = [Security.Cryptography.SHA256]::Create()
        try {{
            $ActualSha256 = ([BitConverter]::ToString($Hasher.ComputeHash($UpdaterBytes))).Replace('-', '').ToLowerInvariant()
        }} finally {{
            $Hasher.Dispose()
        }}
        if ($ActualSha256 -ne $ExpectedSha256) {{
            throw "Embedded updater SHA256 mismatch: expected=$ExpectedSha256 actual=$ActualSha256"
        }}

        $WasUnchanged = $false
        if (Test-Path -LiteralPath $UpdaterPath -PathType Leaf) {{
            $WasUnchanged = (
                (Get-FileHash -LiteralPath $UpdaterPath -Algorithm SHA256).Hash.ToLowerInvariant() -eq
                    $ExpectedSha256 -and $StartupPolicyWasCurrent
            )
        }}
        $TemporaryUpdater = "$UpdaterPath.tmp"
        [IO.File]::WriteAllBytes($TemporaryUpdater, $UpdaterBytes)
        Move-Item -LiteralPath $TemporaryUpdater -Destination $UpdaterPath -Force

        $Config = [ordered]@{{
            current_dir = $CurrentDir
            stop_command = @('powershell.exe', '-NoProfile', '-NonInteractive', '-Command', $StopTaskScript)
            start_command = @('powershell.exe', '-NoProfile', '-NonInteractive', '-Command', $StartTaskScript)
            health_url = $HealthUrl
            health_timeout_seconds = 90
            listener_port = $ListenerPort
            scheduled_task_name = $ScheduledTaskName
        }}
        $Config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
        $Wrapper = @"
`$ErrorActionPreference = 'Stop'
& "$PythonExecutable" "$UpdaterPath" apply --config "$ConfigPath" @args
exit `$LASTEXITCODE
"@
        $Wrapper | Set-Content -LiteralPath $WrapperPath -Encoding UTF8
        [ordered]@{{version=$UpdaterVersion; sha256=$ExpectedSha256}} |
            ConvertTo-Json | Set-Content -LiteralPath $ReleasePath -Encoding UTF8

        & $PythonExecutable $UpdaterPath --help | Out-Null
        if ($LASTEXITCODE -ne 0) {{ throw 'Updater self-check failed' }}
        [ordered]@{{
            status = $(if ($WasUnchanged) {{ 'unchanged' }} else {{ 'installed' }})
            platform = 'windows'
            updater_sha256 = $ExpectedSha256
            updater_version = $UpdaterVersion
            current_dir = $CurrentDir
            current_dir_source = $CurrentDirSource
            scheduled_task_name = $ScheduledTaskName
            startup_policy_version = '{WINDOWS_STARTUP_POLICY_VERSION}'
            server_execute = $ServerExecute
            watchdog_task_name = $WatchdogTaskName
            startup_log = (Join-Path $StartupLogDir 'server-startup-events.log')
        }} | ConvertTo-Json -Compress
        """
    ).strip() + "\n"


def install_updater_with_transport(
    ecs: VolcengineEcsClient,
    instance: InstanceRecord,
    *,
    platform: str,
    updater: UpdaterPayload,
    config: GuestUpdaterConfig,
    transport: str,
    vm_server_port: int,
    execute_wait_timeout_seconds: int,
    execute_request_timeout_seconds: int,
    cloud_assistant_initial_wait_seconds: int,
    cloud_assistant_timeout_seconds: int,
    auto_install_cloud_assistant: bool,
    bootstrap_timeout_seconds: int,
    invocation_name: str,
) -> dict[str, Any]:
    execute_error: Exception | None = None
    if transport in {"auto", "execute"}:
        _emit(
            "custom_image_updater_execute_connecting",
            instance_id=instance.instance_id,
            private_ip=instance.private_ip,
            port=vm_server_port,
        )
        try:
            bootstrap = install_updater_via_execute(
                instance,
                platform=platform,
                updater=updater,
                config=config,
                port=vm_server_port,
                wait_timeout_seconds=execute_wait_timeout_seconds,
                request_timeout_seconds=execute_request_timeout_seconds,
            )
            return {
                "transport": "execute",
                "cloud_assistant": None,
                "bootstrap": bootstrap,
            }
        except Exception as exc:
            execute_error = exc
            _emit(
                "custom_image_updater_execute_failed",
                instance_id=instance.instance_id,
                error=f"{type(exc).__name__}: {exc}",
                will_fallback=transport == "auto",
            )
            if transport == "execute":
                raise

    assistant = ensure_cloud_assistant(
        ecs,
        instance.instance_id,
        initial_wait_seconds=cloud_assistant_initial_wait_seconds,
        timeout_seconds=cloud_assistant_timeout_seconds,
        auto_install=auto_install_cloud_assistant,
    )
    bootstrap = install_updater_on_instance(
        ecs,
        instance.instance_id,
        platform=platform,
        updater=updater,
        config=config,
        timeout_seconds=bootstrap_timeout_seconds,
        invocation_name=invocation_name,
    )
    return {
        "transport": "cloud-assistant",
        "execute_error": (
            f"{type(execute_error).__name__}: {execute_error}"
            if execute_error
            else None
        ),
        "cloud_assistant": assistant,
        "bootstrap": bootstrap,
    }


def install_updater_via_execute(
    instance: InstanceRecord,
    *,
    platform: str,
    updater: UpdaterPayload,
    config: GuestUpdaterConfig,
    port: int,
    wait_timeout_seconds: int,
    request_timeout_seconds: int,
) -> dict[str, Any]:
    wait_for_vm_execute(
        instance,
        platform=platform,
        port=port,
        timeout_seconds=wait_timeout_seconds,
    )
    script = build_bootstrap_script(platform, updater, config)
    suffix = ".ps1" if platform == "windows" else ".sh"
    remote_name = f"arena-osworld-updater-{updater.sha256[:12]}{suffix}"
    remote_path = upload_execute_script(
        instance,
        platform=platform,
        port=port,
        remote_name=remote_name,
        content=script.encode("utf-8"),
        request_timeout_seconds=request_timeout_seconds,
    )
    try:
        command = execute_bootstrap_command(platform, remote_path)
        response = execute_vm_command(
            instance,
            command,
            port=port,
            timeout_seconds=request_timeout_seconds,
        )
        return validate_bootstrap_output(
            str(response.get("output") or ""),
            updater.sha256,
            context=f"/execute bootstrap on {instance.instance_id}",
        )
    finally:
        try:
            remove_execute_file(
                instance,
                platform=platform,
                port=port,
                remote_name=remote_name,
                request_timeout_seconds=min(30, request_timeout_seconds),
            )
        except Exception:
            pass


def wait_for_vm_execute(
    instance: InstanceRecord,
    *,
    platform: str,
    port: int,
    timeout_seconds: int,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "no response"
    command = (
        ["cmd.exe", "/d", "/s", "/c", f"echo {EXECUTE_READY_MARKER}"]
        if platform == "windows"
        else ["/bin/sh", "-c", f"printf {EXECUTE_READY_MARKER}"]
    )
    while time.monotonic() < deadline:
        try:
            result = execute_vm_command(
                instance,
                command,
                port=port,
                timeout_seconds=10,
            )
            if EXECUTE_READY_MARKER in str(result.get("output") or ""):
                return
            last_error = f"unexpected probe response: {result}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(5)
    raise TimeoutError(
        f"Timed out waiting for OSWorld /execute on {instance.instance_id} "
        f"({instance.private_ip}:{port}): {last_error}"
    )


def execute_vm_command(
    instance: InstanceRecord,
    command: list[str],
    *,
    port: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    host = instance.private_ip or instance.public_ip or ""
    if not host:
        raise ValueError(f"Instance {instance.instance_id} has no reachable IP address")
    url = f"http://{host}:{port}/execute"
    body = json.dumps(
        {
            "command": command,
            "shell": False,
            "timeout": timeout_seconds,
        },
        ensure_ascii=True,
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} returned HTTP {exc.code}: {detail[-4000:]}") from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"POST {url} failed: {exc.reason}") from exc

    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"POST {url} returned non-JSON data: {response_body[-4000:]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"POST {url} returned a non-object response: {payload!r}")
    return_code = payload.get("returncode")
    if payload.get("status") != "success" or return_code not in {0, None}:
        detail = str(payload.get("error") or payload.get("message") or payload.get("output") or "")
        raise RuntimeError(
            f"VM command failed on {instance.instance_id}: status={payload.get('status')}, "
            f"returncode={return_code}, detail={detail[-4000:]}"
        )
    return payload


def upload_execute_script(
    instance: InstanceRecord,
    *,
    platform: str,
    port: int,
    remote_name: str,
    content: bytes,
    request_timeout_seconds: int,
) -> str:
    python_command = "python.exe" if platform == "windows" else "python3"
    path_expression = f"pathlib.Path(tempfile.gettempdir()) / {remote_name!r}"
    initialize = (
        "import pathlib,tempfile;"
        f"p={path_expression};p.write_bytes(b'');print(str(p))"
    )
    response = execute_vm_command(
        instance,
        [python_command, "-c", initialize],
        port=port,
        timeout_seconds=request_timeout_seconds,
    )
    remote_path = str(response.get("output") or "").strip()
    if not remote_path:
        raise RuntimeError(f"VM did not return the upload path for {remote_name}")

    for offset in range(0, len(content), EXECUTE_UPLOAD_CHUNK_BYTES):
        encoded = base64.b64encode(
            content[offset : offset + EXECUTE_UPLOAD_CHUNK_BYTES]
        ).decode("ascii")
        append = (
            "import base64,pathlib,tempfile;"
            f"p={path_expression};p.open('ab').write(base64.b64decode({encoded!r}))"
        )
        execute_vm_command(
            instance,
            [python_command, "-c", append],
            port=port,
            timeout_seconds=request_timeout_seconds,
        )

    verify = (
        "import hashlib,pathlib,tempfile;"
        f"p={path_expression};print(hashlib.sha256(p.read_bytes()).hexdigest())"
    )
    response = execute_vm_command(
        instance,
        [python_command, "-c", verify],
        port=port,
        timeout_seconds=request_timeout_seconds,
    )
    actual_sha256 = str(response.get("output") or "").strip().lower()
    expected_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"Uploaded bootstrap SHA256 mismatch on {instance.instance_id}: "
            f"expected={expected_sha256}, actual={actual_sha256}"
        )
    return remote_path


def execute_bootstrap_command(platform: str, remote_path: str) -> list[str]:
    if platform == "windows":
        return [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            remote_path,
        ]
    return ["sudo", "-n", "/bin/bash", remote_path]


def remove_execute_file(
    instance: InstanceRecord,
    *,
    platform: str,
    port: int,
    remote_name: str,
    request_timeout_seconds: int,
) -> None:
    python_command = "python.exe" if platform == "windows" else "python3"
    path_expression = f"pathlib.Path(tempfile.gettempdir()) / {remote_name!r}"
    cleanup = (
        "import pathlib,tempfile;"
        f"p={path_expression};p.unlink() if p.exists() else None"
    )
    execute_vm_command(
        instance,
        [python_command, "-c", cleanup],
        port=port,
        timeout_seconds=request_timeout_seconds,
    )


def ensure_cloud_assistant(
    ecs: VolcengineEcsClient,
    instance_id: str,
    *,
    initial_wait_seconds: int,
    timeout_seconds: int,
    auto_install: bool,
) -> dict[str, Any]:
    try:
        ecs.wait_for_cloud_assistant(
            [instance_id],
            timeout_seconds=max(1, initial_wait_seconds),
        )
        return {"installed": False, "status": "online"}
    except TimeoutError as initial_error:
        statuses = ecs.cloud_assistant_statuses([instance_id])
        current_status = statuses.get(instance_id, "missing")
        ready_reboot = _is_cloud_assistant_ready_reboot(current_status)
        if not auto_install and not ready_reboot:
            raise RuntimeError(
                f"Cloud Assistant is not online on {instance_id}: {statuses}"
            ) from initial_error

        accepted: list[str] = []
        installed = False
        if not ready_reboot:
            _emit(
                "custom_image_updater_cloud_assistant_installing",
                instance_id=instance_id,
                previous_status=current_status,
            )
            accepted = ecs.install_cloud_assistant([instance_id])
            installed = True

        result = _wait_for_cloud_assistant_installation(
            ecs,
            instance_id,
            timeout_seconds=timeout_seconds,
            initial_status=current_status,
        )
        return {
            "installed": installed,
            "status": "online",
            "accepted_instance_ids": accepted,
            **result,
        }


def _wait_for_cloud_assistant_installation(
    ecs: VolcengineEcsClient,
    instance_id: str,
    *,
    timeout_seconds: int,
    initial_status: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = initial_status
    rebooted = False

    while time.monotonic() < deadline:
        statuses = ecs.cloud_assistant_statuses([instance_id])
        status = statuses.get(instance_id, "missing")
        normalized = _normalized_cloud_assistant_status(status)
        if status != last_status:
            _emit(
                "custom_image_updater_cloud_assistant_status",
                instance_id=instance_id,
                previous_status=last_status,
                status=status,
            )
            last_status = status

        if normalized in {"online", "running"}:
            return {"rebooted": rebooted, "final_status": status}
        if normalized == "readyreboot" and not rebooted:
            _emit(
                "custom_image_updater_cloud_assistant_rebooting",
                instance_id=instance_id,
                status=status,
            )
            ecs.reboot_instances([instance_id])
            rebooted = True
            _emit(
                "custom_image_updater_cloud_assistant_reboot_submitted",
                instance_id=instance_id,
            )
        elif normalized in {"failed", "error", "installfailed"}:
            raise RuntimeError(
                f"Cloud Assistant installation failed on {instance_id}: {status}. "
                "Open Volcengine ECS Console > Cloud Assistant > Client Management > "
                "Installation Results for the platform installation error."
            )
        time.sleep(5)

    raise TimeoutError(
        f"Timed out waiting for Cloud Assistant after installation: "
        f"{instance_id}={last_status}, rebooted={rebooted}"
    )


def _normalized_cloud_assistant_status(value: str) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _is_cloud_assistant_ready_reboot(value: str) -> bool:
    return _normalized_cloud_assistant_status(value) == "readyreboot"


def install_updater_on_instance(
    ecs: VolcengineEcsClient,
    instance_id: str,
    *,
    platform: str,
    updater: UpdaterPayload,
    config: GuestUpdaterConfig,
    timeout_seconds: int,
    invocation_name: str,
) -> dict[str, Any]:
    _, results = ecs.run_cloud_assistant_command(
        [instance_id],
        script=build_bootstrap_script(platform, updater, config),
        command_type="PowerShell" if platform == "windows" else "Shell",
        invocation_name=invocation_name,
        timeout_seconds=timeout_seconds,
    )
    if len(results) != 1:
        raise RuntimeError(
            f"Expected one Cloud Assistant result for {instance_id}, got {len(results)}"
        )
    return validate_bootstrap_result(results[0], updater.sha256)


def validate_bootstrap_result(
    result: CloudAssistantCommandResult,
    expected_sha256: str,
) -> dict[str, Any]:
    if result.status.lower() not in {"success", "succeeded", "finished"} or result.exit_code not in {
        0,
        None,
    }:
        raise RuntimeError(
            f"Cloud Assistant updater bootstrap failed on {result.instance_id}: "
            f"status={result.status}, exit_code={result.exit_code}, "
            f"error={result.error_code} {result.error_message}, output={result.output[-4000:]}"
        )
    return validate_bootstrap_output(
        result.output,
        expected_sha256,
        context=f"Cloud Assistant bootstrap on {result.instance_id}",
    )


def validate_bootstrap_output(
    output: str,
    expected_sha256: str,
    *,
    context: str,
) -> dict[str, Any]:
    payload = _last_json_object(output)
    if payload.get("status") not in {"installed", "unchanged"}:
        raise RuntimeError(f"{context} returned an invalid status: {payload}")
    if str(payload.get("updater_sha256") or "").lower() != expected_sha256:
        raise RuntimeError(f"{context} returned an updater SHA256 mismatch: {payload}")
    return payload


def promote_replacement(
    ecs: VolcengineEcsClient,
    request: UpgradeRequest,
    replacement: SharedImage,
    *,
    delete_replaced_image: bool,
    delete_binded_snapshots: bool,
    delete_timeout_seconds: int,
) -> dict[str, Any]:
    source = request.source
    original_name = request.original_name
    renamed_source = False
    backup_name = source.image_name

    if replacement.image_name != original_name:
        backup_name = image_name_with_suffix(
            original_name,
            f"-pre-updater-{source.image_id[-8:]}",
        )
        if source.image_name != backup_name:
            ecs.modify_image_name(source.image_id, backup_name)
            renamed_source = True
        try:
            ecs.modify_image_name(replacement.image_id, original_name)
        except Exception:
            if renamed_source:
                ecs.modify_image_name(source.image_id, original_name)
            raise

    old_image_deleted = False
    if delete_replaced_image:
        ecs.delete_images(
            [source.image_id],
            delete_binded_snapshots=delete_binded_snapshots,
        )
        ecs.wait_for_images_deleted(
            [source.image_id],
            timeout_seconds=delete_timeout_seconds,
        )
        old_image_deleted = True

    return {
        "promoted": True,
        "original_image_name": original_name,
        "replacement_image_id": replacement.image_id,
        "replacement_image_name": original_name,
        "old_image_id": source.image_id,
        "old_image_name": backup_name,
        "old_image_deleted": old_image_deleted,
    }


def confirm_manual_pre_capture(
    instance: InstanceRecord,
    confirmation_reader=None,
) -> None:
    """Wait for an operator to finish GUI-only image preparation."""

    _emit(
        "custom_image_updater_manual_pre_capture_required",
        instance_id=instance.instance_id,
        private_ip=instance.private_ip,
        public_ip=instance.public_ip,
        steps=[
            "Open this instance through the Volcengine VNC console.",
            "Log in as the same Windows user used by evaluation tasks.",
            "Restart Windows once, log in again, and verify the OSWorld server no longer opens a console window.",
            "Start SolidWorks, accept its license agreement, and finish first-run setup.",
            "Close SolidWorks and confirm that no license dialog reappears on the next launch.",
            "Return to this terminal and type CAPTURE.",
        ],
    )
    print(
        f"\nInstance {instance.instance_id} is waiting for manual preparation.",
        flush=True,
    )
    print(
        "Type CAPTURE to stop it and create the replacement image, "
        "or ABORT to retain the build instance and exit.",
        flush=True,
    )
    reader = confirmation_reader or input
    while True:
        try:
            confirmation = reader("Confirmation [CAPTURE/ABORT]: ")
        except EOFError as exc:
            raise RuntimeError(
                "Interactive input closed before image capture was confirmed; "
                "the build instance is retained"
            ) from exc
        normalized = confirmation.strip().upper()
        if normalized == "CAPTURE":
            break
        if normalized == "ABORT":
            raise RuntimeError(
                "Image capture was aborted; the build instance is retained"
            )
        if normalized:
            print(
                f"Unrecognized confirmation {confirmation!r}; "
                "type CAPTURE or ABORT.",
                flush=True,
            )
        else:
            print(
                "Empty input ignored; type CAPTURE when preparation is complete.",
                flush=True,
            )
    _emit(
        "custom_image_updater_manual_pre_capture_confirmed",
        instance_id=instance.instance_id,
    )


def upgrade_one(
    ecs: VolcengineEcsClient,
    request: UpgradeRequest,
    updater: UpdaterPayload,
    guest_config: GuestUpdaterConfig,
    args: argparse.Namespace,
    index: int,
) -> dict[str, Any]:
    source = request.source
    platform = "windows" if "windows" in str(source.os_type or "").lower() else "linux"
    build_id = f"updater-{time.strftime('%Y%m%d-%H%M%S')}-{index}"
    instance_id: str | None = None
    build_instance_id: str | None = None
    replacement: SharedImage | None = None
    success = False

    try:
        _emit(
            "custom_image_updater_started",
            source_image_id=source.image_id,
            source_image_name=source.image_name,
            original_image_name=request.original_name,
            target_image_name=request.target_name,
            platform=platform,
        )
        instances = ecs.run_instances(
            source,
            count=1,
            run_id=build_id,
            snapshot="custom-image-updater",
            os_type="Windows" if platform == "windows" else "Ubuntu",
            wait_timeout_seconds=args.instance_ready_timeout_seconds,
        )
        if len(instances) != 1:
            raise RuntimeError(f"Expected one disposable ECS, got {len(instances)}")
        instance = instances[0]
        instance_id = instance.instance_id
        build_instance_id = instance_id
        installation = install_updater_with_transport(
            ecs,
            instance,
            platform=platform,
            updater=updater,
            config=guest_config,
            transport=args.bootstrap_transport,
            vm_server_port=args.vm_server_port,
            execute_wait_timeout_seconds=args.execute_wait_timeout_seconds,
            execute_request_timeout_seconds=args.execute_request_timeout_seconds,
            cloud_assistant_initial_wait_seconds=(
                args.cloud_assistant_initial_wait_seconds
            ),
            cloud_assistant_timeout_seconds=args.cloud_assistant_timeout_seconds,
            auto_install_cloud_assistant=args.auto_install_cloud_assistant,
            bootstrap_timeout_seconds=args.bootstrap_timeout_seconds,
            invocation_name=f"arena-updater-bootstrap-{build_id}",
        )
        _emit(
            "custom_image_updater_guest_ready",
            instance_id=instance_id,
            transport=installation["transport"],
            cloud_assistant=installation.get("cloud_assistant"),
            bootstrap=installation["bootstrap"],
        )

        if getattr(args, "pause_before_capture", False):
            confirm_manual_pre_capture(instance)

        ecs.stop_instances([instance_id], force=args.force_stop)
        ecs.wait_for_instance_status(
            [instance_id],
            expected_status="STOPPED",
            timeout_seconds=args.instance_stop_timeout_seconds,
        )
        replacement_id = ecs.create_image_from_instance(
            instance_id,
            image_name=request.target_name,
            description=None,
            tags={
                "managed_by": MANAGED_BY_TAG,
                "source": SOURCE_UPGRADE_TAG,
                "replaces_image_id": source.image_id,
                "original_image_name": request.original_name[:256],
                "updater_version": updater.version[:256],
                "updater_sha256": updater.sha256,
                **(
                    {"windows_startup_policy": WINDOWS_STARTUP_POLICY_VERSION}
                    if platform == "windows"
                    else {}
                ),
            },
        )
        replacement = ecs.wait_for_image_available(
            replacement_id,
            timeout_seconds=args.image_timeout_seconds,
        )

        # The captured image no longer depends on the build instance. Releasing
        # it before promotion also avoids image deletion being blocked by a
        # stopped instance created from the old source image.
        if not args.keep_build_instance:
            ecs.terminate_instances([instance_id])
            _emit("custom_image_updater_instance_deleted", instance_id=instance_id)
            instance_id = None

        promotion = None
        if args.promote:
            promotion = promote_replacement(
                ecs,
                request,
                replacement,
                delete_replaced_image=args.delete_replaced_images,
                delete_binded_snapshots=args.delete_binded_snapshots,
                delete_timeout_seconds=args.image_delete_timeout_seconds,
            )
        success = True
        result = {
            "source_image_id": source.image_id,
            "source_image_name": source.image_name,
            "original_image_name": request.original_name,
            "replacement_image_id": replacement.image_id,
            "replacement_image_name": (
                request.original_name if args.promote else replacement.image_name
            ),
            "build_instance_id": build_instance_id,
            "updater_version": updater.version,
            "updater_sha256": updater.sha256,
            "windows_startup_policy": (
                WINDOWS_STARTUP_POLICY_VERSION if platform == "windows" else None
            ),
            "bootstrap_transport": installation["transport"],
            "bootstrap": installation["bootstrap"],
            "promotion": promotion,
        }
        _emit("custom_image_updater_completed", **result)
        return result
    finally:
        should_delete = bool(instance_id) and (
            (success and not args.keep_build_instance)
            or (not success and args.cleanup_on_error)
        )
        if should_delete:
            ecs.terminate_instances([instance_id])
            _emit("custom_image_updater_instance_deleted", instance_id=instance_id)
        elif instance_id and not success:
            _emit(
                "custom_image_updater_instance_retained",
                instance_id=instance_id,
                replacement_image_id=replacement.image_id if replacement else None,
                reason="upgrade_failed",
            )


def _validate_args(args: argparse.Namespace) -> None:
    explicit = bool(args.image_id or args.image_id_file or args.image_name)
    if args.all_managed_copies and explicit:
        raise ValueError(
            "--all-managed-images cannot be combined with explicit image selectors"
        )
    if not args.all_managed_copies and not explicit:
        raise ValueError(
            "Use --all-managed-images or provide --image-id, --image-id-file, or --image-name"
        )
    if args.delete_replaced_images and not args.promote:
        raise ValueError("--delete-replaced-images requires --promote")
    if args.delete_binded_snapshots and not args.delete_replaced_images:
        raise ValueError("--delete-bound-snapshots requires --delete-replaced-images")
    if args.cleanup_on_error and args.keep_build_instance:
        raise ValueError("--cleanup-on-error and --keep-build-instance cannot be combined")
    if args.delete_replaced_images and args.keep_build_instance:
        raise ValueError(
            "--delete-replaced-images and --keep-build-instance cannot be combined"
        )
    for name in (
        "vm_server_port",
        "execute_wait_timeout_seconds",
        "execute_request_timeout_seconds",
        "bootstrap_timeout_seconds",
    ):
        if getattr(args, name) <= 0:
            raise ValueError(f"--{name.replace('_', '-')} must be greater than zero")


def main() -> int:
    args = parse_args()
    _validate_args(args)
    updater = load_updater_payload(args.updater_source, args.updater_version_file)
    target_suffix = args.target_name_suffix or f"-updater-v{updater.version}"

    base_config = VolcengineLaunchConfig.from_env()
    project_name = args.project_name or base_config.project_name or "agent-eval"
    config = custom_image_config(
        base_config,
        project_name,
        install_run_command_agent=args.bootstrap_transport == "cloud-assistant",
    )
    ecs = VolcengineEcsClient(config)
    images = ecs.list_shared_images()
    image_ids = [*args.image_id, *load_image_ids(args.image_id_file)]
    selected = resolve_source_images(
        images,
        all_managed_copies=args.all_managed_copies,
        image_ids=image_ids,
        image_names=args.image_name,
    )
    if args.pause_before_capture and not args.dry_run:
        if len(selected) != 1:
            raise ValueError("--pause-before-capture requires exactly one image")
        if "windows" not in str(selected[0].os_type or "").lower():
            raise ValueError("--pause-before-capture requires a Windows image")
        if not sys.stdin.isatty():
            raise ValueError(
                "--pause-before-capture requires an interactive terminal; do not use nohup"
            )
    requests = build_upgrade_requests(
        selected,
        images,
        updater=updater,
        target_suffix=target_suffix,
        force_rebuild=args.force_rebuild or args.pause_before_capture,
    )
    _emit(
        "custom_image_updater_plan",
        project_name=project_name,
        selected_count=len(selected),
        updater_version=updater.version,
        updater_sha256=updater.sha256,
        dry_run=args.dry_run,
        promote=args.promote,
        delete_replaced_images=args.delete_replaced_images,
        force_rebuild=args.force_rebuild or args.pause_before_capture,
        pause_before_capture=args.pause_before_capture,
        bootstrap_transport=args.bootstrap_transport,
        vm_server_port=args.vm_server_port,
        images=[
            {
                "source_image_id": request.source.image_id,
                "source_image_name": request.source.image_name,
                "original_image_name": request.original_name,
                "target_image_name": request.target_name,
                "os_type": request.source.os_type,
                "action": (
                    "skip_current"
                    if request.existing_replacement
                    and request.existing_replacement.image_id == request.source.image_id
                    else "promote_existing"
                    if request.existing_replacement and args.promote
                    else "skip_existing"
                    if request.existing_replacement
                    else "upgrade"
                ),
                "existing_replacement_id": (
                    request.existing_replacement.image_id
                    if request.existing_replacement
                    else None
                ),
            }
            for request in requests
        ],
    )
    if args.dry_run:
        return 0

    completed = []
    skipped = []
    failed = []
    guest_config = guest_config_from_args(args)
    for index, request in enumerate(requests, start=1):
        try:
            if request.existing_replacement:
                if request.existing_replacement.image_id == request.source.image_id:
                    result = {
                        "source_image_id": request.source.image_id,
                        "replacement_image_id": request.source.image_id,
                        "reason": "source image already contains this updater SHA256",
                    }
                    skipped.append(result)
                    _emit("custom_image_updater_skipped_current", **result)
                elif args.promote:
                    promotion = promote_replacement(
                        ecs,
                        request,
                        request.existing_replacement,
                        delete_replaced_image=args.delete_replaced_images,
                        delete_binded_snapshots=args.delete_binded_snapshots,
                        delete_timeout_seconds=args.image_delete_timeout_seconds,
                    )
                    result = {
                        "source_image_id": request.source.image_id,
                        "replacement_image_id": request.existing_replacement.image_id,
                        "resumed": True,
                        "promotion": promotion,
                    }
                    completed.append(result)
                    _emit("custom_image_updater_existing_promoted", **result)
                else:
                    result = {
                        "source_image_id": request.source.image_id,
                        "replacement_image_id": request.existing_replacement.image_id,
                        "reason": "matching replacement already exists",
                    }
                    skipped.append(result)
                    _emit("custom_image_updater_skipped_existing", **result)
                continue

            completed.append(
                upgrade_one(ecs, request, updater, guest_config, args, index)
            )
        except Exception as exc:
            failure = {
                "source_image_id": request.source.image_id,
                "source_image_name": request.source.image_name,
                "error": f"{type(exc).__name__}: {exc}",
            }
            failed.append(failure)
            _emit("custom_image_updater_failed", **failure)
            if not args.continue_on_error:
                raise

    _emit(
        "custom_image_updater_summary",
        completed=completed,
        skipped=skipped,
        failed=failed,
    )
    return 1 if failed else 0


def _last_json_object(value: str) -> dict[str, Any]:
    for line in reversed(value.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError(f"Cloud Assistant output did not contain JSON: {value[-4000:]}")


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _emit(event: str, **payload: object) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        _emit("custom_image_updater_interrupted")
        raise SystemExit(130)
    except Exception as exc:
        _emit("custom_image_updater_aborted", error=f"{type(exc).__name__}: {exc}")
        raise SystemExit(1)
