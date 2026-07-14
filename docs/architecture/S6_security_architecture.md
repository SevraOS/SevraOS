# HELIOS OS + SEVRA AI — Architecture
# Section 6: Security Architecture

---

## 6.1 Security Philosophy

Security is not a feature — it is a foundational constraint.
Every service is designed as if the network is hostile.
No service trusts another without cryptographic proof of identity.
No data crosses a service boundary without authorization enforcement.
No action in the system goes unlogged.

---

## 6.2 Authentication Architecture

### Identity Provider
- **Internal Auth Service** (Security Service) is the sole identity provider
- No third-party OAuth/OIDC dependency for the core system
- Optional external IdP integration (Azure AD, Okta) via SAML 2.0 federation layer

### Authentication Flow
```
1. Client submits credentials (username + password) to Security Service /auth/login
2. Security Service validates credentials against User Store (PostgreSQL)
3. Password stored as Argon2id hash (never plaintext or MD5/bcrypt)
4. On success: issue JWT Access Token (15 min) + JWT Refresh Token (7 days)
5. Tokens returned to client
6. Client sends Access Token as Bearer in Authorization header on every request
7. Receiving service validates token signature against public key
8. If Access Token expired: client sends Refresh Token to /auth/refresh
9. Security Service validates Refresh Token, issues new Access Token
10. If Refresh Token expired: full re-authentication required
```

### JWT Token Structure
```
Access Token:
  Header: {"alg": "RS256", "typ": "JWT"}
  Payload: {
    "sub": "user_id",
    "jti": "token_unique_id",
    "iat": issued_at,
    "exp": expiry (iat + 900 seconds),
    "roles": ["clinician", "nurse"],
    "facility_id": "FACILITY-001",
    "scope": ["read:vitals", "acknowledge:alerts"]
  }
  Signature: RS256 with 4096-bit RSA private key

Refresh Token:
  Same structure, exp = iat + 604800 (7 days)
  Stored in Redis with TTL for revocation support
```

### Signing Key Management
```
Algorithm: RS256 (asymmetric — private key signs, public key validates)
Key Size: 4096-bit RSA
Private Key Storage: HashiCorp Vault (never in config files or env vars)
Public Key Distribution: JWK endpoint (/auth/jwks.json) — all services validate locally
Key Rotation: Quarterly rotation (or immediately on security event)
Key Rotation Strategy: Dual-key overlap period (old key valid for 24h during rotation)
```

---

## 6.3 Authorization Architecture

### RBAC Model

**Clinical Roles:**
```
clinician
  - Read: patient vitals, AI insights, device status, patient history
  - Write: acknowledge AI alerts, add clinical notes
  - Cannot: modify device config, access other patients' data without assignment

nurse
  - Read: assigned ward patient vitals, AI insights
  - Write: acknowledge alerts, update observation notes
  - Cannot: access admin functions, modify roles

admin
  - Read: everything in assigned facility
  - Write: user management, device registration, facility config
  - Cannot: modify audit logs, access clinical AI model configurations

device_operator
  - Read: device status, device registry, raw device logs
  - Write: device registration, device configuration
  - Cannot: read patient clinical data

auditor
  - Read: all audit logs, all event logs, system health reports
  - Write: nothing
  - Cannot: read patient clinical data content (only metadata/access logs)

ai_reviewer
  - Read: AI model registry, model performance metrics, all AI insights
  - Write: approve/retire AI model versions, add review notes to insights
  - Cannot: modify clinical records, manage users
```

### Permission Enforcement
```
Every service endpoint validates:
  1. Token signature (cryptographic proof of identity)
  2. Token expiry (time validity)
  3. Token not in blacklist (revocation check via Redis)
  4. User role includes required permission for this action
  5. User's facility_id matches the requested resource's facility_id
     (cross-facility access forbidden unless role = admin with multi-facility grant)
```

### Resource-Level Authorization
```
Patient data access:
  - Clinicians and nurses access ONLY patients assigned to their ward
  - Patient assignment managed in the assignment registry
  - Cross-ward access requires explicit admin grant + is logged as exceptional access

AI model access:
  - ai_reviewer role required to read model artifacts and performance metrics
  - admin role required to deploy or retire models
```

---

## 6.4 Encryption at Rest

| Store | Encryption Method | Algorithm | Key Management |
|---|---|---|---|
| SQLite (edge) | SQLCipher | AES-256-CBC | HashiCorp Vault |
| PostgreSQL | Tablespace TDE | AES-256 | HashiCorp Vault |
| MinIO Objects | SSE-S3 | AES-256 | HashiCorp Vault KMS |
| Redis | Encrypted volume (filesystem level) | AES-256 | OS-level disk encryption |
| Log files | Encrypted log volume | AES-256 | OS-level disk encryption |
| Backup files | GPG encryption before storage | AES-256 | HashiCorp Vault |

