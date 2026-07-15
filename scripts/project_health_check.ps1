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
    'data/design_baseline.yaml',
    'data/equipment_selection.yaml',
    'data/equipment_catalog.yaml',
    'docs/PROJECT_BRIEF.md',
    'docs/EXECUTION_PROMPT.md',
    'docs/DESIGN_ASSUMPTIONS_REGISTER.md',
    'docs/HAND_DRAWING_GUIDE.md',
    'docs/MASTER_PLAN.md',
    'docs/MAIN_SCHEME_BASELINE.md',
    'docs/EQUIPMENT_SELECTION_BASELINE.md',
    'docs/STANDARDS_REGISTER.md',
    'docs/REQUIREMENTS_TRACEABILITY.md',
    'docs/CAD_WORKFLOW.md',
    'calculations/README.md',
    'calculations/load_and_transformers/calculate.py',
    'calculations/short_circuit/calculate.py',
    'calculations/equipment_selection/calculate.py',
    'calculations/results/load_and_transformer_results.json',
    'calculations/results/short_circuit/short_circuit_results.json',
    'calculations/results/equipment_selection/equipment_selection_results.json',
    'drawings/README.md',
    'drawings/data/single_line_layout.yaml',
    'drawings/data/switchyard_layout.yaml',
    'drawings/standards/single_line_standard.yaml',
    'drawings/standards/switchyard_standard.yaml',
    'drawings/scripts/sld_symbols.py',
    'drawings/scripts/generate_single_line.py',
    'drawings/scripts/generate_switchyard_drawings.py',
    'drawings/scripts/export_single_line.ps1',
    'drawings/scripts/export_all_drawings.ps1',
    'drawings/scripts/normalize_pdf.py',
    'drawings/source/single_line_a1.dxf',
    'drawings/exports/single_line_a1.pdf',
    'drawings/exports/single_line_a1.png',
    'drawings/source/switchyard_plan_a1.dxf',
    'drawings/exports/switchyard_plan_a1.pdf',
    'drawings/exports/switchyard_plan_a1.png',
    'drawings/source/switchyard_section_a1.dxf',
    'drawings/exports/switchyard_section_a1.pdf',
    'drawings/exports/switchyard_section_a1.png',
    'report/README.md',
    'report/scripts/build_reports.py',
    'report/scripts/export_reports.ps1',
    'report/scripts/sanitize_public_metadata.py',
    'requirements.txt',
    'tests/test_report_deliverables.py',
    'tests/test_load_and_transformers.py',
    'tests/test_short_circuit.py',
    'tests/test_equipment_selection.py',
    'tests/test_single_line_drawing.py',
    'tests/test_switchyard_drawings.py'
)

foreach ($relativePath in $requiredPaths) {
    $fullPath = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        $errors.Add("Missing required path: $relativePath")
    }
}

$requiredReportPatterns = @(
    'report/01_220kV*.docx',
    'report/01_220kV*.pdf',
    'report/02_220kV*.docx',
    'report/02_220kV*.pdf',
    'report/03_220kV*.docx',
    'report/03_220kV*.pdf',
    'report/04_220kV*.pptx',
    'report/04_220kV*.pdf',
    'report/05_220kV*.docx',
    'report/05_220kV*.pdf'
)

foreach ($pattern in $requiredReportPatterns) {
    $matches = @(Get-ChildItem -Path (Join-Path $root $pattern) -File -ErrorAction SilentlyContinue)
    if ($matches.Count -ne 1) {
        $errors.Add("Expected exactly one report deliverable for pattern: $pattern")
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
        'short_circuit_base_mva:',
        'short_circuit_peak_factor_k:',
        'sensitivity_multiplier_range:'
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
    foreach ($dwg in $trackedDwgs) {
        $errors.Add("DWG with machine-authored metadata must not be public: $dwg")
    }
}
else {
    $warnings.Add('Git repository is not initialized yet; tracked-file checks were skipped.')
}

Write-Host "Project root: $root"
Write-Host "Required paths checked: $($requiredPaths.Count + $requiredReportPatterns.Count)"

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
