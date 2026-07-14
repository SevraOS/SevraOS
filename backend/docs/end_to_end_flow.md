# HELIOS OS + SEVRA AI
## End-to-End Flow (Section 26)

This document provides a complete walkthrough of data moving through the system, demonstrating the real-time AI and Dashboard integration.

### 1. Input: Patient Vital Reading
A clinical device attached to Patient `123` detects a sudden drop in Blood Pressure (90/60 mmHg). The MDIL Collector normalizes this to a `VitalEvent` and pushes it to the Redis Event Bus `stream:normalized.events`.

### 2. Transformation & Consumer
The **AI Vitals Consumer** (`backend/ai/consumers/vitals_consumer.py`) pulls the event from the stream asynchronously. 

### 3. Prediction & Inference
The event is passed to the AI Pipeline:
*   **Anomaly Detection:** The `AnomalyDetector` flags the 90 mmHg systolic value as a >3.0 Z-Score deviation from the patient's baseline.
*   **Risk Score:** The `RiskEngine` calculates a MEWS score of 4.
*   **ONNX Inference:** The `ONNXModelManager` feeds the normalized tensor into `deterioration_v1.onnx`, outputting a 0.88 risk probability.
*   **Aggregation:** The `PredictionAggregator` synthesizes these inputs into a final `PredictionEvent` with an 89% deterioration risk.

### 4. Alert Generation
The `AlertEngine` evaluates the 89% risk against the `CRITICAL_RISK_THRESHOLD` (0.85) and generates a `CRITICAL` AlertRecommendation.

### 5. Storage
The `PredictionEvent` and `AlertRecommendation` are published to `stream:ai.predictions` and `stream:ai.alerts`. The Step 7 Database Service syncs these seamlessly to the edge SQLite and central PostgreSQL databases.

### 6. Display
Simultaneously, the AI Consumer publishes the JSON payloads to the Redis Pub/Sub channels:
*   `dashboard:channels:patient:123:alerts`
The **Dashboard WebSocket Manager** (`backend/dashboard/websocket/manager.py`) receives this from Redis and instantly pushes the JSON to the UI of the Doctor viewing Patient `123`, causing a red critical flash on their screen.

### 7. Recovery & Failure Cases
*   **AI Service Crash:** If the ONNX container dies, unacknowledged events remain in the Redis Stream. When it restarts, it replays from its last `xack`, guaranteeing exactly-once processing.
*   **WebSocket Disconnect:** If the clinician's iPad drops Wi-Fi, the WebSocket disconnects. Upon reconnecting, the Dashboard UI will invoke the `GET /api/v1/alerts/active` REST endpoint to backfill any alerts missed during the outage.
