# HELIOS OS + SEVRA AI — Architecture
# Section 10: PROJECT CONTRACT
# THE IMMUTABLE ARCHITECTURAL SOURCE OF TRUTH

---

> This document is the final, binding architectural contract for HELIOS OS + SEVRA AI.
> All future implementation, code review, design decisions, and service additions
> MUST conform to this contract without exception.
> Any deviation requires a formal Architecture Review Board (ARB) decision and
> a version increment of this document.

---

## CONTRACT VERSION

```
Version:      1.0.0
Status:       RATIFIED
Date:         2026-06-11
Authority:    Chief Architect
Next Review:  2026-12-11
```

---

## C1 — APPROVED TECHNOLOGY STACK

### C1.1 Backend Services
```
Language:           Python 3.12 (all backend services)
Web Framework:      FastAPI (all HTTP-based services)
ASGI Server:        Uvicorn
Async Runtime:      asyncio (native Python async)
Data Validation:    Pydantic v2
Testing Framework:  pytest + pytest-asyncio
Type Checking:      mypy (strict mode)
Linting:            ruff
```

### C1.2 Event Bus
```
Technology:         Redis 7.x
Messaging Pattern:  Redis Streams ONLY
No alternatives permitted: Kafka, RabbitMQ, SQS are NOT approved
```

### C1.3 Databases
```
Edge Store:         SQLite + SQLCipher (AES-256 encrypted)
Central Store:      PostgreSQL 16
ORM:                SQLAlchemy 2.x (async)
Migrations:         Alembic (PostgreSQL) + raw SQL scripts (SQLite)
Cache/Operational:  Redis 7.x
Object Storage:     MinIO (S3-compatible)
Metrics TSDB:       Prometheus
```

### C1.4 AI / ML
```
Framework:          PyTorch 2.x (deep learning models)
                    scikit-learn (classical ML, rule scoring)
Model Format:       ONNX for production model export
Feature Engineering: pandas, numpy
Model Serving:      In-process inference within AI Service (no separate model server)
```

### C1.5 Healthcare Standards
```
Clinical Data Model:  HL7 FHIR R4 (canonical model for all normalized events)
Observation Codes:    LOINC (required for all observation types)
Units of Measure:     UCUM (required for all measurement values)
Legacy Protocol:      HL7 v2.x (MDIL adapter only)
Imaging:              DICOM (MDIL adapter only)
IoT Protocol:         MQTT v5 (MDIL adapter only)
```

### C1.6 Security
```
Authentication:      JWT (RS256, 4096-bit RSA)
Authorization:       RBAC (role definitions in Security Service)
Password Hashing:    Argon2id
Secrets Management:  HashiCorp Vault (production) / Docker Secrets (development)
TLS:                 TLS 1.3 minimum (no older versions)
Service-to-service:  mTLS (production)
```

### C1.7 Observability
```
Metrics:    Prometheus + Grafana
Logging:    Loki + Promtail
Alerting:   Alertmanager
Log Format: Structured JSON (stdout only)
```

### C1.8 Containerization and Deployment
```
Containerization:   Docker
Orchestration Dev:  Docker Compose
Orchestration Prod: Kubernetes (K8s) or Docker Swarm
Base Images:        python:3.12-slim (backend), node:20-slim (if any frontend)
Registry:           Private container registry (project-specific)
CI/CD:              GitHub Actions
```

---

## C2 — SERVICE BOUNDARIES (IMMUTABLE)

### C2.1 Data-Path Communication Rule
```
RULE: No service may call another service's internal API in the data hot-path.
RULE: All data-path inter-service communication flows through Redis Streams ONLY.
EXCEPTION: None permitted.
```

### C2.2 Database Ownership Rule
```
RULE: Each service owns its data store exclusively.
RULE: No service reads directly from another service's database.
RULE: Database Service is the ONLY service with write access to SQLite and PostgreSQL.
EXCEPTION: Read replicas may be used for historical query access by Dashboard Service,
           but only through a defined read-only interface, not direct DB connection.
```

