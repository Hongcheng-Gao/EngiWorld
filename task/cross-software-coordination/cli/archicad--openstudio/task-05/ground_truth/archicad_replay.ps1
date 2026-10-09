[CmdletBinding()]
param(
    [string]$Desktop = "C:\Users\user\Desktop",
    [int]$Port = 12343,
    [string]$DatabasePath = "C:\EW05-CODEX-RERUN",
    [string]$ModelName = "EW05-CODEX-RERUN",
    [switch]$ForceOutputs,
    [switch]$KeepDatabase
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$caseId = "multi-cli-2-archicad-openstudio-task-05-windows"
$revision = "EW2A05"
$commandServer = "C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe"
$initPath = Join-Path $Desktop "init.ifc"
$stage1Path = Join-Path $Desktop "stage1.ifc"
$handoffPath = Join-Path $Desktop "handoff.json"
$nativeLogPath = Join-Path $Desktop "native_stage_log.json"
$baseUrl = "http://127.0.0.1:$Port"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$expectedInitSha256 = "6ea42757b6dfc875df89ab031f470e12c9511e8f412f00ddf742d3aa87f07b46"
$expectedServerSha256 = "594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775"

$spaceSpecs = @(
    [ordered]@{ source_name = "STUDIO"; target_name = "MAIN-STUDIO"; zone = "MAIN-STUDIO-ZN"; global_id = '3GooX$w0T64PaMMXb2rVCv'; expected_area_m2 = 96.0; door_count = 0; window_count = 0 },
    [ordered]@{ source_name = "OFFICE"; target_name = "STORAGE"; zone = "STORAGE-ZN"; global_id = "2K1tzn4mb2SuCRjBe5UiEl"; expected_area_m2 = 16.0; door_count = 0; window_count = 0 },
    [ordered]@{ source_name = "STORE"; target_name = "FINISHING-BOOTH"; zone = "FINISHING-BOOTH-ZN"; global_id = "0ef4jH2iXECPvfVOgIk0oi"; expected_area_m2 = 12.0; door_count = 1; window_count = 1 }
)
$projectSpec = [ordered]@{
    global_id = "1ol2jYyjHAGfXzqrbiQ7p9"
    source_name = "North-Light Artist Studio"
    description = "EW2A05 | FINISHING-BOOTH | BOOTH-DOOR | HIGH-VENT-WINDOW | STORAGE-ADJACENT | STUDIO-HIGH-DAYLIGHT | multi-cli-2-archicad-openstudio-task-05-windows"
}
$doorSpec = [ordered]@{
    global_id = '2GhF4UrdvDMQfEapVi$KEI'
    name = "BOOTH-DOOR"
    description = "EW2A05 | FINISHING-BOOTH | STORAGE-ADJACENT"
    height = 2.1
    width = 0.9
}
$windowSpec = [ordered]@{
    global_id = '3$ZvW3I050mf19fX6X8s2E'
    name = "HIGH-VENT-WINDOW"
    description = "EW2A05 | HIGH-VENT-WINDOW | FINISHING-BOOTH"
    height = 0.6
    width = 1.2
}
$containmentGlobalId = '0R_p1$UbTAZ8z2ZXhEkTVa'

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Write-JsonUtf8NoBom([string]$Path, [object]$Value) {
    $json = $Value | ConvertTo-Json -Depth 100
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, $utf8NoBom)
}

function Get-IfcStatementMap([string]$Text) {
    $map = @{}
    $pattern = "(?is)#(?<id>\d+)\s*=\s*(?<body>.*?);"
    foreach ($match in [regex]::Matches($Text, $pattern)) {
        $map[$match.Groups["id"].Value] = $match.Groups["body"].Value.Trim()
    }
    return $map
}

function Get-IfcRootGlobalIds([string]$Text) {
    $pattern = "(?im)^\s*#\d+\s*=\s*IFC[A-Z0-9_]+\s*\(\s*'(?<gid>[0-9A-Za-z_$]{22})'"
    return @([regex]::Matches($Text, $pattern) | ForEach-Object { $_.Groups["gid"].Value })
}

