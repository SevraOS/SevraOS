# HELIOS OS + SEVRA AI — Architecture
# Section 2: Backend Service Architecture

---

## 2.1 Medical Device Integration Layer (MDIL)

**Purpose:** Sole entry point for all device data. Translates every protocol into a
unified internal JSON format. Protocol complexity does not exist beyond this layer.

**Inputs:**
- HL7 v2.x via TCP/MLLP
- MQTT topics from IoT device brokers
- DICOM waveform streams
- RS-232/Serial port data
- REST webhooks from FHIR-capable devices
- Device Simulator payloads (dev/QA mode)

**Outputs:**
- Protocol-Normalized Device Payload → `stream:mdil.raw`
- Parse errors → `stream:mdil.parse_errors`
- Lifecycle events → `stream:device.lifecycle`

**Dependencies:**
- Redis 7.x (stream producer)
- Device Registry (device-to-protocol config store)
- SQLite edge buffer (offline failsafe)

**Responsibilities:**
- Maintain Device Registry: device IDs, protocols, ward/bed mappings
- Handle connection lifecycle per device: connect, reconnect, timeout, drop
- Invoke correct protocol adapter per device registration
- Attach metadata: device_id, facility_id, received_at, protocol_type
- Log ALL raw messages to audit trail BEFORE any transformation
- Support simulator injection mode
- Emit device lifecycle events (connected / disconnected / error)

**Failure Handling:**
| Failure | Response |
|---|---|
| Device disconnect | Log, exponential reconnect backoff, emit lifecycle event |
| Parse failure | Write raw + error to stream:mdil.parse_errors |
| Redis unavailable | Buffer to SQLite edge store; replay on Redis recovery |
| Unknown device | Reject, log, alert monitoring |

---

## 2.2 Collectors Service

**Purpose:** First internal pipeline stage. Assigns UUIDs, resolves patient identity,
wraps payloads in the standard Internal Event Envelope.

**Inputs:** `stream:mdil.raw`

**Outputs:** Internal Event Envelopes → `stream:collector.raw`

**Internal Event Envelope Schema:**
```
event_id          — UUID v4, assigned here, propagated forever (idempotency key)
device_id         — Source device identifier
patient_id        — Resolved from Device Registry (null if unresolved)
facility_id       — Hospital/facility identifier
ward              — Ward identifier
bed               — Bed identifier
received_at       — UTC ISO-8601 timestamp
source_protocol   — HL7v2 | MQTT | DICOM | Serial | FHIR | Simulator
schema_version    — Internal envelope version
payload           — Original protocol-normalized device data
resolution_status — resolved | unresolved
```

**Dependencies:**
- Redis Streams (consumer + producer)
- Patient-Device Mapping Registry (read-only)

**Responsibilities:**
- Consume from stream:mdil.raw as consumer group `collectors-group`
- Resolve patient_id from device-patient mapping
- Assign event_id (UUID v4)
- Wrap in Internal Event Envelope
- Emit to stream:collector.raw
- ACK Redis message ONLY after successful downstream write

**Failure Handling:**
| Failure | Response |
|---|---|
| Patient resolution fails | Emit with patient_id: null, resolution_status: unresolved |
| Redis write fails | Retry with exponential backoff |
| Service crash | PEL re-delivery on restart; at-least-once guaranteed |

---

## 2.3 Validation Service

**Purpose:** Pipeline quality gate. Ensures only structurally complete, domain-valid,
and clinically plausible events proceed. Nothing is silently dropped.

**Inputs:** `stream:collector.raw`

**Outputs:**
- Passed → `stream:validation.passed`
- Failed → `stream:validation.failed` (with full error context)

**Validation Chain:**

Tier 1 — Structural:
- JSON Schema conformance to Internal Event Envelope schema
- Required field presence check
- UUID v4 format on event_id
- Data type correctness

Tier 2 — Domain:
- device_id exists in Device Registry
- facility_id is a registered facility
- received_at within ±5 min clock drift window
- schema_version is supported

Tier 3 — Clinical Plausibility:
```
Heart Rate:       0–300 bpm (reject); 40–180 (warn)
SpO2:             50–100% (reject below 50); warn below 92%
Systolic BP:      40–300 mmHg (reject outside)
Diastolic BP:     20–200 mmHg (reject outside)
Temperature:      25.0–45.0 °C (reject outside)
Respiratory Rate: 0–80 /min (reject outside)
GCS:              3–15 (reject outside)
```

**Dependencies:**
- Redis Streams (consumer + dual producer)
- Clinical rules config store (read-only)
- JSON Schema registry

**Responsibilities:**
- Run all three tiers sequentially
- Attach validation_result: {status, errors[], warnings[], validated_at, validator_version}
- Route to correct stream based on status
- Degraded mode: if rules store unavailable, run Tiers 1 & 2 only, flag as degraded
- Fully stateless and idempotent

---

## 2.4 Normalization Service

