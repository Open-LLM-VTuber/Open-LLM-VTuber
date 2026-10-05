$ErrorActionPreference = "Stop"

$configPath = Join-Path $PSScriptRoot "conf.yaml"
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "conf.yaml was not found. Copy config_templates\conf.default.yaml to conf.yaml and configure the server first."
}

$inSystemConfig = $false
$systemConfigIndent = $null
$serverPort = $null
foreach ($line in Get-Content -LiteralPath $configPath) {
    if ($line -match '^system_config:\s*(?:#.*)?$') {
        $inSystemConfig = $true
        continue
    }
    if (-not $inSystemConfig) {
        continue
    }
    if ($line -match '^\s*(?:#|$)') {
        continue
    }
    if ($line -match '^(\s+)\S') {
        $indent = $Matches[1].Length
    } else {
        break
    }
    if ($null -eq $systemConfigIndent) {
        $systemConfigIndent = $indent
    }
    if ($indent -lt $systemConfigIndent) {
        break
    }
    if (
        $indent -eq $systemConfigIndent -and
        $line -match '^\s+port:\s*["'']?(\d+)["'']?\s*(?:#.*)?$'
    ) {
        $serverPort = [int]$Matches[1]
        break
    }
}

if ($null -eq $serverPort -or $serverPort -lt 1 -or $serverPort -gt 65535) {
    throw "A valid system_config.port was not found in conf.yaml."
}

$appUrl = "http://localhost:$serverPort/character-call/"

function Get-CharacterCallPage {
    try {
        return Invoke-WebRequest -Uri $appUrl -TimeoutSec 3 -UseBasicParsing
    } catch {
        return $null
    }
}

function Test-CharacterCallPage {
    param([object]$response)

    return (
        $null -ne $response -and
        $response.StatusCode -eq 200 -and
        $response.Content.Contains("Aster Vale")
    )
}

$response = Get-CharacterCallPage
if (-not (Test-CharacterCallPage $response)) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        throw "uv was not found. Install uv, then run this launcher again."
    }

    $serverCommand = 'cd /d "' + $PSScriptRoot + '" && "' + $uv.Source + '" run run_server.py'
    Start-Process `
        -FilePath $env:ComSpec `
        -ArgumentList @("/k", $serverCommand) `
        -WorkingDirectory $PSScriptRoot

    Write-Host "Waiting for Open-LLM-VTuber at $appUrl ..."
    $deadline = (Get-Date).AddMinutes(5)
    do {
        Start-Sleep -Seconds 2
        $response = Get-CharacterCallPage
    } while (
        -not (Test-CharacterCallPage $response) -and
        (Get-Date) -lt $deadline
    )

    if (-not (Test-CharacterCallPage $response)) {
        throw "The character-call page did not become available. Check the server window and confirm it is configured for port $serverPort."
    }
}

$edgeCandidates = @()
$edgeCommand = Get-Command msedge.exe -ErrorAction SilentlyContinue
if ($edgeCommand) {
    $edgeCandidates += $edgeCommand.Source
}
foreach ($basePath in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
    if ($basePath) {
        $edgeCandidates += Join-Path $basePath "Microsoft\Edge\Application\msedge.exe"
    }
}

$edgePath = $edgeCandidates |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
    Select-Object -First 1

if ($edgePath) {
    Start-Process -FilePath $edgePath -ArgumentList @("--app=$appUrl")
} else {
    Write-Host "Microsoft Edge was not found; opening Character Call in your default browser."
    Start-Process -FilePath $appUrl
}
