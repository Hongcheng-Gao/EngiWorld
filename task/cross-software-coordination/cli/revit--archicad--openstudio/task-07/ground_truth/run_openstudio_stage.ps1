param(
    [string]$Desktop = "C:\Users\user\Desktop"
)

$ErrorActionPreference = "Stop"
$openStudioExe = "C:\openstudio-3.10.0\bin\openstudio.exe"
$converter = Join-Path $Desktop "openstudio_ifc_to_energy.rb"
$spec = Join-Path $Desktop "workflow_spec.json"
$handoff = Join-Path $Desktop "archicad_handoff.json"
$stage2 = Join-Path $Desktop "stage2.ifc"
$weather = Join-Path $Desktop "weather.epw"

foreach ($required in @($openStudioExe, $converter, $spec, $handoff, $stage2, $weather, (Join-Path $Desktop "native_stage_log.json"))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required OpenStudio stage dependency is missing: $required"
    }
}

$version = (& $openStudioExe --version 2>&1 | Out-String).Trim()
if ($version -notmatch '3\.10\.0') {
    throw "Expected OpenStudio 3.10.0, found $version"
}

& $openStudioExe $converter `
    --spec $spec `
    --handoff $handoff `
    --ifc $stage2 `
    --weather $weather `
    --desktop $Desktop `
    --openstudio-exe $openStudioExe
if ($LASTEXITCODE -ne 0) {
    throw "OpenStudio IFC-to-energy converter exited with code $LASTEXITCODE"
}