**Purpose:** Converts validated events into a canonical FHIR R4-aligned data model.
The final transformation before events become first-class clinical records.

**Inputs:** `stream:validation.passed`

**Outputs:** FHIR R4 Normalized Clinical Events → `stream:normalized.events`

**Transformations Applied:**
| Dimension | Before | After |
|---|---|---|
| Units | Device-specific (mg/dL, lbs) | UCUM standard (/min, mmHg, °C) |
| Codes | Device codes ("HR", "BP") | LOINC codes (8867-4, 55284-4) |
| Timestamps | Device-local, various formats | UTC ISO-8601 with offset |
| Structure | Internal envelope | FHIR R4 Observation resource |
| Provenance | None | FHIR Provenance resource attached |

**Dependencies:**
- Redis Streams (consumer + producer)
- UCUM unit conversion tables (read-only)
- LOINC/SNOMED code mapping tables (read-only)
- FHIR R4 canonical model definitions

**Responsibilities:**
- Consume from stream:validation.passed as `normalization-group`
- Apply unit, code, and timestamp normalization
- Construct valid FHIR R4 Observation resource per observation
- Attach FHIR Provenance tracing full pipeline lineage
- Tag every output with canonical schema_version
- Fully stateless and idempotent

---

## 2.5 Event Bus Service (Redis Streams)

**Purpose:** Central nervous system of the platform. Decouples all services.
Producers write without knowing consumers. Consumers read independently.

**Infrastructure:**
- Redis 7.x with AOF persistence (fsync: everysec)
- Redis Sentinel for HA in production (1 primary, 2 replicas, 3 sentinels)
- Redis Cluster for horizontal scale-out beyond single-node capacity

**Guarantees:**
- At-least-once delivery via consumer group ACK pattern
- Message persistence with minimum 72-hour retention
- Full replay from any stream offset
- Multiple independent consumer groups per stream
- PEL (Pending Entries List) for unacknowledged message tracking

**Stream Topology:**
| Stream | Producer | Consumers |
|---|---|---|
| stream:mdil.raw | MDIL | Collectors |
| stream:mdil.parse_errors | MDIL | Monitoring |
| stream:collector.raw | Collectors | Validation |
| stream:validation.passed | Validation | Normalization |
| stream:validation.failed | Validation | Monitoring, Review |
| stream:normalized.events | Normalization | Database, Dashboard, AI |
| stream:ai.insights | AI Service | Database, Dashboard, Hospital |
| stream:hospital.outbound | Hospital Integration | Hospital Delivery |
| stream:hospital.delivery_failed | Hospital Integration | Monitoring |
| stream:device.lifecycle | MDIL | Monitoring, Dashboard |
| stream:audit.events | All Services | Security |
| stream:system.alerts | Monitoring | Ops |

---

## 2.6 Database Service

**Purpose:** Sole authority for all persistent writes. No other service writes
to SQLite, PostgreSQL, or Object Storage directly.

**Inputs:**
- stream:normalized.events (consumer group: db-service-group)
- stream:ai.insights (consumer group: db-service-group)
- stream:audit.events (consumer group: security-audit-group)

**Outputs:**
- Clinical records → SQLite + SQLCipher (edge, offline-first)
- Records synced → PostgreSQL (central)
- Large binary payloads → MinIO Object Storage

**Storage Hierarchy:**
```
Tier 1: SQLite + SQLCipher     — Local edge, encrypted, always available
Tier 2: PostgreSQL             — Central relational, sync target
Tier 3: MinIO Object Storage   — DICOM, waveforms, large blobs
Tier 4: Redis Cache            — Current-state projection for dashboard
```

**Responsibilities:**
- Write to SQLite FIRST (offline-first guarantee)
- Asynchronously sync SQLite → PostgreSQL on connectivity
- Conflict resolution: last-write-wins by received_at timestamp
- Enforce encryption at rest (SQLCipher + PostgreSQL TDE)
- Manage data retention policies (hot/warm/cold tiering)
- Never expose a direct write API to other services

---

## 2.7 Dashboard Service

**Purpose:** Real-time clinical visibility layer. Pushes live patient vital data
to clinicians via WebSocket. Stateless and horizontally scalable.

**Inputs:**
- stream:normalized.events
- stream:ai.insights
- stream:device.lifecycle

**Outputs:**
- Real-time WebSocket events to browser/desktop clients
- REST responses for historical queries (proxied to Database Service read-only)

**Dependencies:**
- Redis Streams (consumer)
- Redis Cache (current-state projection store)
- Database Service (read-only query interface)
- WebSocket server infrastructure

**Responsibilities:**
- Maintain current-state projection per patient in Redis Cache
- Push delta events to subscribed WebSocket clients
- Support ward/patient subscription scoping
- Apply dashboard-level alert thresholds
- Handle client reconnect with missed-event replay
- Rebuild projection from event stream on service restart

---

## 2.8 AI Service (SEVRA AI)