### C2.3 Stateless Processing Rule
```
RULE: Validation Service holds NO persistent state.
RULE: Normalization Service holds NO persistent state.
RULE: Both services must be restartable at any time without data loss.
```

### C2.4 AI Boundary Rule
```
RULE: AI Service (SEVRA AI) is a pure event consumer and producer.
RULE: AI Service NEVER writes to SQLite or PostgreSQL directly.
RULE: AI Service NEVER modifies clinical source records.
RULE: All AI outputs are published to stream:ai.insights ONLY.
```

### C2.5 Security Boundary Rule
```
RULE: Authentication and token issuance are performed ONLY by Security Service.
RULE: Individual services validate tokens cryptographically (using public key)
      but do NOT issue tokens.
RULE: Audit log writes are performed ONLY by Security Service consuming stream:audit.events.
RULE: Individual services EMIT to stream:audit.events; they do NOT write to the audit DB.
```

### C2.6 Write Path Exclusivity Rule
```
RULE: Only Database Service writes to SQLite and PostgreSQL.
RULE: Only Security Service writes to the audit log table.
RULE: Only AI Service writes to stream:ai.insights.
RULE: Only MDIL writes to stream:mdil.raw.
RULE: Only Normalization writes to stream:normalized.events.
```

---

## C3 — DATA FLOW RULES (IMMUTABLE)

### C3.1 Pipeline Ordering
```
REQUIRED ORDER:
Device/Simulator → MDIL → Collectors → Validation → Normalization
→ Event Bus Fan-Out → {Database, Dashboard, AI} → Hospital Integration

NO SKIPPING STAGES. A service may not publish to a downstream stream
without first receiving from the correct upstream stream.
```

### C3.2 Event Identity Rule
```
RULE: Every event is assigned a UUID v4 event_id by Collectors Service.
RULE: This event_id is IMMUTABLE — it never changes through the pipeline.
RULE: event_id is the global idempotency key for all services.
RULE: No service re-generates or overwrites event_id.
```

### C3.3 At-Least-Once Delivery Rule
```
RULE: All services use Redis consumer groups.
RULE: XACK is sent ONLY after successful processing AND successful downstream write.
RULE: If processing fails: no XACK; PEL holds message for re-delivery.
RULE: All processing must be idempotent.
```

### C3.4 No Silent Data Loss Rule
```
RULE: No event is silently dropped at any pipeline stage.
RULE: Failed events MUST be routed to a named DLQ stream with full error context.
RULE: Every DLQ write MUST trigger a monitoring alert.
```

### C3.5 Offline-First Write Rule
```
RULE: Database Service writes to SQLite FIRST, always.
RULE: PostgreSQL sync is asynchronous and may be delayed.
RULE: Unavailability of PostgreSQL does NOT block writes to SQLite.
RULE: Redis unavailability triggers edge buffering; data must not be lost.
```

### C3.6 Data Transformation Boundary
```
RULE: Raw device protocol data exists ONLY within MDIL.
RULE: Internal Event Envelope format exists from Collectors to Normalization.
RULE: FHIR R4 Observation format is used from Normalization onward.
RULE: No service downstream of Normalization consumes non-FHIR data.
```

---

## C4 — SECURITY RULES (IMMUTABLE)

### C4.1 Authentication
```
RULE: Every API endpoint (except /health, /metrics, /auth/login) requires a valid JWT.
RULE: JWT must be RS256 signed with the Security Service private key.
RULE: JWT access token TTL is exactly 15 minutes.
RULE: JWT refresh token TTL is exactly 7 days.
RULE: Expired tokens are rejected with HTTP 401.
```

### C4.2 Authorization
```
RULE: Every authenticated request is checked against RBAC role permissions.
RULE: Unauthorized requests are rejected with HTTP 403.
RULE: All authorization denials are logged to stream:audit.events.
RULE: Cross-facility data access is forbidden unless explicitly granted by admin role.
```

