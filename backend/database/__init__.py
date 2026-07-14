"""
HELIOS OS + SEVRA AI
Database Service — Healthcare-Grade Storage Platform

The Database Service is the ONLY service with write access to SQLite and PostgreSQL.
It consumes normalized events from Redis Streams and persists them across multiple
storage tiers with offline-first guarantees, idempotent writes, and automatic
SQLite→PostgreSQL synchronization.

Storage Tiers:
  Tier 1: SQLite + SQLCipher  (Edge / Local — primary offline write store)
  Tier 2: PostgreSQL           (Central / Cloud — sync target)
  Tier 3: MinIO Object Storage (Binary / Large Data — archives)
  Tier 4: Redis Cache          (Hot Operational Data — projections)

Architecture Contracts Enforced:
  C2.2: Database Service is the ONLY writer to SQLite and PostgreSQL.
  C3.5: SQLite is written FIRST, always. PostgreSQL sync is asynchronous.
  C3.2: event_id is the global idempotency key (UUID v4, immutable).
  C3.3: XACK only after successful processing AND successful downstream write.
  C3.4: No silent data loss — failed events route to DLQ.
"""

from database.config.settings import DatabaseConfig

__all__ = [
    "DatabaseConfig",
]
