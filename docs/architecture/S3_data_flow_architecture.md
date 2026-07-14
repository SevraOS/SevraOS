# HELIOS OS + SEVRA AI — Architecture
# Section 3: Complete Data Flow Architecture

---

## 3.1 Overview

The data flow is a linear, append-only pipeline with fan-out at the Event Bus.
Data moves strictly forward — no service pulls data from a downstream service.
Every transformation is traceable via the event_id propagated through all stages.

---

## 3.2 Stage 1: Simulator / Medical Device → MDIL

**Input Data (examples):**
```
HL7 v2:
  MSH|^~\&|MONITOR|ICU|HIS|HOSP|20260611120000||ORU^R01|...
  OBX|1|NM|8867-4^Heart Rate^LN||72|/min|60-100||||F
  OBX|2|NM|59408-5^Oxygen Saturation^LN||98|%|95-100||||F

MQTT:
  Topic: hospital/ward3/bed7/vitals
  Payload: {"hr":72,"spo2":98,"nibp_sys":118,"nibp_dia":76,"ts":1749628800}

Serial (RS-232 proprietary binary):
  0x02 0x48 0x52 0x37 0x32 0x03

DICOM:
  DICOM waveform file (12-lead ECG)
```

**MDIL Transformation:**
- Protocol parser invoked based on device_id → protocol mapping in Device Registry
- All protocols mapped to Protocol-Normalized Device Payload

**Output Data → stream:mdil.raw:**
```json
{
  "mdil_message_id": "mdil-8a3f1b2c",
  "device_id": "DEV-ICU-BED07-MONITOR",
  "facility_id": "FACILITY-001",
  "ward": "ICU",
  "bed": "07",
  "protocol_type": "HL7v2",
  "received_at": "2026-06-11T12:00:00.000Z",
  "raw_observations": [
    {"code": "8867-4", "value": 72, "unit": "/min", "label": "Heart Rate"},
    {"code": "59408-5", "value": 98, "unit": "%", "label": "SpO2"},
    {"code": "55284-4", "value": {"systolic": 118, "diastolic": 76}, "unit": "mmHg", "label": "NIBP"}
  ]
}
```

**Failure Handling:**
| Failure | Action |
|---|---|
| Unknown protocol | Write to stream:mdil.parse_errors; alert monitoring |
| Parse error | Write raw payload + error to stream:mdil.parse_errors |
| Device disconnect | Emit to stream:device.lifecycle; begin reconnect backoff |
| Redis unavailable | Buffer to SQLite edge store; replay on Redis recovery |

---

## 3.3 Stage 2: MDIL → Collectors

**Input:** Protocol-Normalized Device Payload from stream:mdil.raw

**Collector Transformation:**
- Assign globally unique event_id (UUID v4)
- Resolve patient_id from Device Registry (device_id → patient mapping)
- Construct Internal Event Envelope

**Output Data → stream:collector.raw:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "schema_version": "1.0.0",
  "device_id": "DEV-ICU-BED07-MONITOR",
  "patient_id": "PAT-00042",
  "facility_id": "FACILITY-001",
  "ward": "ICU",
  "bed": "07",
  "received_at": "2026-06-11T12:00:00.000Z",
  "source_protocol": "HL7v2",
  "resolution_status": "resolved",
  "payload": {
    "raw_observations": [
      {"code": "8867-4", "value": 72, "unit": "/min", "label": "Heart Rate"},
      {"code": "59408-5", "value": 98, "unit": "%", "label": "SpO2"}
    ]
  }
}
```

**Failure Handling:**
| Failure | Action |
|---|---|
| Patient not found | Emit with patient_id: null, resolution_status: unresolved |
| Redis write failure | Retry with exponential backoff |
| Service crash | No XACK sent; Redis re-delivers on restart |

---

## 3.4 Stage 3: Collectors → Validation

**Input:** Internal Event Envelope from stream:collector.raw

**Validation Transformation (3 Tiers):**

Tier 1 — Structural:
  - JSON Schema validation against Internal Event Envelope schema
  - Required fields: event_id, device_id, facility_id, received_at, payload, schema_version
  - UUID v4 format check on event_id

Tier 2 — Domain:
  - device_id exists in Device Registry
  - facility_id is a registered facility
  - received_at clock drift: ±5 minutes from server clock
  - schema_version is supported

Tier 3 — Clinical Plausibility:
  - Heart Rate: reject outside 0–300; warn outside 40–180
  - SpO2: reject below 50%; warn below 92%
  - Systolic BP: reject outside 40–300 mmHg
  - Temperature: reject outside 25–45°C
  - Respiratory Rate: reject outside 0–80 /min

**Output Data — Passed → stream:validation.passed:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "...all original fields...",
  "validation_result": {
    "status": "passed",
    "errors": [],
    "warnings": [],
    "validated_at": "2026-06-11T12:00:00.050Z",
    "validator_version": "1.0.0"
  }
}
```

