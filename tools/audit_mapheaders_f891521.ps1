$ErrorActionPreference = "Stop"

$manifestPath = ".\tools\rom_variants\red_ita_manifest.json"
$zipPath      = ".\italian-mapheaders-f891521-files.zip"
$romPath      = ".\red-ita.gb"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CONFRONTO MAP HEADERS: CURRENT vs f891521 vs ROM" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $manifestPath)) { throw "Manifest non trovato: $manifestPath" }
if (-not (Test-Path $zipPath))      { throw "ZIP storico non trovato: $zipPath" }
if (-not (Test-Path $romPath))      { throw "ROM italiana non trovata: $romPath" }

# ------------------------------------------------------------
# CURRENT MANIFEST
# ------------------------------------------------------------

$current = Get-Content $manifestPath -Raw |
    ConvertFrom-Json -AsHashtable

# ------------------------------------------------------------
# ROM
# ------------------------------------------------------------

$rom = [System.IO.File]::ReadAllBytes(
    (Resolve-Path $romPath).Path
)

# ------------------------------------------------------------
# ZIP STORICO f891521
# ------------------------------------------------------------

Add-Type -AssemblyName System.IO.Compression.FileSystem

$zip = [System.IO.Compression.ZipFile]::OpenRead(
    (Resolve-Path $zipPath).Path
)

try {
    $entry = $zip.Entries |
        Where-Object {
            $_.FullName -eq "tools/rom_variants/red_ita_manifest.json"
        } |
        Select-Object -First 1

    if ($null -eq $entry) {
        throw "Nel ZIP non trovo tools/rom_variants/red_ita_manifest.json"
    }

    $reader = New-Object System.IO.StreamReader($entry.Open())
    try {
        $historicalText = $reader.ReadToEnd()
    }
    finally {
        $reader.Dispose()
    }
}
finally {
    $zip.Dispose()
}

$historical = $historicalText |
    ConvertFrom-Json -AsHashtable

# ------------------------------------------------------------
# DATI MAPPE
# ------------------------------------------------------------

$mapRuntimeCurrent   = $current["maps"]
$mapConstants        = $current["constants"]["maps"]
$symbolsCurrent      = $current["symbols"]

$mapRuntimeHistorical = $historical["maps"]
$symbolsHistorical    = $historical["symbols"]

# ------------------------------------------------------------
# FUNZIONI
# ------------------------------------------------------------

function Get-RawOffset {
    param(
        [int]$Bank,
        [int]$Cpu
    )

    if ($Cpu -lt 0x4000 -or $Cpu -gt 0x7FFF) {
        return $null
    }

    return ($Bank * 0x4000) + ($Cpu - 0x4000)
}

function Get-HeaderInfo {
    param(
        [int]$Bank,
        [int]$Cpu
    )

    $raw = Get-RawOffset $Bank $Cpu

    if ($null -eq $raw) {
        return $null
    }

    if ($raw + 9 -ge $rom.Length) {
        return $null
    }

    $tileset = [int]$rom[$raw]
    $height  = [int]$rom[$raw + 1]
    $width   = [int]$rom[$raw + 2]

    $blockPtr =
        [int]$rom[$raw + 3] -bor
        ([int]$rom[$raw + 4] -shl 8)

    $blockBank = $Bank

    $flags = [int]$rom[$raw + 9]

    return [PSCustomObject]@{
        Bank       = $Bank
        Cpu        = $Cpu
        Address    = "{0:X2}:{1:X4}" -f $Bank,$Cpu
        Tileset    = $tileset
        Height     = $height
        Width      = $width
        BlockPtr   = $blockPtr
        Flags      = $flags
        Raw        = $raw
    }
}

function Get-Candidates {
    param(
        [int]$Bank,
        [int]$ExpectedHeight,
        [int]$ExpectedWidth,
        [int]$CurrentCpu
    )

    $list = @()

    $bankStart = $Bank * 0x4000
    $bankEnd   = [Math]::Min(
        $bankStart + 0x4000 - 10,
        $rom.Length - 10
    )

    for ($raw = $bankStart; $raw -le $bankEnd; $raw++) {

        $cpu = 0x4000 + ($raw - $bankStart)

        $tileset = [int]$rom[$raw]
        $height  = [int]$rom[$raw + 1]
        $width   = [int]$rom[$raw + 2]

        if ($tileset -ge 0x20) {
            continue
        }

        if ($height -ne $ExpectedHeight -or
            $width  -ne $ExpectedWidth) {
            continue
        }

        $blockPtr =
            [int]$rom[$raw + 3] -bor
            ([int]$rom[$raw + 4] -shl 8)

        if ($blockPtr -lt 0x4000 -or
            $blockPtr -gt 0x7FFF) {
            continue
        }

        $distance = [Math]::Abs($cpu - $CurrentCpu)

        $list += [PSCustomObject]@{
            Address  = "{0:X2}:{1:X4}" -f $Bank,$cpu
            Bank     = $Bank
            Cpu      = $cpu
            Distance = $distance
            Tileset  = "{0:X2}" -f $tileset
            Height   = $height
            Width    = $width
            BlockPtr = "{0:X4}" -f $blockPtr
            Flags    = "{0:X2}" -f ([int]$rom[$raw + 9])
        }
    }

    return @($list | Sort-Object Distance)
}

# ------------------------------------------------------------
# ANALISI
# ------------------------------------------------------------

$results = @()