function Get-IfcEntityReferenceByGlobalId([hashtable]$Statements, [string]$GlobalId, [string]$EntityClass) {
    $escapedId = [regex]::Escape($GlobalId)
    $escapedClass = [regex]::Escape($EntityClass)
    $matches = @($Statements.GetEnumerator() | Where-Object {
        $_.Value -match "(?is)^$escapedClass\s*\(\s*'$escapedId'\s*,"
    })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one $EntityClass with GlobalId $GlobalId, found $($matches.Count)."
    }
    return [string]$matches[0].Key
}

function Get-IfcSpaceNetFloorArea([hashtable]$Statements, [string]$SpaceGlobalId) {
    $spaceRef = Get-IfcEntityReferenceByGlobalId -Statements $Statements -GlobalId $SpaceGlobalId -EntityClass "IFCSPACE"
    $quantitySetRefs = New-Object System.Collections.Generic.List[string]
    foreach ($entry in $Statements.GetEnumerator()) {
        if ($entry.Value -notmatch "(?is)^IFCRELDEFINESBYPROPERTIES\s*\(") { continue }
        $match = [regex]::Match($entry.Value, "(?is)\(\s*(?<objects>(?:#\d+\s*,?\s*)+)\)\s*,\s*#(?<property>\d+)\s*\)\s*$")
        if (-not $match.Success) { continue }
        $relatedRefs = @([regex]::Matches($match.Groups["objects"].Value, "#(?<id>\d+)") | ForEach-Object { $_.Groups["id"].Value })
        if ($relatedRefs -contains $spaceRef) {
            [void]$quantitySetRefs.Add($match.Groups["property"].Value)
        }
    }
    $areas = New-Object System.Collections.Generic.List[double]
    foreach ($quantitySetRef in $quantitySetRefs) {
        if (-not $Statements.ContainsKey($quantitySetRef)) { continue }
        $quantitySetBody = [string]$Statements[$quantitySetRef]
        if ($quantitySetBody -notmatch "(?is)^IFCELEMENTQUANTITY\s*\(") { continue }
        $refsMatch = [regex]::Match($quantitySetBody, "(?is)\(\s*(?<refs>(?:#\d+\s*,?\s*)+)\)\s*\)\s*$")
        if (-not $refsMatch.Success) { continue }
        foreach ($quantityMatch in [regex]::Matches($refsMatch.Groups["refs"].Value, "#(?<id>\d+)")) {
            $quantityRef = $quantityMatch.Groups["id"].Value
            if (-not $Statements.ContainsKey($quantityRef)) { continue }
            $areaMatch = [regex]::Match(
                [string]$Statements[$quantityRef],
                "(?is)^IFCQUANTITYAREA\s*\(\s*'NetFloorArea'\s*,[^,]*,[^,]*,\s*(?<area>[-+0-9.Ee]+)\s*,"
            )
            if ($areaMatch.Success) {
                [void]$areas.Add([double]::Parse($areaMatch.Groups["area"].Value, [System.Globalization.CultureInfo]::InvariantCulture))
            }
        }
    }
    if ($areas.Count -ne 1) {
        throw "Expected one NetFloorArea for IfcSpace $SpaceGlobalId, found $($areas.Count)."
    }
    return [double]$areas[0]
}

function Get-IfcEntityCount([string]$Text, [string]$EntityClass) {
    return [regex]::Matches($Text, "(?im)^\s*#\d+\s*=\s*$([regex]::Escape($EntityClass))\s*\(").Count
}

foreach ($required in @($commandServer, $initPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required Task-05 input is missing: $required"
    }
}
if ((Get-Sha256 $initPath) -ne $expectedInitSha256) {
    throw "Task-05 init.ifc SHA-256 does not match the formal seed."
}
if ((Get-Sha256 $commandServer) -ne $expectedServerSha256) {
    throw "IFCCommandServerApp.exe SHA-256 does not match the verified Archicad 27 binary."
}

