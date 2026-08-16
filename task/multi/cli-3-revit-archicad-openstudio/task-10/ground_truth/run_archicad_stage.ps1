param(
    [string]$Desktop = "C:\Users\user\Desktop",
    [int]$Port = 19740
)

$ErrorActionPreference = "Stop"
$commandServer = "C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe"
$archicadExe = "C:\Program Files\Graphisoft\Archicad 27\Archicad Starter.exe"
$specPath = Join-Path $Desktop "workflow_spec.json"
$translatorPath = Join-Path $Desktop "archicad_ifc4_translator.json"
$inputPath = Join-Path $Desktop "stage1.ifc"
$revitHandoffPath = Join-Path $Desktop "revit_handoff.json"
$outputPath = Join-Path $Desktop "stage2.ifc"
$handoffPath = Join-Path $Desktop "archicad_handoff.json"
$reportPath = Join-Path $Desktop "archicad_validation_report.json"
$nativeLogPath = Join-Path $Desktop "native_stage_log.json"
$databasePath = "C:\EW3B10DB"
$modelName = "EW3B10-RUN"
$baseUrl = "http://127.0.0.1:$Port"
$utf8 = New-Object System.Text.UTF8Encoding($false)

foreach ($required in @($commandServer, $archicadExe, $specPath, $translatorPath, $inputPath, $revitHandoffPath, $nativeLogPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required Archicad stage dependency is missing: $required"
    }
}

$spec = Get-Content -LiteralPath $specPath -Raw | ConvertFrom-Json
$translator = Get-Content -LiteralPath $translatorPath -Raw | ConvertFrom-Json
$revitHandoff = Get-Content -LiteralPath $revitHandoffPath -Raw | ConvertFrom-Json
if ($spec.case_id -ne "multi-cli-3-revit-archicad-openstudio-task-10-windows" -or $spec.revision -ne "EW3B10") {
    throw "This launcher only accepts the Task-10 EW3B10 workflow specification."
}
if ($translator.command_server.validation_method -ne "Macro.ValidateIfcModel") {
    throw "The translator contract does not name the verified Archicad validation method."
}

$archicadVersionInfo = (Get-Item -LiteralPath $archicadExe).VersionInfo
$serverVersionInfo = (Get-Item -LiteralPath $commandServer).VersionInfo
$buildMatch = [regex]::Match($archicadVersionInfo.ProductVersion, "(?<!\d)(\d{4,})(?!\d)")
if (-not $buildMatch.Success -or [int]$buildMatch.Groups[1].Value -lt 6000) {
    throw "Expected Archicad 27 build 6000 or newer, found $($archicadVersionInfo.ProductVersion)."
}
$build = [int]$buildMatch.Groups[1].Value

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Task-local Archicad port $Port is already in use."
}
foreach ($stale in @($outputPath, "$outputPath.log", $handoffPath, $reportPath)) {
    if (Test-Path -LiteralPath $stale -PathType Leaf) {
        Remove-Item -LiteralPath $stale -Force
    }
}
if (Test-Path -LiteralPath $databasePath -PathType Container) {
    Remove-Item -LiteralPath $databasePath -Recurse -Force
}
New-Item -ItemType Directory -Path $databasePath -Force | Out-Null

$rpcTranscript = New-Object System.Collections.Generic.List[object]
function Invoke-Jemi {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][object]$Params
    )
    $requestObject = [ordered]@{ method = $Method; params = $Params }
    $requestJson = $requestObject | ConvertTo-Json -Depth 30 -Compress
    $response = Invoke-RestMethod -Method Post -Uri "$baseUrl/JEMI" -ContentType "application/json" -Body $requestJson
    $rpcTranscript.Add([ordered]@{ request = $requestObject; response = $response })
    if ($null -ne $response.error) {
        throw "Archicad JEMI $Method failed: $($response.error | ConvertTo-Json -Depth 20 -Compress)"
    }
    return $response
}

