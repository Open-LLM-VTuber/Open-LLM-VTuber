# Downloads the Major Arcana of the Rider-Waite-Smith deck (1909) from
# Wikimedia Commons into backgrounds/cards as 512 px JPEG thumbnails.
#
# Art: Pamela Colman Smith (1878-1951), first published 1909.
# License: public domain (Commons: "Public domain", PD-old-80-expired).
# Source per card: see backgrounds/cards/README.md
#
#   powershell -ExecutionPolicy Bypass -File scripts/fetch_tarot_art.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/fetch_tarot_art.ps1 -Force

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root "backgrounds\cards"
New-Item -ItemType Directory -Force $outDir | Out-Null

# The new Wikimedia thumbnail service only exposes the 960 px bucket, which is
# more than enough for a card that is drawn ~200 px wide on screen.
$thumbWidth = 960

# Wikimedia asks for a descriptive User-Agent.
$ua = "Open-LLM-VTuber-tarot/1.0 (local tarot show setup)"

# id = path on upload.wikimedia.org (hash dirs + file name)
$cards = @{
    "major_00" = "9/90/RWS_Tarot_00_Fool.jpg"
    "major_01" = "d/de/RWS_Tarot_01_Magician.jpg"
    "major_02" = "8/88/RWS_Tarot_02_High_Priestess.jpg"
    "major_03" = "d/d2/RWS_Tarot_03_Empress.jpg"
    "major_04" = "c/c3/RWS_Tarot_04_Emperor.jpg"
    "major_05" = "8/8d/RWS_Tarot_05_Hierophant.jpg"
    "major_06" = "d/db/RWS_Tarot_06_Lovers.jpg"
    "major_07" = "9/9b/RWS_Tarot_07_Chariot.jpg"
    "major_08" = "f/f5/RWS_Tarot_08_Strength.jpg"
    "major_09" = "4/4d/RWS_Tarot_09_Hermit.jpg"
    "major_10" = "3/3c/RWS_Tarot_10_Wheel_of_Fortune.jpg"
    "major_11" = "e/e0/RWS_Tarot_11_Justice.jpg"
    "major_12" = "2/2b/RWS_Tarot_12_Hanged_Man.jpg"
    "major_13" = "d/d7/RWS_Tarot_13_Death.jpg"
    "major_14" = "f/f8/RWS_Tarot_14_Temperance.jpg"
    "major_15" = "5/55/RWS_Tarot_15_Devil.jpg"
    "major_16" = "5/53/RWS_Tarot_16_Tower.jpg"
    "major_17" = "d/db/RWS_Tarot_17_Star.jpg"
    "major_18" = "7/7f/RWS_Tarot_18_Moon.jpg"
    "major_19" = "1/17/RWS_Tarot_19_Sun.jpg"
    "major_20" = "d/dd/RWS_Tarot_20_Judgement.jpg"
    "major_21" = "f/ff/RWS_Tarot_21_World.jpg"
}

$downloaded = 0
$skipped = 0
$failed = 0

foreach ($id in ($cards.Keys | Sort-Object)) {
    $path = $cards[$id]
    $name = Split-Path $path -Leaf
    $url = "https://thumb.wikimedia.org/wikipedia/commons/thumb/$path/${thumbWidth}px-$name"
    $dest = Join-Path $outDir "$id.jpg"

    if (-not $Force -and (Test-Path $dest) -and (Get-Item $dest).Length -gt 10000) {
        $skipped++
        continue
    }

    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UserAgent $ua
        $size = (Get-Item $dest).Length
        if ($size -lt 10000) {
            throw "suspiciously small file ($size bytes)"
        }
        Write-Host ("{0} <- {1} ({2:N0} bytes)" -f $id, $url, $size)
        $downloaded++
    }
    catch {
        Write-Warning ("{0} failed: {1}" -f $id, $_.Exception.Message)
        $failed++
    }
}

Write-Host ("downloaded {0}, skipped {1}, failed {2} -> {3}" -f $downloaded, $skipped, $failed, $outDir)
if ($failed -gt 0) {
    exit 1
}
