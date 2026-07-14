# HELIOS OS + SEVRA AI
## Database Service - Folder Structure & Responsibilities

As required by Section 1, here is the explicit breakdown of every folder inside the `backend/database` service and its responsibility.

| Folder | Responsibility |
|---|---|
| `models/` | Contains all SQLAlchemy ORM models (`Patient`, `Vital`, `Device`, etc.). Defines the schema, indexes, and constraints for both SQLite and PostgreSQL. All inherit from a common `HeliosBase`. |
| `repositories/` | Implements the Repository Pattern. Abstracts raw SQL queries away from business logic. Contains methods for fetching time-series data, filtering, paginating, and bulk operations. |
| `services/` | Contains the core business logic. Includes the `UnitOfWork` (for transactional boundaries), `DeduplicationService` (for idempotency), `ArchiveService` (MinIO object storage), `QueryService` (complex dashboard queries), and `Orchestrator` (failure recovery). |
| `consumers/` | Integrates with the Redis Event Bus. Contains worker classes (like `VitalsDatabaseConsumer`) that listen to streams, parse payloads, and trigger the `UnitOfWork` to save data to the edge SQLite database. |
| `sync/` | Houses the `SyncEngine` and `ConflictResolver`. Responsible for the asynchronous background task that polls SQLite for `pending` records and pushes them up to PostgreSQL, resolving conflicts via UPSERT. |
| `encryption/` | Manages data-at-rest security. Contains `sqlcipher.py` which intercepts SQLAlchemy connection events to apply the `PRAGMA key` for AES-256 encryption on the SQLite database. |
| `cache/` | Implements the Tier 4 Operational Cache. The `CacheManager` stores and retrieves hot data (like the latest vital reading for a patient) from Redis to prevent hammering the relational databases for repetitive queries. |
| `health/` | Contains the `DatabaseHealthService`. Defines probes that check the connectivity and writeability of SQLite, PostgreSQL, and Redis. Used by the Orchestrator for offline-mode transitions and by Kubernetes for readiness probes. |
| `metrics/` | Centralizes observability. Defines the Prometheus metrics registry (`Counter`, `Histogram`, `Gauge`) used across the service to track DB writes, read latencies, sync lags, and cache hits. |
| `config/` | Environment configuration via Pydantic. Loads `.env` variables and constructs DSN connection strings, retention policies, and offline detection thresholds. |
| `migrations/` | Alembic migration scripts. Manages schema evolution for the central PostgreSQL database. Contains the semantic versioning scripts and rollback logic. |
| `tests/` | The Pytest suite. Contains unit and integration tests for consumers, repositories, the sync engine, the cache layer, and failure recovery orchestrator to ensure >90% coverage. |
| `docs/` | Internal architecture documentation. Contains Mermaid diagrams mapping out the storage flow, replication topology, and failure recovery state machines. |
