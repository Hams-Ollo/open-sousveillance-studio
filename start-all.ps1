# PowerShell Startup Script for Open Sousveillance Studio
# This script activates the virtual environment, upgrades pip, installs requirements,
# and launches the backend (FastAPI) and frontend (Streamlit) in separate terminals.

# Set project root
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $projectRoot

# Activate virtual environment
$venvPath = ".venv/Scripts/Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..."
    . $venvPath
} else {
    Write-Host "Virtual environment not found. Please create it first."
    exit 1
}

# Upgrade pip
Write-Host "Upgrading pip..."
pip install --upgrade pip

# Install requirements only if not already satisfied
if (Test-Path "requirements.txt") {
    Write-Host "Checking Python requirements..."
    $missing = pip install --dry-run -r requirements.txt 2>&1 | Select-String 'would be installed' | Measure-Object | Select-Object -ExpandProperty Count
    if ($missing -gt 0) {
        Write-Host "Installing missing requirements..."
        pip install -r requirements.txt
    } else {
        Write-Host "All requirements already satisfied."
    }
} else {
    Write-Host "requirements.txt not found!"
    exit 1
}

# Create .pids directory for process tracking
$pidsDir = Join-Path $projectRoot ".pids"
if (-not (Test-Path $pidsDir)) {
    New-Item -ItemType Directory -Path $pidsDir | Out-Null
}

# Check if already running
$existingPids = @("fastapi.pid", "streamlit.pid") | ForEach-Object {
    $pidFile = Join-Path $pidsDir $_
    if (Test-Path $pidFile) {
        $savedPid = Get-Content $pidFile
        try {
            $null = Get-Process -Id $savedPid -ErrorAction Stop
            Write-Host "WARNING: $_ process already running (PID $savedPid). Use stop-all.ps1 first." -ForegroundColor Yellow
            return $true
        } catch {
            Remove-Item $pidFile -Force
        }
    }
    return $false
}
if ($existingPids -contains $true) {
    Write-Host "Some services are already running. Stop them first with .\stop-all.ps1" -ForegroundColor Yellow
    exit 1
}

# Start FastAPI backend in new terminal
Write-Host "Starting FastAPI backend in new terminal..."
$fastapi = Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd '$projectRoot'; . .venv/Scripts/Activate.ps1; uvicorn src.app:app --reload --port 8000" -PassThru
$fastapi.Id | Out-File (Join-Path $pidsDir "fastapi.pid") -Encoding ascii

# Start Streamlit frontend in new terminal (will open browser)
Write-Host "Starting Streamlit frontend in new terminal..."
$streamlit = Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd '$projectRoot'; . .venv/Scripts/Activate.ps1; streamlit run src/ui/app.py" -PassThru
$streamlit.Id | Out-File (Join-Path $pidsDir "streamlit.pid") -Encoding ascii

Write-Host ""
Write-Host "All services started:" -ForegroundColor Green
Write-Host "  FastAPI  : http://localhost:8000  (PID $($fastapi.Id))"
Write-Host "  Streamlit: http://localhost:8501  (PID $($streamlit.Id))"
Write-Host "  PID files: $pidsDir"
Write-Host ""
Write-Host "To stop all services: .\stop-all.ps1" -ForegroundColor Cyan
