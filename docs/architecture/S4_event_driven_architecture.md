# HELIOS OS + SEVRA AI — Architecture
# Section 4: Event-Driven Architecture (Redis Streams)

---

## 4.1 Architecture Philosophy

The event bus is built on Redis Streams — a persistent, ordered, log-based messaging system.
Unlike pub/sub (fire-and-forget), Redis Streams guarantee:

- Messages are persisted on disk (AOF + RDB)
- Multiple consumer groups read independently without interfering
- Unacknowledged messages are held in PEL and re-delivered
- Full replay from any historical message offset is possible
- Messages remain in the stream until the retention window expires

All inter-service data communication in the hot path flows EXCLUSIVELY through Redis Streams.
No exceptions. No direct API calls between services in the data path.

---

## 4.2 Complete Stream Topology

| Stream Name | Purpose | Producer(s) | Consumer Group(s) |
|---|---|---|---|
| stream:mdil.raw | Raw device payloads after protocol translation | MDIL | collectors-group |
| stream:mdil.parse_errors | MDIL parse failures with raw payload | MDIL | monitoring-group |
| stream:collector.raw | Enveloped events with UUID and patient_id | Collectors | validation-group |
| stream:validation.passed | Events passing all 3 validation tiers | Validation | normalization-group |
| stream:validation.failed | Rejected events with full error context | Validation | monitoring-group, review-group |
| stream:normalized.events | FHIR R4 canonical clinical observations | Normalization | db-service-group, dashboard-group, ai-service-group |
| stream:ai.insights | ML and rule-based clinical insights | AI Service | db-service-group, dashboard-group, hospital-group |
| stream:hospital.outbound | Outbound delivery queue for external systems | Hospital Integration | hospital-delivery-group |
| stream:hospital.delivery_failed | Dead Letter for failed external delivery | Hospital Integration | monitoring-group |
| stream:device.lifecycle | Device connect/disconnect/error events | MDIL | monitoring-group, dashboard-group |
| stream:audit.events | All security-relevant actions and data access | All Services | security-audit-group |
| stream:system.alerts | Infrastructure-level platform alerts | Monitoring | ops-group |

---

## 4.3 Consumer Group Design

### Design Rules
1. Every consumer is registered in a named consumer group per stream
2. Consumer groups maintain independent read cursors — multiple groups on the same stream do not interfere
3. Within a consumer group, multiple instances compete for messages (load balancing)
4. A message is NOT removed when acknowledged — it remains for the full retention period
5. If a consumer crashes without ACK, the PEL holds the message for re-delivery

### Consumer Group Registry

| Consumer Group | Stream | Min Instances | Max Instances |
|---|---|---|---|
| collectors-group | stream:mdil.raw | 1 | 4 |
| validation-group | stream:collector.raw | 1 | 8 |
| normalization-group | stream:validation.passed | 1 | 8 |
| db-service-group | stream:normalized.events | 1 | 4 |
| dashboard-group | stream:normalized.events | 1 | 8 |
| ai-service-group | stream:normalized.events | 1 | 8 |
| db-service-group | stream:ai.insights | 1 | 2 |
| dashboard-group | stream:ai.insights | 1 | 4 |
| hospital-group | stream:ai.insights | 1 | 4 |
| hospital-delivery-group | stream:hospital.outbound | 1 | 4 |
| monitoring-group | All error/lifecycle streams | 1 | 2 |
| security-audit-group | stream:audit.events | 1 | 2 |
| review-group | stream:validation.failed | 1 | 2 |
| ops-group | stream:system.alerts | 1 | 2 |

---

## 4.4 Message ID Structure

Redis Streams auto-generate message IDs in the format: `<milliseconds>-<sequence>`
Example: `1749628800000-0`

This ID serves as the:
- Replay anchor (start replay from this ID)
- Ordering guarantee (IDs are monotonically increasing)
- Deduplication reference within a stream

The application-level `event_id` (UUID v4) is carried INSIDE the message payload
and serves as the global idempotency key across all services.