### C4.3 Encryption
```
RULE: All data at rest in SQLite uses SQLCipher (AES-256).
RULE: All data at rest in PostgreSQL uses TDE (AES-256).
RULE: All data in transit uses TLS 1.3 minimum.
RULE: No plaintext secrets in any file committed to Git.
RULE: No plaintext database connection strings in environment files committed to Git.
```

### C4.4 Secrets
```
RULE: All secrets are stored in HashiCorp Vault (production).
RULE: No secret is hardcoded in source code.
RULE: No secret is stored in a Dockerfile.
RULE: .env files containing real secrets are NEVER committed to Git.
RULE: .env.example files contain only placeholder values.
```

### C4.5 Audit
```
RULE: Every data read, write, delete, and alert acknowledgement is logged.
RULE: Every authentication attempt (success and failure) is logged.
RULE: Every authorization denial is logged.
RULE: Audit log records are NEVER modified or deleted within retention window.
RULE: Audit logs are retained for minimum 365 days (hot) and 7 years (cold archive).
```

---

## C5 — NAMING CONVENTIONS (IMMUTABLE)

### C5.1 Redis Stream Names
```
Pattern:  stream:{service}.{event_type}
Examples: stream:mdil.raw
          stream:mdil.parse_errors
          stream:validation.passed
          stream:validation.failed
          stream:normalized.events
          stream:ai.insights
          stream:audit.events
Rule:     All lowercase. Dots as separators. No underscores in stream names.
```

### C5.2 Consumer Group Names
```
Pattern:  {consuming-service}-group
Examples: collectors-group
          validation-group
          db-service-group
          ai-service-group
Rule:     All lowercase. Hyphens as separators.
```

### C5.3 Service Names
```
Pattern:  {function}-service (for multi-word: hyphen-separated)
Examples: mdil-service
          collectors-service
          validation-service
          normalization-service
          database-service
          dashboard-service
          ai-service
          hospital-integration-service
          security-service
Rule:     All lowercase. Hyphens as separators.
```

### C5.4 Python Package Names
```
Pattern:  helios_{service_name} (underscores for Python packages)
Examples: helios_mdil
          helios_collectors
          helios_validation
          helios_normalization
          helios_database
          helios_dashboard
          helios_ai
          helios_hospital_integration
          helios_security
```

### C5.5 Environment Variables
```
Pattern:  HELIOS_{SERVICE}_{VARIABLE}
Examples: HELIOS_REDIS_HOST
          HELIOS_REDIS_PORT
          HELIOS_POSTGRES_HOST
          HELIOS_MDIL_MQTT_BROKER
          HELIOS_AI_MODEL_PATH
          HELIOS_SECURITY_JWT_PRIVATE_KEY_PATH
Rule:     All uppercase. Underscores as separators.
```

### C5.6 Docker Image Names
```
Pattern:  helios/{service-name}:{semver}-{git-sha-short}
Examples: helios/mdil-service:1.0.0-abc1234
          helios/ai-service:1.0.0-abc1234
Rule:     Lowercase. Semantic versioning. Git SHA appended.
```

### C5.7 FHIR Observation IDs
```
Rule:     FHIR Observation resource id = event_id (UUID v4)
          This ensures 1:1 traceability from pipeline event to FHIR record.
```

---

## C6 — REPOSITORY CONVENTIONS (IMMUTABLE)

### C6.1 Repository Structure
```
RULE: Every service lives in services/{service-name}/
RULE: Every service has: Dockerfile, requirements.txt, pyproject.toml, src/, tests/
RULE: Shared code lives in shared/helios-common/
RULE: Infrastructure config lives in infrastructure/
RULE: Monitoring config lives in monitoring/
RULE: Deployment config lives in deployment/
RULE: Architecture docs live in docs/architecture/
```

### C6.2 Branching
```
main      — Protected. Production-ready. Requires PR + 2 approvals.
develop   — Integration. Auto-deploys to staging on merge.
feature/* — Feature work. PR to develop.
hotfix/*  — Critical fixes. Expedited review, direct to main.
release/* — Release candidates.
```