$databaseFullPath = [System.IO.Path]::GetFullPath($DatabasePath).TrimEnd('\')
if (-not $databaseFullPath.StartsWith("C:\EW05-CODEX-", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "DatabasePath must stay under the dedicated C:\EW05-CODEX-* namespace."
}
if (Test-Path -LiteralPath $databaseFullPath) {
    throw "Dedicated Task-05 database path already exists; choose a fresh DatabasePath: $databaseFullPath"
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Task-05 port $Port is already in use."
}

foreach ($output in @($stage1Path, $handoffPath, $nativeLogPath)) {
    if (Test-Path -LiteralPath $output) {
        if (-not $ForceOutputs) {
            throw "Output already exists. Re-run with -ForceOutputs only after preserving it: $output"
        }
        Remove-Item -LiteralPath $output -Force
    }
}

$databaseCreated = $false
$serverProcess = $null
$rpcTranscript = New-Object System.Collections.Generic.List[object]
$nativeStageStarted = [DateTimeOffset]::UtcNow.ToString("o")
$actualCommandLine = $null
$processCreationUtc = $null

function Invoke-Jemi {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][object]$Params
    )
    $request = [ordered]@{ method = $Method; params = $Params }
    $requestJson = $request | ConvertTo-Json -Depth 40 -Compress
    $started = [DateTimeOffset]::UtcNow.ToString("o")
    $reply = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$baseUrl/JEMI" -ContentType "application/json" -Body $requestJson -TimeoutSec 30
    $completed = [DateTimeOffset]::UtcNow.ToString("o")
    $responseText = if ($reply.Content -is [byte[]]) { [System.Text.Encoding]::UTF8.GetString($reply.Content) } else { [string]$reply.Content }
    $response = $responseText | ConvertFrom-Json
    if ([int]$reply.StatusCode -ne 200 -or [string]$response.jsonrpc -ne "2.0" -or $null -ne $response.PSObject.Properties["error"]) {
        throw "Archicad JEMI $Method failed: $responseText"
    }
    [void]$rpcTranscript.Add([ordered]@{
        request = $request
        request_json = $requestJson
        status = [int]$reply.StatusCode
        response_text = $responseText
        response = $response
        started_at_utc = $started
        completed_at_utc = $completed
    })
    return $response
}

