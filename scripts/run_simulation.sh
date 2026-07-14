#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# SevraOS Patient Terminal — Local Simulation Runner
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

echo -e "\033[0;32m🏥 Launching SevraOS Kiosk Simulation...\033[0m"

# Navigate to backend
CDPATH="" cd -- "$(dirname -- "$0")/../backend"

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "\033[0;33mCreating Python virtual environment...\033[0m"
    python3 -m venv venv
fi

# Activate venv & install deps
echo -e "\033[0;33mActivating virtual environment & verifying dependencies...\033[0m"
source venv/bin/activate
pip install -r requirements.txt

# Auto-open browser (macOS/Linux compatible)
sleep 1
echo -e "\033[0;36mOpening web browser to http://localhost:8000...\033[0m"
if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:8000"
elif command -v open > /dev/null; then
    open "http://localhost:8000"
fi

# Launch FastAPI Edge server
echo -e "\033[0;32mStarting FastAPI Edge Telemetry server...\033[0m"
uvicorn app.main:app --port 8000
