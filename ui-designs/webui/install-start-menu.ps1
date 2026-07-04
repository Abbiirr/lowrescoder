# Installs "AutoCode" as a Start Menu app (and optionally a Desktop shortcut).
# Generates an icon, then creates a shortcut that runs the launcher hidden.
#   Install (REAL harness, default): powershell -NoProfile -ExecutionPolicy Bypass -File install-start-menu.ps1
#   Install (dev demo / mock):       ... install-start-menu.ps1 -Mock
#   Desktop shortcut too:            ... -Desktop
#   Uninstall:                       ... -Uninstall
#
# Default targets the REAL harness (launch-autocode-real.ps1). Configure the backend
# in harness.config.ps1 first (see REAL-HARNESS.md). Use -Mock only for the offline
# demo backend.
param([switch]$Mock, [switch]$Desktop, [switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$webui   = Split-Path -Parent $MyInvocation.MyCommand.Path
$launch  = Join-Path $webui ($(if ($Mock) { 'launch-autocode.ps1' } else { 'launch-autocode-real.ps1' }))
$icoPath = Join-Path $webui 'autocode.ico'

$startDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$lnkPath  = Join-Path $startDir 'AutoCode.lnk'
$deskLnk  = Join-Path ([Environment]::GetFolderPath('Desktop')) 'AutoCode.lnk'

if ($Uninstall) {
    foreach ($p in @($lnkPath, $deskLnk, $icoPath)) {
        if (Test-Path $p) { Remove-Item $p -Force; Write-Host "removed $p" }
    }
    Write-Host "AutoCode uninstalled."
    return
}

# --- 1. draw a 256x256 icon and wrap the PNG into an .ico container ---
Add-Type -AssemblyName System.Drawing
$sz  = 256
$bmp = New-Object System.Drawing.Bitmap $sz, $sz
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode     = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

function New-RoundRect([int]$x,[int]$y,[int]$w,[int]$h,[int]$r) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = $r * 2
    $p.AddArc($x, $y, $d, $d, 180, 90)
    $p.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $p.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $p.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $p.CloseFigure()
    return $p
}

$bg   = New-RoundRect 8 8 240 240 48
$g.FillPath((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,18,21,29))), $bg)
$pen  = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(60,255,255,255)), 2
$g.DrawPath($pen, $bg)

# three window dots
$dots = @(
    @{ x=66;  c=[System.Drawing.Color]::FromArgb(255,255,95,87) },
    @{ x=104; c=[System.Drawing.Color]::FromArgb(255,254,188,46) },
    @{ x=142; c=[System.Drawing.Color]::FromArgb(255,40,200,64) }
)
foreach ($d in $dots) {
    $g.FillEllipse((New-Object System.Drawing.SolidBrush $d.c), $d.x, 60, 20, 20)
}

# "AC" wordmark in accent blue
$accent = [System.Drawing.Color]::FromArgb(255,101,141,255)
$font   = New-Object System.Drawing.Font 'Consolas', 96, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fmt    = New-Object System.Drawing.StringFormat
$fmt.Alignment     = [System.Drawing.StringAlignment]::Center
$fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
$rect   = New-Object System.Drawing.RectangleF 8, 96, 240, 150
$g.DrawString('AC', $font, (New-Object System.Drawing.SolidBrush $accent), $rect, $fmt)
$g.Dispose()

# PNG -> ICO (Vista+ icons may embed a PNG directly)
$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$png = $ms.ToArray(); $ms.Dispose(); $bmp.Dispose()

$ico = New-Object System.IO.MemoryStream
$bw  = New-Object System.IO.BinaryWriter $ico
$bw.Write([UInt16]0); $bw.Write([UInt16]1); $bw.Write([UInt16]1)      # ICONDIR
$bw.Write([Byte]0); $bw.Write([Byte]0)                                # 0 => 256px
$bw.Write([Byte]0); $bw.Write([Byte]0)
$bw.Write([UInt16]1); $bw.Write([UInt16]32)                           # planes, bpp
$bw.Write([UInt32]$png.Length)
$bw.Write([UInt32]22)                                                 # offset (6+16)
$bw.Write($png)
$bw.Flush()
[System.IO.File]::WriteAllBytes($icoPath, $ico.ToArray())
$ico.Dispose()
Write-Host "icon  -> $icoPath"

# --- 2. create the shortcut(s) ---
function New-Shortcut([string]$path) {
    $sh = New-Object -ComObject WScript.Shell
    $s  = $sh.CreateShortcut($path)
    $s.TargetPath       = (Join-Path $PSHOME 'powershell.exe')
    $s.Arguments        = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $launch
    $s.WorkingDirectory = $webui
    $s.IconLocation     = "$icoPath,0"
    $s.WindowStyle      = 7  # minimized (the launcher itself is hidden)
    $s.Description      = 'AutoCode — local AI coding IDE (WebUI)'
    $s.Save()
}

if (-not (Test-Path $startDir)) { New-Item -ItemType Directory -Path $startDir -Force | Out-Null }
New-Shortcut $lnkPath
Write-Host ("shortcut -> {0}  (target: {1})" -f $lnkPath, (Split-Path -Leaf $launch))
if ($Desktop) { New-Shortcut $deskLnk; Write-Host "shortcut -> $deskLnk" }

Write-Host ""
if ($Mock) {
    Write-Host "Installed (DEV DEMO / mock backend). Press Start and type 'AutoCode'."
} else {
    Write-Host "Installed (REAL harness). Configure the backend in harness.config.ps1 first,"
    Write-Host "then press Start and type 'AutoCode'.  Guide: $webui\REAL-HARNESS.md"
}
Write-Host "Uninstall with:  powershell -NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`" -Uninstall"
