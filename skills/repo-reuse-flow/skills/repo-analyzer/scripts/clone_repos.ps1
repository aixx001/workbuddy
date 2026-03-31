param(
    [string]$Repos     = "",
    [string]$FromFile  = "",
    # 默认使用 .venv 中的 Python
    [string]$VenvPython = "$PSScriptRoot\..\.venv\Scripts\python.exe",
    [string]$OutputDir = "$PSScriptRoot\..\outputs\03_analysis\cloned",
    [int]$Depth        = 1,
    [switch]$Force
)

# Usage examples:
#   .\clone_repos.ps1 -Repos "langchain-ai/langchain"
#   .\clone_repos.ps1 -Repos "langfuse/langfuse,confident-ai/deepeval"
#   .\clone_repos.ps1 -FromFile "repos.json"
#   .\clone_repos.ps1 -Repos "owner/repo" -OutputDir "D:\my_clones"
#   .\clone_repos.ps1 -Repos "owner/repo" -Depth 0   (full clone)
#   .\clone_repos.ps1 -Repos "owner/repo" -Force      (force re-clone)

# --- Collect repo list ---

$repoList = [System.Collections.Generic.List[hashtable]]::new()

if ($FromFile -ne "") {
    if (-not (Test-Path $FromFile)) {
        Write-Host "  ERROR: File not found: $FromFile" -ForegroundColor Red
        exit 1
    }
    $json = Get-Content $FromFile -Encoding UTF8 -Raw | ConvertFrom-Json
    foreach ($item in $json) {
        if ($item -is [string]) {
            $raw = $item.Trim()
        } else {
            $raw = $item.url
        }
        $url  = if ($raw -match "^https?://") { $raw } else { "https://github.com/$raw.git" }
        $name = ($url -replace "\.git$","") -split "/" | Select-Object -Last 1
        $repoList.Add(@{ Url = $url; Name = $name })
    }
}

if ($Repos -ne "") {
    foreach ($r in ($Repos -split ",")) {
        $raw  = $r.Trim()
        $url  = if ($raw -match "^https?://") { $raw } else { "https://github.com/$raw.git" }
        $name = ($url -replace "\.git$","") -split "/" | Select-Object -Last 1
        $repoList.Add(@{ Url = $url; Name = $name })
    }
}

if ($repoList.Count -eq 0) {
    Write-Host "  No repos specified. Using built-in default list..." -ForegroundColor Gray
    $defaults = @(
        "langchain-ai/langchain",
        "langchain-ai/langgraph",
        "langchain-ai/langsmith-sdk",
        "run-llama/llama_index",
        "open-webui/open-webui",
        "langgenius/dify",
        "infiniflow/ragflow",
        "stanfordnlp/dspy",
        "promptfoo/promptfoo",
        "explodinggradients/ragas",
        "confident-ai/deepeval",
        "langfuse/langfuse",
        "microsoft/promptbench",
        "opendatalab/MinerU",
        "opendatalab/DocLayout-YOLO",
        "ollama/ollama-python"
    )
    foreach ($r in $defaults) {
        $url  = "https://github.com/$r.git"
        $name = $r -split "/" | Select-Object -Last 1
        $repoList.Add(@{ Url = $url; Name = $name })
    }
}

# --- Prepare output directory ---

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "  Created dir: $OutputDir" -ForegroundColor Gray
}

# --- Run clone ---

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Cloning $($repoList.Count) repos" -ForegroundColor Cyan
Write-Host "  Output : $OutputDir" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$clonedList  = [System.Collections.Generic.List[string]]::new()
$skippedList = [System.Collections.Generic.List[string]]::new()
$failedList  = [System.Collections.Generic.List[string]]::new()
$report      = [System.Collections.Generic.List[hashtable]]::new()

$idx = 0
foreach ($repo in $repoList) {
    $idx++
    $targetDir = Join-Path $OutputDir $repo.Name

    Write-Host ""
    Write-Host "[$idx/$($repoList.Count)] $($repo.Name)" -ForegroundColor Cyan

    if (Test-Path $targetDir) {
        if ($Force) {
            Write-Host "  Exists, -Force: removing and re-cloning..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $targetDir
        } else {
            Write-Host "  SKIP: already exists (use -Force to re-clone)" -ForegroundColor Yellow
            $skippedList.Add($repo.Name)
            $report.Add(@{ name = $repo.Name; status = "skipped"; url = $repo.Url })
            continue
        }
    }

    Write-Host "  Source: $($repo.Url)" -ForegroundColor Gray

    if ($Depth -gt 0) {
        git clone --depth $Depth $repo.Url $targetDir 2>&1 | Out-Null
    } else {
        git clone $repo.Url $targetDir 2>&1 | Out-Null
    }

    if ($LASTEXITCODE -eq 0) {
        $fileCount = (Get-ChildItem $targetDir -Recurse -File -ErrorAction SilentlyContinue).Count
        Write-Host "  OK: $fileCount files" -ForegroundColor Green
        $clonedList.Add($repo.Name)
        $report.Add(@{ name = $repo.Name; status = "cloned"; files = $fileCount; url = $repo.Url })
    } else {
        Write-Host "  FAIL" -ForegroundColor Red
        $failedList.Add($repo.Name)
        $report.Add(@{ name = $repo.Name; status = "failed"; url = $repo.Url })
    }
}

# --- Summary ---

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Done! Cloned:$($clonedList.Count)  Skipped:$($skippedList.Count)  Failed:$($failedList.Count)" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan

if ($clonedList.Count -gt 0) {
    Write-Host ""
    Write-Host "  Newly cloned:" -ForegroundColor Green
    foreach ($n in $clonedList) {
        Write-Host "    + $n" -ForegroundColor Green
    }
}

if ($skippedList.Count -gt 0) {
    Write-Host ""
    Write-Host "  Skipped (already exist):" -ForegroundColor Yellow
    foreach ($n in $skippedList) {
        Write-Host "    - $n" -ForegroundColor Yellow
    }
}

if ($failedList.Count -gt 0) {
    Write-Host ""
    Write-Host "  Failed:" -ForegroundColor Red
    foreach ($n in $failedList) {
        Write-Host "    x $n" -ForegroundColor Red
    }
}

$reportPath = Join-Path $OutputDir "_clone_report.json"
$report | ConvertTo-Json -Depth 3 | Set-Content $reportPath -Encoding UTF8
Write-Host ""
Write-Host "  Report saved: $reportPath" -ForegroundColor Gray
Write-Host ""
