[CmdletBinding()]
param(
    [ValidateRange(30, 3600)]
    [int]$TimeoutSeconds = 300,

    [string]$CoreConsolePath = 'D:\Software\CAD Electrical2026\AutoCAD 2026\accoreconsole.exe'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-ExistingFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Description,

        [long]$MinimumBytes = 1
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description was not found: $Path"
    }

    $item = Get-Item -LiteralPath $Path
    if ($item.Length -lt $MinimumBytes) {
        throw "$Description is smaller than $MinimumBytes bytes: $Path"
    }

    return $item
}

function Read-CoreConsoleLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return ''
    }

    # AcCoreConsole writes redirected output as UTF-16 LE without a BOM.
    return Get-Content -LiteralPath $Path -Encoding Unicode -Raw
}

function Get-LogTail {
    param(
        [string]$Text,
        [int]$LineCount = 40
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return '<empty>'
    }

    $lines = $Text -split "`r?`n"
    return ($lines | Select-Object -Last $LineCount) -join [Environment]::NewLine
}

function Get-AsciiPrefix {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [int]$ByteCount
    )

    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $buffer = New-Object byte[] $ByteCount
        $readCount = $stream.Read($buffer, 0, $ByteCount)
        return [System.Text.Encoding]::ASCII.GetString($buffer, 0, $readCount)
    }
    finally {
        $stream.Dispose()
    }
}

$scriptDirectory = Split-Path -Parent $PSCommandPath
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDirectory '..\..')).Path
$sourceDirectory = Join-Path $repositoryRoot 'drawings\source'
$exportsDirectory = Join-Path $repositoryRoot 'drawings\exports'

if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) {
    throw "Drawing source directory was not found: $sourceDirectory"
}

