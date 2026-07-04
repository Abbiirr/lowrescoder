# AutoCode WebUI launcher.
# Starts the local harness (mock-server.py), opens the UI in a chromeless browser
# app window, and shuts the server down when that window is closed.
# Invoked by the Start Menu shortcut created by install-start-menu.ps1.

$ErrorActionPreference = 'Stop'
$webui = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-Uv {
    $c = Get-Command uv -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in @("$env:USERPROFILE\.local\bin\uv.exe", "$env:LOCALAPPDATA\Programs\uv\uv.exe")) {
        if (Test-Path $p) { return $p }
    }
    throw "uv was not found on PATH. Install uv, or run the demo build directly (index.html?demo=1)."
}

function Find-Browser {
    $cands = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($b in $cands) { if (Test-Path $b) { return $b } }
    return $null
}

# --- start the harness, capturing stdout so we can read the real URL/port ---
$uv = Resolve-Uv
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $uv
$psi.Arguments = 'run --no-project "{0}\mock-server.py" --port 8901 --max-seconds 86400' -f $webui
$psi.WorkingDirectory = $webui
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$server = [System.Diagnostics.Process]::Start($psi)

try {
    # Read stdout until the server reports its actual URL (it may fall back to an
    # ephemeral port if the requested one is reserved by Windows).
    $url = $null
    $deadline = (Get-Date).AddSeconds(40)
    while ((Get-Date) -lt $deadline -and -not $server.HasExited) {
        $line = $server.StandardOutput.ReadLine()
        if ($null -eq $line) { break }
        if ($line -match '^UI_URL\s+(\S+)') { $url = $Matches[1]; break }
    }
    if (-not $url) { throw "Harness did not start (no UI_URL). Check: uv run --no-project webui/mock-server.py" }

    # Drain the pipes in the background so the server never blocks on a full buffer.
    [void]$server.StandardOutput.ReadToEndAsync()
    [void]$server.StandardError.ReadToEndAsync()

    $browser = Find-Browser
    if ($browser) {
        # App mode + a dedicated profile dir => a distinct, waitable window process.
        $profileDir = Join-Path $env:LOCALAPPDATA 'AutoCodeApp'
        $args = @("--app=$url", "--user-data-dir=$profileDir", "--no-first-run", "--no-default-browser-check")
        $app = Start-Process -FilePath $browser -ArgumentList $args -PassThru
        $app.WaitForExit()
    } else {
        # No Chromium browser found: open the default browser and keep the server up
        # until this launcher is closed.
        Start-Process $url
        while (-not $server.HasExited) { Start-Sleep -Seconds 2 }
    }
}
finally {
    if ($server -and -not $server.HasExited) {
        # Tree-kill: killing uv alone would orphan its python child on Windows.
        Start-Process -FilePath 'taskkill' -ArgumentList @('/F', '/T', '/PID', $server.Id) -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
    }
}
