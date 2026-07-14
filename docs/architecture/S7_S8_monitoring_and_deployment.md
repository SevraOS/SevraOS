# HELIOS OS + SEVRA AI — Architecture
# Section 7: Monitoring Architecture

---

## 7.1 Monitoring Philosophy

No service monitors itself. All observability is centralized.
Every service exposes metrics, logs, and health endpoints.
The Monitoring Service owns collection, storage, visualization, and alerting.

---

## 7.2 Metrics Collection (Prometheus)

### Collection Strategy
```
Mode: Pull-based scraping (Prometheus scrapes service endpoints)
Scrape Endpoint: /metrics on each service (Prometheus text format)
Scrape Interval: 15 seconds (standard), 5 seconds (critical services)
Retention: 15 days in Prometheus TSDB
Long-term: Thanos or Victoria Metrics for 90-day+ retention
```

### Metrics Per Service
```
All services expose:
  helios_up                          — Service availability (1 = up, 0 = down)
  helios_http_request_duration_ms    — HTTP request latency histogram
  helios_http_requests_total         — Total HTTP requests by status code
  helios_errors_total                — Error count by error type

MDIL Service:
  mdil_devices_connected_total       — Number of connected devices
  mdil_messages_received_total       — Messages received per protocol
  mdil_parse_errors_total            — Parse failure count
  mdil_device_reconnects_total       — Device reconnect events

Collectors Service:
  collector_events_wrapped_total     — Events successfully enveloped
  collector_patient_resolution_failures_total  — Unresolved patient IDs

Validation Service:
  validation_events_passed_total     — Events passing validation
  validation_events_failed_total     — Events failing validation
  validation_tier_failures_total     — Failures per tier (1, 2, 3)
  validation_processing_duration_ms  — Validation latency histogram

Normalization Service:
  normalization_events_total         — Events normalized
  normalization_loinc_unmapped_total — Events with unknown LOINC code
  normalization_unit_conversion_failures_total

Database Service:
  db_sqlite_writes_total             — SQLite write count
  db_postgres_writes_total           — PostgreSQL write count
  db_sync_pending_total              — Records pending sync to PostgreSQL
  db_sync_duration_ms                — Sync batch duration histogram
  db_sync_failures_total             — Sync failure count

AI Service:
  ai_inference_duration_ms           — ML inference latency histogram
  ai_insights_generated_total        — Insights generated per model
  ai_insights_severity_total         — Insights by severity (info/warning/critical)
  ai_model_errors_total              — Model inference errors

Event Bus (Redis):
  redis_stream_length                — Current stream length per stream
  redis_stream_pending_count         — PEL size per consumer group
  redis_consumer_lag                 — Consumer group lag (unread messages)
  redis_memory_used_bytes            — Redis memory utilization
```

---

## 7.3 Log Aggregation (Loki)

### Log Format
```
All services emit structured JSON logs to stdout:
{
  "timestamp": "2026-06-11T12:00:00.000Z",
  "level": "INFO",          // DEBUG | INFO | WARNING | ERROR | CRITICAL
  "service": "validation",
  "version": "1.0.0",
  "request_id": "req-abc123",
  "event_id": "550e8400-...",
  "facility_id": "FACILITY-001",
  "message": "Event passed Tier 3 clinical validation",
  "context": {
    "patient_id": "PAT-00042",
    "device_id": "DEV-ICU-BED07",
    "validator_version": "1.0.0"
  }
}
```

### Log Collection Pipeline
```
Service stdout → Docker log driver → Promtail (log agent) → Loki → Grafana
```

### Log Retention
```
Hot (Loki): 30 days (full query access)
Cold (MinIO archive): 1 year (compressed, restored on demand)
Audit logs: 7 years (separate from application logs, stored in PostgreSQL)
```

### Log Level Policy
```
Production:    INFO and above (DEBUG disabled)
Staging:       DEBUG and above
Development:   DEBUG and above
Sensitive data: NEVER logged (patient_id in metadata is acceptable, clinical values are not logged)
```

---

## 7.4 Health Check Architecture