---

## 4.5 Replay Strategy

### Definition
Replay allows any consumer group to re-read historical events from any point in a stream.
It is non-destructive — original data is never modified.

### When Replay Is Used
- **Service recovery**: New instance re-reads events missed during downtime
- **Bug fix re-processing**: After fixing a normalization bug, re-process affected events
- **AI model retraining**: Feed historical normalized events to a new model version
- **Audit investigation**: Replay a patient's event timeline for clinical review
- **Testing**: Replay production events in a staging environment

### Replay Mechanism
```
1. Operator sets consumer group cursor to historical position:
   XGROUP SETID <stream> <group> <message-id>

2. Consumer group reads forward from that position
   All re-delivered events carry original event_id (idempotency prevents duplicates)

3. Each service's idempotency check suppresses duplicate writes

4. Replay is authorized and logged to stream:audit.events
```

### Replay Authorization
- Requires `auditor` or `admin` RBAC role
- Every replay logged: who, which stream, from_id, to_id, reason, timestamp
- For replay beyond stream retention window: events re-injected from Object Storage archive

---

## 4.6 Retry Strategy

### 3-Tier Retry Model

**Tier 1 — Immediate Retry**
- Trigger: Transient error (network blip, momentary timeout)
- Action: Re-process immediately
- Max retries: 3
- No delay between retries

**Tier 2 — Exponential Backoff Retry**
- Trigger: Persistent error (database temporarily unavailable, upstream service down)
- Action: Retry with exponential backoff
- Backoff schedule: 1s → 2s → 4s → 8s → 16s
- Max retries: 5

**Tier 3 — Dead Letter Queue**
- Trigger: All Tier 1 and Tier 2 retries exhausted
- Action: Move event to appropriate DLQ stream with full diagnostic context
- No automatic further retry — requires human review or manual re-injection

### Retry Implementation Mechanism
```
1. Consumer reads message from stream via XREADGROUP
2. Processing attempt begins; message enters PEL (Pending Entries List)
3. If processing fails:
   a. Increment _retry_count in message metadata
   b. Apply Tier 1 immediate retry (up to 3 times)
   c. If Tier 1 exhausted: apply Tier 2 backoff (up to 5 times)
   d. If Tier 2 exhausted: emit to DLQ stream; XACK original message
4. If processing succeeds: XACK message; remove from PEL

Background Claim Worker (per consumer group):
   - Scans PEL every 30 seconds
   - Claims messages stuck in PEL longer than visibility_timeout (default: 30s)
   - Uses XCLAIM to reassign stale messages to available consumers
   - Enforces retry count limits
```

---

## 4.7 Dead Letter Queue (DLQ) Strategy

### DLQ Streams and Owners

| DLQ Stream | Source Service | Review Owner |
|---|---|---|
| stream:mdil.parse_errors | MDIL (parse failures) | MDIL engineering team |
| stream:validation.failed | Validation (rejected events) | Clinical data quality team |
| stream:hospital.delivery_failed | Hospital Integration (delivery failures) | Integration operations team |
| stream:dlq.normalization | Normalization (mapping failures) | Data engineering team |

### Mandatory DLQ Event Fields
```
Every DLQ event MUST contain:
  original_event_id      — event_id from the original payload
  original_stream        — Source stream name
  failure_reason         — Structured error object with error code + message
  failure_stage          — Which service/tier produced the failure
  retry_count            — Number of retries exhausted before DLQ placement
  dlq_placed_at          — UTC timestamp of DLQ placement
  dlq_stream             — Which DLQ stream this was placed in
  original_payload       — Full original message payload (preserved for re-injection)
```

### DLQ Operations
```
Review:    review-group consumers monitor DLQ streams continuously
Diagnose:  Error is investigated by designated owner team
Fix:       Root cause is remediated (bug fix, rule update, config change)
Re-inject: Authorized operator replays DLQ events to originating stream
Discard:   Events marked as permanently invalid (requires audit log entry)
Alert:     Any DLQ write triggers an immediate monitoring alert
```

