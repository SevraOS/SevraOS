# HELIOS OS + SEVRA AI
## Database Service

This module implements the core Database Service as defined in the Architecture Contracts.

### End-to-End Flow Walkthrough (Section 23)

The following describes the exact lifecycle of a normalized event as it hits the Database Service.

#### 1. Input (Redis Stream)
1. The **Normalization Service** publishes a `VitalEvent` JSON payload to the `sevra:streams:vitals` stream.
2. The `VitalsDatabaseConsumer` (running inside this service via `eventbus.ConsumerWorker`) receives the event using `XREADGROUP`.

#### 2. Idempotency Check
1. The consumer uses the `IdempotencyService` (Redis `SETNX`) to acquire a lock using `client_event_id`.
2. It then checks the local SQLite database using `DeduplicationService` to ensure `client_event_id` hasn't been written previously.

#### 3. Storage (Offline-First)
1. A **UnitOfWork** transaction is opened for the SQLite database (Tier 1).
2. The `Vital` SQLAlchemy model is constructed.
3. The vital is inserted into SQLite. 
   - `sync_status` defaults to `pending`.
   - Data is encrypted at rest using SQLCipher (AES-256).
4. The SQLite transaction is committed locally. The write latency is <1ms.
5. Upon successful commit, the consumer issues an `XACK` to Redis, removing the message from the stream.

#### 4. Sync Engine (Asynchronous)
1. The background `SyncEngine` polls the SQLite database every 5 seconds for records where `sync_status == 'pending'`.
2. It batches these records (e.g., 1000 at a time).
3. It opens a transaction with PostgreSQL (Tier 2).
4. It performs an `UPSERT` using the `ConflictResolver`:
   - `ON CONFLICT (client_event_id) DO UPDATE`
   - Clinical data is preserved; only metadata (`updated_at`, `sync_status`) is overwritten if a conflict occurs.
5. If the PostgreSQL write succeeds, the SQLite records are updated to `sync_status = 'synced'`.

#### 5. Failure Cases & Recovery (Section 20)
*   **Network Partition (PostgreSQL unreachable):** 
    *   The `Orchestrator` detects the failure via `DatabaseHealthService`.
    *   The `SyncEngine` is paused.
    *   Consumers *continue* writing to SQLite without interruption (Offline-First).
    *   When the network returns, the `Orchestrator` resumes the `SyncEngine`, which processes the backlog.
*   **Redis Offline:**
    *   The `EventProducer` buffers messages to local disk.
    *   The Database Service waits; it cannot process new events but existing data is safe.
*   **SQLite Corruption:**
    *   The `Orchestrator` halts all consumers.
    *   Because `XACK` is only sent *after* SQLite commit, events remain safely in the Redis stream.
    *   Once SQLite is restored, consumers restart and replay the events from Redis.
*   **PostgreSQL Write Failure (Constraint Violation):**
    *   The batch is rolled back in PostgreSQL.
    *   The `SyncEngine` marks the SQLite records as `sync_status = 'error'` and increments `sync_attempts`.
    *   Exponential backoff is applied for retries.

### Architecture Compliance
*   **C2.2 Database Ownership:** Only this service writes to SQLite and PostgreSQL.
*   **C3.5 Offline-First:** Handled by SQLite Tier 1 and Sync Engine.
*   **C4.3 Encryption:** Implemented via SQLCipher hooking in `connection.py`.