### Health Check Endpoints (per service)
```
GET /health   — Basic liveness check (returns 200 if process is alive)
GET /ready    — Readiness check (returns 200 only if service can handle traffic)
GET /live     — Liveness probe (returns 200 if service is not deadlocked)
GET /metrics  — Prometheus metrics endpoint
```

### Readiness Check Logic
```
A service is NOT ready if:
  - Cannot reach Redis (if it's a stream consumer/producer)
  - Cannot reach its required database (if it's the Database Service)
  - Has not completed startup initialization
  - Has a PEL backlog exceeding the alert threshold

A service IS ready even if:
  - PostgreSQL is unavailable (Database Service writes to SQLite only)
  - AI model registry is unavailable (falls back to rule-based scoring)
```

### Health Aggregator
```
Monitoring Service exposes a unified system health endpoint:
GET /system/health

Returns:
{
  "status": "healthy" | "degraded" | "critical",
  "timestamp": "...",
  "services": {
    "mdil": {"status": "healthy", "devices_connected": 12},
    "validation": {"status": "healthy", "error_rate": 0.002},
    "ai_service": {"status": "degraded", "reason": "ml_model_unavailable", "fallback": "rule_based_active"},
    "database": {"status": "healthy", "sync_pending": 0},
    ...
  }
}
```

---

## 7.5 Grafana Dashboards

### Dashboard 1: System Overview
```
Panels:
  - Overall system status (UP/DOWN per service)
  - Events per second through the pipeline (real-time)
  - Redis stream lag per consumer group
  - Error rates across all services
  - Active device connections
```

### Dashboard 2: Clinical Pipeline
```
Panels:
  - Events entering MDIL per minute
  - Validation pass/fail rate
  - Normalization success rate
  - Pipeline end-to-end latency (P50, P95, P99)
  - Dead letter queue depth per stream
```

### Dashboard 3: AI Service
```
Panels:
  - Inference requests per minute per model
  - Inference latency histogram (P50, P95, P99 vs 500ms SLA)
  - Insights generated per severity (info/warning/critical)
  - Model error rate
  - Active early warning alerts by facility
```

### Dashboard 4: Database
```
Panels:
  - SQLite write throughput (records/sec)
  - PostgreSQL sync pending count (trend)
  - Sync success/failure rate
  - Database connection pool utilization
  - Disk usage per tier
```

### Dashboard 5: Security and Audit
```
Panels:
  - Authentication attempts (success vs failed)
  - Authorization denials per role
  - Active sessions count
  - Token refresh rate
  - Audit log write rate
  - DLQ event count (streams:validation.failed, hospital.delivery_failed)
```

---

## 7.6 Alerting Architecture

### Alert Routing
```
Alert Source: Prometheus Alertmanager
Channels:
  Critical → PagerDuty (on-call engineer paged immediately)
  Warning  → Slack (#helios-warnings channel)
  Info     → Slack (#helios-info channel)
```

### Alert Rules

**Infrastructure Alerts:**
```
ServiceDown:
  Condition: helios_up == 0 for 1 minute
  Severity: CRITICAL
  Response: PagerDuty page

RedisStreamLag:
  Condition: redis_consumer_lag > 1000 messages for 5 minutes
  Severity: WARNING
  Response: Slack warning

RedisMemoryHigh:
  Condition: redis_memory_used_bytes > 80% of max memory
  Severity: WARNING
  Response: Slack warning
```

**Clinical Pipeline Alerts:**
```
ValidationFailureSpike:
  Condition: rate(validation_events_failed_total[5m]) > 10% of total events
  Severity: WARNING
  Response: Slack warning + email to clinical data team

DLQDepthCritical:
  Condition: any DLQ stream length > 50 messages in 5 minutes
  Severity: CRITICAL
  Response: PagerDuty page

DeviceDisconnect:
  Condition: mdil_device_reconnects_total increases for a known device
  Severity: WARNING
  Response: Slack warning with device_id and ward/bed
```

