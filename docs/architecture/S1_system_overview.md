# HELIOS OS + SEVRA AI — Architecture
# Section 1: Complete System Overview

---

## 1.1 What Is HELIOS OS + SEVRA AI?

**HELIOS OS** is a real-time, offline-first healthcare operating layer that ingests, validates,
normalizes, and persists clinical data from medical devices at the point of care.
It operates fully autonomously at the hospital edge — even without cloud connectivity —
and syncs with central infrastructure when connectivity is available.

**SEVRA AI** is the clinical intelligence layer on top of HELIOS OS.
It consumes normalized FHIR-aligned events from the event bus and applies ML models
to produce early warning scores, deterioration predictions, and anomaly detection.

Together they form a **vertically integrated, event-driven healthcare intelligence platform**
spanning every data stage from bedside device to AI-assisted clinical alert.

---

## 1.2 Core Design Principles

| Principle          | Contract                                                               |
|--------------------|------------------------------------------------------------------------|
| Offline First      | Full operation without external connectivity. Local store is primary truth. |
| Event Driven       | All inter-service data comms go through Redis Streams. No direct calls. |
| Fault Tolerant     | Any service may crash without data loss. Bus persists until ACK.        |
| Highly Available   | Critical services replicated. No single point of failure in data path.  |
| Scalable           | Services stateless where possible. Horizontal scaling is primary.       |
| Dockerized         | Every service runs in a container. No bare-metal assumptions.           |
| Secure             | Every data boundary encrypted. Auth/authz at every service edge.        |
| Healthcare Compliant | HIPAA, HL7 FHIR R4, DICOM are design constraints, not afterthoughts. |
| Future Expandable  | New services plug into event bus without modifying existing services.   |

---

## 1.3 What the System Does

Medical devices (monitors, ventilators, wearables, infusion pumps) or a simulator emit
raw clinical data in heterogeneous protocols: HL7 v2, MQTT, DICOM, Serial, proprietary binary.

**MDIL** receives raw data and translates all protocols into a unified internal JSON format.
Protocol complexity never leaks beyond this layer.

**Collectors** wraps translated payloads into a standard Internal Event Envelope —
assigning a global UUID, resolving patient identity, stamping metadata.

**Validation** applies a 3-tier quality gate: structural → domain → clinical plausibility.
Failed events are quarantined; passed events proceed.

**Normalization** maps validated events to canonical FHIR R4 Observations,
normalizing units (UCUM), codes (LOINC), timestamps (UTC ISO-8601).

**Redis Streams Event Bus** fans out normalized events to 3 independent consumers:
Database Service, Dashboard Service, and AI Service — all in parallel.

**Database Service** persists to SQLite first (offline-first), then syncs to PostgreSQL.

**Dashboard Service** pushes real-time vital sign updates to clinicians via WebSocket.

**AI Service (SEVRA AI)** runs ML inference and clinical scoring (NEWS2/MEWS/SOFA),
publishing clinical insights back to the event bus.

**Hospital Integration Layer** translates events and AI insights to external HIS/EMR systems
over HL7 FHIR, HL7 v2 MLLP, or proprietary APIs.

---

## 1.4 Data Flow Diagram

```
Medical Devices / Simulator
  (HL7 v2 | MQTT | DICOM | Serial | FHIR | Binary)
          |
          v
 MEDICAL DEVICE INTEGRATION LAYER (MDIL)
  Protocol Adapters → Unified Internal JSON
  Writes: stream:mdil.raw
          |
          v
     COLLECTORS SERVICE
  UUID | Patient Resolution | Envelope
  Writes: stream:collector.raw
          |
          v
     VALIDATION SERVICE
  Structural → Domain → Clinical Plausibility
          |                |
          v                v
 stream:validation.passed  stream:validation.failed (DLQ)
          |
          v
  NORMALIZATION SERVICE
  FHIR R4 | LOINC | UCUM | UTC
  Writes: stream:normalized.events
          |
    ______+_____________
    |           |       |
    v           v       v
DATABASE   DASHBOARD  AI SERVICE (SEVRA AI)
SERVICE    SERVICE    ML Inference | NEWS2/MEWS/SOFA
SQLite     WebSocket  Writes: stream:ai.insights
PostgreSQL Real-time         |
                             v
                    HOSPITAL INTEGRATION LAYER
                    HL7 FHIR | HIS | EMR
```

---

## 1.5 Service Boundaries — Immutable Rules

1. No service reads from another service's database.
2. No service calls another service's internal API in the data hot-path.
3. Control-plane REST/gRPC permitted for health checks and config only.
4. Validation and Normalization are fully stateless — no persistent state.
5. AI Service is a pure consumer/producer — never writes to primary databases.
6. Database Service is the sole write authority to SQLite and PostgreSQL.
7. Security Service is the sole authority for token issuance and audit log writes.
