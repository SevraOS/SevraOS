# SevraOS Edge Telemetry Backend (Embedded)

This directory contains the FastAPI-based edge server for the Sevra patient terminal, embedded inside the [SevraOS Build Profile](file:///c:/Users/ThePC/SevraOS/sevraos/README.md). It acts as the local edge gateway hosting the patient dashboard interface and serving real-time telemetry datasets inside the live OS.

## 🚀 Completed Backend Integrations

- **Static Asset Delivery**: Serves the [Embedded Frontend UI](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/frontend/README.md) assets directly from the root `/` URL.
- **WebSocket Streaming**: Exposes `/ws/telemetry` which pushes high-frequency, drift-simulated patient vitals (Heart Rate, Blood Pressure, SpO2, Temperature, Blood Glucose) every second.
- **API Status Registers**: Exposes `/api/status` endpoint to report database connectivity, backup status, and system uptime indicators.

## 📁 Directory Structure

```text
backend/
├── app/
│   └── main.py          # FastAPI server initialization, static mapping, and WebSockets
├── Dockerfile           # Edge deployment container configuration
└── requirements.txt     # Dependencies (fastapi, uvicorn, websockets, aiofiles)
```

Detailed links:
- 💻 **Edge App Entry**: [app/main.py](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/backend/app/main.py).
- ⚙️ **Docker Config**: [Dockerfile](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/backend/Dockerfile).
- 📦 **Dependencies**: [requirements.txt](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/backend/requirements.txt).

## 🛠️ Execution & Local Testing

1. Initialize virtual environment and install packages:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Start the FastAPI uvicorn edge server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
3. Open `http://localhost:8000` in a web browser to view the client-side patient terminal dashboard.