foreach ($mapName in $mapConstants.Keys) {

    $spec = $mapConstants[$mapName]

    if (-not $spec.ContainsKey("height") -or
        -not $spec.ContainsKey("width")) {
        continue
    }

    $runtime = $mapRuntimeCurrent[$mapName]

    if ($null -eq $runtime) {
        continue
    }

    $label = $runtime["label"]

    if ([string]::IsNullOrWhiteSpace($label)) {
        continue
    }

    $symbolName = "${label}_h"

    if (-not $symbolsCurrent.ContainsKey($symbolName)) {
        continue
    }

    # ---------------- CURRENT ----------------

    $cur = $symbolsCurrent[$symbolName]

    $currentBank = [int]$cur[0]
    $currentCpu  = [int]$cur[1]

    $currentInfo = Get-HeaderInfo $currentBank $currentCpu

    # ---------------- HISTORICAL ----------------

    $historicalInfo = $null

    if ($symbolsHistorical.ContainsKey($symbolName)) {

        $hist = $symbolsHistorical[$symbolName]

        $historicalBank = [int]$hist[0]
        $historicalCpu  = [int]$hist[1]

        $historicalInfo =
            Get-HeaderInfo $historicalBank $historicalCpu
    }

    # ---------------- CANDIDATES ----------------

    $candidates = Get-Candidates `
        $currentBank `
        ([int]$spec["height"]) `
        ([int]$spec["width"]) `
        $currentCpu

    $top = @($candidates | Select-Object -First 5)

    # ---------------- STATUS ----------------

    $currentAddress =
        "{0:X2}:{1:X4}" -f $currentBank,$currentCpu

    $historicalAddress = ""

    if ($symbolsHistorical.ContainsKey($symbolName)) {
        $hist = $symbolsHistorical[$symbolName]
        $historicalAddress =
            "{0:X2}:{1:X4}" -f ([int]$hist[0]),([int]$hist[1])
    }

    $expectedH = [int]$spec["height"]
    $expectedW = [int]$spec["width"]

    $currentCorrect = $false

    if ($null -ne $currentInfo) {
        $currentCorrect =
            ($currentInfo.Height -eq $expectedH) -and
            ($currentInfo.Width  -eq $expectedW)
    }

    $historicalValidCandidate = $false

    if ($historicalAddress -ne "") {
        $historicalValidCandidate =
            @($candidates |
                Where-Object { $_.Address -eq $historicalAddress }
            ).Count -gt 0
    }

    $currentCandidate =
        @($candidates |
            Where-Object { $_.Address -eq $currentAddress }
        ).Count -gt 0

    $status = "UNKNOWN"

    if ($currentCorrect) {

        $status = "CURRENT_OK"

    }
    elseif ($historicalValidCandidate) {

        $status = "HISTORICAL_MATCH"

    }
    elseif ($top.Count -eq 1) {

        $status = "SCANNER_ONLY"

    }
    elseif ($top.Count -eq 0) {

        $status = "NO_CANDIDATE"

    }
    else {

        $status = "AMBIGUOUS"
    }

    # ---------------- CANDIDATE STRING ----------------

    $candidateText = ""

    if ($top.Count -gt 0) {
        $candidateText =
            ($top | ForEach-Object {
                "$($_.Address) d=$($_.Distance)"
            }) -join " | "
    }

    $results += [PSCustomObject]@{
        Map          = $mapName
        Header       = $symbolName
        Expected     = "${expectedH}x${expectedW}"
        Current      = $currentAddress
        Historical   = $historicalAddress
        Status       = $status
        CurrentOK    = $currentCorrect
        HistFound    = $historicalValidCandidate
        Candidates   = $candidates.Count
        TopCandidates = $candidateText
    }
}

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " RISULTATO COMPLESSIVO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$results |
    Group-Object Status |
    Sort-Object Name |
    Format-Table Name,Count -AutoSize

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STORICO f891521 CONFERMATO DALLO SCANNER" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$results |
    Where-Object { $_.Status -eq "HISTORICAL_MATCH" } |
    Format-Table Map,Header,Expected,Current,Historical,Candidates -AutoSize

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SCANNER UNICO" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$results |
    Where-Object { $_.Status -eq "SCANNER_ONLY" } |
    Format-Table Map,Header,Expected,Current,Historical,TopCandidates -AutoSize

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " AMBIGUI" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Cyan

$results |
    Where-Object { $_.Status -eq "AMBIGUOUS" } |
    Format-Table Map,Header,Expected,Current,Historical,Candidates,TopCandidates -AutoSize

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " NESSUN CANDIDATO" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Cyan

$results |
    Where-Object { $_.Status -eq "NO_CANDIDATE" } |
    Format-Table Map,Header,Expected,Current,Historical -AutoSize

# ------------------------------------------------------------
# SALVATAGGIO CSV
# ------------------------------------------------------------

$out = ".\tools\mapheaders_f891521_vs_rom.csv"

$results |
    Export-Csv $out -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "CSV salvato in:" -ForegroundColor Green
Write-Host "  $out"
Write-Host ""

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

$total = $results.Count
$hist  = @($results | Where-Object Status -eq "HISTORICAL_MATCH").Count
$scan  = @($results | Where-Object Status -eq "SCANNER_ONLY").Count
$amb   = @($results | Where-Object Status -eq "AMBIGUOUS").Count
$none  = @($results | Where-Object Status -eq "NO_CANDIDATE").Count
$ok    = @($results | Where-Object Status -eq "CURRENT_OK").Count

Write-Host "------------------------------------------------------------"
Write-Host "TOTAL MAPPE ANALIZZATE : $total"
Write-Host "CURRENT GIÀ CORRETTE   : $ok"
Write-Host "STORICO CONFERMATO     : $hist"
Write-Host "SCANNER UNICO           : $scan"
Write-Host "AMBIGUE                 : $amb"
Write-Host "NESSUN CANDIDATO        : $none"
Write-Host "------------------------------------------------------------"
Write-Host ""
