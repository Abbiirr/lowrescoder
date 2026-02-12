<#
.SYNOPSIS
    Run the HybridCoder E2E benchmark and validate results.

.DESCRIPTION
    Drives HybridCoder's AgentLoop to create a React calculator app,
    then validates: npm install, npm build, and scoring rubric.
    Exits 0 on pass, 1 on fail.

.PARAMETER MinScore
    Minimum acceptable score (0-100). Default: 30.

.EXAMPLE
    .\scripts\run_e2e_benchmark.ps1
    .\scripts\run_e2e_benchmark.ps1 -MinScore 50
#>

param(
    [int]$MinScore = 30
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " HybridCoder E2E Benchmark Runner"       -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Min score: $MinScore"
Write-Host "Project root: $ProjectRoot"
Write-Host ""

# --- Step 1: Validate .env ---
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "FAIL: .env file not found at $envFile" -ForegroundColor Red
    exit 1
}

# --- Step 2: Clean old sandboxes ---
$sandboxDir = Join-Path $ProjectRoot "sandboxes"
if (Test-Path $sandboxDir) {
    Write-Host "Cleaning old benchmark sandboxes..."
    Get-ChildItem -Path $sandboxDir -Directory -Filter "bench_*" | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# --- Step 3: Run the benchmark ---
Write-Host ""
Write-Host "Running benchmark..." -ForegroundColor Yellow
$startTime = Get-Date

$proc = Start-Process -FilePath "uv" `
    -ArgumentList "run", "python", "scripts/run_calculator_benchmark.py" `
    -WorkingDirectory $ProjectRoot `
    -NoNewWindow -PassThru -Wait

$duration = (Get-Date) - $startTime
Write-Host ""
Write-Host "Duration: $([math]::Round($duration.TotalMinutes, 1)) minutes"

if ($proc.ExitCode -ne 0) {
    Write-Host "FAIL: Benchmark script exited with code $($proc.ExitCode)" -ForegroundColor Red
    exit 1
}

# --- Step 4: Find the sandbox and results ---
$benchDirs = Get-ChildItem -Path $sandboxDir -Directory -Filter "bench_*" | Sort-Object Name -Descending
if ($benchDirs.Count -eq 0) {
    Write-Host "FAIL: No benchmark sandbox found" -ForegroundColor Red
    exit 1
}
$latestSandbox = $benchDirs[0].FullName
$jsonFile = Join-Path $latestSandbox ".hybridcoder-benchmark.json"

if (-not (Test-Path $jsonFile)) {
    Write-Host "FAIL: Results JSON not found at $jsonFile" -ForegroundColor Red
    exit 1
}

# --- Step 5: Parse and validate results ---
$results = Get-Content $jsonFile -Raw | ConvertFrom-Json
$totalScore = $results.scores.total

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " RESULTS"                                  -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Provider: $($results.provider)"
Write-Host "  Model:    $($results.model)"
Write-Host "  Score:    $totalScore / 100"
Write-Host ""
Write-Host "  Scaffold:   $($results.scores.scaffold) / 15"
Write-Host "  Regular:    $($results.scores.regular) / 10"
Write-Host "  Scientific: $($results.scores.scientific) / 15"
Write-Host "  Currency:   $($results.scores.currency) / 15"
Write-Host "  Unit:       $($results.scores.unit) / 10"
Write-Host "  Quality:    $($results.scores.quality) / 10"
Write-Host "  UI:         $($results.scores.ui) / 25"
Write-Host ""

# Check npm results
$npmInstall = $results.npm.install.success
$npmBuild = $results.npm.build.success
Write-Host "  npm install: $(if ($npmInstall) { 'PASS' } else { 'FAIL' })"
Write-Host "  npm build:   $(if ($npmBuild) { 'PASS' } else { 'FAIL' })"
Write-Host ""

# --- Step 6: Pass/Fail ---
$passed = $true
$failures = @()

if ($totalScore -lt $MinScore) {
    $passed = $false
    $failures += "Score $totalScore < minimum $MinScore"
}

if (-not $npmInstall) {
    $failures += "npm install failed"
}

if (-not $npmBuild) {
    $failures += "npm build failed"
}

if ($passed -and $failures.Count -eq 0) {
    Write-Host "PASS - Score $totalScore >= $MinScore" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAIL:" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
