import os
import random
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Resolve path to the frontend directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "frontend"))

# API status endpoint
@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "database": "connected",
        "backup": "up-to-date",
        "uptime": "15d 8h 24m"
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
            # Drift simulation values
            hr += random.choice([-2, -1, 0, 1, 2])
            hr = min(130, max(65, hr))
            
            spo2 += random.choice([-0.2, -0.1, 0.0, 0.1, 0.2])
            spo2 = min(100.0, max(92.0, spo2))
            
            bp_sys = int(140 + hr * 0.15 + random.randint(-4, 4))
            bp_dia = int(80 + hr * 0.1 + random.randint(-3, 3))
            
            telemetry_data = {
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