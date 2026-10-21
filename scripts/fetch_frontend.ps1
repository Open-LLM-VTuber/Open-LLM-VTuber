# Download the prebuilt official web UI (branch "build") into frontend-build/.
#
# Why: the docker image does not ship the `frontend` submodule, so
# run_server.py tries to clone it from GitHub on every start. That clone can
# hang or fail (WAF / blocked network), leaving "/" without a UI. This script
# downloads the compiled site once and docker-compose mounts it at
# /app/frontend.
#
# Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File scripts/fetch_frontend.ps1
#
# Mirrors are tried in order because github.com/codeload can be blocked while
# raw/mirror hosts still work.

param(
    [string]$Branch = "build"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$target = Join-Path $repoRoot "frontend-build"
$tempZip = Join-Path $env:TEMP "open-llm-vtuber-frontend.zip"
$tempDir = Join-Path $env:TEMP "open-llm-vtuber-frontend"

$archive = "https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web/archive/refs/heads/$Branch.zip"
$urls = @(
    "https://ghfast.top/$archive",
    "https://ghproxy.net/$archive",
    $archive
)

Write-Host "Downloading the official web UI ($Branch branch)..."

$downloaded = $false
foreach ($url in $urls) {
    try {
        Write-Host "  trying $url"
        if (Test-Path $tempZip) { Remove-Item $tempZip -Force }
        & curl.exe -L --fail --max-time 300 --silent --show-error -o $tempZip $url
        if ((Test-Path $tempZip) -and (Get-Item $tempZip).Length -gt 1MB) {
            $downloaded = $true
            break
        }
    } catch {
        Write-Host "  failed: $($_.Exception.Message)"
    }
}

if (-not $downloaded) {
    throw "Could not download the frontend from any mirror. Try again or set a proxy."
}

if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
Expand-Archive -Path $tempZip -DestinationPath $tempDir -Force

$extracted = Get-ChildItem $tempDir -Directory | Select-Object -First 1
if (-not $extracted) {
    throw "The archive did not contain a directory."
}

if (-not (Test-Path (Join-Path $extracted.FullName "index.html"))) {
    throw "The archive does not look like the compiled frontend (no index.html)."
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Get-ChildItem $extracted.FullName -Force | Copy-Item -Destination $target -Recurse -Force

Remove-Item $tempDir -Recurse -Force
Remove-Item $tempZip -Force

Write-Host ""
Write-Host "Frontend ready at: $target"
Write-Host "It is mounted at /app/frontend by docker-compose.yml."
Write-Host "Restart the container to serve it:"
Write-Host "  docker compose up -d --force-recreate"
