"""Provision the OSWorld server code inside newly launched ECS instances."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from engiworld.scheduler.schemas import InstanceRecord
from engiworld.scheduler.storage import create_s3_client
from engiworld.scheduler.volcengine_ecs import (
    CloudAssistantCommandResult,
    VolcengineEcsClient,
)


DEFAULT_VM_OSWORLD_BUCKET = "osworld-server"
DEFAULT_VM_OSWORLD_BUNDLE_PATH = "releases/osworld-vm-server-dpi-physical-20260922.tgz"
_EXECUTE_READY_MARKER = "arena-osworld-execute-ready"
_VALID_TRANSPORTS = {"auto", "execute", "cloud-assistant"}
_EXECUTE_UPLOAD_CHUNK_BYTES = 6 * 1024
_DEFAULT_UPDATER_SOURCE_PATH = "deploy/vm-updater/osworld_updater.py"
WINDOWS_SERVER_SUPERVISOR_POLICY_VERSION = "7"

_WINDOWS_SERVER_SUPERVISOR_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$InstallDir = Join-Path $env:ProgramData 'ArenaOSWorldUpdater'
$StartupScriptPath = Join-Path $InstallDir 'start-osworld-server.ps1'
$WatchdogScriptPath = Join-Path $InstallDir 'watch-osworld-server.ps1'
$StartupConfigPath = Join-Path $InstallDir 'server-startup.json'
$ConfigPath = Join-Path $InstallDir 'config.json'
$LogDir = Join-Path $InstallDir 'logs'
$PolicyVersion = '__POLICY_VERSION__'
$RestartRunning = $__RESTART_RUNNING__
$WatchdogTaskName = 'ArenaOSWorldServerWatchdog'

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Arena OSWorld updater config was not found: $ConfigPath"
}
$UpdaterConfig = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$TaskName = [string]$UpdaterConfig.scheduled_task_name
if ([string]::IsNullOrWhiteSpace($TaskName)) { $TaskName = 'OSWorldServer' }
$ScheduledTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$WatchdogTask = Get-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
$CurrentWatchdogAction = $null
if ($WatchdogTask) { $CurrentWatchdogAction = @($WatchdogTask.Actions)[0] }
$ListenerPort = ([Uri][string]$UpdaterConfig.health_url).Port
$ExistingStartupConfig = $null
if (Test-Path -LiteralPath $StartupConfigPath -PathType Leaf) {
    $ExistingStartupConfig = Get-Content -LiteralPath $StartupConfigPath -Raw | ConvertFrom-Json
}
$CurrentAction = @($ScheduledTask.Actions)[0]
if (-not $CurrentAction) { throw "Scheduled task has no action: $TaskName" }

$ServerExecute = [string]$CurrentAction.Execute
$ServerArguments = [string]$CurrentAction.Arguments
$ServerWorkingDirectory = [string]$CurrentAction.WorkingDirectory
if ($ExistingStartupConfig) {
    if (-not [string]::IsNullOrWhiteSpace([string]$ExistingStartupConfig.execute)) {
        $ServerExecute = [string]$ExistingStartupConfig.execute
        $ServerArguments = [string]$ExistingStartupConfig.arguments
        $ServerWorkingDirectory = [string]$ExistingStartupConfig.working_directory
    }
}
if ([string]::IsNullOrWhiteSpace($ServerWorkingDirectory)) {
    $ServerWorkingDirectory = [string]$UpdaterConfig.current_dir
}
if ([IO.Path]::GetFileName($ServerExecute) -ieq 'python.exe') {
    $WindowlessPython = Join-Path (Split-Path -Parent $ServerExecute) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $WindowlessPython -PathType Leaf)) {
        throw "Windowless Python executable was not found: $WindowlessPython"
    }
    $ServerExecute = $WindowlessPython
}
if (-not (Test-Path -LiteralPath $ServerExecute -PathType Leaf)) {
    throw "OSWorld server executable was not found: $ServerExecute"
}

$PolicyCurrent = (
    $ExistingStartupConfig -and
    [string]$ExistingStartupConfig.startup_policy_version -eq $PolicyVersion -and
    (Test-Path -LiteralPath $StartupScriptPath -PathType Leaf) -and
    (Test-Path -LiteralPath $WatchdogScriptPath -PathType Leaf) -and
    [string]$CurrentAction.Arguments -like "*$StartupScriptPath*" -and
    $CurrentWatchdogAction -and
    [string]$CurrentWatchdogAction.Arguments -like "*$WatchdogScriptPath*"
)
if ($PolicyCurrent) {
    [ordered]@{
        status = 'unchanged'
        policy_version = $PolicyVersion
        restart_scheduled = $false
        task_name = $TaskName
        watchdog_task_name = $WatchdogTaskName
    } | ConvertTo-Json -Compress
    exit 0
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
[ordered]@{
    execute = $ServerExecute
    arguments = $ServerArguments
    working_directory = $ServerWorkingDirectory
    startup_policy_version = $PolicyVersion
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StartupConfigPath -Encoding UTF8

$StartupWrapper = @'
$ErrorActionPreference = 'Continue'
$InstallDir = Join-Path $env:ProgramData 'ArenaOSWorldUpdater'
$Config = Get-Content (Join-Path $InstallDir 'server-startup.json') -Raw | ConvertFrom-Json
$LogDir = Join-Path $InstallDir 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$EventLog = Join-Path $LogDir 'server-startup-events.log'
while ($true) {
    $Timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss-fff')
    $StdoutLog = Join-Path $LogDir "server-$Timestamp.stdout.log"
    $StderrLog = Join-Path $LogDir "server-$Timestamp.stderr.log"
    Add-Content -LiteralPath $EventLog -Value "$(Get-Date -Format o) starting $($Config.execute) $($Config.arguments) cwd=$($Config.working_directory)"
    try {
        $StartParameters = @{
            FilePath = [string]$Config.execute
            WorkingDirectory = [string]$Config.working_directory
            PassThru = $true
            Wait = $true
            RedirectStandardOutput = $StdoutLog
            RedirectStandardError = $StderrLog
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$Config.arguments)) {
            $StartParameters.ArgumentList = [string]$Config.arguments
        }
        $Process = Start-Process @StartParameters
        Add-Content -LiteralPath $EventLog -Value "$(Get-Date -Format o) exited pid=$($Process.Id) code=$($Process.ExitCode)"
    } catch {
        Add-Content -LiteralPath $EventLog -Value "$(Get-Date -Format o) failed: $($_ | Out-String)"
    }
    Start-Sleep -Seconds 5
}
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
while ($true) {
    if ([string]::IsNullOrWhiteSpace([string]$UpdateLockPath)) {
        try {
            if (Test-Path -LiteralPath $UpdaterConfigPath -PathType Leaf) {
                $UpdaterConfig = Get-Content -LiteralPath $UpdaterConfigPath -Raw |
                    ConvertFrom-Json
                $ConfiguredCurrentDir = [string]$UpdaterConfig.current_dir
                if (-not [string]::IsNullOrWhiteSpace($ConfiguredCurrentDir)) {
                    $UpdateParent = Split-Path -Parent $ConfiguredCurrentDir
                    $UpdateLockPath = Join-Path $UpdateParent '.arena-osworld-update.lock'
                }
            }
        } catch {
            $UpdateLockPath = $null
        }
        if ([string]::IsNullOrWhiteSpace([string]$UpdateLockPath)) {
            $ConsecutiveMisses = 0
            Start-Sleep -Seconds 10
            continue
        }
    }
    if (Test-Path -LiteralPath $UpdateLockPath -PathType Leaf) {
        $ConsecutiveMisses = 0
        Start-Sleep -Seconds 10
        continue
    }
$Listening = @(
        Get-NetTCPConnection -LocalPort __LISTENER_PORT__ -State Listen -ErrorAction SilentlyContinue
    ).Count -gt 0
    if ($Listening) {
        $ConsecutiveMisses = 0
    } else {
        $ConsecutiveMisses += 1
    }
    if ($ConsecutiveMisses -ge 3) {
        Add-Content -LiteralPath $WatchdogLog -Value "$(Get-Date -Format o) restarting $TaskName after $ConsecutiveMisses closed-port probes"
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        $ConsecutiveMisses = 0
        Start-Sleep -Seconds 15
    }
    Start-Sleep -Seconds 10
}
'@
$WatchdogWrapper = $WatchdogWrapper.Replace(
    '__TASK_NAME__',
    $TaskName.Replace("'", "''")
).Replace(
    '__LISTENER_PORT__',
    [string]$ListenerPort
)
[IO.File]::WriteAllText($WatchdogScriptPath, $WatchdogWrapper, $Utf8NoBom)

$TaskUser = [string]$ScheduledTask.Principal.UserId
if ([string]::IsNullOrWhiteSpace($TaskUser)) {
    throw "Scheduled task has no principal user: $TaskName"
}
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
Set-ScheduledTask -TaskName $TaskName -TaskPath $ScheduledTask.TaskPath `
    -Action $ManagedAction -Trigger @($StartupTrigger, $LoginTrigger) `
    -Settings $TaskSettings | Out-Null

$WatchdogTrigger = New-ScheduledTaskTrigger -AtStartup
$WatchdogTrigger.Delay = 'PT20S'
$WatchdogArguments = '-NoProfile -NonInteractive -WindowStyle Hidden ' +
    '-ExecutionPolicy Bypass -File "' + $WatchdogScriptPath + '"'
$WatchdogAction = New-ScheduledTaskAction -Execute $TaskPowerShell `
    -Argument $WatchdogArguments -WorkingDirectory $InstallDir
$WatchdogPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' `
    -LogonType ServiceAccount -RunLevel Highest
$WatchdogSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Stop-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $WatchdogTaskName -Action $WatchdogAction `
    -Trigger $WatchdogTrigger -Principal $WatchdogPrincipal `
    -Settings $WatchdogSettings -Force | Out-Null
Start-ScheduledTask -TaskName $WatchdogTaskName

$RestartScheduled = $false
if ($RestartRunning) {
    $ApplyTaskName = 'ArenaOSWorldSupervisorApply'
    $ApplyScriptPath = Join-Path $InstallDir 'apply-server-supervisor.ps1'
    $EscapedTaskName = $TaskName.Replace("'", "''")
    $ApplyScript = @"
Start-Sleep -Seconds 3
Stop-ScheduledTask -TaskName '$EscapedTaskName' -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-ScheduledTask -TaskName '$EscapedTaskName' -ErrorAction Stop
Unregister-ScheduledTask -TaskName '$ApplyTaskName' -Confirm:`$false -ErrorAction SilentlyContinue
"@
    [IO.File]::WriteAllText($ApplyScriptPath, $ApplyScript, $Utf8NoBom)
    $ApplyArguments = '-NoProfile -NonInteractive -WindowStyle Hidden ' +
        '-ExecutionPolicy Bypass -File "' + $ApplyScriptPath + '"'
    $ApplyAction = New-ScheduledTaskAction -Execute $TaskPowerShell -Argument $ApplyArguments
    $ApplyPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' `
        -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName $ApplyTaskName -Action $ApplyAction `
        -Principal $ApplyPrincipal -Force | Out-Null
    Start-ScheduledTask -TaskName $ApplyTaskName
    $RestartScheduled = $true
}

[ordered]@{
    status = 'updated'
    policy_version = $PolicyVersion
    restart_scheduled = $RestartScheduled
    task_name = $TaskName
    watchdog_task_name = $WatchdogTaskName
    server_execute = $ServerExecute
} | ConvertTo-Json -Compress
'''.strip()


@dataclass(frozen=True)
class VmOsworldBundleSpec:
    bucket: str
    object_key: str
    manifest_key: str
    version: str
    root_dir: str
    archive_sha256: str
    content_sha256: str
    archive_size_bytes: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VmOsworldBundleSpec":
        required = [
            "bucket",
            "object_key",
            "manifest_key",
            "version",
            "root_dir",
            "archive_sha256",
            "content_sha256",
        ]
        missing = [name for name in required if not payload.get(name)]
        if missing:
            raise ValueError("VM OSWorld bundle metadata is missing: " + ", ".join(missing))
        return cls(
            bucket=str(payload["bucket"]),
            object_key=str(payload["object_key"]),
            manifest_key=str(payload["manifest_key"]),
            version=str(payload["version"]),
            root_dir=str(payload["root_dir"]),
            archive_sha256=_sha256(payload["archive_sha256"], "archive_sha256"),
            content_sha256=_sha256(payload["content_sha256"], "content_sha256"),
            archive_size_bytes=_optional_int(payload.get("archive_size_bytes")),
        )


@dataclass(frozen=True)
class VmOsworldProvisionConfig:
    presign_expires_seconds: int = 3600
    update_timeout_seconds: int = 600
    cloud_assistant_wait_timeout_seconds: int = 300
    transport: str = "auto"
    execute_port: int = 5000
    execute_wait_timeout_seconds: int = 300
    execute_request_timeout_seconds: int = 30
    execute_max_workers: int = 32
    max_attempts: int = 2
    max_failed_instances: int = 5
    skip_health: bool = False
    linux_updater_command: str = "/opt/arena-osworld-updater/update-osworld"
    windows_updater_command: str = (
        "C:\\ProgramData\\ArenaOSWorldUpdater\\update-osworld.ps1"
    )

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "VmOsworldProvisionConfig":
        payload = payload or {}
        config = cls(
            presign_expires_seconds=int(payload.get("presign_expires_seconds", 3600)),
            update_timeout_seconds=int(payload.get("update_timeout_seconds", 600)),
            cloud_assistant_wait_timeout_seconds=int(
                payload.get("cloud_assistant_wait_timeout_seconds", 300)
            ),
            transport=str(payload.get("transport") or "auto").strip().lower(),
            execute_port=int(payload.get("execute_port", 5000)),
            execute_wait_timeout_seconds=int(
                payload.get("execute_wait_timeout_seconds", 300)
            ),
            execute_request_timeout_seconds=int(
                payload.get("execute_request_timeout_seconds", 30)
            ),
            execute_max_workers=int(payload.get("execute_max_workers", 32)),
            max_attempts=int(payload.get("max_attempts", 2)),
            max_failed_instances=int(payload.get("max_failed_instances", 5)),
            skip_health=bool(payload.get("skip_health", False)),
            linux_updater_command=str(
                payload.get("linux_updater_command")
                or "/opt/arena-osworld-updater/update-osworld"
            ),
            windows_updater_command=str(
                payload.get("windows_updater_command")
                or "C:\\ProgramData\\ArenaOSWorldUpdater\\update-osworld.ps1"
            ),
        )
        _validate_provision_config(config)
        return config


def resolve_vm_osworld_bundle(
    *,
    bucket: str,
    object_key: str,
    manifest_key: str | None = None,
) -> VmOsworldBundleSpec:
    manifest_key = manifest_key or f"{object_key}.manifest.json"
    client, settings = create_s3_client(bucket)
    try:
        response = client.get_object(Bucket=settings.bucket, Key=manifest_key)
        payload = json.loads(response["Body"].read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read VM OSWorld manifest s3://{bucket}/{manifest_key}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"VM OSWorld manifest must be a JSON object: {manifest_key}")
    if payload.get("bundle_type") != "osworld-vm-server":
        raise ValueError(
            f"Unsupported VM OSWorld bundle_type={payload.get('bundle_type')!r}"
        )
    return VmOsworldBundleSpec.from_dict(
        {
            **payload,
            "bucket": bucket,
            "object_key": object_key,
            "manifest_key": manifest_key,
        }
    )


def provision_vm_osworld(
    ecs: VolcengineEcsClient,
    instances: list[InstanceRecord],
    *,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    run_id: str,
) -> tuple[list[InstanceRecord], dict[str, Any]]:
    if not instances:
        return [], {"target_version": bundle.version, "instances": []}
    _validate_provision_config(config)

    client, settings = create_s3_client(bundle.bucket)
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.bucket, "Key": bundle.object_key},
        ExpiresIn=config.presign_expires_seconds,
        HttpMethod="GET",
    )

    reports: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    grouped: dict[str, list[InstanceRecord]] = {"linux": [], "windows": []}
    for instance in instances:
        group = "windows" if "windows" in instance.os_type.lower() else "linux"
        grouped[group].append(instance)

    for platform, platform_instances in grouped.items():
        for batch_number, batch in enumerate(_chunks(platform_instances, 100), start=1):
            batch_reports, batch_errors = _provision_batch(
                ecs,
                batch,
                platform=platform,
                bundle=bundle,
                config=config,
                url=url,
                invocation_name=f"arena-osworld-{run_id}-{platform}-{batch_number}",
            )
            reports.update(batch_reports)
            errors.update(batch_errors)

    if len(errors) > config.max_failed_instances:
        raise RuntimeError(
            "VM OSWorld provisioning failure count exceeds tolerance "
            f"({len(errors)} > {config.max_failed_instances}): "
            + _format_instance_errors(errors)
        )

    failed_instance_ids = [
        instance.instance_id for instance in instances if instance.instance_id in errors
    ]
    termination_error = None
    if failed_instance_ids:
        try:
            ecs.terminate_instances(failed_instance_ids)
        except Exception as exc:
            termination_error = f"{type(exc).__name__}: {exc}"

    provisioned = [
        replace(
            instance,
            metadata={
                **instance.metadata,
                "vm_osworld_version": bundle.version,
                "vm_osworld_content_sha256": bundle.content_sha256,
                "vm_osworld_archive_sha256": bundle.archive_sha256,
                "vm_osworld_update_status": reports[instance.instance_id]["status"],
            },
        )
        for instance in instances
        if instance.instance_id in reports
    ]
    return provisioned, {
        "target_version": bundle.version,
        "content_sha256": bundle.content_sha256,
        "updated": sum(item["status"] == "updated" for item in reports.values()),
        "unchanged": sum(item["status"] == "unchanged" for item in reports.values()),
        "failed": len(errors),
        "max_failed_instances": config.max_failed_instances,
        "failed_instances": [
            {
                "instance_id": instance.instance_id,
                "private_ip": instance.private_ip,
                "snapshot": instance.metadata.get("snapshot", ""),
                "image_id": instance.metadata.get("image_id", ""),
                "error": errors[instance.instance_id],
            }
            for instance in instances
            if instance.instance_id in errors
        ],
        "terminated_failed_instance_ids": failed_instance_ids if not termination_error else [],
        "failed_instance_termination_error": termination_error,
        "instances": [
            reports[instance.instance_id]
            for instance in instances
            if instance.instance_id in reports
        ],
    }


def _provision_batch(
    ecs: VolcengineEcsClient,
    instances: list[InstanceRecord],
    *,
    platform: str,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
    invocation_name: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if config.transport == "cloud-assistant":
        return _provision_batch_via_cloud_assistant(
            ecs,
            instances,
            platform=platform,
            bundle=bundle,
            config=config,
            url=url,
            invocation_name=invocation_name,
        )

    reports, execute_errors = _provision_batch_via_execute(
        instances,
        platform=platform,
        bundle=bundle,
        config=config,
        url=url,
        invocation_name=invocation_name,
    )
    if not execute_errors:
        return reports, {}
    if config.transport == "execute":
        return reports, execute_errors

    fallback_instances = [
        instance for instance in instances if instance.instance_id in execute_errors
    ]
    fallback_reports, fallback_errors = _provision_batch_via_cloud_assistant(
        ecs,
        fallback_instances,
        platform=platform,
        bundle=bundle,
        config=config,
        url=url,
        invocation_name=f"{invocation_name}-fallback",
    )

    for instance_id, report in fallback_reports.items():
        report["execute_error"] = execute_errors[instance_id]
    reports.update(fallback_reports)
    combined_errors = {
        instance_id: (
            f"execute={execute_errors[instance_id]}; cloud-assistant={fallback_error}"
        )
        for instance_id, fallback_error in fallback_errors.items()
    }
    return reports, combined_errors


def _provision_batch_via_execute(
    instances: list[InstanceRecord],
    *,
    platform: str,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
    invocation_name: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    reports: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    cancel_event = threading.Event()
    max_workers = min(len(instances), config.execute_max_workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_instances = {
            executor.submit(
                _provision_instance_via_execute,
                instance,
                platform=platform,
                bundle=bundle,
                config=config,
                url=url,
                invocation_name=invocation_name,
                cancel_event=cancel_event,
            ): instance
            for instance in instances
        }
        try:
            for future in concurrent.futures.as_completed(future_instances):
                instance = future_instances[future]
                try:
                    reports[instance.instance_id] = future.result()
                except Exception as exc:
                    errors[instance.instance_id] = f"{type(exc).__name__}: {exc}"
        except BaseException:
            cancel_event.set()
            for future in future_instances:
                future.cancel()
            raise
    return reports, errors


def _provision_instance_via_execute(
    instance: InstanceRecord,
    *,
    platform: str,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
    invocation_name: str,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    _raise_if_cancelled(cancel_event)
    health_matches = _vm_health_matches(
        instance,
        config.execute_port,
        bundle.content_sha256,
    )
    if health_matches and platform != "windows":
        return {
            "instance_id": instance.instance_id,
            "status": "unchanged",
            "downloaded": False,
            "transport": "execute",
            "invocation_id": None,
            "attempt": 0,
        }

    if not health_matches:
        _wait_for_vm_execute(
            instance,
            platform=platform,
            config=config,
            cancel_event=cancel_event,
        )
    updater_bootstrap = _ensure_runtime_updater_current(
        instance,
        platform=platform,
        config=config,
    )
    startup_supervisor = None
    if platform == "windows":
        startup_supervisor = _ensure_windows_server_supervisor(
            instance,
            config=config,
            restart_running=health_matches,
        )
    _verify_vm_updater(instance, platform=platform, config=config)
    if health_matches:
        if startup_supervisor and startup_supervisor.get("restart_scheduled"):
            _sleep_with_cancel(cancel_event, 5)
            _wait_for_vm_health(
                instance,
                port=config.execute_port,
                expected_content_sha256=bundle.content_sha256,
                timeout_seconds=config.update_timeout_seconds,
                cancel_event=cancel_event,
            )
        return {
            "instance_id": instance.instance_id,
            "status": "unchanged",
            "downloaded": False,
            "transport": "execute",
            "invocation_id": None,
            "attempt": 0,
            "updater_bootstrap": updater_bootstrap,
            "startup_supervisor": startup_supervisor,
        }

    last_error: Exception | None = None
    for attempt in range(1, max(1, config.max_attempts) + 1):
        update_name = _safe_update_name(
            f"{invocation_name}-{instance.instance_id}",
            suffix=f"a{attempt}",
        )
        try:
            _raise_if_cancelled(cancel_event)
            command = build_execute_updater_command(
                platform,
                bundle,
                config,
                url,
                update_name=update_name,
            )
            _execute_vm_command(
                instance,
                command,
                port=config.execute_port,
                timeout_seconds=config.execute_request_timeout_seconds,
            )
            _wait_for_vm_health(
                instance,
                port=config.execute_port,
                expected_content_sha256=bundle.content_sha256,
                timeout_seconds=config.update_timeout_seconds,
                cancel_event=cancel_event,
            )
            return {
                "instance_id": instance.instance_id,
                "status": "updated",
                "downloaded": True,
                "transport": "execute",
                "invocation_id": f"execute:{update_name}",
                "attempt": attempt,
                "updater_bootstrap": updater_bootstrap,
                "startup_supervisor": startup_supervisor,
            }
        except Exception as exc:
            last_error = exc
            if attempt < max(1, config.max_attempts):
                _sleep_with_cancel(cancel_event, min(5 * attempt, 15))
                _wait_for_vm_execute(
                    instance,
                    platform=platform,
                    config=config,
                    cancel_event=cancel_event,
                )
    raise RuntimeError(
        f"Failed to update {instance.instance_id} through /execute: {last_error}"
    ) from last_error


def _provision_batch_via_cloud_assistant(
    ecs: VolcengineEcsClient,
    instances: list[InstanceRecord],
    *,
    platform: str,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
    invocation_name: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    instance_ids = [instance.instance_id for instance in instances]
    try:
        ecs.wait_for_cloud_assistant(
            instance_ids,
            timeout_seconds=config.cloud_assistant_wait_timeout_seconds,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        return {}, {instance_id: error for instance_id in instance_ids}
    script = build_updater_script(platform, bundle, config, url)
    reports: dict[str, dict[str, Any]] = {}
    pending_ids = list(instance_ids)
    errors: dict[str, str] = {}
    for attempt in range(1, max(1, config.max_attempts) + 1):
        try:
            invocation_id, results = ecs.run_cloud_assistant_command(
                pending_ids,
                script=script,
                command_type="PowerShell" if platform == "windows" else "Shell",
                invocation_name=f"{invocation_name}-a{attempt}",
                timeout_seconds=config.update_timeout_seconds,
            )
            errors = {}
            returned_ids = set()
            for result in results:
                returned_ids.add(result.instance_id)
                try:
                    reports[result.instance_id] = _validate_command_result(
                        result,
                        invocation_id=invocation_id,
                        attempt=attempt,
                        expected_content_sha256=bundle.content_sha256,
                        transport="cloud-assistant",
                    )
                except Exception as exc:
                    errors[result.instance_id] = f"{type(exc).__name__}: {exc}"
            for instance_id in pending_ids:
                if instance_id not in returned_ids:
                    errors[instance_id] = "Cloud Assistant returned no result"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            errors = {instance_id: error for instance_id in pending_ids}
        if not errors:
            return reports, {}
        pending_ids = list(errors)
        if attempt < max(1, config.max_attempts):
            time.sleep(min(5 * attempt, 15))
    return reports, errors


def build_execute_updater_command(
    platform: str,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
    *,
    update_name: str,
) -> list[str]:
    arguments = _updater_arguments(bundle, config, url)
    if platform == "windows":
        updater_command = " ".join(
            [_powershell_quote(config.windows_updater_command)]
            + [_powershell_quote(value) for value in arguments]
        )
        script_path = (
            "$env:ProgramData\\ArenaOSWorldUpdater\\"
            f"{update_name}.ps1"
        )
        log_path = (
            "$env:ProgramData\\ArenaOSWorldUpdater\\logs\\"
            f"{update_name}.log"
        )
        script = (
            "$ErrorActionPreference = 'Stop'\n"
            f"$TaskName = {_powershell_quote(update_name)}\n"
            f"$ScriptPath = \"{script_path}\"\n"
            "$UpdateScript = @'\n"
            "$ErrorActionPreference = 'Continue'\n"
            f"$LogPath = \"{log_path}\"\n"
            "New-Item -ItemType Directory -Path (Split-Path -Parent $LogPath) "
            "-Force | Out-Null\n"
            "try {\n"
            f"    & {updater_command} *>&1 | Tee-Object -FilePath $LogPath\n"
            "    $ExitCode = $LASTEXITCODE\n"
            "    if ($null -eq $ExitCode) { $ExitCode = 0 }\n"
            "} catch {\n"
            "    $_ | Out-String | Tee-Object -FilePath $LogPath -Append\n"
            "    $ExitCode = 1\n"
            "}\n"
            "exit $ExitCode\n"
            "'@\n"
            "$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)\n"
            "[System.IO.File]::WriteAllText($ScriptPath, $UpdateScript, $Utf8NoBom)\n"
            "$PowerShell = Join-Path $PSHOME 'powershell.exe'\n"
            "$ActionArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass "
            "-File \"' + $ScriptPath + '\"'\n"
            "$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $ActionArgs\n"
            "$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' "
            "-LogonType ServiceAccount -RunLevel Highest\n"
            "Register-ScheduledTask -TaskName $TaskName -Action $Action "
            "-Principal $Principal -Force | Out-Null\n"
            "Start-ScheduledTask -TaskName $TaskName\n"
            "Write-Output 'arena-osworld-update-started'\n"
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        ]

    return [
        "sudo",
        "-n",
        "systemd-run",
        "--quiet",
        "--collect",
        f"--unit={update_name}",
        config.linux_updater_command,
        *arguments,
    ]


def build_updater_script(
    platform: str,
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
) -> str:
    arguments = _updater_arguments(bundle, config, url)
    if platform == "windows":
        command = " ".join(
            [_powershell_quote(config.windows_updater_command)]
            + [_powershell_quote(value) for value in arguments]
        )
        return (
            "$ErrorActionPreference = 'Stop'\n"
            f"& {command}\n"
            "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n"
        )

    command = " ".join(
        [shlex.quote(config.linux_updater_command)]
        + [shlex.quote(value) for value in arguments]
    )
    return "#!/bin/bash\nset -euo pipefail\n" + command + "\n"


def _updater_arguments(
    bundle: VmOsworldBundleSpec,
    config: VmOsworldProvisionConfig,
    url: str,
) -> list[str]:
    arguments = [
        "--url",
        url,
        "--archive-sha256",
        bundle.archive_sha256,
        "--content-sha256",
        bundle.content_sha256,
        "--version",
        bundle.version,
        "--root-dir",
        bundle.root_dir,
    ]
    if config.skip_health:
        arguments.append("--skip-health")
    return arguments


def bundle_spec_dict(bundle: VmOsworldBundleSpec | None) -> dict[str, Any]:
    return asdict(bundle) if bundle else {}


def provision_config_dict(config: VmOsworldProvisionConfig | None) -> dict[str, Any]:
    return asdict(config) if config else {}


def _validate_command_result(
    result: CloudAssistantCommandResult,
    *,
    invocation_id: str,
    attempt: int,
    expected_content_sha256: str,
    transport: str,
) -> dict[str, Any]:
    if result.exit_code not in {0, None} or result.status.lower() not in {
        "success",
        "succeeded",
        "finished",
    }:
        raise RuntimeError(
            f"Cloud Assistant failed on {result.instance_id}: status={result.status}, "
            f"exit_code={result.exit_code}, error={result.error_code} {result.error_message}, "
            f"output={result.output[-2000:]}"
        )
    payload = _last_json_object(result.output)
    if payload.get("status") not in {"updated", "unchanged"}:
        raise RuntimeError(
            f"Updater returned an invalid status on {result.instance_id}: {payload}"
        )
    if str(payload.get("content_sha256") or "").lower() != expected_content_sha256:
        raise RuntimeError(
            f"Updater SHA mismatch on {result.instance_id}: {payload}"
        )
    return {
        "instance_id": result.instance_id,
        "status": payload["status"],
        "downloaded": bool(payload.get("downloaded")),
        "transport": transport,
        "invocation_id": invocation_id,
        "attempt": attempt,
    }


def _wait_for_vm_execute(
    instance: InstanceRecord,
    *,
    platform: str,
    config: VmOsworldProvisionConfig,
    cancel_event: threading.Event | None = None,
) -> None:
    deadline = time.monotonic() + config.execute_wait_timeout_seconds
    last_error = "no response"
    command = (
        ["cmd.exe", "/d", "/s", "/c", f"echo {_EXECUTE_READY_MARKER}"]
        if platform == "windows"
        else ["/bin/sh", "-c", f"printf {_EXECUTE_READY_MARKER}"]
    )
    while time.monotonic() < deadline:
        _raise_if_cancelled(cancel_event)
        try:
            response = _execute_vm_command(
                instance,
                command,
                port=config.execute_port,
                timeout_seconds=min(config.execute_request_timeout_seconds, 10),
            )
            if _EXECUTE_READY_MARKER in str(response.get("output") or ""):
                return
            last_error = f"unexpected probe response: {response}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        _sleep_with_cancel(cancel_event, 5)
    raise TimeoutError(
        f"Timed out waiting for OSWorld /execute on {instance.instance_id} "
        f"({_instance_host(instance)}:{config.execute_port}): {last_error}"
    )


def _execute_vm_command(
    instance: InstanceRecord,
    command: list[str],
    *,
    port: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    url = f"http://{_instance_host(instance)}:{port}/execute"
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {"command": command, "shell": False, "timeout": timeout_seconds},
            ensure_ascii=True,
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"POST {url} returned HTTP {exc.code}: {detail[-4000:]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"POST {url} failed: {exc.reason}") from exc
    except OSError as exc:
        raise ConnectionError(f"POST {url} failed: {exc}") from exc

    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"POST {url} returned non-JSON data: {response_body[-4000:]}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"POST {url} returned a non-object response: {payload!r}")
    return_code = payload.get("returncode")
    if payload.get("status") != "success" or return_code not in {0, None}:
        detail = str(
            payload.get("error") or payload.get("message") or payload.get("output") or ""
        )
        raise RuntimeError(
            f"VM command failed on {instance.instance_id}: status={payload.get('status')}, "
            f"returncode={return_code}, detail={detail[-4000:]}"
        )
    return payload


def _ensure_runtime_updater_current(
    instance: InstanceRecord,
    *,
    platform: str,
    config: VmOsworldProvisionConfig,
) -> dict[str, Any]:
    source_path = Path(
        os.getenv("VM_OSWORLD_UPDATER_SOURCE_PATH", _DEFAULT_UPDATER_SOURCE_PATH)
    ).expanduser()
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    try:
        source = source_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Cannot read runtime updater source {source_path}: {exc}") from exc

    expected_sha256 = hashlib.sha256(source).hexdigest()
    destination = (
        r"C:\ProgramData\ArenaOSWorldUpdater\osworld_updater.py"
        if platform == "windows"
        else "/opt/arena-osworld-updater/osworld_updater.py"
    )
    python_command = "python.exe" if platform == "windows" else "python3"
    hash_code = (
        "import hashlib,pathlib,sys;"
        "p=pathlib.Path(sys.argv[1]);"
        "print(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else '')"
    )
    response = _execute_vm_command(
        instance,
        [python_command, "-c", hash_code, destination],
        port=config.execute_port,
        timeout_seconds=config.execute_request_timeout_seconds,
    )
    current_sha256 = str(response.get("output") or "").strip().lower()
    if current_sha256 == expected_sha256:
        return {
            "status": "unchanged",
            "sha256": expected_sha256,
            "source_path": str(source_path),
        }

    remote_name = f"arena-osworld-runtime-updater-{expected_sha256[:12]}.py"
    remote_path = _upload_execute_file(
        instance,
        platform=platform,
        port=config.execute_port,
        remote_name=remote_name,
        content=source,
        request_timeout_seconds=config.execute_request_timeout_seconds,
    )
    try:
        command = _runtime_updater_install_command(
            platform,
            remote_path=remote_path,
            expected_sha256=expected_sha256,
            listener_port=config.execute_port,
        )
        response = _execute_vm_command(
            instance,
            command,
            port=config.execute_port,
            timeout_seconds=config.execute_request_timeout_seconds,
        )
    finally:
        try:
            _remove_execute_file(
                instance,
                platform=platform,
                port=config.execute_port,
                remote_name=remote_name,
                request_timeout_seconds=config.execute_request_timeout_seconds,
            )
        except Exception:
            pass

    installed_sha256 = str(response.get("output") or "").strip().lower()
    if installed_sha256 != expected_sha256:
        raise RuntimeError(
            f"Runtime updater SHA mismatch on {instance.instance_id}: "
            f"expected={expected_sha256}, actual={installed_sha256}"
        )
    return {
        "status": "updated",
        "sha256": expected_sha256,
        "previous_sha256": current_sha256,
        "source_path": str(source_path),
    }


def _runtime_updater_install_command(
    platform: str,
    *,
    remote_path: str,
    expected_sha256: str,
    listener_port: int,
) -> list[str]:
    if platform == "windows":
        install_code = r'''
import hashlib
import json
import os
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
expected_sha256 = sys.argv[2]
listener_port = int(sys.argv[3])
data = source.read_bytes()
actual_sha256 = hashlib.sha256(data).hexdigest()
if actual_sha256 != expected_sha256:
    raise RuntimeError(f"updater source SHA mismatch: {actual_sha256}")

install_dir = pathlib.Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "ArenaOSWorldUpdater"
updater_path = install_dir / "osworld_updater.py"
config_path = install_dir / "config.json"
wrapper_path = install_dir / "update-osworld.ps1"
if not config_path.is_file() or not wrapper_path.is_file():
    raise RuntimeError("runtime bootstrap requires an existing ArenaOSWorldUpdater installation")

config = json.loads(config_path.read_text(encoding="utf-8-sig"))
task_name = str(config.get("scheduled_task_name") or "OSWorldServer")
escaped_task_name = task_name.replace("'", "''")
config["scheduled_task_name"] = task_name
config["listener_port"] = listener_port
config["stop_command"] = [
    "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
    f"Stop-ScheduledTask -TaskName '{escaped_task_name}' -ErrorAction SilentlyContinue",
]
config["start_command"] = [
    "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
    f"Start-ScheduledTask -TaskName '{escaped_task_name}' -ErrorAction Stop",
]

temporary_updater = updater_path.with_suffix(".py.tmp")
temporary_updater.write_bytes(data)
os.replace(temporary_updater, updater_path)
temporary_config = config_path.with_suffix(".json.tmp")
temporary_config.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
os.replace(temporary_config, config_path)
print(hashlib.sha256(updater_path.read_bytes()).hexdigest())
'''.strip()
        return [
            "python.exe",
            "-c",
            install_code,
            remote_path,
            expected_sha256,
            str(listener_port),
        ]

    install_code = r'''
import hashlib
import os
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
destination = pathlib.Path("/opt/arena-osworld-updater/osworld_updater.py")
expected_sha256 = sys.argv[2]
data = source.read_bytes()
actual_sha256 = hashlib.sha256(data).hexdigest()
if actual_sha256 != expected_sha256:
    raise RuntimeError(f"updater source SHA mismatch: {actual_sha256}")
if not destination.parent.is_dir() or not pathlib.Path("/etc/arena-osworld-updater.json").is_file():
    raise RuntimeError("runtime bootstrap requires an existing ArenaOSWorldUpdater installation")
temporary = destination.with_suffix(".py.tmp")
temporary.write_bytes(data)
os.chmod(temporary, 0o755)
os.replace(temporary, destination)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
'''.strip()
    return [
        "sudo",
        "-n",
        "python3",
        "-c",
        install_code,
        remote_path,
        expected_sha256,
    ]


def _upload_execute_file(
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
    response = _execute_vm_command(
        instance,
        [python_command, "-c", initialize],
        port=port,
        timeout_seconds=request_timeout_seconds,
    )
    remote_path = str(response.get("output") or "").strip()
    if not remote_path:
        raise RuntimeError(f"VM did not return an upload path for {remote_name}")

    for offset in range(0, len(content), _EXECUTE_UPLOAD_CHUNK_BYTES):
        encoded = base64.b64encode(
            content[offset : offset + _EXECUTE_UPLOAD_CHUNK_BYTES]
        ).decode("ascii")
        append = (
            "import base64,pathlib,tempfile;"
            f"p={path_expression};p.open('ab').write(base64.b64decode({encoded!r}))"
        )
        _execute_vm_command(
            instance,
            [python_command, "-c", append],
            port=port,
            timeout_seconds=request_timeout_seconds,
        )

    verify = (
        "import hashlib,pathlib,tempfile;"
        f"p={path_expression};print(hashlib.sha256(p.read_bytes()).hexdigest())"
    )
    response = _execute_vm_command(
        instance,
        [python_command, "-c", verify],
        port=port,
        timeout_seconds=request_timeout_seconds,
    )
    actual_sha256 = str(response.get("output") or "").strip().lower()
    expected_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"Uploaded updater SHA mismatch on {instance.instance_id}: "
            f"expected={expected_sha256}, actual={actual_sha256}"
        )
    return remote_path


def _remove_execute_file(
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
    _execute_vm_command(
        instance,
        [python_command, "-c", cleanup],
        port=port,
        timeout_seconds=request_timeout_seconds,
    )


def _ensure_windows_server_supervisor(
    instance: InstanceRecord,
    *,
    config: VmOsworldProvisionConfig,
    restart_running: bool,
) -> dict[str, Any]:
    response = _execute_vm_command(
        instance,
        _windows_server_supervisor_command(restart_running=restart_running),
        port=config.execute_port,
        timeout_seconds=config.execute_request_timeout_seconds,
    )
    payload = _last_json_object(str(response.get("output") or ""))
    if payload.get("status") not in {"updated", "unchanged"}:
        raise RuntimeError(
            f"Windows server supervisor returned an invalid result on "
            f"{instance.instance_id}: {payload}"
        )
    if str(payload.get("policy_version") or "") != WINDOWS_SERVER_SUPERVISOR_POLICY_VERSION:
        raise RuntimeError(
            f"Windows server supervisor policy mismatch on {instance.instance_id}: "
            f"{payload}"
        )
    return payload


def _windows_server_supervisor_command(*, restart_running: bool) -> list[str]:
    script = _WINDOWS_SERVER_SUPERVISOR_SCRIPT.replace(
        "__POLICY_VERSION__",
        WINDOWS_SERVER_SUPERVISOR_POLICY_VERSION,
    ).replace(
        "$__RESTART_RUNNING__",
        "$true" if restart_running else "$false",
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


def _verify_vm_updater(
    instance: InstanceRecord,
    *,
    platform: str,
    config: VmOsworldProvisionConfig,
) -> None:
    if platform == "windows":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "if (-not (Test-Path -LiteralPath "
                f"{_powershell_quote(config.windows_updater_command)})) {{ exit 2 }}"
            ),
        ]
    else:
        command = ["test", "-x", config.linux_updater_command]
    try:
        _execute_vm_command(
            instance,
            command,
            port=config.execute_port,
            timeout_seconds=config.execute_request_timeout_seconds,
        )
    except Exception as exc:
        updater_command = (
            config.windows_updater_command
            if platform == "windows"
            else config.linux_updater_command
        )
        raise RuntimeError(
            f"OSWorld updater is unavailable on {instance.instance_id}: "
            f"{updater_command}: {exc}"
        ) from exc


def _vm_health_matches(
    instance: InstanceRecord,
    port: int,
    expected_content_sha256: str,
) -> bool:
    try:
        payload = _read_vm_health(instance, port=port, timeout_seconds=5)
    except Exception:
        return False
    return (
        payload.get("status") == "ok"
        and str(payload.get("content_sha256") or "").lower()
        == expected_content_sha256.lower()
    )


def _wait_for_vm_health(
    instance: InstanceRecord,
    *,
    port: int,
    expected_content_sha256: str,
    timeout_seconds: int,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error = "no response"
    while time.monotonic() < deadline:
        _raise_if_cancelled(cancel_event)
        try:
            payload = _read_vm_health(instance, port=port, timeout_seconds=5)
            actual = str(payload.get("content_sha256") or "").lower()
            if payload.get("status") == "ok" and actual == expected_content_sha256.lower():
                return payload
            last_error = f"unexpected health payload: {payload}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        _sleep_with_cancel(cancel_event, 2)
    raise TimeoutError(
        f"OSWorld health check timed out on {instance.instance_id} "
        f"({_instance_host(instance)}:{port}): {last_error}"
    )


def _read_vm_health(
    instance: InstanceRecord,
    *,
    port: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    url = f"http://{_instance_host(instance)}:{port}/health"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GET {url} returned HTTP {exc.code}: {detail[-4000:]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"GET {url} failed: {exc.reason}") from exc
    except OSError as exc:
        raise ConnectionError(f"GET {url} failed: {exc}") from exc
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"GET {url} returned non-JSON data: {response_body[-4000:]}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"GET {url} returned a non-object response: {payload!r}")
    return payload


def _instance_host(instance: InstanceRecord) -> str:
    host = instance.private_ip or instance.public_ip or ""
    if not host:
        raise ValueError(f"Instance {instance.instance_id} has no reachable IP address")
    return host


def _safe_update_name(value: str, *, suffix: str = "") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-").lower()
    normalized = normalized or "arena-osworld-update"
    normalized_suffix = re.sub(r"[^a-zA-Z0-9-]+", "-", suffix).strip("-").lower()
    candidate = (
        f"{normalized}-{normalized_suffix}" if normalized_suffix else normalized
    )
    if len(candidate) <= 80:
        return candidate
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    tail = f"-{digest}"
    if normalized_suffix:
        tail += f"-{normalized_suffix}"
    prefix = normalized[: 80 - len(tail)].rstrip("-")
    return f"{prefix}{tail}"


def _format_instance_errors(errors: dict[str, str]) -> str:
    return "; ".join(
        f"{instance_id}={error}" for instance_id, error in sorted(errors.items())
    )


def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise RuntimeError("VM OSWorld update cancelled")


def _sleep_with_cancel(
    cancel_event: threading.Event | None,
    seconds: float,
) -> None:
    if cancel_event is None:
        time.sleep(seconds)
        return
    if cancel_event.wait(seconds):
        raise RuntimeError("VM OSWorld update cancelled")


def _validate_provision_config(config: VmOsworldProvisionConfig) -> None:
    if config.transport not in _VALID_TRANSPORTS:
        choices = ", ".join(sorted(_VALID_TRANSPORTS))
        raise ValueError(
            f"VM OSWorld update transport must be one of {choices}; "
            f"got {config.transport!r}"
        )
    positive_values = {
        "presign_expires_seconds": config.presign_expires_seconds,
        "update_timeout_seconds": config.update_timeout_seconds,
        "cloud_assistant_wait_timeout_seconds": (
            config.cloud_assistant_wait_timeout_seconds
        ),
        "execute_port": config.execute_port,
        "execute_wait_timeout_seconds": config.execute_wait_timeout_seconds,
        "execute_request_timeout_seconds": config.execute_request_timeout_seconds,
        "execute_max_workers": config.execute_max_workers,
        "max_attempts": config.max_attempts,
    }
    invalid = [name for name, value in positive_values.items() if value < 1]
    if invalid:
        raise ValueError(
            "VM OSWorld provision values must be positive: " + ", ".join(invalid)
        )
    if config.max_failed_instances < 0:
        raise ValueError("max_failed_instances must be zero or greater")


def _last_json_object(value: str) -> dict[str, Any]:
    for line in reversed(value.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError(f"Cloud Assistant output did not contain JSON: {value[-2000:]}")


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _chunks(items: list[InstanceRecord], size: int) -> list[list[InstanceRecord]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _sha256(value: Any, name: str) -> str:
    normalized = str(value or "").strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ValueError(f"Invalid {name}: {value!r}")
    return normalized


def _optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)
