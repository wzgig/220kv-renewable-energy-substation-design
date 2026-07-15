[CmdletBinding()]
param(
    [string]$ReportDirectory = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$documents = Get-ChildItem -LiteralPath $ReportDirectory -Filter '*.docx' -File |
    Where-Object { $_.Name -notlike '~$*' } |
    Sort-Object Name

if (-not $documents) {
    throw "No DOCX files found in $ReportDirectory"
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    foreach ($file in $documents) {
        $doc = $word.Documents.Open($file.FullName, $false, $false)
        try {
            foreach ($toc in $doc.TablesOfContents) {
                $toc.Update()
            }
            $doc.Fields.Update() | Out-Null
            foreach ($section in $doc.Sections) {
                foreach ($header in $section.Headers) {
                    $header.Range.Fields.Update() | Out-Null
                }
                foreach ($footer in $section.Footers) {
                    $footer.Range.Fields.Update() | Out-Null
                }
            }
            $doc.Save()
            $pdfPath = [System.IO.Path]::ChangeExtension($file.FullName, '.pdf')
            $doc.ExportAsFixedFormat(
                $pdfPath,
                17,
                $false,
                0,
                0,
                1,
                $doc.ComputeStatistics(2),
                0,
                $true,
                $true,
                1,
                $true,
                $true,
                $false
            )
            Write-Output ([System.IO.Path]::GetFileName($pdfPath))
        }
        finally {
            $doc.Close($false)
        }
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$venvPython = Join-Path $repositoryRoot '.venv\Scripts\python.exe'
$python = if (Test-Path -LiteralPath $venvPython) {
    $venvPython
}
else {
    (Get-Command python -ErrorAction Stop).Source
}
$sanitizer = Join-Path $PSScriptRoot 'sanitize_public_metadata.py'

& $python $sanitizer --report-dir $ReportDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Public metadata sanitization failed with exit code $LASTEXITCODE"
}
