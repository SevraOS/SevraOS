"""
HELIOS OS + SEVRA AI
Prometheus Metrics - SECTION 15
"""

from prometheus_client import Counter, Histogram, Gauge

class DatabaseMetrics:
    def __init__(self):
        self.db_writes_total = Counter(
            "sevra_db_writes_total",
            "Total successful database writes",
            ["table", "storage_tier"]
        )
        self.db_reads_total = Counter(
            "sevra_db_reads_total",
            "Total database read operations",
            ["table", "storage_tier"]
        )
        self.sync_events_total = Counter(
            "sevra_sync_events_total",
            "Total events synced to PostgreSQL",
            ["status"] # success, error, duplicate
        )
        self.cache_hits_total = Counter(
            "sevra_cache_hits_total",
            "Total Redis cache hits",
            ["entity_type"]
        )
        self.cache_misses_total = Counter(
            "sevra_cache_misses_total",
            "Total Redis cache misses",
            ["entity_type"]
        )
        self.storage_failures_total = Counter(
            "sevra_storage_failures_total",
            "Total storage layer failures",
            ["storage_tier", "operation"]
        )
        
        self.storage_latency = Histogram(
            "sevra_storage_latency_seconds",
            "Database operation latency",
            ["storage_tier"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        
        self.pending_sync_queue = Gauge(
            "sevra_pending_sync_queue",
            "Number of records pending sync from SQLite to PostgreSQL",
            ["table"]
        )

    def inc_db_writes(self, table: str, tier: str):
        self.db_writes_total.labels(table=table, storage_tier=tier).inc()

    def inc_db_reads(self, table: str, tier: str):
        self.db_reads_total.labels(table=table, storage_tier=tier).inc()

    def inc_sync(self, status: str, count: int = 1):
        self.sync_events_total.labels(status=status).inc(count)

    def inc_cache_hit(self, entity: str):
        self.cache_hits_total.labels(entity_type=entity).inc()

    def inc_cache_miss(self, entity: str):
        self.cache_misses_total.labels(entity_type=entity).inc()

    def inc_failure(self, tier: str, operation: str):
        self.storage_failures_total.labels(storage_tier=tier, operation=operation).inc()

    def observe_storage_latency(self, tier: str, seconds: float):
        self.storage_latency.labels(storage_tier=tier).observe(seconds)

    def set_pending_sync(self, table: str, count: int):
        self.pending_sync_queue.labels(table=table).set(count)

metrics = DatabaseMetrics()