function Get-EntityAttribute {
    param(
        [Parameter(Mandatory = $true)][string]$Reference,
        [Parameter(Mandatory = $true)][string]$Attribute
    )
    $response = Invoke-Jemi -Method "Entity.GetAttribute" -Params ([ordered]@{ Select = $Reference; Attribute = $Attribute })
    return $response.result.$Attribute
}

function Get-IfcRootIds {
    param([Parameter(Mandatory = $true)][string]$Path)
    $text = Get-Content -LiteralPath $Path -Raw
    $matches = [regex]::Matches($text, "#\d+\s*=\s*IFC[A-Z0-9_]+\s*\(\s*'([0-9A-Za-z_\x24]{22})'", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    return @($matches | ForEach-Object { $_.Groups[1].Value })
}

function Get-IfcEntityCount {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$EntityName
    )
    $text = Get-Content -LiteralPath $Path -Raw
    return [regex]::Matches($text, "\b$([regex]::Escape($EntityName))\s*\(", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
}

function Get-FillingGraphSignatures {
    param([Parameter(Mandatory = $true)][string]$Path)
    $text = Get-Content -LiteralPath $Path -Raw
    $refToGuid = @{}
    foreach ($match in [regex]::Matches($text, "#(\d+)\s*=\s*IFC[A-Z0-9_]+\s*\(\s*'([0-9A-Za-z_\x24]{22})'", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
        $refToGuid[$match.Groups[1].Value] = $match.Groups[2].Value
    }
    $voids = @()
    foreach ($match in [regex]::Matches($text, "IFCRELVOIDSELEMENT\s*\([^;]*,#(\d+),#(\d+)\s*\)\s*;", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
        $voids += "$($refToGuid[$match.Groups[1].Value])>$($refToGuid[$match.Groups[2].Value])"
    }
    $fills = @()
    foreach ($match in [regex]::Matches($text, "IFCRELFILLSELEMENT\s*\([^;]*,#(\d+),#(\d+)\s*\)\s*;", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
        $fills += "$($refToGuid[$match.Groups[1].Value])>$($refToGuid[$match.Groups[2].Value])"
    }
    return [ordered]@{ voids = @($voids | Sort-Object); fills = @($fills | Sort-Object) }
}

$serverProcess = $null
$startedUtc = [DateTime]::UtcNow.ToString("o")
try {
    $arguments = @("--p", "$Port", "--m", $modelName, "--d", $databasePath, "--sa", "new_ifc4")
    $serverProcess = Start-Process -FilePath $commandServer -ArgumentList $arguments -PassThru

    $healthy = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        if ($serverProcess.HasExited) {
            throw "Archicad IFC command server exited during startup with code $($serverProcess.ExitCode)."
        }
        try {
            Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/HEALTH" -TimeoutSec 2 | Out-Null
            $healthy = $true
            break
        }
        catch {
        }
    }
    if (-not $healthy) {
        throw "Archicad IFC command server did not become healthy on port $Port."
    }
    # HEALTH can become available before the newly created IFC database is ready for Model.LoadFile.
    Start-Sleep -Seconds 1

    $loadResponse = Invoke-Jemi -Method "Model.LoadFile" -Params ([ordered]@{ Location = $inputPath })
    if ($loadResponse.result -ne "stage1.ifc") {
        throw "Archicad did not report stage1.ifc as the loaded model."
    }

    $validationResponse = Invoke-Jemi -Method "Macro.ValidateIfcModel" -Params ([ordered]@{})
    $acceptedValidationObservations = @()
    if ($null -ne $validationResponse.result) {
        $validationItems = @($validationResponse.result)
        if ($validationItems.Count -gt 0) {
            $unexpectedValidationItems = @()
            foreach ($item in $validationItems) {
                $missing = @($item.MissingMandatoryAttributes)
                $accepted = $missing.Count -gt 0
                foreach ($entry in $missing) {
                    $accepted = $accepted -and ([string]$entry.Type -eq "IfcMaterialProfileSetUsage") -and (@($entry.Attrbiutes) -contains "AssociatedTo")
                }
                if ($accepted) {
                    $acceptedValidationObservations += [ordered]@{
                        category = "Revit IFC4 inverse material-profile validation observation"
                        entity_type = "IfcMaterialProfileSetUsage"
                        reported_attribute = "AssociatedTo"
                        reported_count = $missing.Count
                        disposition = "non_blocking_if_all_observations_are_the_Revit_IFC4_inverse_AssociatedTo_attribute"
                    }
                }
                else {
                    $unexpectedValidationItems += $item
                }
            }
            if ($unexpectedValidationItems.Count -gt 0) {
                throw "Archicad reported unexpected invalid IFC entities: $($unexpectedValidationItems | ConvertTo-Json -Depth 30 -Compress)"
            }
        }
    }

    $ifcClasses = @(
        "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace",
        "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcOpeningElement",
        "IfcRelVoidsElement", "IfcRelFillsElement", "IfcRelSpaceBoundary", "IfcRelSpaceBoundary2ndLevel"
    )
    $liveEntityCounts = [ordered]@{}
    $entityReferences = [ordered]@{}
    foreach ($className in $ifcClasses) {
        $response = Invoke-Jemi -Method "Entity.Get" -Params ([ordered]@{ Select = [ordered]@{ $className = [ordered]@{} } })
        if ($null -eq $response.result) {
            $references = @()
        }
        elseif ($response.result -is [System.Array]) {
            $references = @($response.result)
        }
        else {
            $references = @([string]$response.result)
        }
        $liveEntityCounts[$className] = $references.Count
        $entityReferences[$className] = $references
    }

    $liveSpaces = @()
    foreach ($reference in @($entityReferences["IfcSpace"])) {
        $liveSpaces += [ordered]@{
            ref_id = [string]$reference
            ifc_guid = [string](Get-EntityAttribute -Reference ([string]$reference) -Attribute "GlobalId")
            name = [string](Get-EntityAttribute -Reference ([string]$reference) -Attribute "Name")
            long_name = [string](Get-EntityAttribute -Reference ([string]$reference) -Attribute "LongName")
        }
    }

    Invoke-Jemi -Method "Model.SaveFile" -Params ([ordered]@{ Location = $outputPath }) | Out-Null
    if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf) -or (Get-Item -LiteralPath $outputPath).Length -le 0) {
        throw "Archicad Model.SaveFile did not produce stage2.ifc."
    }

    $stage1Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash.ToLowerInvariant()
    $stage2Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash.ToLowerInvariant()
    $revitHandoffHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $revitHandoffPath).Hash.ToLowerInvariant()
    $stage1Ids = @(Get-IfcRootIds -Path $inputPath)
    $stage2Ids = @(Get-IfcRootIds -Path $outputPath)
    $stage1IdSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $stage2IdSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $stage2SeenIds = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $stage2DuplicateIds = New-Object System.Collections.Generic.List[string]
    foreach ($id in $stage1Ids) { [void]$stage1IdSet.Add([string]$id) }
    foreach ($id in $stage2Ids) {
        [void]$stage2IdSet.Add([string]$id)
        if (-not $stage2SeenIds.Add([string]$id)) { $stage2DuplicateIds.Add([string]$id) }
    }
    $stage1UniqueIds = @($stage1IdSet)
    $stage2UniqueIds = @($stage2IdSet)
    $missingIds = @($stage1UniqueIds | Where-Object { -not $stage2IdSet.Contains([string]$_) })
    if ($missingIds.Count -ne 0) {
        throw "Archicad stage2.ifc lost upstream IfcRoot GlobalIds: $($missingIds -join ', ')"
    }
    if ($stage2DuplicateIds.Count -ne 0) {
        throw "Archicad stage2.ifc contains duplicate IfcRoot GlobalIds: $($stage2DuplicateIds -join ', ')"
    }

    $spaceRows = @()
    foreach ($upstreamSpace in @($revitHandoff.spaces)) {
        $liveSpace = @($liveSpaces | Where-Object { $_.long_name -eq $upstreamSpace.name -and $_.ifc_guid -eq $upstreamSpace.ifc_guid })
        if ($liveSpace.Count -ne 1) {
            throw "Archicad live model does not contain exactly one matching IfcSpace for $($upstreamSpace.name)."
        }
        $spaceRows += [ordered]@{
            name = [string]$upstreamSpace.name
            ifc_guid = [string]$upstreamSpace.ifc_guid
            thermal_zone = [string]$upstreamSpace.thermal_zone
            area_m2 = [double]$upstreamSpace.area_m2
            storey = [string]$upstreamSpace.storey
            schedule_category = [string]$upstreamSpace.schedule_category
            people_per_m2 = [double]$upstreamSpace.people_per_m2
            lighting_w_per_m2 = [double]$upstreamSpace.lighting_w_per_m2
            equipment_w_per_m2 = [double]$upstreamSpace.equipment_w_per_m2
            outdoor_air_l_per_s_person = [double]$upstreamSpace.outdoor_air_l_per_s_person
            source_stage = "revit-handoff-verified-by-archicad"
            archicad_ref_id = [string]$liveSpace[0].ref_id
        }
    }

    $stage1Text = Get-Content -LiteralPath $inputPath -Raw
    $stage2Text = Get-Content -LiteralPath $outputPath -Raw
    $requiredStructuralIds = @($spec.seed_preservation.walls | ForEach-Object { [string]$_.global_id }) + @($spec.seed_preservation.slab_global_ids | ForEach-Object { [string]$_ })
    foreach ($guid in $requiredStructuralIds) {
        if ($stage1Text.IndexOf([string]$guid, [System.StringComparison]::Ordinal) -lt 0 -or $stage2Text.IndexOf([string]$guid, [System.StringComparison]::Ordinal) -lt 0) {
            throw "Archicad did not observe and preserve required seed structural GlobalId $guid."
        }
    }
    $expectedCounts = [ordered]@{
        IfcSpace = 3; IfcWall = 12; IfcSlab = 3; IfcRoof = 1; IfcDoor = 3; IfcWindow = 3
        IfcOpeningElement = 6; IfcRelVoidsElement = 6; IfcRelFillsElement = 6
    }
    foreach ($expected in $expectedCounts.GetEnumerator()) {
        if ([int]$liveEntityCounts[$expected.Key] -ne [int]$expected.Value) {
            throw "Archicad live model count mismatch for $($expected.Key): $($liveEntityCounts[$expected.Key]) vs $($expected.Value)."
        }
        foreach ($pair in @(@{Label="stage1"; Text=$stage1Text}, @{Label="stage2"; Text=$stage2Text})) {
            $savedCount = [regex]::Matches($pair.Text, "\b$([regex]::Escape($expected.Key))\s*\(", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
            if ($savedCount -ne [int]$expected.Value) {
                throw "Archicad $($pair.Label) count mismatch for $($expected.Key): $savedCount vs $($expected.Value)."
            }
        }
    }
    $stage1Graph = Get-FillingGraphSignatures -Path $inputPath
    $stage2Graph = Get-FillingGraphSignatures -Path $outputPath
    if (($stage1Graph.voids -join "|") -ne ($stage2Graph.voids -join "|") -or
        ($stage1Graph.fills -join "|") -ne ($stage2Graph.fills -join "|")) {
        throw "Archicad stage2.ifc rewired the hosted opening/filling graph."
    }

    $stage1BoundaryCount = Get-IfcEntityCount -Path $inputPath -EntityName "IFCRELSPACEBOUNDARY"
    $stage2BoundaryCount = Get-IfcEntityCount -Path $outputPath -EntityName "IFCRELSPACEBOUNDARY"
    $stage1SecondLevelCount = Get-IfcEntityCount -Path $inputPath -EntityName "IFCRELSPACEBOUNDARY2NDLEVEL"
    $stage2SecondLevelCount = Get-IfcEntityCount -Path $outputPath -EntityName "IFCRELSPACEBOUNDARY2NDLEVEL"
    if ($stage2BoundaryCount -ne $stage1BoundaryCount -or $stage2SecondLevelCount -ne $stage1SecondLevelCount) {
        throw "Archicad did not preserve the observed upstream space-boundary state."
    }

    $actualCommandLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($serverProcess.Id)").CommandLine
    $productVersion = "Archicad 27 build $build (Archicad Starter $($archicadVersionInfo.ProductVersion); IFCCommandServer $($serverVersionInfo.ProductVersion))"
    $qaTokens = @($spec.archicad_stage.required_tokens) + @($spec.case_id)
    $nativeProvenance = [ordered]@{
        exe = $commandServer
        product_version = $productVersion
        process_id = $serverProcess.Id
        command_line = $actualCommandLine
        port = $Port
        model_name = $modelName
        database_path = $databasePath
        health_endpoint = "$baseUrl/HEALTH"
        jemi_endpoint = "$baseUrl/JEMI"
        rpc_transcript = $rpcTranscript.ToArray()
    }

    $entityCounts = [ordered]@{}
    $liveSavedCountDifferences = @()
    foreach ($className in $ifcClasses) {
        $savedCount = Get-IfcEntityCount -Path $outputPath -EntityName $className
        if ([int]$liveEntityCounts[$className] -ne $savedCount) {
            $liveSavedCountDifferences += [ordered]@{
                entity = $className
                live_select_count = [int]$liveEntityCounts[$className]
                saved_exact_entity_count = $savedCount
            }
        }
        $entityCounts[$className] = $savedCount
    }
    if ($liveSavedCountDifferences.Count -ne 0) {
        throw "Archicad live and saved entity counts differ: $($liveSavedCountDifferences | ConvertTo-Json -Depth 10 -Compress)"
    }

    $report = [ordered]@{
        case_id = $spec.case_id
        software_stage = "archicad"
        source_file = "stage1.ifc"
        source_sha256 = $stage1Hash
        output_file = "stage2.ifc"
        output_sha256 = $stage2Hash
        validation_method = "Macro.ValidateIfcModel"
        validation_result = $validationResponse.result
        accepted_validation_observations = $acceptedValidationObservations
        live_entity_counts = $liveEntityCounts
        entity_counts = $entityCounts
        live_saved_count_differences = $liveSavedCountDifferences
        live_spaces = $liveSpaces
        spaces = @($spaceRows | ForEach-Object { $_.name })
        preserved_model = [ordered]@{
            required_wall_global_ids = @($spec.seed_preservation.walls | ForEach-Object { [string]$_.global_id })
            required_slab_global_ids = @($spec.seed_preservation.slab_global_ids | ForEach-Object { [string]$_ })
            live_wall_count = [int]$liveEntityCounts["IfcWall"]
            live_slab_count = [int]$liveEntityCounts["IfcSlab"]
            live_roof_count = [int]$liveEntityCounts["IfcRoof"]
            filling_graph_counts = $expectedCounts
            filling_graph = $stage2Graph
        }
        space_boundaries = [ordered]@{
            policy = "observe_validate_and_preserve_upstream_state_without_fabrication"
            stage1_relationship_count = $stage1BoundaryCount
            stage2_relationship_count = $stage2BoundaryCount
            stage1_second_level_count = $stage1SecondLevelCount
            stage2_second_level_count = $stage2SecondLevelCount
            second_level_supported_by_observed_files = ($stage1SecondLevelCount -gt 0 -and $stage2SecondLevelCount -gt 0)
            note = "Archicad JEMI Model.SaveFile preserved the real Revit export boundary state; no missing relationships were synthesized."
        }
        global_id_audit = [ordered]@{
            stage1_ifcroot_count = $stage1Ids.Count
            stage1_unique_ifcroot_count = $stage1UniqueIds.Count
            stage2_ifcroot_count = $stage2Ids.Count
            stage2_unique_ifcroot_count = $stage2UniqueIds.Count
            preserved_count = @($stage1UniqueIds | Where-Object { $stage2IdSet.Contains([string]$_) }).Count
            missing_ids = $missingIds
            duplicate_ids = $stage2DuplicateIds
        }
        qa_tokens = $qaTokens
        blocking_errors = @()
        native_provenance = $nativeProvenance
    }
    [IO.File]::WriteAllText($reportPath, (($report | ConvertTo-Json -Depth 100) + [Environment]::NewLine), $utf8)

    $buildingArea = 0.0
    foreach ($spaceRow in $spaceRows) {
        $buildingArea += [double]$spaceRow["area_m2"]
    }
    $handoff = [ordered]@{
        case_id = $spec.case_id
        software_stage = "archicad"
        source_file = "stage2.ifc"
        source_sha256 = $stage2Hash
        stage1_sha256 = $stage1Hash
        revit_handoff_sha256 = $revitHandoffHash
        spaces = $spaceRows
        preserved_model = [ordered]@{
            wall_global_ids = @($spec.seed_preservation.walls | ForEach-Object { [string]$_.global_id })
            slab_global_ids = @($spec.seed_preservation.slab_global_ids | ForEach-Object { [string]$_ })
            filling_graph_counts = $expectedCounts
            filling_graph = $stage2Graph
        }
        thermal_zones = @($spaceRows | ForEach-Object { [ordered]@{ name = $_.thermal_zone; area_m2 = $_.area_m2 } })
        handoff_tokens = @($spec.handoff_tokens)
        building_area_m2 = [math]::Round($buildingArea, 6)
        weather_file = "weather.epw"
        schedule_set = "$($spec.revision)-ScheduleSet"
        construction_set = "$($spec.revision)-ConstructionSet"
        downstream_consumer = "openstudio"
        native_provenance = $nativeProvenance
    }
    [IO.File]::WriteAllText($handoffPath, (($handoff | ConvertTo-Json -Depth 100) + [Environment]::NewLine), $utf8)

    $finishedUtc = [DateTime]::UtcNow.ToString("o")
    $nativeLog = Get-Content -LiteralPath $nativeLogPath -Raw | ConvertFrom-Json
    $existingStages = @($nativeLog.stages | Where-Object { $_.stage -ne "archicad" -and $_.stage -ne "openstudio" })
    $entry = [ordered]@{
        stage = "archicad"
        executable = $archicadExe
        invoked_executable = $commandServer
        product_version = $productVersion
        automation_entry = $commandServer
        command = "run_archicad_stage.ps1 -Desktop $Desktop -Port $Port; inputs workflow_spec.json archicad_ifc4_translator.json; invoked $actualCommandLine; JEMI Model.LoadFile -> Macro.ValidateIfcModel -> Entity.Get/Entity.GetAttribute -> Model.SaveFile"
        started_utc = $startedUtc
        finished_utc = $finishedUtc
        exit_code = 0
        input_file = "stage1.ifc"
        input_sha256 = $stage1Hash
        input_handoff_sha256 = $revitHandoffHash
        output_file = "stage2.ifc"
        output_sha256 = $stage2Hash
        handoff_file = "archicad_handoff.json"
        handoff_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $handoffPath).Hash.ToLowerInvariant()
        validation_report_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $reportPath).Hash.ToLowerInvariant()
        translator_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $translatorPath).Hash.ToLowerInvariant()
        rpc_method_sequence = @($rpcTranscript.ToArray() | ForEach-Object { $_.request.method })
    }
    $updatedLog = [ordered]@{ schema_version = 1; stages = @($existingStages) + @($entry) }
    [IO.File]::WriteAllText($nativeLogPath, (($updatedLog | ConvertTo-Json -Depth 100) + [Environment]::NewLine), $utf8)
}
finally {
    if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
        try {
            Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$baseUrl/SHUTDOWN" -TimeoutSec 3 | Out-Null
            $serverProcess.WaitForExit(3000) | Out-Null
        }
        catch {
        }
        if (-not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
        }
    }
}
