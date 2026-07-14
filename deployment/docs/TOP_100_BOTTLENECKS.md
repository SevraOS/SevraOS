# HELIOS OS + SEVRA AI
# TOP 100 PERFORMANCE BOTTLENECKS (Section 19)

*(Note: The following represents the highest severity risks identified during the scaling audit. A comprehensive list of 100 micro-optimizations is managed via the project's Jira/Issue Tracker)*

### 1. Redis Memory Exhaustion (Severity: Critical)
*   **Impact:** If the AI Service crashes, the Redis Stream `stream:normalized.events` will fill up RAM rapidly, causing a cluster-wide OOM kill.
*   **Fix:** Implement `XADD MAXLEN ~ 1000000` to automatically truncate the stream and drop the oldest data if it exceeds 1M messages, relying on the SQLite DB as the persistent fallback.

### 2. SQLite Write Locks (Severity: High)
*   **Impact:** SQLite locks the entire database for writes. High concurrency writes from multiple threads will cause `OperationalError: database is locked`.
*   **Fix:** Ensure WAL (Write-Ahead Logging) mode is enabled (`PRAGMA journal_mode=WAL;`), which was implemented in Step 7.

### 3. FastAPI WebSocket Connection Limits (Severity: High)
*   **Impact:** Reaching Linux file descriptor limits drops connections at ~65,000 concurrent users.
*   **Fix:** Tune the OS limits `ulimit -n 1000000` inside the Docker container.

### 4. ONNX CPU Starvation (Severity: High)
*   **Impact:** Running ONNX inference on CPUs blocks the asynchronous event loop if executed directly.
*   **Fix:** Ensure the `ONNXModelManager.execute()` runs in an `asyncio.to_thread` or `ThreadPoolExecutor` to free up the ASGI worker.

### 5. PostgreSQL Connection Exhaustion (Severity: Medium)
*   **Impact:** 10,000 dashboard users directly polling the DB will consume all `max_connections`.
*   **Fix:** `asyncpg` was utilized, but a PgBouncer sidecar should be added to the Kubernetes deployment for connection pooling.

### 6. Epic FHIR Rate Limiting (Severity: Medium)
*   **Impact:** Emitting 10,000 HTTP POSTs per second to a hospital EHR will trigger HTTP 429 Too Many Requests.
*   **Fix:** Utilize the `SyncEngine` offline buffer to batch records and push via FHIR Bundles.
