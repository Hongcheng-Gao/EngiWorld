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

foreach ($required in @($revitExe, $bridgeSourceDll, $bridgeSourceAddin, $specPath, $inputPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required Revit stage dependency is missing: $required"
    }
}

$versionInfo = (Get-Item -LiteralPath $revitExe).VersionInfo
if ($versionInfo.FileMajorPart -ne 25) {
    throw "Expected Revit 2025 (file major 25), found file version $($versionInfo.FileVersion), product build $($versionInfo.ProductVersion)"
}

try {
    New-Item -ItemType Directory -Path $bridgeInstallDir -Force | Out-Null
    Copy-Item -LiteralPath $bridgeSourceDll -Destination $bridgeDll -Force
    Copy-Item -LiteralPath $bridgeSourceAddin -Destination $bridgeAddin -Force

    foreach ($stale in @($outputPath, $handoffPath, $logPath, $bridgeErrorPath)) {
        if (Test-Path -LiteralPath $stale -PathType Leaf) {
            Remove-Item -LiteralPath $stale -Force
        }
    }

    $env:ENGIWORLD_BIM_JOB = $specPath
    $env:ENGIWORLD_BIM_STAGE = "revit"
    $startedUtc = [DateTime]::UtcNow.ToString("o")
    $process = Start-Process -FilePath $revitExe -ArgumentList @("/language", "ENU", "/nosplash") -PassThru
    $process.WaitForExit()
    $finishedUtc = [DateTime]::UtcNow.ToString("o")

    if ($process.ExitCode -ne 0) {
        throw "Revit stage exited with code $($process.ExitCode)"
    }
    if (Test-Path -LiteralPath $bridgeErrorPath -PathType Leaf) {
        throw "Revit bridge failed: $(Get-Content -LiteralPath $bridgeErrorPath -Raw)"
    }
    foreach ($required in @($outputPath, $handoffPath)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Revit bridge did not produce: $required"
        }
    }

    $entry = [ordered]@{
        stage = "revit"
        executable = $revitExe
        product_version = $versionInfo.FileVersion
        product_build = $versionInfo.ProductVersion
        file_version = $versionInfo.FileVersion
        automation_entry = $bridgeAddin
        command = 'Revit.exe /language ENU /nosplash (ENGIWORLD_BIM_STAGE=revit)'
        started_utc = $startedUtc
        finished_utc = $finishedUtc
        exit_code = $process.ExitCode
        input_file = "init.ifc"
        input_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash.ToLowerInvariant()
        output_file = "stage1.ifc"
        output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash.ToLowerInvariant()
        handoff_file = "revit_handoff.json"
        handoff_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $handoffPath).Hash.ToLowerInvariant()
    }

    [ordered]@{ schema_version = 1; stages = @($entry) } |
        ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $logPath -Encoding UTF8
}
finally {
    if (Test-Path -LiteralPath $bridgeAddin -PathType Leaf) {
        Remove-Item -LiteralPath $bridgeAddin -Force
    }
    if (Test-Path -LiteralPath $bridgeInstallDir -PathType Container) {
        Remove-Item -LiteralPath $bridgeInstallDir -Recurse -Force
    }
}
