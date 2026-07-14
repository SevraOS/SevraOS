# HELIOS OS + SEVRA AI — Architecture
# Section 5: Database Architecture

---

## 5.1 Storage Philosophy

The database layer is designed around one primary rule:
**Local storage is the source of truth. Cloud/central storage is the sync target.**

This is the foundation of the offline-first guarantee. The system never blocks on
remote database availability. Every write succeeds locally first, then propagates upward.

---

## 5.2 Storage Tiers

```
TIER 1: SQLite + SQLCipher          (Edge / Local)
  Purpose:    Primary offline write store. Encrypted at rest.
  Location:   On the hospital edge server (same machine as MDIL/Collectors)
  Scope:      Single-facility, local-only data
  Encryption: AES-256 via SQLCipher
  Latency:    Sub-millisecond write

TIER 2: PostgreSQL                  (Central / Cloud)
  Purpose:    Central relational store. Sync target from SQLite.
              Multi-facility queryable database.
  Location:   On-premise data center or private cloud
  Scope:      All facilities, historical records, audit logs
  Encryption: TDE (Transparent Data Encryption) + encrypted connections (TLS 1.3)
  Latency:    10–50ms (local network), 50–200ms (cloud)

TIER 3: MinIO Object Storage        (Binary / Large Data)
  Purpose:    DICOM images, waveform files, ECG recordings, audio notes
  Location:   Co-located with PostgreSQL (on-premise) or S3-compatible cloud
  Scope:      Large binary payloads not suitable for relational storage
  Encryption: Server-side AES-256 encryption (SSE-S3)

TIER 4: Redis Cache                 (Hot Operational Data)
  Purpose:    Current-state projection per patient. Latest vital per LOINC code.
              Session data, token blacklists, idempotency cache.
  Location:   Co-located with application services
  Scope:      Ephemeral operational data; reconstructible from Tier 2 if lost
  Persistence: RDB snapshot; data loss of max 15 minutes is acceptable

TIER 5: Prometheus TSDB             (Time-Series Metrics)
  Purpose:    System and application metrics time-series data
  Location:   Monitoring infrastructure
  Scope:      Infrastructure and application observability only
              No clinical patient data stored here
```

---

## 5.3 Data Ownership Per Store

| Data Type | Primary Store | Secondary Store | Archive |
|---|---|---|---|
| Clinical observations (vitals) | SQLite (edge) | PostgreSQL | MinIO (compressed) |
| AI insights and alerts | PostgreSQL | Redis Cache (24h) | MinIO |
| Patient demographics | PostgreSQL | SQLite (read-only replica) | — |
| Device registry | SQLite + PostgreSQL | Redis Cache | — |
| Audit logs | PostgreSQL (append-only) | — | MinIO (cold archive) |
| User accounts and roles | PostgreSQL | Redis Cache (session) | — |
| JWT blacklist | Redis | — | — |
| DICOM / ECG waveforms | MinIO | — | Cold MinIO tier |
| System metrics | Prometheus TSDB | — | — |

---

## 5.4 Offline-First Strategy

### Write Path (Always Succeeds Locally)
```
1. Database Service receives event from Redis Streams
2. Write to SQLite (Tier 1) — ALWAYS first, regardless of connectivity
3. SQLite write confirmed → XACK Redis message
4. Async sync worker checks connectivity to PostgreSQL
5. If connected: sync pending SQLite records to PostgreSQL
6. If disconnected: records remain in SQLite; retry sync on next connectivity check
```

### Offline Detection
```
Connectivity check runs every 30 seconds:
  - Ping PostgreSQL: SELECT 1
  - If ping fails 3 consecutive times: system enters OFFLINE mode
  - In OFFLINE mode: all writes go to SQLite only
  - When connectivity restored: trigger full sync of pending records
```

### Offline-First Guarantees
- Zero data loss during offline periods (all data captured in SQLite)
- Zero write latency penalty (SQLite is always the first write target)
- Automatic sync resumes without manual intervention
- No maximum offline duration limit (SQLite disk space is the only constraint)

---

## 5.5 Sync Flow

### SQLite → PostgreSQL Sync

