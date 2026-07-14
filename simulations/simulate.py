import time
import json
import random
import uuid
from datetime import datetime, timezone
import redis

# Connect to the Redis Event Bus (running on localhost:6379)
# The password is the one we set in the Docker environment
try:
    # First try with password (if .env was loaded properly)
    r = redis.Redis(host='localhost', port=6379, password='secure-redis-password', decode_responses=True)
    r.ping()
    print("✅ Connected to HELIOS Redis Event Bus (with password)!")
except redis.exceptions.AuthenticationError:
    # Fallback if docker was started without the .env file
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("✅ Connected to HELIOS Redis Event Bus (no password)!")
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
    exit(1)

patient_id = str(uuid.uuid4())
device_id = "SIM-MONITOR-001"

print(f"🏥 Starting Simulation for Patient: {patient_id}")
print(f"📡 Pushing data to Stream: helios.telemetry.raw")
print("-" * 50)

while True:
    try:
        # 1. Generate fake vitals
        heart_rate = random.randint(60, 100)
        systolic = random.randint(110, 130)
        diastolic = random.randint(70, 85)
        spo2 = random.randint(95, 100)
        temp = round(random.uniform(36.5, 37.5), 1)
        
        # We need to send them as individual telemetry frames per metric, or as a single raw block.
        # The MDIL Validation service expects RawReading format (JSON).
        # Let's send a heart rate frame
        timestamp = datetime.now(timezone.utc).isoformat()
        
        hr_reading = {
            "device_id": device_id,
            "patient_id": patient_id,
            "metric": "heart_rate",
            "value": float(heart_rate),
            "unit": "bpm",
            "timestamp": timestamp
        }

        # 2. Push to Redis Stream
        r.xadd("helios.telemetry.raw", {"payload": json.dumps(hr_reading)})
        print(f"[{timestamp}] Sent Heart Rate: {heart_rate} bpm")
        
        # Wait 1 second
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n⏹️ Simulator stopped.")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
