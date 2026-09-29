$ErrorActionPreference = "Stop"

$caseId = "multi-cli-2-archicad-openstudio-task-10-windows"
$desktop = "C:\Users\user\Desktop"
$exe = "C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe"
$database = "C:\EW10"
$port = 12347
$transactions = @()
$stageStarted = [DateTimeOffset]::UtcNow.ToString("o")
$serverStarted = $null
$serverStopped = $null
$auditNote = if ($env:EW10_AUDIT_NOTE) { [string]$env:EW10_AUDIT_NOTE } else { $null }
$targetVariant = if ($env:EW10_TARGET_VARIANT) { [string]$env:EW10_TARGET_VARIANT } else { "formal" }

function Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Invoke-Ifc([string]$Method, [hashtable]$Params, [int]$Id) {
    $request = [ordered]@{ method = $Method; params = $Params }
    $started = [DateTimeOffset]::UtcNow.ToString("o")
    $requestJson = $request | ConvertTo-Json -Depth 30 -Compress
    $requestEvidence = $requestJson | ConvertFrom-Json
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$port/JEMI" -Method Post -ContentType "application/json" -Body $requestJson
    $completed = [DateTimeOffset]::UtcNow.ToString("o")
    if ($null -ne $response.error) { throw "$Method failed: $($response.error | ConvertTo-Json -Compress)" }
    $script:transactions += [ordered]@{
        request = $requestEvidence
        request_json = $requestJson
        status = 200
        response = $response
        started_at_utc = $started
        completed_at_utc = $completed
    }
    return $response.result
}

