param(
    [string]$InstallDir = "$env:ProgramData\ArenaOSWorldUpdater",
    [string]$CurrentDir = "C:\Users\User\server",
    [string]$ScheduledTaskName = "OSWorldServer",
    [string]$HealthUrl = "http://127.0.0.1:5000/health",
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $InstallDir "config.json"

if (-not $PythonExecutable) {
    $PythonExecutable = (Get-Command python.exe -ErrorAction Stop).Source
}
$PythonExecutable = (Resolve-Path $PythonExecutable -ErrorAction Stop).Path
$ListenerPort = ([Uri]$HealthUrl).Port
$EscapedScheduledTaskName = $ScheduledTaskName.Replace("'", "''")
$StopTaskScript = "Stop-ScheduledTask -TaskName '$EscapedScheduledTaskName' -ErrorAction SilentlyContinue"
$StartTaskScript = "Start-ScheduledTask -TaskName '$EscapedScheduledTaskName' -ErrorAction Stop"

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item (Join-Path $ScriptDir "osworld_updater.py") (Join-Path $InstallDir "osworld_updater.py") -Force

$Config = @{
    current_dir = $CurrentDir
    stop_command = @("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", $StopTaskScript)
    start_command = @("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", $StartTaskScript)
    health_url = $HealthUrl
    health_timeout_seconds = 90
    listener_port = $ListenerPort
    scheduled_task_name = $ScheduledTaskName
}
$Config | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $ConfigPath

$Wrapper = @"
`$ErrorActionPreference = "Stop"
& "$PythonExecutable" "$(Join-Path $InstallDir 'osworld_updater.py')" apply --config "$ConfigPath" @args
exit `$LASTEXITCODE
"@
$Wrapper | Set-Content -Encoding UTF8 (Join-Path $InstallDir "update-osworld.ps1")

Write-Host "Installed OSWorld updater: $(Join-Path $InstallDir 'update-osworld.ps1')"
Write-Host "Updater config: $ConfigPath"