**AI Service Alerts:**
```
AIInferenceLatencyBreach:
  Condition: ai_inference_duration_ms P99 > 500ms for 5 minutes
  Severity: WARNING
  Response: Slack warning

AIModelError:
  Condition: rate(ai_model_errors_total[5m]) > 0
  Severity: WARNING
  Response: Slack warning

CriticalClinicalAlert:
  Condition: ai_insights_severity_total{severity="critical"} increases
  Severity: INFO (clinical staff notified via Dashboard WebSocket, not ops channel)
```

**Security Alerts:**
```
AuthFailureSpike:
  Condition: Failed authentication attempts > 10 in 1 minute from same IP
  Severity: CRITICAL
  Response: PagerDuty + automatic IP block recommendation

TokenBlacklistHigh:
  Condition: Blacklisted token count increases > 100 in 5 minutes
  Severity: WARNING
  Response: Slack warning (possible session hijack investigation)
```

---

# SECTION 8 — DEPLOYMENT ARCHITECTURE

---

## 8.1 Environment Strategy

### Three Environments

```
DEVELOPMENT
  Purpose: Local developer workflow
  Infrastructure: Docker Compose (single machine)
  Data: Synthetic/simulated device data only
  Security: Relaxed (no TLS for local services, simple JWT secrets)
  Scale: Single instance per service

STAGING (Testing)
  Purpose: Integration testing, QA, performance validation
  Infrastructure: Docker Compose or lightweight Kubernetes (kind/k3s)
  Data: Anonymized production data snapshots or enhanced simulation
  Security: Production-equivalent configuration
  Scale: Production-like (2 instances of critical services)
  CI/CD: Automated deployment from main branch

PRODUCTION
  Purpose: Live hospital environment
  Infrastructure: Kubernetes (K8s) or Docker Swarm
  Data: Real patient data — full compliance enforcement
  Security: Full TLS, mTLS, Vault, RBAC, audit logging
  Scale: Auto-scaling based on load
  CI/CD: Manual approval gate after staging validation
```

---

## 8.2 Container Architecture

### Container Design Rules
```
1. One process per container (not multiple services in one container)
2. No root user in containers (all services run as non-root uid:gid)
3. Read-only filesystem where possible
4. No secrets in container images (injected at runtime)
5. Minimal base images (python:3.12-slim, not python:3.12)
6. Multi-stage builds to minimize image size
7. Health check defined in every Dockerfile
8. Images tagged with semantic version + git SHA
```

### Service Container Registry
```
helios/mdil-service:1.0.0-abc1234
helios/collectors-service:1.0.0-abc1234
helios/validation-service:1.0.0-abc1234
helios/normalization-service:1.0.0-abc1234
helios/database-service:1.0.0-abc1234
helios/dashboard-service:1.0.0-abc1234
helios/ai-service:1.0.0-abc1234
helios/hospital-integration-service:1.0.0-abc1234
helios/security-service:1.0.0-abc1234
helios/monitoring-service:1.0.0-abc1234
```

---

## 8.3 Docker Compose Architecture (Development + Staging)

### Service Groups in docker-compose.yml
```
Group 1 — Infrastructure (must start first):
  redis           — Redis 7.x with AOF persistence
  postgres        — PostgreSQL 16
  minio           — MinIO object storage
  vault           — HashiCorp Vault dev mode

Group 2 — Device Layer (depends on infrastructure):
  mdil-service
  simulator       — Device simulator (dev/staging only)

Group 3 — Pipeline (depends on device layer):
  collectors-service
  validation-service
  normalization-service

Group 4 — Consumers (depends on pipeline):
  database-service
  dashboard-service
  ai-service
  hospital-integration-service

Group 5 — Cross-cutting (depends on all):
  security-service
  monitoring-service

Group 6 — Observability:
  prometheus
  grafana
  loki
  promtail
  alertmanager
```

### Docker Networks
```
helios-device-net     — MDIL, Simulator (device zone)
helios-pipeline-net   — Collectors, Validation, Normalization
helios-app-net        — Dashboard, AI, Hospital Integration, Security
helios-data-net       — Database Service, Redis, PostgreSQL, MinIO
helios-obs-net        — Prometheus, Grafana, Loki, Alertmanager

Services connect to multiple networks as needed.
Redis is on helios-pipeline-net AND helios-app-net (event bus shared access).
No service is on more networks than it needs.
```

