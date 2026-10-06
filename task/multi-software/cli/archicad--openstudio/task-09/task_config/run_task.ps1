$ErrorActionPreference = "Stop"
$desktop = "C:\Users\user\Desktop"
$documents = "C:\Users\user\Documents"
$openstudio = "C:\openstudio-3.10.0\bin\openstudio.exe"
$energyplus = "C:\openstudio-3.10.0\EnergyPlus\energyplus.exe"

function Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$outputs = @("stage1.ifc", "handoff.json", "native_stage_log.json", "result.osm", "in.idf", "workflow.osw", "weather.epw", "flow_report.json", "model_summary.csv", "openstudio_simulation_transaction.json")
foreach ($name in $outputs) {
    $path = Join-Path $desktop $name
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
}
if (Test-Path -LiteralPath "$desktop\run") { Remove-Item -LiteralPath "$desktop\run" -Recurse -Force }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$documents\ew09-archicad.ps1"
if ($LASTEXITCODE -ne 0) { throw "Archicad stage failed: $LASTEXITCODE" }

& $openstudio "$documents\ew09-build.rb"
if ($LASTEXITCODE -ne 0) { throw "OpenStudio build failed: $LASTEXITCODE" }

$started = [DateTimeOffset]::UtcNow.ToString("o")
$process = Start-Process -FilePath $openstudio -ArgumentList @("run", "-w", "$desktop\workflow.osw") -WorkingDirectory $desktop -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "OpenStudio simulation failed: $($process.ExitCode)" }
$transaction = [ordered]@{
    stage = "openstudio_energyplus_annual_simulation"
    executable_path = $openstudio
    executable_sha256 = Sha256 $openstudio
    executable_product_version = (Get-Item $openstudio).VersionInfo.ProductVersion
    energyplus_executable_path = $energyplus
    energyplus_executable_sha256 = Sha256 $energyplus
    energyplus_product_version = (Get-Item $energyplus).VersionInfo.ProductVersion
    arguments = @("run", "-w", "$desktop\workflow.osw")
    working_directory = $desktop
    pid = $process.Id
    started_at_utc = $started
    completed_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    exit_code = $process.ExitCode
    result_osm_sha256 = Sha256 "$desktop\result.osm"
    idf_sha256 = Sha256 "$desktop\in.idf"
    workflow_sha256 = Sha256 "$desktop\workflow.osw"
    weather_sha256 = Sha256 "$desktop\weather.epw"
    sql_sha256 = Sha256 "$desktop\run\eplusout.sql"
    err_sha256 = Sha256 "$desktop\run\eplusout.err"
    end_sha256 = Sha256 "$desktop\run\eplusout.end"
}
$transaction | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath "$desktop\openstudio_simulation_transaction.json" -Encoding utf8

& $openstudio "$documents\ew09-post.rb"
if ($LASTEXITCODE -ne 0) { throw "OpenStudio postprocess failed: $LASTEXITCODE" }
Write-Output "EW09 task completed"
