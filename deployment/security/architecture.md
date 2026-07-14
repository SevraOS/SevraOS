# HELIOS OS + SEVRA AI
## Security & Compliance Architecture (Sections 11 & 12)

### 1. HIPAA & GDPR Compliance
*   **Encryption at Rest:** Tier 1 SQLite uses **SQLCipher** with `PRAGMA rekey` runtime rotation. Tier 2 PostgreSQL uses AWS EBS encryption / PG_CRYPTO.
*   **Encryption in Transit:** All connections, including Internal Cluster traffic (mTLS via Istio) and external EHR connections, strictly enforce **TLS 1.3**.
*   **Data Minimization:** AI Inference payloads strip PII before routing to the ONNX execution provider.

### 2. Security Hardening
*   **mTLS (Mutual TLS):** Configured via Kubernetes service mesh to ensure that only the AI Service can talk to the Database Service, and only the Dashboard API can read from it.
*   **Secrets Management:** Kubernetes Secrets / HashiCorp Vault is injected at runtime. `HELIOS_JWT_SECRET` and `HELIOS_SQLITE_ENCRYPTION_KEY` are never committed.
*   **RBAC (Role Based Access Control):** Defined via JWT claims (`role`). Enforced at the FastAPI Router level using `Depends(require_role(["Admin", "Doctor"]))`.

### 3. Audit Framework (IEC 62304 / FDA Compliance)
*   **Access Logging:** Every `GET` request to Patient endpoints logs the `sub` (User ID), `patient_id`, and `timestamp` to `stream:audit.access`.
*   **Inference Logging:** Every AI decision is pushed to the `InferenceHistoryRepository` to explain the heuristic model output if an adverse event occurs.
