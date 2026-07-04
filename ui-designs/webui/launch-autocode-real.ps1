# AutoCode launcher — REAL harness.
# Starts the real AutoCode backend (autocode serve --transport tcp) + the WS<->TCP
# bridge, opens the UI in a chromeless app window, and tears both down on close.
# Configure the backend in harness.config.ps1. See REAL-HARNESS.md.
#
# This does NOT fall back to the demo/mock — if the backend isn't configured or won't
# start, it shows a dialog explaining what to do.

$ErrorActionPreference = 'Stop'
$webui = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Error($msg) {
    try { (New-Object -ComObject WScript.Shell).Popup($msg, 0, 'AutoCode', 0x10) | Out-Null } catch {}
}
function Resolve-Uv {
    $c = Get-Command uv -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in @("$env:USERPROFILE\.local\bin\uv.exe", "$env:LOCALAPPDATA\Programs\uv\uv.exe")) {
        if (Test-Path $p) { return $p }
    }
    return $null
}
function Find-Browser {
    foreach ($b in @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )) { if (Test-Path $b) { return $b } }
    return $null
}
function Test-Port($h, $p) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect($h, $p); $c.Close(); return $true }
    catch { return $false }
}
function Kill-Tree($proc) {
    if ($proc -and -not $proc.HasExited) {
        Start-Process taskkill -ArgumentList @('/F','/T','/PID',$proc.Id) -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
    }
}

# --- config ---
$cfgPath = Join-Path $webui 'harness.config.ps1'
if (-not (Test-Path $cfgPath)) { Show-Error "Missing harness.config.ps1 in`n$webui`n`nSee REAL-HARNESS.md."; exit 1 }
. $cfgPath
$H = $Harness
$uv = Resolve-Uv
if (-not $uv) { Show-Error "uv was not found on PATH.`nInstall uv, then edit harness.config.ps1."; exit 1 }
if (-not $H.BackendCwd -or -not (Test-Path $H.BackendCwd)) {
    Show-Error "The real AutoCode backend is not configured.`n`nEdit:`n$cfgPath`n`nSet BackendCwd to your autocode repo (where 'uv run autocode serve' works), then relaunch.`n`nDetails: $webui\REAL-HARNESS.md"
    exit 1
}

$port = [int]$H.BackendPort
$backend = $null; $bridge = $null
try {
    # --- start the real backend ---
    $bArgs = $H.BackendArgs -replace '\{PORT\}', "$port"
    $backend = Start-Process -FilePath $H.BackendExe -ArgumentList $bArgs -WorkingDirectory $H.BackendCwd -WindowStyle Hidden -PassThru

    $deadline = (Get-Date).AddSeconds([int]$H.StartupTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ($backend.HasExited) { Show-Error "The backend exited on startup.`nCommand: $($H.BackendExe) $bArgs`nCwd: $($H.BackendCwd)`n`nRun it manually to see the error. See REAL-HARNESS.md."; exit 1 }
        if (Test-Port '127.0.0.1' $port) { break }
        Start-Sleep -Milliseconds 400
    }
    if (-not (Test-Port '127.0.0.1' $port)) { Show-Error "Backend did not open tcp://127.0.0.1:$port within $($H.StartupTimeoutSec)s.`nCheck harness.config.ps1 (port may be reserved) and REAL-HARNESS.md."; Kill-Tree $backend; exit 1 }

    # --- start the WS<->TCP bridge (serves the UI too) ---
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName  = $uv
    $psi.Arguments = 'run --no-project "{0}\ws-bridge.py" --backend-port {1} --framing {2} --max-seconds 86400' -f $webui, $port, $H.Framing
    $psi.WorkingDirectory = $webui
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    $bridge = [System.Diagnostics.Process]::Start($psi)

    $url = $null; $bd = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $bd -and -not $bridge.HasExited) {
        $line = $bridge.StandardOutput.ReadLine()
        if ($null -eq $line) { break }
        if ($line -match '^UI_URL\s+(\S+)') { $url = $Matches[1]; break }
    }
    if (-not $url) { Show-Error "The bridge failed to start. See REAL-HARNESS.md."; Kill-Tree $bridge; Kill-Tree $backend; exit 1 }
    [void]$bridge.StandardOutput.ReadToEndAsync()
    [void]$bridge.StandardError.ReadToEndAsync()

    # --- open the app ---
    $browser = Find-Browser
    if ($browser) {
        $profileDir = Join-Path $env:LOCALAPPDATA 'AutoCodeApp'
        $app = Start-Process -FilePath $browser -ArgumentList @("--app=$url", "--user-data-dir=$profileDir", "--no-first-run", "--no-default-browser-check") -PassThru
        $app.WaitForExit()
    } else {
        Start-Process $url
        while (-not $bridge.HasExited -and -not $backend.HasExited) { Start-Sleep -Seconds 2 }
    }
}
finally {
    Kill-Tree $bridge
    Kill-Tree $backend
}
