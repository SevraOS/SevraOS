# ═══════════════════════════════════════════════════════════════
# SevraOS Patient Terminal — Local Simulation Runner
# ═══════════════════════════════════════════════════════════════

Write-Host "🏥 Launching SevraOS Kiosk Simulation..." -ForegroundColor Green

# 1. Navigate to backend
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path "$ScriptDir\..\backend"
cd $BackendDir

# 2. Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# 3. Activate venv & install deps
Write-Host "Activating virtual environment & verifying dependencies..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
pip install -r requirements.txt

# 4. Auto-open browser
Start-Sleep -Seconds 1
Write-Host "Opening web browser to http://localhost:8000..." -ForegroundColor Cyan
Start-Process "http://localhost:8000"

# 5. Launch FastAPI Edge server
Write-Host "Starting FastAPI Edge Telemetry server..." -ForegroundColor Green
uvicorn app.main:app --port 8000
