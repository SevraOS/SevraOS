# HELIOS OS + SEVRA AI
## Hospital Integration Architecture

### Folder Structure & Responsibilities (Section 1)

| Folder | Responsibility |
|---|---|
| `fhir/` | Pydantic models for FHIR R4 resources, validation, serialization. |
| `hl7/` | Parsers and routers for HL7 v2.x (ADT, ORU) messages via MLLP or API. |
| `sync/` | Bidirectional synchronization engine (Database <-> EHR) with conflict resolution. |
| `mappings/` | Transformation rules from internal Canonical Events to FHIR/HL7 structures. |
| `adapters/` | Vendor-specific clients (Epic, Cerner, Generic) mapping to their specific APIs. |
| `validators/` | Schema validation for outgoing/incoming healthcare payloads. |
| `repositories/` | Local sync state, audit logs, and mapping references storage. |
| `services/` | Business orchestration bridging Event Bus to External Systems. |
| `health/` | EHR connection status monitoring and Circuit Breakers. |
| `metrics/` | Prometheus instrumentation for sync success, latency, and FHIR throughput. |

---

### Hospital Integration Diagrams (Section 2)

#### 1. Architecture Diagram
```mermaid
graph TD
    A[Redis Event Bus] -->|Canonical Event| B(Integration Orchestrator)
    B --> C{Protocol Router}
    
    C -->|FHIR R4| D[FHIR Mapper]
    C -->|HL7 v2.x| E[HL7 Builder]
    
    D --> F[Epic / Cerner Adapter]
    E --> G[Legacy HIS / LIS Adapter]
    
    F -->|HTTPS mTLS| H[(EHR Platform)]
    G -->|MLLP/VPN| I[(Hospital Systems)]
```

#### 2. Offline Sync Diagram
```mermaid
sequenceDiagram
    participant DB as SQLite (Edge)
    participant Engine as Sync Engine
    participant HIS as Hospital System

    Engine->>HIS: Ping
    HIS-->>Engine: Timeout (Offline)
    Engine->>DB: Set SyncState = PENDING
    Note over DB, Engine: System operates offline normally.
    
    HIS-->>Engine: Connection Restored
    Engine->>DB: Fetch PENDING records
    Engine->>HIS: Push Batch (Conflict Resolution applied)
    HIS-->>Engine: ACK
    Engine->>DB: Set SyncState = SYNCED
```
