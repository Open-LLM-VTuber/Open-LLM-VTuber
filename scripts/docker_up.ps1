#Requires -Version 5.1
<#
.SYNOPSIS
    Arranca Open-LLM-VTuber con Docker Compose comprobando antes el conf.yaml.

.DESCRIPTION
    Evita el fallo de arranque:

        ERROR: conf.yaml is required.
        Please mount your config dir to /app/conf

    Ese mensaje lo imprime el entrypoint de la imagen (/usr/local/bin/start-app, generado
    en el dockerfile) cuando no existe /app/conf/conf.yaml DENTRO del contenedor.
    run_server.py hace read_yaml("conf.yaml"), es decir lee /app/conf.yaml (relativo al
    CWD), y el entrypoint crea ese symlink -> /app/conf/conf.yaml. Si falta el bind mount
    (docker run sin -v), si apunta a otro directorio o si conf/conf.yaml no existe, el
    contenedor sale con exit 1.

    El script:
      1. Se coloca en la raiz del repo (donde esta docker-compose.yml).
      2. Crea conf/conf.yaml si falta (desde ./conf.yaml o la plantilla por defecto).
      3. Avisa si system_config.host no es 0.0.0.0 (el puerto publicado no responderia).
      4. Comprueba que el motor de Docker responde (Docker Desktop arrancando da
         "Internal Server Error ... /version").
      5. Ejecuta docker compose up -d [--build].
      6. Espera a "Uvicorn running" y verifica /app/conf.yaml dentro del contenedor.

.PARAMETER Build
    Reconstruye la imagen antes de arrancar (docker compose up -d --build).

.PARAMETER TimeoutSeconds
    Cuanto esperar el arranque en frio. Por defecto 900 s (7-9 min cargando los modelos
    desde D: en drvfs).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\docker_up.ps1

.EXAMPLE
    .\scripts\docker_up.ps1 -Build
#>
[CmdletBinding()]
param(
    [switch]$Build,
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step([string]$Text) {
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Stop-WithError([string]$Text) {
    Write-Host "ERROR: $Text" -ForegroundColor Red
    exit 1
}

$repo = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repo 'docker-compose.yml'))) {
    Stop-WithError "no encuentro docker-compose.yml junto a scripts\ (repo: $repo)"
}
Set-Location $repo
Write-Step "repo: $repo"

# --------------------------------------------------------------------------- #
# 1) conf/conf.yaml (lo que se monta en /app/conf)
# --------------------------------------------------------------------------- #
$conf = Join-Path $repo 'conf\conf.yaml'
if (-not (Test-Path $conf)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $repo 'conf') | Out-Null
    $rootConfig = Join-Path $repo 'conf.yaml'
    $template = Join-Path $repo 'config_templates\conf.default.yaml'
    if (Test-Path $rootConfig) {
        Copy-Item $rootConfig $conf
        $origin = 'conf.yaml'
    } else {
        Copy-Item $template $conf
        $origin = 'config_templates\conf.default.yaml'
    }
    Write-Host "    creado conf\conf.yaml desde $origin" -ForegroundColor Yellow
    Write-Host "    revisa LLM/TTS/API keys antes de usarlo en serio" -ForegroundColor Yellow
} else {
    $sizeKiB = [math]::Round((Get-Item $conf).Length / 1KB, 1)
    Write-Host "    conf\conf.yaml presente ($sizeKiB KiB)"
}

$hostLine = Select-String -Path $conf -Pattern "^\s{2}host:\s*'?([^'#\s]+)" | Select-Object -First 1
if ($null -eq $hostLine) {
    Write-Host "    AVISO: no encuentro system_config.host en conf\conf.yaml" -ForegroundColor Yellow
} else {
    $bindHost = $hostLine.Matches[0].Groups[1].Value
    if ($bindHost -ne '0.0.0.0') {
        Write-Host "    AVISO: system_config.host = '$bindHost'; con Docker debe ser '0.0.0.0'" -ForegroundColor Yellow
        Write-Host "           (si no, Uvicorn escucha solo en el loopback del contenedor)" -ForegroundColor Yellow
    }
}

# --------------------------------------------------------------------------- #
# 2) motor de Docker
# --------------------------------------------------------------------------- #
Write-Step 'comprobando el motor de Docker'
if (-not $env:DOCKER_HOST) {
    $pipes = @('\\.\pipe\dockerDesktopLinuxEngine', '\\.\pipe\docker_engine')
    $pipeHit = $false
    foreach ($pipe in $pipes) {
        if (Test-Path -LiteralPath $pipe) {
            $pipeHit = $true
            break
        }
    }
    if (-not $pipeHit) {
        Stop-WithError 'Docker Desktop no esta corriendo (no hay pipe del motor). Abrelo y espera a "Engine running".'
    }
}

