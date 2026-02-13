<#
.SYNOPSIS
    Run the HybridCoder E2E benchmark and validate results.

.DESCRIPTION
    Drives HybridCoder's AgentLoop to create a React calculator app,
    then validates: npm install, npm build, and scoring rubric.
    Exits 0 on pass, 1 on fail, 2 on infra failure.

.PARAMETER MinScore
    Minimum acceptable score (0-100). Default: 30.

.PARAMETER Strict
    Enable strict mode (higher thresholds, enforced budgets).

.PARAMETER Runs
    Number of benchmark runs. Default: 1.

.PARAMETER Replay
    Path to an existing sandbox directory to re-score.

.PARAMETER ScoreOnly
    In replay mode, skip npm validation and only re-score.

.PARAMETER Scenario
    Name of the E2E scenario to run (default: calculator).

.EXAMPLE
    .\scripts\run_e2e_benchmark.ps1
    .\scripts\run_e2e_benchmark.ps1 -MinScore 50
    .\scripts\run_e2e_benchmark.ps1 -Strict
    .\scripts\run_e2e_benchmark.ps1 -Replay .\sandboxes\bench_20260212_203313
    .\scripts\run_e2e_benchmark.ps1 -Runs 3
#>

param(
    [int]$MinScore = 30,
    [switch]$Strict,
    [int]$Runs = 1,
    [string]$Replay = "",
    [switch]$ScoreOnly,
    [string]$Scenario = "calculator"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " HybridCoder E2E Benchmark Runner"       -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Min score: $MinScore"
Write-Host "Project root: $ProjectRoot"
if ($Strict) { Write-Host "Mode: STRICT" -ForegroundColor Yellow }
if ($Runs -gt 1) { Write-Host "Runs: $Runs" }
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
Write-Host "Scenario: $Scenario" -ForegroundColor Cyan
Write-Host "Running benchmark..." -ForegroundColor Yellow
$startTime = Get-Date

if ($Scenario -ne "calculator") {
    # Non-calculator scenarios: dispatch to generic scenario runner
    Write-Host "Dispatching to generic scenario runner for: $Scenario" -ForegroundColor Cyan
    $argList = @("run", "python", "scripts/e2e/run_scenario.py", $Scenario)

    $proc = Start-Process -FilePath "uv" `
        -ArgumentList $argList `
        -WorkingDirectory $ProjectRoot `
        -NoNewWindow -PassThru -Wait

    $duration = (Get-Date) - $startTime
    Write-Host ""
    Write-Host "Duration: $([math]::Round($duration.TotalMinutes, 1)) minutes"

    # Handle exit codes: 0=PASS, 1=FAIL, 2=INFRA_FAIL
    if ($proc.ExitCode -eq 2) {
        Write-Host "INFRA_FAIL: Scenario $Scenario failed due to infrastructure issues" -ForegroundColor Yellow
        exit 2
    }
    if ($proc.ExitCode -eq 0) {
        Write-Host "PASS: Scenario $Scenario completed successfully" -ForegroundColor Green
        exit 0
    }
    Write-Host "FAIL: Scenario $Scenario exited with code $($proc.ExitCode)" -ForegroundColor Red
    exit 1
}

# Calculator scenario: use dedicated calculator benchmark script
# Build argument list
$argList = @("run", "python", "scripts/run_calculator_benchmark.py")

if ($Replay) {
    $argList += "--replay"
    $argList += $Replay
    if ($ScoreOnly) {
        $argList += "--score-only"
    }
} else {
    $argList += "--min-score"
    $argList += $MinScore.ToString()
    if ($Strict) {
        $argList += "--strict"
    }
    if ($Runs -gt 1) {
        $argList += "--runs"
        $argList += $Runs.ToString()
    }
}

$proc = Start-Process -FilePath "uv" `
    -ArgumentList $argList `
    -WorkingDirectory $ProjectRoot `
    -NoNewWindow -PassThru -Wait

$duration = (Get-Date) - $startTime
Write-Host ""
Write-Host "Duration: $([math]::Round($duration.TotalMinutes, 1)) minutes"

# Handle exit codes: 0=PASS, 1=FAIL, 2=INFRA_FAIL
if ($proc.ExitCode -eq 2) {
    Write-Host "INFRA_FAIL: Benchmark failed due to infrastructure issues (API errors, rate limits)" -ForegroundColor Yellow
    Write-Host "This is NOT a product regression — retry when infrastructure is stable." -ForegroundColor Yellow
    exit 2
}

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
Write-Host "  Verdict:  $($results.verdict)"
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

# --- Step 6: Pass/Fail based on verdict ---
$verdict = $results.verdict

if ($verdict -eq "INFRA_FAIL") {
    Write-Host "INFRA_FAIL - Infrastructure issues detected, not a product regression" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    exit 2
}

if ($verdict -eq "PASS") {
    Write-Host "PASS - Score $totalScore >= $MinScore" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    exit 0
}

# FAIL
$failures = @()
if ($totalScore -lt $MinScore) {
    $failures += "Score $totalScore < minimum $MinScore"
}
if (-not $npmInstall) {
    $failures += "npm install failed"
}
if (-not $npmBuild) {
    $failures += "npm build failed"
}
if ($results.verdict_reasons) {
    foreach ($reason in $results.verdict_reasons) {
        $failures += $reason
    }
}

Write-Host "FAIL:" -ForegroundColor Red
foreach ($f in $failures) {
    Write-Host "  - $f" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Red
exit 1
