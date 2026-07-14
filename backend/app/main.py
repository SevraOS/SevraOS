import os
import random
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# Global state for telemetry simulation
telemetry_active = True

class VitalsData(BaseModel):
    hr: float
    bp: str
    temp: float
    spo2: float
    glucose: float

# Resolve path to the frontend directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "frontend"))

# API status endpoint
@app.get("/api/status")
def get_status():
    return {
        "status": "online" if telemetry_active else "offline",
        "database": "connected",
        "backup": "up-to-date",
        "uptime": "15d 8h 24m",
        "telemetry_active": telemetry_active
    }

# Simulated remote reboot
@app.post("/api/restart")
def restart_device():
    global telemetry_active
    telemetry_active = True
    return {"message": "Reboot instruction sent. Reconnecting telemetry...", "status": "online"}

# Simulated database synchronization
@app.post("/api/sync")
def sync_data():
    return {"message": "Syncing latest database registers... Completed.", "status": "synced"}

# Simulated telemetry stream disconnect
@app.post("/api/disconnect")
def disconnect_device():
    global telemetry_active
    telemetry_active = False
    return {"message": "Safely disconnected telemetry stream.", "status": "offline"}

# Simulated clinical risk calculation engine (NEWS2 scoring rule)
@app.post("/api/risk")
def calculate_risk(vitals: VitalsData):
    score = 0
    if vitals.hr > 110 or vitals.hr < 50:
        score += 3
    elif vitals.hr > 90 or vitals.hr < 60:
        score += 1
        
    if vitals.spo2 < 92:
        score += 3
    elif vitals.spo2 < 95:
        score += 2
        
    try:
        sys = int(vitals.bp.split('/')[0])
        if sys > 160 or sys < 90:
            score += 3
        elif sys > 140 or sys < 100:
            score += 1
    except Exception:
        pass
        
    risk_pct = min(100, int((score / 9) * 100))
    risk_pct = max(5, min(95, risk_pct + random.randint(-5, 5)))
    
    status_label = "Low Risk"
    if risk_pct > 70:
        status_label = "Critical Risk"
    elif risk_pct > 40:
        status_label = "Moderate Risk"
        
    return {
        "risk_percentage": risk_pct,
        "status_label": status_label
    }

# Patient telemetry streaming websocket
@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # Seed value trackers
    hr = 105
    spo2 = 97.2
    
    try:
        while True:
            if not telemetry_active:
                await websocket.send_json({"status": "disconnected"})
                await asyncio.sleep(1)
                continue
                
            # Drift simulation values
            hr += random.choice([-2, -1, 0, 1, 2])
            hr = min(130, max(65, hr))
            
            spo2 += random.choice([-0.2, -0.1, 0.0, 0.1, 0.2])
            spo2 = min(100.0, max(92.0, spo2))
            
            bp_sys = int(140 + hr * 0.15 + random.randint(-4, 4))
            bp_dia = int(80 + hr * 0.1 + random.randint(-3, 3))
            
            telemetry_data = {
                "status": "connected",
                "hr": hr,
                "bp": f"{bp_sys}/{bp_dia}",
                "temp": round(35.5 + random.random() * 0.6, 1),
                "spo2": round(spo2, 1),
                "glucose": round(6.2 + random.random() * 1.2, 1)
            }
            
            await websocket.send_json(telemetry_data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

# Setup Static Files Mounting
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    @app.get("/")
    def get_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
        
    @app.get("/{file_name}")
    def get_file(file_name: str):
        file_path = os.path.join(FRONTEND_DIR, file_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    print(f"Warning: frontend directory not found at {FRONTEND_DIR}")