try {
    New-Item -ItemType Directory -Path $databaseFullPath -Force | Out-Null
    $databaseCreated = $true
    $arguments = @("--p", "$Port", "--m", $ModelName, "--d", $databaseFullPath, "--sa", "new_ifc4")
    $serverProcess = Start-Process -FilePath $commandServer -ArgumentList $arguments -PassThru

    $healthy = $false
    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        Start-Sleep -Milliseconds 250
        if ($serverProcess.HasExited) {
            throw "Archicad IFC command server exited during startup with code $($serverProcess.ExitCode)."
        }
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Method Get -Uri "$baseUrl/HEALTH" -TimeoutSec 2
            if ([int]$health.StatusCode -eq 200) { $healthy = $true; break }
        }
        catch {
        }
    }
    if (-not $healthy) { throw "Archicad IFC command server did not become healthy on port $Port." }

    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($serverProcess.Id)"
    $actualCommandLine = [string]$processInfo.CommandLine
    $processCreationUtc = $processInfo.CreationDate.ToUniversalTime().ToString("o")
    if ($actualCommandLine -notmatch "(^|\s)--p\s+$Port(\s|$)" -or $actualCommandLine -notmatch [regex]::Escape($databaseFullPath)) {
        throw "Observed IFC command server command line is not bound to this Task-05 port/database."
    }

    $load = Invoke-Jemi -Method "Model.LoadFile" -Params ([ordered]@{ location = $initPath })
    if ([string]$load.result -ne "init.ifc") { throw "Model.LoadFile did not bind init.ifc." }

    foreach ($space in $spaceSpecs) {
        $reply = Invoke-Jemi -Method "Entity.Modify" -Params ([ordered]@{
            select = [ordered]@{ IfcSpace = [ordered]@{ GlobalId = $space.global_id; Name = $space.source_name } }
            EntityData = [ordered]@{ IfcSpace = [ordered]@{ Name = $space.target_name; LongName = $space.zone } }
        })
        if ([string]::IsNullOrWhiteSpace([string]$reply.result)) {
            throw "Entity.Modify returned no native reference for $($space.target_name)."
        }
    }

    $projectReply = Invoke-Jemi -Method "Entity.Modify" -Params ([ordered]@{
        select = [ordered]@{ IfcProject = [ordered]@{ GlobalId = $projectSpec.global_id; Name = $projectSpec.source_name } }
        EntityData = [ordered]@{ IfcProject = [ordered]@{ Description = $projectSpec.description } }
    })
    if ([string]::IsNullOrWhiteSpace([string]$projectReply.result)) { throw "IfcProject revision update returned no native reference." }

    $doorReply = Invoke-Jemi -Method "Entity.Create" -Params ([ordered]@{
        EntityData = [ordered]@{ IfcDoor = [ordered]@{
            GlobalId = $doorSpec.global_id
            Name = $doorSpec.name
            Description = $doorSpec.description
            OverallHeight = $doorSpec.height
            OverallWidth = $doorSpec.width
            PredefinedType = "DOOR"
            OperationType = "SINGLE_SWING_LEFT"
            UserDefinedOperationType = $null
        } }
    })
    $doorRef = [string]$doorReply.result
    if ([string]::IsNullOrWhiteSpace($doorRef)) { throw "BOOTH-DOOR creation returned no native entity reference." }

    $windowReply = Invoke-Jemi -Method "Entity.Create" -Params ([ordered]@{
        EntityData = [ordered]@{ IfcWindow = [ordered]@{
            GlobalId = $windowSpec.global_id
            Name = $windowSpec.name
            Description = $windowSpec.description
            OverallHeight = $windowSpec.height
            OverallWidth = $windowSpec.width
            PredefinedType = "WINDOW"
            PartitioningType = "SINGLE_PANEL"
            UserDefinedPartitioningType = $null
        } }
    })
    $windowRef = [string]$windowReply.result
    if ([string]::IsNullOrWhiteSpace($windowRef) -or $windowRef -eq $doorRef) { throw "HIGH-VENT-WINDOW creation returned an invalid native entity reference." }

    $containmentReply = Invoke-Jemi -Method "Entity.GetAttribute" -Params ([ordered]@{
        Select = [ordered]@{ IfcRelContainedInSpatialStructure = [ordered]@{ GlobalId = $containmentGlobalId } }
        Attribute = "RelatedElements"
    })
    $seedContainmentRefs = @($containmentReply.result.RelatedElements | ForEach-Object { [string]$_ })
    if ($seedContainmentRefs.Count -ne 3 -or $seedContainmentRefs -contains $doorRef -or $seedContainmentRefs -contains $windowRef) {
        throw "Task-05 seed containment query did not return the expected three distinct seed references."
    }
    $updatedContainmentRefs = @($seedContainmentRefs) + @($doorRef, $windowRef)
    $containmentUpdate = Invoke-Jemi -Method "Entity.Modify" -Params ([ordered]@{
        select = [ordered]@{ IfcRelContainedInSpatialStructure = [ordered]@{ GlobalId = $containmentGlobalId } }
        EntityData = [ordered]@{ IfcRelContainedInSpatialStructure = [ordered]@{ RelatedElements = $updatedContainmentRefs } }
    })
    if ([string]::IsNullOrWhiteSpace([string]$containmentUpdate.result)) { throw "Containment update returned no native relationship reference." }

    $doorCheck = Invoke-Jemi -Method "Entity.GetAttribute" -Params ([ordered]@{
        Select = [ordered]@{ IfcDoor = [ordered]@{ GlobalId = $doorSpec.global_id } }
        Attribute = "Name"
    })
    if ([string]$doorCheck.result.Name -ne $doorSpec.name) { throw "Native BOOTH-DOOR identity check failed." }

    $windowCheck = Invoke-Jemi -Method "Entity.GetAttribute" -Params ([ordered]@{
        Select = [ordered]@{ IfcWindow = [ordered]@{ GlobalId = $windowSpec.global_id } }
        Attribute = "Name"
    })
    if ([string]$windowCheck.result.Name -ne $windowSpec.name) { throw "Native HIGH-VENT-WINDOW identity check failed." }

    $saveReply = Invoke-Jemi -Method "Model.SaveFile" -Params ([ordered]@{ location = $stage1Path })
    if ($null -ne $saveReply.result) { throw "Model.SaveFile returned unexpected non-null result." }
    if (-not (Test-Path -LiteralPath $stage1Path -PathType Leaf) -or (Get-Item -LiteralPath $stage1Path).Length -le 0) {
        throw "Model.SaveFile did not produce stage1.ifc."
    }
    $nativeStageCompleted = [DateTimeOffset]::UtcNow.ToString("o")

    if ($rpcTranscript.Count -ne 12) { throw "Task-05 replay must contain exactly 12 native JEMI transactions, found $($rpcTranscript.Count)." }
    $expectedMethods = @("Model.LoadFile", "Entity.Modify", "Entity.Modify", "Entity.Modify", "Entity.Modify", "Entity.Create", "Entity.Create", "Entity.GetAttribute", "Entity.Modify", "Entity.GetAttribute", "Entity.GetAttribute", "Model.SaveFile")
    $actualMethods = @($rpcTranscript | ForEach-Object { [string]$_.request.method })
    if (($actualMethods -join "|") -ne ($expectedMethods -join "|")) { throw "Task-05 native transaction sequence mismatch." }

    $initText = Get-Content -LiteralPath $initPath -Raw
    $stage1Text = Get-Content -LiteralPath $stage1Path -Raw
    if ($stage1Text -notmatch "The EXPRESS Data Manager") { throw "stage1.ifc lacks Archicad EDM export evidence." }
    if ($stage1Text -notmatch "(?im)^\s*#\d+\s*=\s*IFCSIUNIT\s*\(\s*\*\s*,\s*\.LENGTHUNIT\.\s*,\s*\$\s*,\s*\.METRE\.\s*\)") {
        throw "Task-05 stage1.ifc does not declare metre SI length units."
    }
    $statements = Get-IfcStatementMap $stage1Text

    $spaceRows = New-Object System.Collections.Generic.List[object]
    for ($spaceIndex = 0; $spaceIndex -lt $spaceSpecs.Count; $spaceIndex++) {
        $space = $spaceSpecs[$spaceIndex]
        $spaceRef = Get-IfcEntityReferenceByGlobalId -Statements $statements -GlobalId $space.global_id -EntityClass "IFCSPACE"
        $spaceBody = [string]$statements[$spaceRef]
        if ($spaceBody -notmatch [regex]::Escape("'$($space.target_name)'") -or $spaceBody -notmatch [regex]::Escape("'$($space.zone)'")) {
            throw "Saved stage1.ifc target name/zone mismatch for $($space.target_name)."
        }
        $area = Get-IfcSpaceNetFloorArea -Statements $statements -SpaceGlobalId $space.global_id
        if ([math]::Abs($area - [double]$space.expected_area_m2) -gt 0.000001) {
            throw "Saved stage1.ifc NetFloorArea mismatch for $($space.target_name): $area vs $($space.expected_area_m2)."
        }
        $nativeSpaceReference = [string]$rpcTranscript[$spaceIndex + 1].response.result
        [void]$spaceRows.Add([ordered]@{
            name = $space.target_name
            ifc_global_id = $space.global_id
            thermal_zone = $space.zone
            floor_area_m2 = $area
            door_count = [int]$space.door_count
            window_count = [int]$space.window_count
            native_entity_reference = $nativeSpaceReference
        })
    }

    $doorSavedRef = Get-IfcEntityReferenceByGlobalId -Statements $statements -GlobalId $doorSpec.global_id -EntityClass "IFCDOOR"
    $windowSavedRef = Get-IfcEntityReferenceByGlobalId -Statements $statements -GlobalId $windowSpec.global_id -EntityClass "IFCWINDOW"
    $containmentSavedRef = Get-IfcEntityReferenceByGlobalId -Statements $statements -GlobalId $containmentGlobalId -EntityClass "IFCRELCONTAINEDINSPATIALSTRUCTURE"
    $containmentBody = [string]$statements[$containmentSavedRef]
    if ($containmentBody -notmatch "#$doorSavedRef(?:\D|$)" -or $containmentBody -notmatch "#$windowSavedRef(?:\D|$)") {
        throw "Saved stage1.ifc does not contain both new openings in the target storey relationship."
    }

    $initRootIds = @(Get-IfcRootGlobalIds $initText)
    $stageRootIds = @(Get-IfcRootGlobalIds $stage1Text)
    $initSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $stageSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($id in $initRootIds) { [void]$initSet.Add([string]$id) }
    foreach ($id in $stageRootIds) { [void]$stageSet.Add([string]$id) }
    $lostIds = @($initSet | Where-Object { -not $stageSet.Contains([string]$_) })
    $addedIds = @($stageSet | Where-Object { -not $initSet.Contains([string]$_) } | Sort-Object)
    $expectedAddedIds = @($doorSpec.global_id, $windowSpec.global_id) | Sort-Object
    if ($lostIds.Count -ne 0 -or ($addedIds -join "|") -ne ($expectedAddedIds -join "|")) {
        throw "IfcRoot preservation failed. Lost=$($lostIds -join ','); added=$($addedIds -join ',')."
    }

    $ifcClassLabels = [ordered]@{
        IFCPROJECT = "IfcProject"
        IFCSITE = "IfcSite"
        IFCBUILDING = "IfcBuilding"
        IFCBUILDINGSTOREY = "IfcBuildingStorey"
        IFCSPACE = "IfcSpace"
        IFCWALL = "IfcWall"
        IFCSLAB = "IfcSlab"
        IFCROOF = "IfcRoof"
        IFCDOOR = "IfcDoor"
        IFCWINDOW = "IfcWindow"
        IFCOPENINGELEMENT = "IfcOpeningElement"
    }
    $bimCounts = [ordered]@{}
    foreach ($entityClass in $ifcClassLabels.Keys) {
        $label = $ifcClassLabels[$entityClass]
        $bimCounts[$label] = Get-IfcEntityCount -Text $stage1Text -EntityClass $entityClass
    }
    $expectedCounts = [ordered]@{ IfcProject=1; IfcSite=1; IfcBuilding=1; IfcBuildingStorey=1; IfcSpace=5; IfcWall=0; IfcSlab=1; IfcRoof=2; IfcDoor=1; IfcWindow=1; IfcOpeningElement=0 }
    foreach ($entry in $expectedCounts.GetEnumerator()) {
        if ([int]$bimCounts[$entry.Key] -ne [int]$entry.Value) {
            throw "Saved stage1.ifc count mismatch for $($entry.Key): $($bimCounts[$entry.Key]) vs $($entry.Value)."
        }
    }

    $stage1Sha256 = Get-Sha256 $stage1Path
    $initSha256 = Get-Sha256 $initPath
    $buildingArea = 0.0
    foreach ($spaceRow in $spaceRows) {
        $buildingArea += [double]$spaceRow.floor_area_m2
    }
    $buildingArea = [math]::Round($buildingArea, 6)
    if ([math]::Abs($buildingArea - 124.0) -gt 0.000001) { throw "Task-05 target-space area sum must be 124.0 m2, found $buildingArea." }

    $handoff = [ordered]@{
        schema = "engiworld.archicad-handoff.v2"
        case_id = $caseId
        software_stage = "archicad"
        authoring_software = "Graphisoft Archicad 27 $((Get-Item -LiteralPath $commandServer).VersionInfo.ProductVersion) IFCCommandServerApp"
        native_cli_executable = $commandServer
        source_file = "stage1.ifc"
        source_sha256 = $stage1Sha256
        source_init_sha256 = $initSha256
        source_stage1_sha256 = $stage1Sha256
        revision_code = $revision
        handoff_tokens = @("FINISHING-BOOTH-EXHAUST", "HIGH-OUTDOOR-AIR", "STUDIO-HIGH-DAYLIGHT", "SEPARATE-BOOTH-ZONE")
        spaces = $spaceRows.ToArray()
        thermal_zones = @($spaceRows | ForEach-Object { $_.thermal_zone })
        building_area_m2 = $buildingArea
        bim_counts = $bimCounts
        door_count = 1
        window_count = 1
        opening_records = @(
            [ordered]@{ type="IfcDoor"; name=$doorSpec.name; global_id=$doorSpec.global_id; native_entity_reference=$doorRef; overall_height_m=$doorSpec.height; overall_width_m=$doorSpec.width },
            [ordered]@{ type="IfcWindow"; name=$windowSpec.name; global_id=$windowSpec.global_id; native_entity_reference=$windowRef; overall_height_m=$windowSpec.height; overall_width_m=$windowSpec.width }
        )
        quantity_evidence = @($spaceRows | ForEach-Object { [ordered]@{ name=$_.name; global_id=$_.ifc_global_id; source="stage1.ifc/Qto_SpaceBaseQuantities/NetFloorArea"; area_m2=$_.floor_area_m2 } })
        archicad_api_commands = @($rpcTranscript | ForEach-Object { $_.request })
        generated_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    }
    Write-JsonUtf8NoBom -Path $handoffPath -Value $handoff

    $headerMatch = [regex]::Match($stage1Text.Substring(0, [math]::Min(2000, $stage1Text.Length)), "The EXPRESS Data Manager[^']+")
    if (-not $headerMatch.Success) { throw "Unable to capture Archicad EDM header preprocessor." }
    $serverVersion = (Get-Item -LiteralPath $commandServer).VersionInfo
    $nativeLog = [ordered]@{
        schema = "engiworld-archicad-ifc-command-server-native-log-v2"
        case_id = $caseId
        software_stage = "archicad"
        native_stage_started_at_utc = $nativeStageStarted
        native_stage_completed_at_utc = $nativeStageCompleted
        command_server_process = [ordered]@{
            pid = [int]$serverProcess.Id
            executable_path = $commandServer
            command_line = $actualCommandLine
            creation_time = $processCreationUtc
            product_version = $serverVersion.ProductVersion
            file_version = $serverVersion.FileVersion
            executable_sha256 = Get-Sha256 $commandServer
            listening_port = $Port
            listening = $true
        }
        task_database = [ordered]@{ path=$databaseFullPath; database_name=$ModelName }
        artifacts = [ordered]@{
            "init.ifc" = [ordered]@{ sha256=$initSha256; size=(Get-Item -LiteralPath $initPath).Length }
            "stage1.ifc" = [ordered]@{ sha256=$stage1Sha256; size=(Get-Item -LiteralPath $stage1Path).Length; header_preprocessor=$headerMatch.Value }
            "handoff.json" = [ordered]@{ sha256=(Get-Sha256 $handoffPath); size=(Get-Item -LiteralPath $handoffPath).Length }
        }
        preservation_evidence = [ordered]@{
            seed_root_global_ids_preserved = $true
            seed_root_global_id_count = $initSet.Count
            output_root_global_id_count = $stageSet.Count
            added_global_ids = $addedIds
            output_counts = $bimCounts
            target_area_m2 = [ordered]@{ "MAIN-STUDIO"=96.0; "STORAGE"=16.0; "FINISHING-BOOTH"=12.0 }
            target_area_source = "native Archicad stage1.ifc Qto_SpaceBaseQuantities/NetFloorArea"
        }
        native_transactions = [ordered]@{ Items=$rpcTranscript.ToArray(); Count=$rpcTranscript.Count }
        archicad_api_commands = @($rpcTranscript | ForEach-Object { $_.request })
        generated_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    }
    Write-JsonUtf8NoBom -Path $nativeLogPath -Value $nativeLog

    Write-Output ([ordered]@{
        case_id = $caseId
        stage1_ifc = $stage1Path
        stage1_sha256 = $stage1Sha256
        handoff = $handoffPath
        handoff_sha256 = Get-Sha256 $handoffPath
        native_stage_log = $nativeLogPath
        native_stage_log_sha256 = Get-Sha256 $nativeLogPath
        native_transaction_count = $rpcTranscript.Count
        areas_m2 = [ordered]@{ "MAIN-STUDIO"=96.0; "STORAGE"=16.0; "FINISHING-BOOTH"=12.0 }
    } | ConvertTo-Json -Depth 10)
}
finally {
    if ($null -ne $serverProcess -and -not $serverProcess.HasExited) {
        try {
            Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$baseUrl/SHUTDOWN" -TimeoutSec 3 | Out-Null
            [void]$serverProcess.WaitForExit(3000)
        }
        catch {
        }
        if (-not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
        }
    }
    if ($databaseCreated -and -not $KeepDatabase -and (Test-Path -LiteralPath $databaseFullPath)) {
        $verifiedCleanupPath = [System.IO.Path]::GetFullPath($databaseFullPath).TrimEnd('\')
        if (-not $verifiedCleanupPath.StartsWith("C:\EW05-CODEX-", [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing cleanup outside the dedicated Task-05 database namespace: $verifiedCleanupPath"
        }
        Remove-Item -LiteralPath $verifiedCleanupPath -Recurse -Force
    }
}