```
Sync Worker runs continuously:

1. Query SQLite for records where sync_status = 'pending'
   ORDER BY received_at ASC (oldest first)
   LIMIT 1000 per batch (configurable)

2. For each batch:
   a. Begin PostgreSQL transaction
   b. UPSERT records using event_id as conflict key
      ON CONFLICT(event_id) DO UPDATE (idempotent sync)
   c. Commit transaction
   d. Update SQLite sync_status = 'synced' for that batch

3. If PostgreSQL write fails:
   a. Rollback PostgreSQL transaction
   b. Leave SQLite records as sync_status = 'pending'
   c. Increment sync_retry_count
   d. Apply exponential backoff before next attempt

4. Log sync metrics:
   - Records synced per batch
   - Sync latency
   - Pending record count
   - Last successful sync timestamp
```

### Sync Status Per Record
```
Every record in SQLite carries:
  sync_status:       pending | synced | error
  sync_attempts:     integer count
  last_sync_attempt: UTC timestamp
  sync_error:        last error message (if any)
```

---

## 5.6 Conflict Resolution Strategy

Conflicts occur when the same event_id is written to PostgreSQL twice
(e.g., due to network retry or replay).

**Resolution Rule: UPSERT with Idempotent Merge**
```
ON CONFLICT (event_id):
  DO UPDATE SET
    updated_at = EXCLUDED.updated_at      (latest timestamp wins for metadata)
    payload = EXCLUDED.payload            (preserve original, do not overwrite clinical data)
    sync_status = 'synced'               (mark as synced)

Clinical data fields are NEVER overwritten — only metadata is updated.
```

**Multi-Facility Conflict:**
If the same patient record is written from two different facilities simultaneously:
- Primary key is `event_id` (UUID) — guaranteed globally unique
- No conflict is possible at the record level
- Patient aggregation uses `patient_id` + `event_id` composite queries

---

## 5.7 Replication Architecture

### PostgreSQL Replication
```
Mode: PostgreSQL Streaming Replication
Topology:
  Primary:  1 read/write primary (receives all writes)
  Replicas: 2 read-only streaming replicas (synchronous replication for HA)
  Standby:  1 async replica in a separate datacenter (disaster recovery)

Replication Lag Target: < 100ms for synchronous replicas
Failover: Automatic with pg_auto_failover or Patroni
Read Distribution: Dashboard historical queries routed to read replicas
Write Lock: All writes go to primary only
```

### Redis Sentinel Replication
```
See Section 4 Redis Infrastructure Configuration
1 primary + 2 replicas + 3 sentinels
Automatic failover with quorum of 2
```

---

## 5.8 Data Retention and Tiering

### Hot Tier (SQLite + PostgreSQL Active)
```
Duration: 0 to 90 days
Data: All clinical observations, AI insights, recent audit logs
Access pattern: Real-time queries, dashboard reads, AI inference context
```

### Warm Tier (PostgreSQL + MinIO compressed)
```
Duration: 90 days to 2 years
Data: Historical observations, resolved alerts, closed episodes
Access pattern: Trend analysis, retrospective review, model training
```

### Cold Tier (MinIO cold archive)
```
Duration: 2 years to 7 years (configurable, compliance-driven)
Data: Archived clinical records, audit logs, raw waveforms
Access pattern: Compliance audits, legal discovery, long-term research
Storage: Compressed NDJSON + DICOM files in MinIO cold tier
Retrieval: Manual re-hydration to warm tier on request
```

### Data Deletion Policy
```
Records are NEVER physically deleted within the retention window.
Soft deletion (deleted_at timestamp) is used for logical removal.
Physical deletion only occurs when retention window expires AND
  authorized deletion request exists in audit log.
All deletions are logged to audit trail.
```

---

## 5.9 Database Encryption Strategy

### Encryption at Rest
```
SQLite: AES-256 via SQLCipher
  Key source: Hardware Security Module (HSM) or HashiCorp Vault
  Key rotation: Annual or on security event
  Scope: Entire database file

PostgreSQL: AES-256 TDE (Transparent Data Encryption) at tablespace level
  Key source: PostgreSQL encryption key managed by HashiCorp Vault
  Scope: All clinical data tablespaces

MinIO: Server-Side Encryption (SSE-S3) with AES-256
  Key source: MinIO KMS integration or HashiCorp Vault
  Scope: All stored objects
```

### Encryption in Transit
```
All database connections use TLS 1.3 minimum.
No plaintext database connections permitted.
Certificate validation enforced on all connections.
```