### C6.3 Commit Messages
```
Pattern: {type}({scope}): {description}
Types:   feat | fix | refactor | test | docs | chore | security
Examples:
  feat(validation): add Tier 3 clinical plausibility rules
  fix(mdil): handle MQTT broker disconnect edge case
  security(security-service): rotate JWT signing key
```

### C6.4 Testing Requirements
```
RULE: Unit test coverage minimum: 80% per service
RULE: Every public function has a corresponding unit test
RULE: Integration tests cover the full pipeline (device → database)
RULE: Performance tests validate SLA targets (pipeline < 200ms, AI < 500ms)
RULE: Tests must pass in CI before any merge to develop or main
```

---

## C7 — DEPLOYMENT CONVENTIONS (IMMUTABLE)

### C7.1 Environment Parity
```
RULE: Development, staging, and production use the same Docker images.
RULE: Only configuration (environment variables, secrets) differs between environments.
RULE: No code changes between environments.
```

### C7.2 Production Deployment
```
RULE: Production deployments require manual approval after staging passes.
RULE: All production deployments use blue-green strategy.
RULE: Automatic rollback triggers if error rate exceeds 5% within 5 minutes.
RULE: Every production deployment is logged to the audit trail.
```

### C7.3 Container Rules
```
RULE: One process per container.
RULE: No root user in production containers.
RULE: No secrets in Docker images.
RULE: Health check defined in every Dockerfile.
RULE: Images built with multi-stage builds.
RULE: Base images pinned to specific versions (not :latest).
```

### C7.4 Kubernetes Rules
```
RULE: Every service has resource requests and limits defined.
RULE: Every service has a HorizontalPodAutoscaler.
RULE: Every service has a PodDisruptionBudget.
RULE: NetworkPolicies enforce zone-based isolation.
RULE: All secrets sourced from HashiCorp Vault via External Secrets Operator.
```

---

## C8 — HEALTHCARE COMPLIANCE RULES (IMMUTABLE)

```
RULE: All patient data (PHI) is encrypted at rest and in transit.
RULE: All access to PHI is logged to the audit trail.
RULE: Patient data is scoped to facility — cross-facility access is forbidden without grant.
RULE: Clinical observations use LOINC codes (no proprietary codes in normalized events).
RULE: Measurement values use UCUM units (no vendor-specific units in normalized events).
RULE: Normalized events conform to HL7 FHIR R4 Observation resource structure.
RULE: AI insights include clinical_rationale (mandatory — no black-box alerts).
RULE: Data retention: clinical records minimum 7 years; audit logs minimum 7 years.
RULE: AI models used in clinical decision support must have a model_version and be logged.
```

---

## C9 — FUTURE EXPANSION RULES

```
RULE: New services MUST integrate via Redis Streams event bus.
RULE: New services MUST NOT introduce direct service-to-service API calls in the data path.
RULE: New device protocols are added as MDIL adapters only.
RULE: New clinical models are added as AI Service model plugins only.
RULE: New hospital systems are added as Hospital Integration Layer connectors only.
RULE: This contract must be updated and re-ratified if any new service boundary is introduced.
RULE: Breaking changes to stream message schemas require schema versioning and migration plan.
```

---

## C10 — CONTRACT CHANGE PROCESS

```
Any deviation from this contract requires:

1. Written Architecture Change Request (ACR) submitted to Chief Architect
2. Impact assessment on all affected services
3. Security review (if security-related)
4. Compliance review (if PHI or retention affected)
5. ARB (Architecture Review Board) approval
6. Version increment of this document (semantic versioning)
7. All affected teams notified before implementation begins
8. Implementation must be backward-compatible or include a migration plan

Unauthorized deviations from this contract detected in code review
must be rejected and flagged to the Chief Architect immediately.
```

---

*END OF ARCHITECTURAL CONTRACT*
*HELIOS OS + SEVRA AI — Version 1.0.0*
*This document is the source of truth. All future work begins here.*