---

## 6.5 Encryption in Transit

```
All service-to-service communication: TLS 1.3 minimum
  - No TLS 1.0 or TLS 1.1 permitted
  - Certificate validation enforced (no skip-verify in production)
  - Mutual TLS (mTLS) for service-to-service internal communication

All client-to-service communication: TLS 1.3
  - HTTPS only; HTTP redirected to HTTPS
  - HSTS header enforced (max-age: 31536000)

Redis connections: TLS-encrypted Redis connections
PostgreSQL connections: SSL mode = require (verify-full in production)
External hospital systems: TLS 1.3 for FHIR REST; TLS tunnel for MLLP

Certificate Authority:
  - Internal services: Private CA managed in HashiCorp Vault PKI
  - External-facing: Publicly trusted CA (Let's Encrypt or commercial CA)
```

---

## 6.6 Secrets Management

### Secret Categories
```
Category 1 — Database Credentials
  What: PostgreSQL username/password, SQLite encryption key, Redis password
  Store: HashiCorp Vault (dynamic secrets with lease TTL)

Category 2 — JWT Signing Keys
  What: RS256 private key for token signing
  Store: HashiCorp Vault (never in files or environment variables)

Category 3 — Service Credentials
  What: Inter-service API keys, MinIO credentials, external hospital API keys
  Store: HashiCorp Vault

Category 4 — TLS Certificates
  What: Private keys for all services
  Store: HashiCorp Vault PKI engine (auto-renew before expiry)

Category 5 — External System Credentials
  What: Hospital HIS/EMR API keys, MLLP tunnel credentials
  Store: HashiCorp Vault
```

### Secret Injection Strategy
```
Development: Docker Secrets (docker-compose secrets)
Production:  HashiCorp Vault Agent sidecar (injects secrets into service env at startup)

Rules:
  - No secrets in Dockerfiles
  - No secrets in docker-compose.yml (use secret references only)
  - No secrets in Git repository (any commit with secrets triggers immediate rotation)
  - Secrets are rotated on: scheduled interval, personnel change, security event
```

---

## 6.7 Audit Logging

### What Is Logged
```
Every event written to stream:audit.events includes:

  event_type       — auth.login | auth.logout | auth.failed | data.read |
                     data.write | data.delete | alert.acknowledged |
                     device.registered | model.deployed | replay.executed |
                     config.changed | secret.rotated | role.changed

  actor_id         — User ID performing the action (null for system actors)
  actor_role       — Role(s) at time of action
  actor_ip         — Source IP address
  session_id       — JWT jti (token unique ID)
  facility_id      — Facility context
  resource_type    — What type of resource was accessed
  resource_id      — Specific resource identifier (patient_id, event_id, etc.)
  action           — read | write | delete | execute | acknowledge
  outcome          — success | denied | error
  timestamp        — UTC ISO-8601
  request_id       — Unique request identifier for correlation
```

### Audit Log Immutability
```
Audit logs are written to PostgreSQL in an append-only table.
  - No UPDATE or DELETE operations permitted on audit log table
  - Table-level triggers block any modification
  - PostgreSQL role for audit writes has INSERT-only permission
  - Regular audit log exports to MinIO cold storage (tamper-evident)
  - Audit log hash chain: each log entry stores hash of previous entry
    (detects any tampering attempt)

Retention: 365 days in PostgreSQL (hot access)
           7 years in MinIO cold archive (regulatory compliance)
```

---

## 6.8 Network Security

### Network Segmentation
```
Zone 1 — Public Zone
  Contains: Load balancer, API gateway
  Access: Internet-facing (port 443 only)

Zone 2 — Application Zone
  Contains: Dashboard Service, Hospital Integration Layer, Security Service
  Access: From Zone 1 only; no direct internet access

Zone 3 — Data Zone
  Contains: Database Service, Redis, PostgreSQL, MinIO
  Access: From Zone 2 only; completely isolated from internet

Zone 4 — Device Zone
  Contains: MDIL, Collectors, Validation, Normalization
  Access: From hospital device network; no internet access
  Communication to Zone 3 only via Event Bus

Zone 5 — AI Zone
  Contains: AI Service, ML Model Registry
  Access: From Zone 3 (event bus) only; no internet in production
```

### Firewall Rules
```
- Only explicitly permitted ports are open
- Default deny on all zones
- All inter-zone traffic logged
- Port 443: public HTTPS (Zone 1 → Zone 2)
- Port 5432: PostgreSQL (Zone 2 → Zone 3, internal only)
- Port 6379: Redis (Zone 2/4 → Zone 3, internal only)
- Port 9000: MinIO (Zone 2/3, internal only)
- No SSH permitted in production containers (use kubectl exec or Vault SSH)
```
