$ErrorActionPreference = "Stop"
$desktop = "C:\Users\user\Desktop"
$documents = "C:\Users\user\Documents"
$openstudio = "C:\openstudio-3.10.0\bin\openstudio.exe"
$energyplus = "C:\openstudio-3.10.0\EnergyPlus\energyplus.exe"

function Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$archStarted = [DateTimeOffset]::UtcNow.ToString("o")
$archProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$documents\ew10-archicad.ps1") -PassThru
$observed = $null
$health = $null
$jemiProbe = $null
$portSample = $null
for ($i = 0; $i -lt 300 -and -not $archProcess.HasExited; $i++) {
    Start-Sleep -Milliseconds 100
    $candidate = Get-CimInstance Win32_Process -Filter "Name='IFCCommandServerApp.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match '(^|\s)--p(?:ort)?\s+12347(\s|$)' -and $_.CommandLine -match 'C:\\EW10' } |
        Select-Object -First 1
    if ($candidate -and -not $observed) {
        $observed = [ordered]@{
            sampled_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
            pid = [int]$candidate.ProcessId
            parent_pid = [int]$candidate.ParentProcessId
            executable_path = $candidate.ExecutablePath
            command_line = $candidate.CommandLine
            creation_time_utc = $candidate.CreationDate.ToUniversalTime().ToString("o")
            executable_sha256 = Sha256 $candidate.ExecutablePath
        }
    }
    if ($observed -and -not $portSample) {
        $tcp = Get-NetTCPConnection -LocalPort 12347 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -eq $observed.pid } | Select-Object -First 1
        if ($tcp) {
            $portSample = [ordered]@{sampled_at_utc=[DateTimeOffset]::UtcNow.ToString("o");local_address=$tcp.LocalAddress;local_port=[int]$tcp.LocalPort;state=$tcp.State.ToString();owning_pid=[int]$tcp.OwningProcess}
            try {
                $reply = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:12347/HEALTH" -Method Get -TimeoutSec 5
                $health = [ordered]@{sampled_at_utc=[DateTimeOffset]::UtcNow.ToString("o");endpoint="http://127.0.0.1:12347/HEALTH";status_code=[int]$reply.StatusCode;body=[string]$reply.Content}
            } catch {
                $health = [ordered]@{sampled_at_utc=[DateTimeOffset]::UtcNow.ToString("o");endpoint="http://127.0.0.1:12347/HEALTH";status_code=[int]$_.Exception.Response.StatusCode.value__;body=[string]$_.ErrorDetails.Message}
            }
            try {
                $probeBody = '{"method":"__EW10_OBSERVER_PROBE__","params":{}}'
                $probeReply = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:12347/JEMI" -Method Post -ContentType "application/json" -Body $probeBody -TimeoutSec 5
                $probeContent = if ($probeReply.Content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($probeReply.Content) } else { [string]$probeReply.Content }
                $jemiProbe = [ordered]@{sampled_at_utc=[DateTimeOffset]::UtcNow.ToString("o");endpoint="http://127.0.0.1:12347/JEMI";request_json=$probeBody;status_code=[int]$probeReply.StatusCode;body=$probeContent}
            } catch {
                $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode.value__ } else { -1 }
                $jemiProbe = [ordered]@{sampled_at_utc=[DateTimeOffset]::UtcNow.ToString("o");endpoint="http://127.0.0.1:12347/JEMI";request_json=$probeBody;status_code=$status;body=[string]$_.ErrorDetails.Message}
            }
        }
    }
}
$archProcess.WaitForExit()
$archExited = [DateTimeOffset]::UtcNow.ToString("o")
if ($archProcess.ExitCode -ne 0) { throw "Archicad stage failed: $($archProcess.ExitCode)" }
if (-not $observed -or -not $portSample -or -not $health -or $health.status_code -ne 200 -or -not $jemiProbe -or $jemiProbe.status_code -ne 200) { throw "Archicad process/port/endpoint evidence incomplete" }
$nativeLog = Get-Content -LiteralPath "$desktop\native_stage_log.json" -Raw | ConvertFrom-Json
$journal = [ordered]@{
    schema = "engiworld.archicad-process-journal.v1"
    observer = "formal-runner"
    runner_pid = $PID
    archicad_stage_process_pid = $archProcess.Id
    observer_started_at_utc = $archStarted
    observer_completed_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    server_process = $observed
    tcp_listener = $portSample
    health_probe = $health
    jemi_probe = $jemiProbe
    first_jemi_request_at_utc = $nativeLog.native_transactions.Items[0].started_at_utc
    last_jemi_response_at_utc = $nativeLog.native_transactions.Items[-1].completed_at_utc
    server_exit_observed_at_utc = $archExited
    server_running_after_stage = [bool](Get-Process -Id $observed.pid -ErrorAction SilentlyContinue)
    port_listening_after_stage = [bool](Get-NetTCPConnection -LocalPort 12347 -State Listen -ErrorAction SilentlyContinue)
    native_stage_log_sha256 = Sha256 "$desktop\native_stage_log.json"
    stage1 = [ordered]@{sha256=Sha256 "$desktop\stage1.ifc";last_write_time_utc=(Get-Item "$desktop\stage1.ifc").LastWriteTimeUtc.ToString("o")}
    handoff = [ordered]@{sha256=Sha256 "$desktop\handoff.json";last_write_time_utc=(Get-Item "$desktop\handoff.json").LastWriteTimeUtc.ToString("o")}
}
$journal | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath "$desktop\archicad_process_journal.json" -Encoding utf8

& $openstudio "$documents\ew10-build.rb"
if ($LASTEXITCODE -ne 0) { throw "OpenStudio build failed: $LASTEXITCODE" }

$started = [DateTimeOffset]::UtcNow.ToString("o")
$process = Start-Process -FilePath $openstudio -ArgumentList @("run", "-w", "$desktop\workflow.osw") -WorkingDirectory $desktop -PassThru -Wait
$exited = [DateTimeOffset]::UtcNow.ToString("o")
if ($process.ExitCode -ne 0) { throw "OpenStudio simulation failed: $($process.ExitCode)" }
$samples = @()
foreach ($sample in 1..2) {
    Start-Sleep -Seconds 2
    $samples += [ordered]@{
        sampled_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
        sql_size = (Get-Item "$desktop\run\eplusout.sql").Length
        err_size = (Get-Item "$desktop\run\eplusout.err").Length
        end_size = (Get-Item "$desktop\run\eplusout.end").Length
        sql_sha256 = Sha256 "$desktop\run\eplusout.sql"
        err_sha256 = Sha256 "$desktop\run\eplusout.err"
        end_sha256 = Sha256 "$desktop\run\eplusout.end"
    }
}
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
    openstudio_process_exited_at_utc = $exited
    completed_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    exit_code = $process.ExitCode
    result_osm_sha256 = Sha256 "$desktop\result.osm"
    idf_sha256 = Sha256 "$desktop\in.idf"
    workflow_sha256 = Sha256 "$desktop\workflow.osw"
    weather_sha256 = Sha256 "$desktop\weather.epw"
    sql_sha256 = Sha256 "$desktop\run\eplusout.sql"
    err_sha256 = Sha256 "$desktop\run\eplusout.err"
    end_sha256 = Sha256 "$desktop\run\eplusout.end"
    stable_file_samples = $samples
}
$transaction | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath "$desktop\openstudio_simulation_transaction.json" -Encoding utf8

& $openstudio "$documents\ew10-post.rb"
if ($LASTEXITCODE -ne 0) { throw "OpenStudio postprocess failed: $LASTEXITCODE" }
Write-Output "EW10 task completed"
