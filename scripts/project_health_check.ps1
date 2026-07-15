[CmdletBinding()]
param(
    [switch]$Ci
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

$requiredPaths = @(
    'README.md',
    'PROJECT_LOG.md',
    'data/design_inputs.yaml',
    'docs/PROJECT_BRIEF.md',
    'docs/MASTER_PLAN.md',
    'docs/REQUIREMENTS_TRACEABILITY.md',
    'docs/CAD_WORKFLOW.md',
    'calculations/README.md',
    'calculations/load_and_transformers/calculate.py',
    'calculations/results/load_and_transformer_results.json',
    'drawings/README.md',
    'report/README.md',
    'requirements.txt',
    'tests/test_load_and_transformers.py'
)

foreach ($relativePath in $requiredPaths) {
    $fullPath = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        $errors.Add("Missing required path: $relativePath")
    }
}

$inputPath = Join-Path $root 'data/design_inputs.yaml'
if (Test-Path -LiteralPath $inputPath) {
    $inputText = Get-Content -Raw -LiteralPath $inputPath
    $requiredInputKeys = @(
        'title:',
        'voltage_levels_kv:',
        'system_sources:',
        'loads_35kv:',
        'line_loss_rate:',
        'short_circuit_base_mva:'
    )
    foreach ($key in $requiredInputKeys) {
        if ($inputText -notmatch [regex]::Escape($key)) {
            $errors.Add("Design input key missing: $key")
        }
    }
}

$gitHead = Join-Path (Join-Path $root '.git') 'HEAD'
if (Test-Path -LiteralPath $gitHead) {
    $trackedFiles = @(
        & git -C $root ls-files |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
    )
    if ($LASTEXITCODE -ne 0) {
        $errors.Add('Unable to list Git-tracked files.')
    }

    $forbiddenNamePattern = '(?i)(\.baiduyun\.uploading\.cfg$|(^|/)~\$|\.dwl2?$|\.sv\$$|\.autosave$|\.bak$|(^|/)\.env($|\.))'
    foreach ($trackedFile in $trackedFiles) {
        $normalized = $trackedFile -replace '\\', '/'
        if ($normalized.StartsWith('materials-private/') -and $normalized -ne 'materials-private/README.md') {
            $errors.Add("Private material is tracked: $normalized")
        }
        if ($normalized -match $forbiddenNamePattern) {
            $errors.Add("Temporary or sensitive file is tracked: $normalized")
        }

        $fullPath = Join-Path $root $trackedFile
        if ([System.IO.File]::Exists($fullPath)) {
            $size = [System.IO.FileInfo]::new($fullPath).Length
            if ($size -gt 50MB) {
                $errors.Add("Tracked file exceeds 50 MiB: $normalized")
            }
            elseif ($size -gt 25MB) {
                $warnings.Add("Tracked file exceeds 25 MiB: $normalized")
            }
        }
    }

    $trackedDwgs = @($trackedFiles | Where-Object { ($_ -replace '\\', '/') -match '^drawings/source/.+\.dwg$' })
    if ($trackedDwgs.Count -gt 0) {
        $lfsFiles = @(& git -C $root lfs ls-files --name-only)
        if ($LASTEXITCODE -ne 0) {
            $errors.Add('Unable to inspect Git LFS files.')
        }
        foreach ($dwg in $trackedDwgs) {
            if ($lfsFiles -notcontains $dwg) {
                $errors.Add("DWG is not managed by Git LFS: $dwg")
            }
        }
    }
}
else {
    $warnings.Add('Git repository is not initialized yet; tracked-file checks were skipped.')
}

Write-Host "Project root: $root"
Write-Host "Required paths checked: $($requiredPaths.Count)"

foreach ($warning in $warnings) {
    Write-Warning $warning
}

if ($errors.Count -gt 0) {
    foreach ($errorMessage in $errors) {
        Write-Host "ERROR: $errorMessage" -ForegroundColor Red
    }
    exit 1
}

Write-Host 'Project health check passed.' -ForegroundColor Green
exit 0
