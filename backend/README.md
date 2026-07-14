# HELIOS OS & SevraOS Edge Telemetry Backend

This directory contains the backend implementation for the HELIOS OS platform and the SevraOS Edge Telemetry gateway. It operates as part of the wider [Sevra Healthcare Operating Ecosystem](file:///c:/Users/ThePC/SevraOS/README.md).

## 🚀 Completed Backend Integrations (SevraOS Edge)

- **Static Asset Delivery**: Serves the [SevraOS Patient Terminal Frontend](file:///c:/Users/ThePC/SevraOS/frontend/README.md) web assets directly from the root `/` URL.
- **WebSocket Streaming**: Exposes `/ws/telemetry` which pushes high-frequency, drift-simulated patient vitals (Heart Rate, Blood Pressure, SpO2, Temperature, Blood Glucose) every second.
- **API Status Registers**: Exposes `/api/status` endpoint to report database connectivity, backup status, and system uptime indicators.

## 📁 Directory Structure (Combined)

```text
backend/
├── app/                 # SevraOS Edge Telemetry main uvicorn app
│   └── main.py          # FastAPI server initialization, static mapping, and WebSockets
├── dashboard/           # Dashboard backend microservice
├── database/            # Database configurations and schemas
├── eventbus/            # Eventbus producer/consumer integration
├── integration/         # HL7 / FHIR integrations
├── Dockerfile           # Edge / Production deployment container configuration
├── requirements.txt     # Local edge dependencies
└── pyproject.toml       # Production backend package manager configuration
```

Detailed links:
- 💻 **Edge App**: See the gateway code in [app/main.py](file:///c:/Users/ThePC/SevraOS/backend/app/main.py).
- 🗄️ **Database Service**: See the storage and sync engine implementation details in the [Database Service README](file:///c:/Users/ThePC/SevraOS/backend/database/README.md).
- ⚡ **Event Bus**: Powered by Redis Streams, see [eventbus/](file:///c:/Users/ThePC/SevraOS/backend/eventbus/).
- 🔌 **Integration Layer**: FHIR mapping and HL7 parsing, see [integration/](file:///c:/Users/ThePC/SevraOS/backend/integration/).
- ⚙️ **Configurations**: See root [Dockerfile](file:///c:/Users/ThePC/SevraOS/backend/Dockerfile), [requirements.txt](file:///c:/Users/ThePC/SevraOS/backend/requirements.txt), and [pyproject.toml](file:///c:/Users/ThePC/SevraOS/backend/pyproject.toml).

## 🛠️ Execution & Local Testing

### Running the SevraOS Edge Telemetry gateway:
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

### Running the HELIOS OS Central Services locally:
See the root [Ecosystem README](file:///c:/Users/ThePC/SevraOS/README.md) for full deployment instructions.
