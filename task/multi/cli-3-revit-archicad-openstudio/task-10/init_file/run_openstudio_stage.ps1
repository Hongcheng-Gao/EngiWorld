param(
    [string]$Desktop = "C:\Users\user\Desktop"
)

$ErrorActionPreference = "Stop"
$openStudioExe = "C:\openstudio-3.10.0\bin\openstudio.exe"
$converter = Join-Path $Desktop "openstudio_ifc_to_energy.rb"
$extractor = Join-Path $Desktop "extract_ifc_space_geometry.py"
$ifcGeometry = Join-Path $Desktop "stage2_space_geometry.json"
$spec = Join-Path $Desktop "workflow_spec.json"
$handoff = Join-Path $Desktop "archicad_handoff.json"
$stage2 = Join-Path $Desktop "stage2.ifc"
$weather = Join-Path $Desktop "weather.epw"

foreach ($required in @($openStudioExe, $converter, $extractor, $spec, $handoff, $stage2, $weather, (Join-Path $Desktop "native_stage_log.json"))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required OpenStudio stage dependency is missing: $required"
    }
}

$workflow = Get-Content -LiteralPath $spec -Raw | ConvertFrom-Json
if ($workflow.case_id -ne "multi-cli-3-revit-archicad-openstudio-task-10-windows" -or $workflow.revision -ne "EW3B10") {
    throw "This launcher only accepts the Task-10 EW3B10 workflow specification."
}

& python $extractor --ifc $stage2 --output $ifcGeometry
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ifcGeometry -PathType Leaf)) {
    throw "Structured stage2 IFC geometry extraction failed"
}

$version = (& $openStudioExe --version 2>&1 | Out-String).Trim()
if ($version -notmatch '3\.10\.0') {
    throw "Expected OpenStudio 3.10.0, found $version"
}

& $openStudioExe $converter `
    --spec $spec `
    --handoff $handoff `
    --ifc $stage2 `
    --ifc-geometry $ifcGeometry `
    --weather $weather `
    --desktop $Desktop `
    --openstudio-exe $openStudioExe
if ($LASTEXITCODE -ne 0) {
    throw "OpenStudio IFC-to-energy converter exited with code $LASTEXITCODE"
}
