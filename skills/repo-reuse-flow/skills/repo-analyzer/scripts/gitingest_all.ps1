param(
    [string]$VenvPython = "$PSScriptRoot\..\.venv\Scripts\python.exe",
    [string]$ClonedDir  = "$PSScriptRoot\..\outputs\03_analysis\cloned",
    [string]$OutputDir  = "$PSScriptRoot\..\outputs\03_analysis\digests",
    [int]$MaxSize       = 500000,
    [switch]$Force
)

# Usage:
#   .\gitingest_all.ps1                    # analyze all repos, skip existing
#   .\gitingest_all.ps1 -Force             # re-analyze all repos
#   .\gitingest_all.ps1 -MaxSize 1000000   # larger size limit

# --- Prepare dirs ---

$ClonedDir = [System.IO.Path]::GetFullPath($ClonedDir)
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)

if (-not (Test-Path $ClonedDir)) {
    Write-Host "ERROR: ClonedDir not found: $ClonedDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created: $OutputDir" -ForegroundColor Gray
}

# --- Collect repos ---

$repos = Get-ChildItem $ClonedDir -Directory | Where-Object { $_.Name -notmatch "^\." }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  gitingest analysis: $($repos.Count) repos" -ForegroundColor Cyan
Write-Host "  Input : $ClonedDir" -ForegroundColor Cyan
Write-Host "  Output: $OutputDir" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$doneList    = [System.Collections.Generic.List[string]]::new()
$skippedList = [System.Collections.Generic.List[string]]::new()
$failedList  = [System.Collections.Generic.List[string]]::new()

$idx = 0
foreach ($repo in $repos) {
    $idx++
    $repoName  = $repo.Name
    $repoPath  = $repo.FullName
    $outFile   = Join-Path $OutputDir "$($repoName)_digest.txt"

    Write-Host ""
    Write-Host "[$idx/$($repos.Count)] $repoName" -ForegroundColor Cyan

    if ((Test-Path $outFile) -and (-not $Force)) {
        $sizeKB = [math]::Round((Get-Item $outFile).Length / 1KB)
        Write-Host "  SKIP: digest exists ($sizeKB KB) -- use -Force to re-analyze" -ForegroundColor Yellow
        $skippedList.Add($repoName)
        continue
    }

    Write-Host "  Running gitingest..." -ForegroundColor Gray

    & $VenvPython -m gitingest $repoPath `
        -i "*.py" -i "*.ts" -i "*.tsx" -i "*.js" -i "*.md" -i "*.json" -i "*.yaml" -i "*.yml" `
        -e "test_*" -e "*_test.py" -e "*.test.ts" -e "*.spec.ts" -e "*.test.tsx" `
        -e "node_modules" -e ".git" -e "__pycache__" -e "*.min.js" `
        -o $outFile `
        --max-size $MaxSize 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0 -and (Test-Path $outFile)) {
        $sizeKB = [math]::Round((Get-Item $outFile).Length / 1KB)
        Write-Host "  OK: $sizeKB KB -> $outFile" -ForegroundColor Green
        $doneList.Add($repoName)
    } else {
        Write-Host "  FAIL" -ForegroundColor Red
        $failedList.Add($repoName)
    }
}

# --- Summary ---

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Done! Analyzed:$($doneList.Count)  Skipped:$($skippedList.Count)  Failed:$($failedList.Count)" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan

if ($doneList.Count -gt 0) {
    Write-Host ""
    Write-Host "  Analyzed:" -ForegroundColor Green
    foreach ($n in $doneList) { Write-Host "    + $n" -ForegroundColor Green }
}
if ($skippedList.Count -gt 0) {
    Write-Host ""
    Write-Host "  Skipped (already exist):" -ForegroundColor Yellow
    foreach ($n in $skippedList) { Write-Host "    - $n" -ForegroundColor Yellow }
}
if ($failedList.Count -gt 0) {
    Write-Host ""
    Write-Host "  Failed:" -ForegroundColor Red
    foreach ($n in $failedList) { Write-Host "    x $n" -ForegroundColor Red }
}

# Save report
$report = @{
    timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    analyzed  = $doneList
    skipped   = $skippedList
    failed    = $failedList
}
$reportPath = Join-Path $OutputDir "_gitingest_report.json"
$report | ConvertTo-Json -Depth 3 | Set-Content $reportPath -Encoding UTF8
Write-Host ""
Write-Host "  Report: $reportPath" -ForegroundColor Gray
Write-Host ""