### DLQ Alert Thresholds
- Any single DLQ write → INFO alert to ops channel
- > 10 DLQ events in 5 minutes → WARNING alert
- > 50 DLQ events in 5 minutes → CRITICAL alert + PagerDuty page

---

## 4.8 Idempotency Strategy

### Definition
Processing the same event more than once must produce the same result.
This is mandatory because Redis Streams guarantees at-least-once delivery,
meaning duplicate delivery is expected and must be handled.

### Global Idempotency Key
The `event_id` (UUID v4 assigned by Collectors) is the global idempotency key.
It is propagated unchanged through every pipeline stage.
Every service that performs a write operation checks event_id before writing.

### Idempotency Enforcement Per Service

| Service | Mechanism |
|---|---|
| Collectors | UUID generated once; never re-generated on retry |
| Validation | Stateless transform; duplicate input → identical output; safe to re-run |
| Normalization | Stateless transform; fully idempotent |
| Database Service | Upsert on event_id: INSERT ... ON CONFLICT(event_id) DO UPDATE |
| AI Service | insight_id derived from hash(event_id + model_id); duplicate suppressed |
| Hospital Integration | Delivery tracked in delivery log keyed by event_id; duplicate blocked |
| Security Service | Audit entries keyed by (event_id, action); duplicates suppressed |

### Idempotency Cache
```
Redis Cache maintains short-lived idempotency cache per service:
  Key:   idempotency:{service_name}:{event_id}
  Value: processing result summary (status, output_id)
  TTL:   1 hour

If key exists:
  Skip processing
  Return cached result
  XACK message (it was already handled)

If key absent:
  Process event
  Write result to cache
  XACK message
```

---

## 4.9 Stream Retention Policy

| Stream | Retention | Rationale |
|---|---|---|
| stream:mdil.raw | 24 hours | High volume; quickly consumed downstream |
| stream:collector.raw | 24 hours | High volume; short-lived |
| stream:validation.passed | 48 hours | Buffer for normalization recovery window |
| stream:validation.failed | 30 days | Clinical data quality review timeline |
| stream:normalized.events | 72 hours | Multi-consumer fan-out window |
| stream:ai.insights | 72 hours | Downstream delivery guarantee window |
| stream:audit.events | 365 days | Regulatory compliance requirement |
| stream:hospital.outbound | 7 days | External delivery retry window |
| stream:hospital.delivery_failed | 90 days | Investigation and re-injection window |
| stream:device.lifecycle | 7 days | Operational incident investigation |
| stream:system.alerts | 30 days | Ops incident review |

### Long-Term Archive Strategy
- Events beyond stream retention are archived to MinIO Object Storage
- Archive format: compressed NDJSON (newline-delimited JSON) per stream per day
- Archive path: `s3://helios-archive/{stream_name}/{YYYY}/{MM}/{DD}/{HH}.ndjson.gz`
- Re-injection: Archived events can be re-read and injected into any stream by authorized ops

---

## 4.10 Redis Infrastructure Configuration

### Development Environment
```
Mode:        Single Redis instance
Persistence: AOF enabled (fsync: everysec)
Memory:      512MB
Replicas:    None
```

### Production Environment
```
Mode:        Redis Sentinel
Nodes:       1 primary + 2 replicas + 3 sentinel processes
Persistence: AOF + RDB snapshot (RDB every 15 minutes)
Memory:      16GB per node
Failover:    Automatic sentinel-managed primary election
Quorum:      2 of 3 sentinels must agree for failover
Max memory policy: noeviction (streams must never lose messages)
```

### Cluster Mode (Scale-Out)
```
Mode:        Redis Cluster
Shards:      6 minimum (3 primary + 3 replica)
Hash slots:  16384 distributed across shards
Trigger:     When single-node memory exceeds 80% or throughput > 100K msg/sec
```
