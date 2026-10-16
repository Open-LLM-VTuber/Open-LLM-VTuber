#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$host.UI.RawUI.WindowTitle = "Open-LLM-VTuber Installer"

function Write-Step {
    param([string]$Message)
    Write-Host "[...] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Open-LLM-VTuber One-Click Installer" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$installDir = Join-Path $env:USERPROFILE "Open-LLM-VTuber"

Write-Step "Checking prerequisites..."

if (-not (Test-Path "C:\Python311")) {
    Write-Host "Python 3.11 not found. Installing..." -ForegroundColor Yellow
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $pythonInstaller = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Remove-Item $pythonInstaller -Force
    $env:Path += ";C:\Python311;C:\Python311\Scripts"
    Write-Success "Python 3.11 installed"
} else {
    Write-Success "Python 3.11 found"
}

Write-Step "Checking GPU (optional)..."
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    Write-Success "NVIDIA GPU detected"
    $gpuAvailable = $true
} else {
    Write-Host "No NVIDIA GPU detected. CPU mode will be used." -ForegroundColor Yellow
    $gpuAvailable = $false
}

Write-Step "Cloning repository..."
if (Test-Path $installDir) {
    Write-Host "Existing installation found. Pulling latest..." -ForegroundColor Yellow
    Set-Location $installDir
    git pull --ff-only
    Write-Success "Repository updated"
} else {
    git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git $installDir
    Write-Success "Repository cloned"
}

Set-Location $installDir

Write-Step "Creating virtual environment..."
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Success "Virtual environment created"
} else {
    Write-Success "Virtual environment exists"
}

Write-Step "Installing dependencies..."
& .\venv\Scripts\python.exe -m pip install --upgrade pip
if ($gpuAvailable) {
    & .\venv\Scripts\python.exe -m pip install -r requirements.txt
} else {
    & .\venv\Scripts\python.exe -m pip install -r requirements.txt
    & .\venv\Scripts\python.exe -m pip uninstall -y onnxruntime-gpu onnxruntime
    & .\venv\Scripts\python.exe -m pip install onnxruntime
}
Write-Success "Dependencies installed"

Write-Step "Creating data directories..."
$dirs = @("data", "cache", "logs", "config", "live2d-models")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "Directories created"

Write-Step "Checking for Live2D model..."
$modelPath = Join-Path $installDir "live2d-models"
if ((Get-ChildItem -Path $modelPath -Directory -Recurse -Filter "*.model3.json" -ErrorAction SilentlyContinue).Count -eq 0) {
    Write-Host "No Live2D model found. Downloading default..." -ForegroundColor Yellow
    # Default model placeholder
    Write-Host "Please download your Live2D model and place it in live2d-models/" -ForegroundColor Yellow
} else {
    Write-Success "Live2D model found"
}

Write-Step "Creating desktop shortcut..."
$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut("$env:USERPROFILE\Desktop\Open-LLM-VTuber.lnk")
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$installDir\run_server.ps1`""
$shortcut.WorkingDirectory = $installDir
$shortcut.Save()
Write-Success "Desktop shortcut created"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host " Installation Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start Open-LLM-VTuber:" -ForegroundColor White
Write-Host "  1. Double-click the desktop shortcut" -ForegroundColor White
Write-Host "  2. Or run: cd $installDir && .\run_server.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Web interface: http://localhost:8000" -ForegroundColor White
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"