# `docker info` puede quedarse colgado cuando el motor esta a medio arrancar: se acota a 60 s.
$probeLog = Join-Path $env:TEMP ("olv_docker_probe_{0}.log" -f $PID)
$probe = Start-Job -ScriptBlock {
    param($logFile)
    & docker info --format '{{.ServerVersion}}' *> $logFile
    $LASTEXITCODE
} -ArgumentList $probeLog
if (-not (Wait-Job $probe -Timeout 60)) {
    Stop-Job $probe
    Remove-Job $probe -Force
    Stop-WithError 'docker info no respondio en 60 s: el motor esta arrancando o colgado (reinicia Docker Desktop).'
}
$probeExit = @(Receive-Job $probe) | Select-Object -Last 1
$probeState = (Get-Job -Id $probe.Id).State
Remove-Job $probe -Force

$probeOut = ''
if (Test-Path $probeLog) {
    $probeOut = ((Get-Content $probeLog -Raw) -as [string])
    if ($null -eq $probeOut) { $probeOut = '' }
    $probeOut = $probeOut.Trim()
    Remove-Item $probeLog -Force -ErrorAction SilentlyContinue
}
if ($probeState -ne 'Completed') {
    Stop-WithError "la sonda a Docker termino en estado '$probeState':`n$probeOut"
}
if (($probeExit -ne 0) -or (-not $probeOut) -or
    ($probeOut -match 'Internal Server Error|error during connect|Cannot connect|API version')) {
    Write-Host "    el motor responde con error:`n$probeOut" -ForegroundColor Yellow
    Stop-WithError ('el motor de Docker no esta sano. El pipe existe pero la VM Linux no ' +
        'atiende (sintoma tipico en com.docker.backend: "connect tcp 192.168.65.7:2375: ' +
        'no route to host" o "compose [start] exit status 1" en la app Compose). ' +
        'Arreglo: docker desktop restart  y volver a lanzar este script.')
}
Write-Host "    engine $probeOut"

# --------------------------------------------------------------------------- #
# 3) arranque
# --------------------------------------------------------------------------- #
if ($Build) {
    Write-Step 'docker compose up -d --build'
    & docker compose up -d --build
} else {
    Write-Step 'docker compose up -d'
    & docker compose up -d
}
if ($LASTEXITCODE -ne 0) {
    Stop-WithError 'docker compose up fallo (ver salida de arriba)'
}

# --------------------------------------------------------------------------- #
# 4) espera del arranque
# --------------------------------------------------------------------------- #
Write-Step "esperando 'Uvicorn running' (max. $TimeoutSeconds s)"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$started = $false
$logs = ''
while ((Get-Date) -lt $deadline) {
    $logs = (& docker compose logs --tail 300 2>&1 | Out-String)
    if ($logs -match 'conf\.yaml is required|/app/conf/conf\.yaml not found') {
        Stop-WithError ('el contenedor no ve /app/conf/conf.yaml. Comprueba el bind mount con: ' +
            'docker compose exec -T open-llm-vtuber ls -l /app/conf')
    }
    if ($logs -match 'Uvicorn running on') {
        $started = $true
        break
    }
    Start-Sleep -Seconds 5
}
if ($started) {
    $ready = ($logs -split "`n") | Where-Object { $_ -match 'Uvicorn running on' } | Select-Object -Last 1
    Write-Host "    listo: $($ready.Trim())"
} else {
    Write-Host "    AVISO: no aparecio 'Uvicorn running' en $TimeoutSeconds s; sigue con: docker compose logs -f" -ForegroundColor Yellow
}

# --------------------------------------------------------------------------- #
# 5) verificacion dentro del contenedor
# --------------------------------------------------------------------------- #
Write-Step 'verificando /app/conf dentro del contenedor'
& docker compose exec -T open-llm-vtuber sh -c 'ls -l /app/conf/conf.yaml /app/conf.yaml'
& docker compose exec -T open-llm-vtuber sh -c "grep -n '^  host:' /app/conf.yaml | head -n 1"
& docker compose ps

Write-Host ''
Write-Host 'Web:        http://localhost:12393/' -ForegroundColor Green
Write-Host 'Overlay:    http://localhost:12393/web-tool/stage-test.html' -ForegroundColor Green
Write-Host 'Stage API:  curl.exe -s http://localhost:12393/api/stage' -ForegroundColor Green
Write-Host 'OBS en Docker: scheduler_config.obs.host debe ser host.docker.internal' -ForegroundColor Green

