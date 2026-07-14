# HELIOS OS + SEVRA AI
## Database Service Architecture & Strategies

### Storage Architecture Diagrams (Section 2)

#### 1. Architecture Diagram
```mermaid
graph TD
    A[Redis Event Bus] -->|Consumes| B(Database Consumer)
    B -->|Writes| C[(Tier 1: SQLite Edge)]
    B -->|Caches| D[(Tier 4: Redis Cache)]
    C -->|Async Sync| E(Sync Engine)
    E -->|Replicates| F[(Tier 2: PostgreSQL Central)]
    F -->|Long-term Archive| G[(Tier 3: MinIO S3)]
    
    subgraph Hospital Edge Node
    B
    C
    D
    end
    
    subgraph Data Center / Cloud
    E
    F
    G
    end
```

#### 2. Storage Flow Diagram (Offline-First)
```mermaid
sequenceDiagram
    participant Redis as Redis Stream
    participant Consumer as DB Consumer
    participant SQLite as SQLite (Tier 1)
    participant Sync as Sync Engine
    participant PG as PostgreSQL (Tier 2)

    Redis->>Consumer: Deliver VitalEvent
    Consumer->>SQLite: Insert (sync_status='pending')
    SQLite-->>Consumer: ACK
    Consumer->>Redis: XACK (Message Acknowledged)
    
    loop Every 5 Seconds
        Sync->>SQLite: Select pending records
        SQLite-->>Sync: Return records
        Sync->>PG: UPSERT records
        PG-->>Sync: Success
        Sync->>SQLite: Update sync_status='synced'
    end
```

#### 3. Replication Diagram (PostgreSQL)
```mermaid
graph TD
    A[Sync Engine] -->|Writes| B[(PG Primary Node)]
    B -->|Synchronous Streaming| C[(PG Sync Replica 1)]
    B -->|Synchronous Streaming| D[(PG Sync Replica 2)]
    B -->|Asynchronous| E[(PG Async DR Standby)]
    
    F[Dashboard Service] -->|Reads| C
    F -->|Reads| D
```

#### 4. Failure Recovery Diagram
```mermaid
stateDiagram-v2
    [*] --> ONLINE
    
    ONLINE --> OFFLINE_MODE: PG Unreachable (Network Partition)
    OFFLINE_MODE --> OFFLINE_MODE: Continue writing to SQLite
    OFFLINE_MODE --> ONLINE: PG Restored (Resume Sync)
    
    ONLINE --> DEGRADED: Redis Down
    DEGRADED --> ONLINE: Redis Restored (Replay DLQ)
    
    ONLINE --> CRITICAL_HALT: SQLite Corrupted
    CRITICAL_HALT --> ONLINE: SQLite Recovered (Replay Stream)
```

---

### PostgreSQL Backup and Recovery Strategy (Section 10)

**Backup Strategy:**
1. **Continuous Archiving (WAL):** Write-Ahead Logs are continuously archived to MinIO (Tier 3) using `pgBackRest` or `WAL-G`. This enables Point-In-Time Recovery (PITR).
2. **Daily Full Backups:** A full snapshot of the PostgreSQL database is taken daily during low-traffic windows and pushed to cold object storage.
3. **Retention:** WAL logs kept for 30 days. Full backups kept for 1 year in standard tier, then moved to Glacier equivalent.

**Recovery Strategy:**
1. **Minor Failure (Primary crashes):** Automated failover via `Patroni`. A synchronous replica is promoted to primary within 30 seconds. No data loss.
2. **Major Failure (Datacenter loss):** Failover to the asynchronous Disaster Recovery (DR) Standby node.
3. **Logical Corruption (e.g., accidental table drop):** Restore from daily full backup + replay WAL logs via PITR up to the second before the catastrophic query executed.

---

### Migrations Strategy (Section 16)
- **Tooling:** Alembic for PostgreSQL (Central DB). Raw SQL scripts or Alembic for SQLite (Edge).
- **Versioning Strategy:** Linear timeline. Scripts use semantic timestamps (e.g., `20260617_01_init`).
- **Rollback Strategy:** Every `upgrade()` must have a corresponding `downgrade()`. In production, rolling back requires an explicit CLI command and audit log entry.
