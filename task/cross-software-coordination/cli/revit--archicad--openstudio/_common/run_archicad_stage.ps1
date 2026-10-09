param(
    [string]$Desktop = "C:\Users\user\Desktop"
)

$ErrorActionPreference = "Stop"
$archicadExe = "C:\Program Files\Graphisoft\Archicad 27\Archicad Starter.exe"
$commandServer = "C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe"
$specPath = Join-Path $Desktop "workflow_spec.json"
$translatorPath = Join-Path $Desktop "archicad_ifc4_translator.json"
$inputPath = Join-Path $Desktop "stage1.ifc"
$revitHandoffPath = Join-Path $Desktop "revit_handoff.json"
$outputPath = Join-Path $Desktop "stage2.ifc"
$handoffPath = Join-Path $Desktop "archicad_handoff.json"
$reportPath = Join-Path $Desktop "archicad_validation_report.json"
$logPath = Join-Path $Desktop "native_stage_log.json"

foreach ($required in @($archicadExe, $commandServer, $specPath, $translatorPath, $inputPath, $revitHandoffPath, $logPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required Archicad stage dependency is missing: $required"
    }
}

$version = (Get-Item -LiteralPath $archicadExe).VersionInfo.ProductVersion
if (-not $version.StartsWith("27.")) {
    throw "Expected Archicad 27, found $version"
}

$arguments = @(
    "--job", $specPath,
    "--input-ifc", $inputPath,
    "--input-handoff", $revitHandoffPath,
    "--translator", $translatorPath,
    "--output-ifc", $outputPath,
    "--validation-report", $reportPath,
    "--energy-handoff", $handoffPath
)
$startedUtc = [DateTime]::UtcNow.ToString("o")
$process = Start-Process -FilePath $commandServer -ArgumentList $arguments -Wait -PassThru
$finishedUtc = [DateTime]::UtcNow.ToString("o")

if ($process.ExitCode -ne 0) {
    throw "Archicad IFC command server exited with code $($process.ExitCode)"
}
foreach ($required in @($outputPath, $handoffPath, $reportPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Archicad command server did not produce: $required"
    }
}

$nativeLog = Get-Content -LiteralPath $logPath -Raw | ConvertFrom-Json
$entry = [ordered]@{
    stage = "archicad"
    executable = $archicadExe
    product_version = $version
    automation_entry = $commandServer
    command = "IFCCommandServerApp.exe --job workflow_spec.json --input-ifc stage1.ifc --translator archicad_ifc4_translator.json --output-ifc stage2.ifc"
    started_utc = $startedUtc
    finished_utc = $finishedUtc
    exit_code = $process.ExitCode
    input_file = "stage1.ifc"
    input_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash.ToLowerInvariant()
    input_handoff_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $revitHandoffPath).Hash.ToLowerInvariant()
    output_file = "stage2.ifc"
    output_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash.ToLowerInvariant()
    handoff_file = "archicad_handoff.json"
    handoff_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $handoffPath).Hash.ToLowerInvariant()
    validation_report_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $reportPath).Hash.ToLowerInvariant()
    translator_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $translatorPath).Hash.ToLowerInvariant()
}
$stages = @($nativeLog.stages) + @($entry)
[ordered]@{ schema_version = 1; stages = $stages } |
    ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath $logPath -Encoding UTF8