**Output Data — Failed → stream:validation.failed:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "...all original fields...",
  "validation_result": {
    "status": "failed",
    "errors": [
      {
        "tier": 3,
        "field": "heart_rate",
        "value": 450,
        "rule": "max_physiological_range",
        "message": "Heart rate 450 exceeds maximum physiological range of 300 bpm"
      }
    ],
    "validated_at": "2026-06-11T12:00:00.050Z",
    "validator_version": "1.0.0"
  }
}
```

---

## 3.5 Stage 4: Validation → Normalization

**Input:** Validated Event (status: passed) from stream:validation.passed

**Normalization Transformation:**
- LOINC code mapping: raw device codes → canonical LOINC codes
- UCUM unit normalization: device units → standard measurement units
- Timestamp normalization: all timestamps → UTC ISO-8601
- FHIR R4 Observation resource construction
- FHIR Provenance resource attachment

**LOINC Mapping Examples:**
```
"HR"     → LOINC 8867-4  (Heart rate)
"SpO2"   → LOINC 59408-5 (Oxygen saturation)
"NIBP"   → LOINC 55284-4 (Blood pressure panel)
"TEMP"   → LOINC 8310-5  (Body temperature)
"RR"     → LOINC 9279-1  (Respiratory rate)
"GCS"    → LOINC 9269-2  (Glasgow coma score)
```

**Output Data → stream:normalized.events:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "schema_version": "fhir-r4-1.0.0",
  "normalized_at": "2026-06-11T12:00:00.120Z",
  "fhir_resource": {
    "resourceType": "Observation",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "final",
    "category": [{
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
        "code": "vital-signs"
      }]
    }],
    "code": {
      "coding": [{
        "system": "http://loinc.org",
        "code": "8867-4",
        "display": "Heart rate"
      }]
    },
    "subject": {"reference": "Patient/PAT-00042"},
    "effectiveDateTime": "2026-06-11T12:00:00.000Z",
    "valueQuantity": {
      "value": 72,
      "unit": "/min",
      "system": "http://unitsofmeasure.org",
      "code": "/min"
    }
  },
  "provenance": {
    "device_id": "DEV-ICU-BED07-MONITOR",
    "facility_id": "FACILITY-001",
    "pipeline_stages": ["mdil", "collector", "validator", "normalizer"]
  },
  "validation_result": {"status": "passed", "validator_version": "1.0.0"}
}
```

**Failure Handling:**
| Failure | Action |
|---|---|
| LOINC mapping not found | Emit with coding.system: unknown; flag normalization_warning |
| Unit conversion fails | Emit with original unit preserved + normalization_warning flag |
| Service crash | Redis PEL re-delivery; normalization is stateless and idempotent |

---

## 3.6 Stage 5: Redis Streams Fan-Out

The normalized event is written to stream:normalized.events.
Three independent consumer groups read from this stream simultaneously.

```
stream:normalized.events
     |
     +---> [Consumer Group: db-service-group]    → Database Service
     |
     +---> [Consumer Group: dashboard-group]     → Dashboard Service
     |
     +---> [Consumer Group: ai-service-group]    → AI Service
```

Each consumer group maintains its own read cursor.
Progress of one group does not affect others.
All three consume at their own rate.

---

## 3.7 Stage 6: AI Service Processing

**Input:** Normalized FHIR events from stream:normalized.events

**Internal Processing:**
1. Build/update sliding window context per patient (configurable: last 30 min of vitals)
2. Run rule-based scoring: NEWS2, MEWS, SOFA against current observations
3. Run ML anomaly detection on context window
4. Generate insight if threshold is crossed
5. Attach clinical rationale

**Output → stream:ai.insights:**
```json
{
  "insight_id": "ai-insight-003f1a2b",
  "patient_id": "PAT-00042",
  "model_id": "news2-calculator",
  "model_version": "1.0.0",
  "insight_type": "early_warning",
  "severity": "warning",
  "score": {"news2": 5},
  "confidence_score": 1.0,
  "clinical_rationale": "NEWS2 score of 5 detected. Contributing: SpO2 91% (+2pts), RR 22/min (+2pts), HR 108/min (+1pt). Recommend clinical review within 30 minutes.",
  "triggered_by": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "generated_at": "2026-06-11T12:00:00.380Z"
}
```

**Failure Handling:**
| Failure | Action |
|---|---|
| Model inference fails | Emit degraded_mode insight; do not block pipeline |
| Model registry unavailable | Fall back to rule-based scoring only |
| Service crash | Stateless per request; restart does not cause data loss |

---

## 3.8 Stage 7: Hospital Integration Outbound

**Input:**
- stream:ai.insights
- stream:normalized.events (filtered by hospital subscription config)

**Processing:**
1. Check hospital subscription filter (which event types does this hospital receive?)
2. Apply consent and data-sharing rules
3. Translate to target format (FHIR Bundle, HL7 v2 ORU, proprietary)
4. Deliver via configured transport (REST, MLLP, SFTP)
5. Log transmission to stream:audit.events with payload hash

**Failure Handling:**
| Failure | Action |
|---|---|
| External system unreachable | Queue to stream:hospital.outbound with retry metadata |
| Max retries exceeded | Move to stream:hospital.delivery_failed (Dead Letter) |
| Translation fails | Log error; emit to monitoring; do not silently discard |
| Inbound translation fails | Reject and log; never silently drop inbound data |

---

## 3.9 Complete Pipeline Timing Budget (Target SLA)

```
Stage 1: Device → MDIL parse              Target: < 50ms
Stage 2: MDIL → Collector wrap            Target: < 20ms
Stage 3: Collector → Validation           Target: < 30ms
Stage 4: Validation → Normalization       Target: < 50ms
Stage 5: Normalization → Event Bus        Target: < 10ms
Stage 6: Event Bus → AI Inference         Target: < 500ms
Stage 7: AI → Hospital Delivery           Target: < 2000ms

Total: Device signal to dashboard update  Target: < 200ms (stages 1–5)
Total: Device signal to AI insight        Target: < 700ms
```
