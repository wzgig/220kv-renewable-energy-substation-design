[CmdletBinding()]
param(
    [ValidateRange(30, 3600)]
    [int]$TimeoutSeconds = 300,

    [string]$CoreConsolePath = 'D:\Software\CAD Electrical2026\AutoCAD 2026\accoreconsole.exe'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDirectory = Split-Path -Parent $PSCommandPath
$exportScript = Join-Path $scriptDirectory 'export_single_line.ps1'
$normalizeScript = Join-Path $scriptDirectory 'normalize_pdf.py'
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDirectory '..\..')).Path
$python = Join-Path $repositoryRoot '.venv\Scripts\python.exe'

foreach ($stem in @('single_line_a1', 'switchyard_plan_a1', 'switchyard_section_a1')) {
    Write-Host "Exporting $stem..."
    & $exportScript `
        -DrawingStem $stem `
        -TimeoutSeconds $TimeoutSeconds `
        -CoreConsolePath $CoreConsolePath

    & $python $normalizeScript `
        --input (Join-Path $repositoryRoot "drawings\exports\${stem}_raw.pdf") `
        --output (Join-Path $repositoryRoot "drawings\exports\${stem}.pdf")

    if ($LASTEXITCODE -ne 0) {
        throw "PDF normalization failed for $stem with exit code $LASTEXITCODE"
    }
}

Write-Host 'All drawing exports completed.'
