# HELIOS OS + SEVRA AI
## Dashboard Service Architecture

### Folder Structure & Responsibilities (Section 1)

| Folder | Responsibility |
|---|---|
| `api/` | Main FastAPI application factory, global middleware (CORS, Auth), and exception handlers. |
| `routers/` | FastAPI route definitions grouped by domain (`patients.py`, `vitals.py`, `alerts.py`). |
| `services/` | Business logic bridging routers to database repositories. |
| `websocket/` | Real-time connection manager, channel multiplexing (Pub/Sub via Redis), and live data emitters. |
| `schemas/` | Pydantic models for request validation and response serialization. |
| `repositories/` | (Reused or wrapped from `database` service) Data access layer. |
| `metrics/` | Prometheus metrics definitions for API latency and WebSocket concurrent connections. |
| `health/` | Kubernetes readiness/liveness probes. |
| `tests/` | Pytest suite with `TestClient` for APIs and WebSockets. |

---

### Dashboard Architecture Diagrams (Section 2)

#### 1. Architecture Diagram
```mermaid
graph TD
    UI[Frontend Client] -->|HTTPS REST| API(FastAPI Routers)
    UI -->|WSS| WS(WebSocket Manager)
    
    API --> AUTH[Security/RBAC]
    WS --> AUTH
    
    API --> DB[(PostgreSQL / SQLite)]
    WS --> REDIS[(Redis Pub/Sub)]
    
    REDIS -->|Live Events| WS
```

#### 2. Request Flow Diagram
```mermaid
sequenceDiagram
    participant Client
    participant Router
    participant Service
    participant Database

    Client->>Router: GET /api/v1/patients/123/vitals
    Router->>Auth: Validate JWT & RBAC
    Router->>Service: fetch_patient_vitals(123)
    Service->>Database: Query (Optimized TS Index)
    Database-->>Service: Return Rows
    Service-->>Router: Serialize to Pydantic
    Router-->>Client: JSON 200 OK
```

#### 3. WebSocket Flow Diagram
```mermaid
sequenceDiagram
    participant Client
    participant WSManager
    participant RedisPubSub
    participant AI_Service

    Client->>WSManager: Connect /ws?token=JWT
    WSManager->>Auth: Validate Token
    WSManager->>RedisPubSub: Subscribe to 'channel:patient:123'
    WSManager-->>Client: Connection Accepted
    
    AI_Service->>RedisPubSub: Publish Critical Alert
    RedisPubSub->>WSManager: Receive Event
    WSManager->>Client: Stream JSON Payload
```