**Purpose:** Clinical intelligence engine. Applies rule-based scoring and ML
inference to normalized observations. Produces explainable clinical insights.

**Inputs:**
- stream:normalized.events
- Historical patient baseline (read-only via Database Service interface)

**Outputs:** stream:ai.insights

**Insight Payload Schema:**
```
insight_id        — UUID (derived from event_id + model_id for idempotency)
patient_id        — Target patient
model_id          — Model identifier
model_version     — Semantic version
insight_type      — early_warning | anomaly | prediction | alert
severity          — info | warning | critical
score             — {news2: N, mews: N, sofa: N}
confidence_score  — 0.0 to 1.0
clinical_rationale — Human-readable explanation (mandatory, no black-box alerts)
triggered_by      — List of contributing event_ids
generated_at      — UTC timestamp
```

**Built-in Clinical Models:**
- NEWS2 — National Early Warning Score 2
- MEWS — Modified Early Warning Score
- SOFA — Sequential Organ Failure Assessment
- ML Anomaly Detector — Pattern-based deterioration (sliding window)
- Sepsis Risk Model — Predictive sepsis probability scoring

**SLAs:**
- Inference latency: < 500ms per event (P99)
- Model hot-swap without service restart
- All insights must include clinical_rationale

---

## 2.9 Hospital Integration Layer (HIL)

**Purpose:** Bidirectional data exchange with external hospital systems (HIS/EMR/EHR).
The platform's external boundary.

**Inputs:**
- stream:ai.insights
- stream:normalized.events (filtered by subscription config)
- Inbound feeds from external systems (ADT, orders, medications)

**Outputs:**
- HL7 FHIR R4 bundles to registered hospital endpoints
- HL7 v2 ORU messages over MLLP
- Inbound events re-injected to stream:collector.raw

**Dependencies:**
- Redis Streams (consumer + producer)
- External hospital connectors (FHIR REST, MLLP, proprietary)
- Credential vault
- stream:audit.events (all transmissions logged)

**Responsibilities:**
- Maintain Hospital Registry (endpoints, protocols, subscription filters)
- Apply consent and data-sharing rules before outbound transmission
- Confirm delivery; retry with exponential backoff on failure
- Log every transmission with payload hash
- Queue persistent failures to stream:hospital.delivery_failed

---

## 2.10 Monitoring Service

**Purpose:** System-wide observability. No service monitors itself.
Centralized metrics, logs, health checks, alerting.

**Components:**
- Prometheus — Metrics collection (scrapes all service /metrics endpoints)
- Grafana — Operational + clinical SLA dashboards
- Alertmanager — Alert routing (Slack, PagerDuty, email)
- Loki — Structured log aggregation
- Health Check Engine — /health /ready /live per service

**Inputs:**
- Prometheus scrape from all service metrics endpoints
- Structured JSON logs from all services
- stream:device.lifecycle, stream:validation.failed, stream:system.alerts

**Outputs:**
- Prometheus TSDB (metric storage)
- Grafana dashboards
- Alertmanager notifications
- Unified system health API

---

## 2.11 Security Service

**Purpose:** Centralized identity, access, and audit. Auth logic is NOT embedded
in individual services — delegated exclusively here.

**Clinical RBAC Roles:**
```
clinician       — Read patient data, acknowledge AI alerts
nurse           — Read/update vitals, acknowledge alerts
admin           — Full system access, user management
device_operator — Device registration and management
auditor         — Read-only access to all audit logs and reports
ai_reviewer     — Review and approve AI insights and model versions
```

**Inputs:**
- Authentication requests (login, token refresh)
- Authorization queries from other services
- stream:audit.events

**Outputs:**
- RS256-signed JWT access tokens (15 min TTL)
- RS256-signed JWT refresh tokens (7 day TTL)
- RBAC permit/deny decisions
- Immutable audit log records

**Dependencies:**
- PostgreSQL (user store, role store, audit log)
- Redis (token blacklist, session invalidation cache)
- HashiCorp Vault / Docker Secrets (signing key storage)

---

## 2.12 Service Dependency Matrix

| Service | Reads Streams | Writes Streams | Data Stores |
|---|---|---|---|
| MDIL | — | mdil.raw, parse_errors, device.lifecycle | SQLite edge |
| Collectors | mdil.raw | collector.raw | — |
| Validation | collector.raw | validation.passed, validation.failed | — |
| Normalization | validation.passed | normalized.events | — |
| Database | normalized.events, ai.insights | — | SQLite, PostgreSQL, MinIO |
| Dashboard | normalized.events, ai.insights, device.lifecycle | — | Redis Cache |
| AI Service | normalized.events | ai.insights | — |
| Hospital Integration | ai.insights, normalized.events | hospital.outbound, collector.raw | — |
| Monitoring | All error/lifecycle streams | system.alerts | Prometheus TSDB |
| Security | audit.events | — | PostgreSQL, Redis |