if (-not (Test-Path -LiteralPath $exportsDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $exportsDirectory | Out-Null
}

$inputDxf = Join-Path $sourceDirectory 'single_line_a1.dxf'
$outputDwg = Join-Path $sourceDirectory 'single_line_a1.dwg'
$outputPdf = Join-Path $exportsDirectory 'single_line_a1_raw.pdf'

$null = Assert-ExistingFile -Path $inputDxf -Description 'Input DXF' -MinimumBytes 128
$null = Assert-ExistingFile -Path $CoreConsolePath -Description 'AutoCAD Core Console executable' -MinimumBytes 1024

$signature = Get-AuthenticodeSignature -LiteralPath $CoreConsolePath
if ($signature.Status.ToString() -ne 'Valid') {
    throw "AutoCAD Core Console signature is not valid ($($signature.Status)): $CoreConsolePath"
}

if ($null -eq $signature.SignerCertificate -or $signature.SignerCertificate.Subject -notmatch 'Autodesk, Inc\.') {
    throw "AutoCAD Core Console is not signed by Autodesk, Inc.: $CoreConsolePath"
}

$plottersDirectory = Join-Path $env:APPDATA 'Autodesk\AutoCAD Electrical 2026\R25.1\chs\Plotters'
$plotterConfig = Join-Path $plottersDirectory 'DWG To PDF.pc3'
$plotStyle = Join-Path $plottersDirectory 'Plot Styles\monochrome.ctb'
$null = Assert-ExistingFile -Path $plotterConfig -Description 'PDF plotter configuration' -MinimumBytes 128
$null = Assert-ExistingFile -Path $plotStyle -Description 'Monochrome plot style' -MinimumBytes 128

$runStamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$stdoutLog = Join-Path $exportsDirectory "single_line_a1_accoreconsole_${runStamp}_${PID}.stdout.log"
$stderrLog = Join-Path $exportsDirectory "single_line_a1_accoreconsole_${runStamp}_${PID}.stderr.log"
$temporaryScriptName = 'export_single_line_{0}_{1}.scr' -f $PID, ([Guid]::NewGuid().ToString('N'))
$temporaryScriptPath = Join-Path $sourceDirectory $temporaryScriptName

# Every path embedded in the SCR is deliberately ASCII and relative to drawings/source.
# The canonical media name avoids localized unit text while still selecting 841 x 594 mm.
$scriptLines = @(
    '_.CMDECHO',
    '1',
    '_.FILEDIA',
    '0',
    '_.BACKGROUNDPLOT',
    '0',
    '_.AUDIT',
    '_Y',
    '_.SAVEAS',
    '_2018',
    'single_line_a1.dwg',
    '_.-PLOT',
    '_Y',
    '',
    'DWG To PDF.pc3',
    'ISO_full_bleed_A1_(841.00_x_594.00_MM)',
    '_M',
    '_L',
    '_N',
    '_E',
    '_F',
    '_C',
    '_Y',
    'monochrome.ctb',
    '_Y',
    '',
    '..\exports\single_line_a1_raw.pdf',
    '_N',
    '_Y',
    '_.QSAVE',
    '_.QUIT'
)

$scriptText = ($scriptLines -join "`r`n") + "`r`n"
if ($scriptText.ToCharArray() | Where-Object { [int]$_ -gt 127 } | Select-Object -First 1) {
    throw 'Internal error: the generated AutoCAD script contains non-ASCII characters.'
}

$runSucceeded = $false
$stdoutText = ''
$stderrText = ''

try {
    foreach ($staleOutput in @($outputDwg, $outputPdf)) {
        if (Test-Path -LiteralPath $staleOutput -PathType Leaf) {
            Remove-Item -LiteralPath $staleOutput -Force
        }
    }

    [System.IO.File]::WriteAllText(
        $temporaryScriptPath,
        $scriptText,
        [System.Text.Encoding]::ASCII
    )

    $arguments = @(
        '/i',
        ('"{0}"' -f $inputDxf),
        '/s',
        ('"{0}"' -f $temporaryScriptPath),
        '/product',
        'ACADE',
        '/p',
        '<<ACADE>>',
        '/l',
        'zh-CN'
    )

    Write-Host "Running signed AutoCAD Core Console..."
    $process = Start-Process `
        -FilePath $CoreConsolePath `
        -ArgumentList $arguments `
        -WorkingDirectory $sourceDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    # Force the process handle to remain open so ExitCode is available after WaitForExit().
    $null = $process.Handle
    $finished = $process.WaitForExit($TimeoutSeconds * 1000)

    if (-not $finished) {
        try {
            $process.Kill()
        }
        catch {
            Write-Warning "Could not terminate timed-out Core Console process $($process.Id): $($_.Exception.Message)"
        }

        $process.WaitForExit()
        $stdoutText = [string](Read-CoreConsoleLog -Path $stdoutLog)
        $stderrText = [string](Read-CoreConsoleLog -Path $stderrLog)
        throw "AutoCAD Core Console timed out after $TimeoutSeconds seconds.`nSTDOUT tail:`n$(Get-LogTail -Text $stdoutText)`nSTDERR tail:`n$(Get-LogTail -Text $stderrText)"
    }

    # Complete asynchronous redirection before reading logs or querying ExitCode.
    $process.WaitForExit()
    $stdoutText = [string](Read-CoreConsoleLog -Path $stdoutLog)
    $stderrText = [string](Read-CoreConsoleLog -Path $stderrLog)
    if ($null -eq $stdoutText) { $stdoutText = [string]::Empty }
    if ($null -eq $stderrText) { $stderrText = [string]::Empty }

    if ($process.ExitCode -ne 0) {
        throw "AutoCAD Core Console exited with code $($process.ExitCode).`nSTDOUT tail:`n$(Get-LogTail -Text $stdoutText)`nSTDERR tail:`n$(Get-LogTail -Text $stderrText)"
    }

    $unknownCommandZh = -join @([char]0x672A, [char]0x77E5, [char]0x547D, [char]0x4EE4)
    $fatalErrorZh = -join @([char]0x81F4, [char]0x547D, [char]0x9519, [char]0x8BEF)
    $fatalPatterns = @(
        'FATAL ERROR',
        'Unhandled Exception',
        'Unknown command',
        $unknownCommandZh,
        $fatalErrorZh
    )

    foreach ($pattern in $fatalPatterns) {
        if (([string]$stdoutText).IndexOf([string]$pattern, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            ([string]$stderrText).IndexOf([string]$pattern, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            throw "AutoCAD Core Console log contains a fatal command/runtime marker: $pattern`nSTDOUT tail:`n$(Get-LogTail -Text $stdoutText)`nSTDERR tail:`n$(Get-LogTail -Text $stderrText)"
        }
    }

    $dwgItem = Assert-ExistingFile -Path $outputDwg -Description '2018 DWG output' -MinimumBytes 1024
    $pdfItem = Assert-ExistingFile -Path $outputPdf -Description 'A1 PDF output' -MinimumBytes 1024

    $dwgHeader = Get-AsciiPrefix -Path $outputDwg -ByteCount 6
    if ($dwgHeader -ne 'AC1032') {
        throw "Unexpected DWG header '$dwgHeader'; AutoCAD 2018 DWG must use AC1032: $outputDwg"
    }

    $pdfHeader = Get-AsciiPrefix -Path $outputPdf -ByteCount 5
    if ($pdfHeader -ne '%PDF-') {
        throw "Unexpected PDF header '$pdfHeader': $outputPdf"
    }

    $runSucceeded = $true
    Write-Host "Export complete."
    Write-Host "DWG: $outputDwg ($($dwgItem.Length) bytes, AC1032)"
    Write-Host "PDF: $outputPdf ($($pdfItem.Length) bytes)"
    Write-Host "STDOUT log: $stdoutLog"
    Write-Host "STDERR log: $stderrLog"
}
finally {
    if (Test-Path -LiteralPath $temporaryScriptPath -PathType Leaf) {
        Remove-Item -LiteralPath $temporaryScriptPath -Force -ErrorAction SilentlyContinue
    }

    if (-not $runSucceeded) {
        foreach ($partialOutput in @($outputDwg, $outputPdf)) {
            if (Test-Path -LiteralPath $partialOutput -PathType Leaf) {
                Remove-Item -LiteralPath $partialOutput -Force -ErrorAction SilentlyContinue
            }
        }

        Write-Host "Core Console logs retained for diagnosis:"
        Write-Host "  $stdoutLog"
        Write-Host "  $stderrLog"
    }
}
