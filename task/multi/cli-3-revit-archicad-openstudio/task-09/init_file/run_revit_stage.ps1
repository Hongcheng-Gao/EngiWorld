param(
    [string]$Desktop = "C:\Users\user\Desktop"
)

$ErrorActionPreference = "Stop"
$revitExe = "C:\Program Files\Autodesk\Revit 2025\Revit.exe"
$bridgeSourceDll = Join-Path $Desktop "EngiWorld.BimBridge.dll"
$bridgeSourceAddin = Join-Path $Desktop "EngiWorld.BimBridge.addin"
$bridgeInstallDir = "C:\ProgramData\Autodesk\Revit\Addins\2025\EngiWorld.BimBridge"
$bridgeAddin = "C:\ProgramData\Autodesk\Revit\Addins\2025\EngiWorld.BimBridge.addin"
$bridgeDll = Join-Path $bridgeInstallDir "EngiWorld.BimBridge.dll"
$specPath = Join-Path $Desktop "workflow_spec.json"
$inputPath = Join-Path $Desktop "init.ifc"
$outputPath = Join-Path $Desktop "stage1.ifc"
$handoffPath = Join-Path $Desktop "revit_handoff.json"
$logPath = Join-Path $Desktop "native_stage_log.json"
$bridgeErrorPath = Join-Path $Desktop "revit_bridge_error.txt"
$processLog = Join-Path $Desktop "revit_stage_process.json"
$spec = Get-Content -LiteralPath $specPath -Raw | ConvertFrom-Json

foreach ($required in @($revitExe, $bridgeSourceDll, $bridgeSourceAddin, $specPath, $inputPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required Revit stage dependency is missing: $required" }
}
if ($spec.case_id -ne "multi-cli-3-revit-archicad-openstudio-task-09-windows" -or $spec.revision -ne "EW3B09") {
    throw "This launcher only accepts task-09 EW3B09."
}
$versionInfo = (Get-Item -LiteralPath $revitExe).VersionInfo
if ($versionInfo.FileMajorPart -ne 25) { throw "Expected Revit 2025, found $($versionInfo.FileVersion)." }

try {
    New-Item -ItemType Directory -Path $bridgeInstallDir -Force | Out-Null
    Copy-Item -LiteralPath $bridgeSourceDll -Destination $bridgeDll -Force
    [xml]$manifest = Get-Content -LiteralPath $bridgeSourceAddin -Raw
    $manifest.SelectSingleNode("//Assembly").InnerText = [string]$bridgeDll
    $manifest.Save($bridgeAddin)
    foreach ($stale in @($outputPath, $handoffPath, $logPath, $bridgeErrorPath, $processLog)) {
        if (Test-Path -LiteralPath $stale -PathType Leaf) { Remove-Item -LiteralPath $stale -Force }
    }
    $env:ENGIWORLD_BIM_JOB = $specPath
    $env:ENGIWORLD_BIM_STAGE = "revit"
    $startedUtc = [DateTime]::UtcNow.ToString("o")
    $process = Start-Process -FilePath $revitExe -ArgumentList @("/language", "ENU", "/nosplash") -PassThru
    [ordered]@{ schema_version = 1; launcher_process_id = $process.Id; started_utc = $startedUtc; executable = $revitExe } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $processLog -Encoding UTF8
    if (-not $process.WaitForExit(300000)) { throw "Revit stage did not exit within five minutes." }
    $finishedUtc = [DateTime]::UtcNow.ToString("o")
    if ($process.ExitCode -ne 0) { throw "Revit stage exited with code $($process.ExitCode)." }
    if (Test-Path -LiteralPath $bridgeErrorPath -PathType Leaf) { throw "Revit bridge failed: $(Get-Content -LiteralPath $bridgeErrorPath -Raw)" }
    foreach ($required in @($outputPath, $handoffPath)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Revit bridge did not produce: $required" }
    }
    $entry = [ordered]@{
        stage = "revit"; executable = $revitExe; product_version = $versionInfo.FileVersion; product_build = $versionInfo.ProductVersion
        automation_entry = $bridgeAddin; command = 'Revit.exe /language ENU /nosplash (ENGIWORLD_BIM_STAGE=revit)'
        started_utc = $startedUtc; finished_utc = $finishedUtc; exit_code = $process.ExitCode
        input_file = "init.ifc"; input_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash.ToLowerInvariant()
        output_file = "stage1.ifc"; output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash.ToLowerInvariant()
        handoff_file = "revit_handoff.json"; handoff_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $handoffPath).Hash.ToLowerInvariant()
    }
    [ordered]@{ schema_version = 1; stages = @($entry) } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $logPath -Encoding UTF8
}
finally {
    Remove-Item Env:ENGIWORLD_BIM_JOB -ErrorAction SilentlyContinue
    Remove-Item Env:ENGIWORLD_BIM_STAGE -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $bridgeAddin -PathType Leaf) { Remove-Item -LiteralPath $bridgeAddin -Force }
    if (Test-Path -LiteralPath $bridgeInstallDir -PathType Container) { Remove-Item -LiteralPath $bridgeInstallDir -Recurse -Force }
}