---

## 8.4 Kubernetes Readiness

### Kubernetes Object Design
```
Per service:
  Deployment       — Service pod definition with replicas, resource limits
  Service          — ClusterIP (internal) or LoadBalancer (external)
  ConfigMap        — Non-sensitive configuration
  Secret           — Sensitive config (sourced from Vault via External Secrets Operator)
  HorizontalPodAutoscaler — Auto-scaling based on CPU/memory or custom metrics
  PodDisruptionBudget     — Minimum available replicas during updates

Infrastructure:
  StatefulSet      — Redis, PostgreSQL (stateful workloads)
  PersistentVolumeClaim — SQLite volume, PostgreSQL data volume, MinIO data
  Ingress          — NGINX ingress for external traffic
  NetworkPolicy    — Enforce zone-based network segmentation
```

### Resource Limits Per Service
```
mdil-service:          CPU: 0.5–2.0 | Memory: 256MB–1GB
collectors-service:    CPU: 0.25–1.0 | Memory: 128MB–512MB
validation-service:    CPU: 0.5–2.0  | Memory: 256MB–1GB
normalization-service: CPU: 0.5–2.0  | Memory: 256MB–1GB
database-service:      CPU: 0.5–2.0  | Memory: 512MB–2GB
dashboard-service:     CPU: 0.25–1.0 | Memory: 256MB–1GB
ai-service:            CPU: 2.0–8.0  | Memory: 2GB–16GB (GPU node if ML)
hospital-integration:  CPU: 0.25–1.0 | Memory: 256MB–512MB
security-service:      CPU: 0.25–0.5 | Memory: 128MB–256MB
```

### Auto-Scaling Rules
```
ai-service:         Scale at CPU > 70% or inference queue depth > 100
validation-service: Scale at CPU > 70% or Redis consumer lag > 500
dashboard-service:  Scale at WebSocket connections > 500 per instance
```

---

## 8.5 CI/CD Pipeline Strategy

### Pipeline Stages
```
Stage 1 — Code Quality
  Trigger: Every pull request
  Steps:
    - Lint (ruff for Python, eslint for JS/TS)
    - Type checking (mypy for Python)
    - Unit tests (pytest, coverage > 80% required)
    - Security scan (bandit for Python, npm audit for Node)

Stage 2 — Build
  Trigger: Merge to main branch
  Steps:
    - Docker image build (multi-stage)
    - Image vulnerability scan (Trivy)
    - Tag with semantic version + git SHA
    - Push to private container registry

Stage 3 — Staging Deployment
  Trigger: Successful image build
  Steps:
    - Deploy to staging environment (automated)
    - Integration test suite execution
    - Performance test (latency benchmarks vs SLA targets)
    - Smoke tests (end-to-end pipeline validation with simulator)
    - Health check validation

Stage 4 — Production Deployment
  Trigger: Manual approval by Tech Lead or Architect after staging passes
  Steps:
    - Blue-green deployment (zero downtime)
    - Traffic shift: 10% → 50% → 100% with automated rollback on error rate spike
    - Post-deploy health check
    - Smoke test on production with synthetic patient (controlled simulator)
    - Alert team on deployment completion
```

### Branch Strategy
```
main          — Production-ready code only. Protected. Requires PR + 2 reviews.
develop       — Integration branch. Auto-deploys to staging on merge.
feature/*     — Feature branches. PR required to merge to develop.
hotfix/*      — Critical production fixes. Direct to main with expedited review.
release/*     — Release candidate branches. Full regression testing before merge to main.
```

### Rollback Strategy
```
Automatic rollback:
  If error rate > 5% within 5 minutes of production deployment
  If health check fails post-deploy
  Docker Compose: docker-compose down && docker-compose up --rollback
  Kubernetes: kubectl rollout undo deployment/<service-name>

Manual rollback:
  Triggered by on-call engineer
  Previous image tag deployed immediately
  Rollback logged to audit trail
```