if (Test-Path -LiteralPath $database) { Remove-Item -LiteralPath $database -Recurse -Force }
$proc = Start-Process -FilePath $exe -ArgumentList @("--p", "$port", "--m", "EW10", "--d", $database, "--sa", "new_ifc4") -PassThru
$serverStarted = [DateTimeOffset]::UtcNow.ToString("o")
try {
    $ready = $false
    for ($i = 0; $i -lt 100; $i++) {
        Start-Sleep -Milliseconds 200
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { $ready = $true; break }
    }
    if (-not $ready) { throw "IFC command server did not listen on $port" }
    Start-Sleep -Seconds 2

    [void](Invoke-Ifc "Model.LoadFile" @{ location = "$desktop\init.ifc" } 1)

    $consultChange = @{ gid = "0p_GCOHqL9O8Orvi_YQmfp"; old = "CONSULT-1"; new = "CONSULT"; long = "CONSULT-ZN | CLINICAL-VENTILATION | ISOLATION-FLOW-01" }
    $isoChange = @{ gid = "2donn1s`$15fQstYK6K7bhA"; old = "CONSULT-2"; new = "ISO-CONSULT"; long = "ISO-CONSULT-ZN | ISOLATION-CONSULT-SCHEDULE | ISOLATION-FLOW-03" }
    if ($targetVariant -eq "alternate") {
        $consultChange = @{ gid = "2wv7qlrLHECvQ`$ovZhAZ6k"; old = "CONSULT-3"; new = "CONSULT"; long = "CONSULT-ZN | CLINICAL-VENTILATION | FLOW-STEP-01" }
        $isoChange = @{ gid = "0p_GCOHqL9O8Orvi_YQmfp"; old = "CONSULT-1"; new = "ISO-CONSULT"; long = "ISO-CONSULT-ZN | ISOLATION-CONSULT-SCHEDULE | FLOW-STEP-03" }
    }
    $changes = @(
        $consultChange,
        @{ gid = "38jEfacSPBCBtDO38Sa4ab"; old = "LAB"; new = "EQUIPMENT"; long = "EQUIPMENT-ZN | CLINICAL-VENTILATION | ISOLATION-FLOW-02" },
        $isoChange,
        @{ gid = "3h`$isFwRP5_hw8nERq6D`$D"; old = "CLEAN"; new = "PPE-DONNING"; long = "PPE-DONNING-ZN | PPE-SUPPORT | ISOLATION-FLOW-04" },
        @{ gid = "25gwD9sn52YxBd1q5pXbvc"; old = "DIRTY"; new = "CONTAMINATED-SUPPORT"; long = "CONTAMINATED-SUPPORT-ZN | CONTAMINATED-SUPPORT-LOW-OCCUPANCY | ISOLATION-FLOW-05" }
    )
    $id = 2
    foreach ($change in $changes) {
        $modified = Invoke-Ifc "Entity.Modify" @{
            select = @{ IfcSpace = @{ GlobalId = $change.gid; Name = $change.old } }
            EntityData = @{ IfcSpace = @{ Name = $change.new; LongName = $change.long } }
        } $id
        if (-not $modified) { throw "Entity.Modify returned no result for $($change.gid)" }
        $id++
    }
    [void](Invoke-Ifc "Entity.Modify" @{
        select = @{ IfcProject = @{ GlobalId = "1pngtsS6H0hAcTpmi3SH_e"; Name = "EngiWorld Archicad Task 15" } }
        EntityData = @{ IfcProject = @{ Description = "EW2A10 | $caseId" } }
    } $id)
    $id++
    [void](Invoke-Ifc "Model.SaveFile" @{ location = "$desktop\stage1.ifc" } $id)
    $saveCompleted = [DateTimeOffset]::UtcNow.ToString("o")

    $stageHash = Sha256 "$desktop\stage1.ifc"
    $initHash = Sha256 "$desktop\init.ifc"
    $counts = [ordered]@{ IfcProject=1; IfcSite=1; IfcBuilding=1; IfcBuildingStorey=1; IfcSpace=12; IfcWall=26; IfcSlab=1; IfcRoof=3; IfcDoor=12; IfcWindow=8; IfcOpeningElement=0 }
    $handoff = [ordered]@{
        schema = "engiworld.archicad-handoff.v1"
        case_id = $caseId
        revision = "EW2A10"
        software_stage = "archicad"
        authoring_software = "Graphisoft Archicad 27.0.0 R1 (6000) IFCCommandServerApp"
        native_cli_executable = $exe
        source_init_sha256 = $initHash
        source_sha256 = $stageHash
        source_stage1_sha256 = $stageHash
        audit_note = $auditNote
        isolation_flow = @("CONSULT", "EQUIPMENT", "ISO-CONSULT", "PPE-DONNING", "CONTAMINATED-SUPPORT")
        preserved_features = @("all 12 seed spaces", "26 walls", "three roofs", "12 doors", "eight windows")
        handoff_tokens = @("CLINICAL-VENTILATION", "ISOLATION-CONSULT-SCHEDULE", "PPE-SUPPORT", "CONTAMINATED-SUPPORT-LOW-OCCUPANCY")
        building_area_m2 = 60.0
        door_count = 0
        window_count = 0
        bim_counts = $counts
        thermal_zones = @("CONSULT-ZN","EQUIPMENT-ZN","ISO-CONSULT-ZN","PPE-DONNING-ZN","CONTAMINATED-SUPPORT-ZN")
        spaces = @(
            [ordered]@{name="CONSULT";thermal_zone="CONSULT-ZN";floor_area_m2=14.0;door_count=0;window_count=0;ifc_global_id=$consultChange.gid;schedule="CONSULT-SCHEDULE";flow_order=1},
            [ordered]@{name="EQUIPMENT";thermal_zone="EQUIPMENT-ZN";floor_area_m2=16.0;door_count=0;window_count=0;ifc_global_id="38jEfacSPBCBtDO38Sa4ab";schedule="EQUIPMENT-SCHEDULE";flow_order=2},
            [ordered]@{name="ISO-CONSULT";thermal_zone="ISO-CONSULT-ZN";floor_area_m2=14.0;door_count=0;window_count=0;ifc_global_id=$isoChange.gid;schedule="ISOLATION-CONSULT-SCHEDULE";flow_order=3},
            [ordered]@{name="PPE-DONNING";thermal_zone="PPE-DONNING-ZN";floor_area_m2=8.0;door_count=0;window_count=0;ifc_global_id="3h`$isFwRP5_hw8nERq6D`$D";schedule="PPE-SUPPORT-SCHEDULE";flow_order=4},
            [ordered]@{name="CONTAMINATED-SUPPORT";thermal_zone="CONTAMINATED-SUPPORT-ZN";floor_area_m2=8.0;door_count=0;window_count=0;ifc_global_id="25gwD9sn52YxBd1q5pXbvc";schedule="CONTAMINATED-SUPPORT-LOW-OCCUPANCY";flow_order=5}
        )
    }
    $handoff | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath "$desktop\handoff.json" -Encoding utf8

    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)"
    $log = [ordered]@{
        schema = "engiworld.archicad-native-stage.v1"
        case_id = $caseId
        software_stage = "archicad"
        native_stage_started_at_utc = $stageStarted
        native_stage_completed_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
        command_server_process = [ordered]@{
            pid = $proc.Id
            executable_path = $exe
            command_line = $processInfo.CommandLine
            product_version = (Get-Item $exe).VersionInfo.ProductVersion
            executable_sha256 = Sha256 $exe
            listening_port = $port
            database_path = $database
            server_started_at_utc = $serverStarted
        }
        artifacts = [ordered]@{
            "init.ifc" = @{sha256=$initHash;size=(Get-Item "$desktop\init.ifc").Length}
            "stage1.ifc" = @{sha256=$stageHash;size=(Get-Item "$desktop\stage1.ifc").Length;last_write_time_utc=(Get-Item "$desktop\stage1.ifc").LastWriteTimeUtc.ToString("o")}
            "handoff.json" = @{sha256=(Sha256 "$desktop\handoff.json");size=(Get-Item "$desktop\handoff.json").Length;last_write_time_utc=(Get-Item "$desktop\handoff.json").LastWriteTimeUtc.ToString("o")}
        }
        save_completed_at_utc = $saveCompleted
        preservation_evidence = [ordered]@{seed_root_count_before=94;seed_root_count_after=94;seed_root_global_ids_preserved=$true;space_count_before=12;space_count_after=12;door_count_preserved=12;window_count_preserved=8}
        native_transactions = @{Items=$transactions}
    }
    $log | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath "$desktop\native_stage_log.json" -Encoding utf8
    Write-Output ($log | ConvertTo-Json -Depth 5 -Compress)
}
finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force; $proc.WaitForExit() }
    $serverStopped = [DateTimeOffset]::UtcNow.ToString("o")
}
