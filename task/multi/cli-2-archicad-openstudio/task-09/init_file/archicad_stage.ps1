$ErrorActionPreference = "Stop"

$caseId = "multi-cli-2-archicad-openstudio-task-09-windows"
$desktop = "C:\Users\user\Desktop"
$exe = "C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe"
$database = "C:\EW09"
$port = 12346
$transactions = @()
$stageStarted = [DateTimeOffset]::UtcNow.ToString("o")

function Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Invoke-Ifc([string]$Method, [hashtable]$Params) {
    $request = [ordered]@{ method = $Method; params = $Params }
    $started = [DateTimeOffset]::UtcNow.ToString("o")
    $requestJson = $request | ConvertTo-Json -Depth 30 -Compress
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$port/JEMI" -Method Post -ContentType "application/json" -Body $requestJson
    $completed = [DateTimeOffset]::UtcNow.ToString("o")
    if ($null -ne $response.error) { throw "$Method failed: $($response.error | ConvertTo-Json -Compress)" }
    $script:transactions += [ordered]@{
        request = ($requestJson | ConvertFrom-Json)
        request_json = $requestJson
        status = 200
        response = $response
        started_at_utc = $started
        completed_at_utc = $completed
    }
    return $response.result
}

if (Test-Path -LiteralPath $database) { Remove-Item -LiteralPath $database -Recurse -Force }
$proc = Start-Process -FilePath $exe -ArgumentList @("--p", "$port", "--m", "EW09", "--d", $database, "--sa", "new_ifc4") -PassThru
try {
    $ready = $false
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 250
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/HEALTH" -TimeoutSec 1
            if ($health.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
    }
    if (-not $ready) { throw "IFC command server did not become healthy on port $port" }

    [void](Invoke-Ifc "Model.LoadFile" @{ location = "$desktop\init.ifc" })
    $changes = @(
        @{ cls="IfcSpace"; gid="2cvyGW3FP0ihcYL5rR0ExL"; old="LOUNGE"; data=@{Name="SOCIAL-COMMONS";LongName="SOCIAL-COMMONS-ZN"} },
        @{ cls="IfcSpace"; gid="2AJL71eRHDF8hYnJDd9x1g"; old="SHARED-KITCHEN"; data=@{Name="QUIET-STUDY";LongName="QUIET-STUDY-ZN | LOW-EQUIPMENT-STUDY"} },
        @{ cls="IfcSpace"; gid="12QQ5n5sr4r9qW`$eloRCk6"; old="LAUNDRY"; data=@{Name="LAUNDRY";LongName="LAUNDRY-ZN | HIGH-EQUIPMENT-LAUNDRY"} },
        @{ cls="IfcSpace"; gid="0s4DhhVRv2bg8`$9xnROM2z"; old="BED-1"; data=@{LongName="BEDROOM-GROUP-ZN | BEDROOM-GROUP | BEDROOM-COUNT-PRESERVED"} },
        @{ cls="IfcSpace"; gid="2turPsEaf00f9_GTNbDdYS"; old="BED-2"; data=@{LongName="BEDROOM-GROUP-ZN | BEDROOM-GROUP | BEDROOM-COUNT-PRESERVED"} },
        @{ cls="IfcSpace"; gid="36relbj9D7wwSTsPZOQMFT"; old="BED-3"; data=@{LongName="BEDROOM-GROUP-ZN | BEDROOM-GROUP | BEDROOM-COUNT-PRESERVED"} },
        @{ cls="IfcSpace"; gid="1DLQ7ctwH1MAnWIo9abD6O"; old="BED-4"; data=@{LongName="BEDROOM-GROUP-ZN | BEDROOM-GROUP | BEDROOM-COUNT-PRESERVED"} },
        @{ cls="IfcSpace"; gid="0O3aHiYETAYAIAFv3EUqD2"; old="BED-5"; data=@{LongName="BEDROOM-GROUP-ZN | BEDROOM-GROUP | BEDROOM-COUNT-PRESERVED"} },
        @{ cls="IfcSpace"; gid="3po1NdHJD8Ahh2IkxPFep2"; old="BED-6"; data=@{LongName="BEDROOM-GROUP-ZN | BEDROOM-GROUP | BEDROOM-COUNT-PRESERVED"} },
        @{ cls="IfcProject"; gid="2BlDJ8uLf6lRdJ7nhdcylY"; old="c11 result"; data=@{Description="EW2A09 | multi-cli-2-archicad-openstudio-task-09-windows"} }
    )
    foreach ($change in $changes) {
        $select = @{ GlobalId = $change.gid; Name = $change.old }
        $modified = Invoke-Ifc "Entity.Modify" @{
            select = @{ $change.cls = $select }
            EntityData = @{ $change.cls = $change.data }
        }
        if (-not $modified) { throw "Entity.Modify returned no result for $($change.gid)" }
    }
    [void](Invoke-Ifc "Model.SaveFile" @{ location = "$desktop\stage1.ifc" })

    $stageHash = Sha256 "$desktop\stage1.ifc"
    $initHash = Sha256 "$desktop\init.ifc"
    $counts = [ordered]@{ IfcProject=1; IfcSite=1; IfcBuilding=1; IfcBuildingStorey=2; IfcSpace=11; IfcWall=8; IfcSlab=2; IfcRoof=1; IfcDoor=0; IfcWindow=0; IfcOpeningElement=0 }
    $handoff = [ordered]@{
        schema = "engiworld.archicad-handoff.v1"
        case_id = $caseId
        revision = "EW2A09"
        software_stage = "archicad"
        authoring_software = "Graphisoft Archicad 27.0.0 R1 (6000) IFCCommandServerApp"
        native_cli_executable = $exe
        source_init_sha256 = $initHash
        source_sha256 = $stageHash
        source_stage1_sha256 = $stageHash
        bedroom_count = 6
        bedroom_count_preserved = $true
        preserved_features = @("six individual BED-* IfcSpace entities", "COURTYARD", "CoLivingRoof", "two building storeys", "walls and slabs")
        handoff_tokens = @("LOW-EQUIPMENT-STUDY", "HIGH-EQUIPMENT-LAUNDRY", "RESIDENTIAL-SCHEDULE", "SOCIAL-SPACE-SCHEDULE")
        building_area_m2 = 148.0
        door_count = 0
        window_count = 0
        bim_counts = $counts
        thermal_zones = @("SOCIAL-COMMONS-ZN", "BEDROOM-GROUP-ZN", "QUIET-STUDY-ZN", "LAUNDRY-ZN")
        spaces = @(
            [ordered]@{name="SOCIAL-COMMONS";thermal_zone="SOCIAL-COMMONS-ZN";floor_area_m2=16.0;door_count=0;window_count=0;ifc_global_id="2cvyGW3FP0ihcYL5rR0ExL";schedule="SOCIAL-SPACE-SCHEDULE"},
            [ordered]@{name="BEDROOM-GROUP";thermal_zone="BEDROOM-GROUP-ZN";floor_area_m2=96.0;door_count=0;window_count=0;ifc_global_ids=@("0s4DhhVRv2bg8`$9xnROM2z","2turPsEaf00f9_GTNbDdYS","36relbj9D7wwSTsPZOQMFT","1DLQ7ctwH1MAnWIo9abD6O","0O3aHiYETAYAIAFv3EUqD2","3po1NdHJD8Ahh2IkxPFep2");schedule="RESIDENTIAL-SCHEDULE";bedroom_count=6},
            [ordered]@{name="QUIET-STUDY";thermal_zone="QUIET-STUDY-ZN";floor_area_m2=20.0;door_count=0;window_count=0;ifc_global_id="2AJL71eRHDF8hYnJDd9x1g";equipment_assumption="LOW-EQUIPMENT-STUDY"},
            [ordered]@{name="LAUNDRY";thermal_zone="LAUNDRY-ZN";floor_area_m2=16.0;door_count=0;window_count=0;ifc_global_id="12QQ5n5sr4r9qW`$eloRCk6";equipment_assumption="HIGH-EQUIPMENT-LAUNDRY"}
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
        }
        artifacts = [ordered]@{
            "init.ifc" = @{sha256=$initHash;size=(Get-Item "$desktop\init.ifc").Length}
            "stage1.ifc" = @{sha256=$stageHash;size=(Get-Item "$desktop\stage1.ifc").Length}
            "handoff.json" = @{sha256=(Sha256 "$desktop\handoff.json");size=(Get-Item "$desktop\handoff.json").Length}
        }
        native_transactions = @{Items=$transactions}
    }
    $log | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath "$desktop\native_stage_log.json" -Encoding utf8
    Write-Output ($log | ConvertTo-Json -Depth 6 -Compress)
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
        $proc.WaitForExit()
    }
}
