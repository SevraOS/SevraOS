"""
HELIOS OS + SEVRA AI
Locust Load Testing Framework (Section 17)
"""

from locust import HttpUser, task, between
from locust import events
import websockets
import asyncio
import json
import threading

class HeliosRESTUser(HttpUser):
    wait_time = between(1, 2)
    
    def on_start(self):
        # Authenticate and get JWT token
        # In a real test, mock the auth endpoint
        self.token = "mock_jwt_token"
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def get_patients(self):
        self.client.get("/api/v1/patients", headers=self.headers, name="Get Patients List")

    @task(1)
    def get_patient_summary(self):
        self.client.get("/api/v1/patients/pt-123/summary", headers=self.headers, name="Get Patient Summary")
        
    @task(2)
    def get_active_alerts(self):
        self.client.get("/api/v1/alerts/active", headers=self.headers, name="Get Active Alerts")

class HeliosWebSocketUser(HttpUser):
    wait_time = between(5, 15)
    
    @task
    def stream_vitals(self):
        # Simulate WebSocket connection using an async thread
        def ws_thread():
            async def run():
                uri = f"ws://localhost:8000/ws/stream?token=mock_jwt_token"
                try:
                    async with websockets.connect(uri) as ws:
                        await ws.send(json.dumps({"action": "subscribe", "channel": "patient:pt-123:vitals"}))
                        # Hold connection and receive messages
                        for _ in range(10):
                            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                            events.request.fire(
                                request_type="WebSocket",
                                name="Receive Vital",
                                response_time=10,
                                response_length=len(msg),
                                exception=None
                            )
                except Exception as e:
                    events.request.fire(
                        request_type="WebSocket",
                        name="Receive Vital",
                        response_time=0,
                        response_length=0,
                        exception=e
                    )
            asyncio.run(run())
            
        t = threading.Thread(target=ws_thread)
        t.start()
        t.join(timeout=25)
