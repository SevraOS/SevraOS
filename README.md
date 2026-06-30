# Sevra Healthcare Operating Ecosystem

Sevra is a next-generation healthcare operating ecosystem designed to modernize hospital infrastructure through intelligent edge computing, real-time patient telemetry, embedded AI, medical device interoperability, and robust offline-first security.

Unlike traditional isolated clinical software, Sevra connects patients, clinicians, medical devices, and AI models through a unified, high-reliability platform architecture.

```text
                        SEVRA ECOSYSTEM
                               │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
         SevraOS             Helios            Sevra AI
   (Real-Time Edge OS)   (Edge Hardware)   (Clinical Intel)
             │                  │                  │
             └──────────────────┬──────────────────┘
                                ▼
                       Healthcare Platform
                               │
                     Hospital Infrastructure
```

---

## 📁 Repository Structure

The repository is organized into distinct sub-projects separating the operating system environment from the clinical application backend, deployment assets, and system monitoring:

- 📁 **[sevraos/](file:///c:/Users/ThePC/SevraOS/sevraos/README.md)**: The Arch Linux-based build profile for the custom **SevraOS** Live operating system.
  - `airootfs/` - Custom filesystem overlay (system configuration files, telemetry services, sddm config, autostart rules).
  - `efiboot/` & `grub/` & `syslinux/` - Configured bootloaders branded for SevraOS, supporting both UEFI and BIOS boot modes.
  - `profiledef.sh` - Archiso configuration profile defining filesystem permissions and ISO build specifications.
  - `packages.x86_64` - Packages installed on the live environment (including real-time kernel `linux-rt`, network stacks, and custom diagnostic tools).
- 📁 **[backend/](file:///c:/Users/ThePC/SevraOS/backend/README.md)**: Core platform service implementation (FastAPI / ASGI App).
  - `app/` - Edge telemetry endpoints, static asset routing, and high-frequency WebSocket streams.
  - `dashboard/` - Clinician portal REST API and WebSocket dispatcher.
  - **[database/](file:///c:/Users/ThePC/SevraOS/backend/database/README.md)** - Repository layers, Unit of Work patterns, and migration tools.
  - `mdil/` - Medical Device Interoperability Layer (serial, socket, BLE, USB).
  - `eventbus/` - Redis Stream-based high-throughput pub/sub and dead-letter channels.
  - `validation/` & `normalization/` - Clinical safety checking, outlier mitigation, and FHIR/HL7 normalizers.
- 📁 **[frontend/](file:///c:/Users/ThePC/SevraOS/frontend/README.md)**: The client-side dashboard and visualization user interface.
  - [index.html](file:///c:/Users/ThePC/SevraOS/frontend/index.html) - Sidebar navigation, patient headers, and views frame.
  - [index.css](file:///c:/Users/ThePC/SevraOS/frontend/index.css) - Custom styling theme, glassmorphic layout parameters, animations.
  - [index.js](file:///c:/Users/ThePC/SevraOS/frontend/index.js) - Telemetry waveform loop, scan split-slider widget, settings triggers.
- 📁 **[simulations/](file:///c:/Users/ThePC/SevraOS/simulations/README.md)**: Telemetry and data generators.
- 📁 **[deployment/](file:///c:/Users/ThePC/SevraOS/deployment/README.md)**: Production infrastructure configurations (Docker Compose, Kubernetes Manifests, Terraform, Prometheus Configs).
- 📁 **`docs/`**: Detailed system architectures, security contracts, and scaling analysis.
- 📁 **`monitoring/`**: Logging and telemetry pipelines (Prometheus, Loki, Promtail).

---

## ⚡ SevraOS Features

SevraOS is built on a hardened, deterministic Linux base engineered specifically for medical device gateways and edge workstations:

- 🚀 **Real-Time kernel (`linux-rt`)**: Lower scheduler latency for high-precision telemetry capture.
- 📺 **Kiosk Telemetry UI**: Fullscreen interactive patient dashboard starting automatically on graphical session load.
- 🔌 **Auto Graphical Login**: Configured to boot straight to KDE Plasma and sign in the default `severa` user.
- 🛡️ **Sevra Recovery Mode**: Dedicated bootable recovery console equipped with disk repair tools, diagnostic analyzers, and journal collectors.
- 🌐 **Branded Bootloaders**: Fully custom GRUB, UEFI systemd-boot, and Syslinux configurations pre-set with real-time kernel configurations.

## 🛠️ Getting Started

### 1. Virtually Booting the Operating System (QEMU)
To boot and test the compiled SevraOS live ISO virtually in a QEMU virtual machine before deploying to bare metal:
- **Windows PowerShell**:
  ```powershell
  .\scripts\run_vm_qemu.ps1
  ```
- **Linux/macOS**:
  ```bash
  chmod +x scripts/run_vm_qemu.sh
  ./scripts/run_vm_qemu.sh
  ```
*Note: This requires QEMU installed and the ISO compiled inside `sevraos/out/`.*

### 2. Running the Local Simulation Environment (One-Click)
If you want to run the FastAPI edge server and interactive web client terminal dashboard instantly without a virtual machine:
- **Windows PowerShell**:
  ```powershell
  .\scripts\run_simulation.ps1
  ```
- **Linux/macOS**:
  ```bash
  chmod +x scripts/run_simulation.sh
  ./scripts/run_simulation.sh
  ```
This script automatically sets up the Python virtual environment, installs gateway dependencies, opens your default web browser to `http://localhost:8000`, and fires up the Edge gateway.

### 3. Running the HELIOS OS Production Stack
To run the full multi-service production stack (Database, Cache, Dashboard, AI Engine, Object Storage, and Prometheus monitoring):
1. `docker-compose -f deployment/docker/docker-compose.yaml up -d`
2. Run Central Dashboard APIs: `cd backend && uvicorn dashboard.api.main:app --reload --port 8000`
3. Run AI Service: `cd backend && uvicorn ai.main:app --reload --port 8001`

---

## 📖 Deployment & Operations Guide

*   **Kubernetes:** Production deployment templates are provided in `deployment/kubernetes/base/`. Requires Nginx Ingress Controller and cert-manager for mTLS.
*   **Scalability:** Configure the Horizontal Pod Autoscaler (`HPA`) to monitor CPU usage. Default `minReplicas` is 3, max is 20.
*   **High Availability:** Redis requires Redis Sentinel or Redis Cluster in production. PostgreSQL requires Patroni.

---

## 🔒 Security Guide

*   **RBAC:** Role-Based Access Control definitions reside in `backend/core/security/rbac.py`. Never share `HELIOS_JWT_SECRET`.
*   **Encryption:** The edge devices run SQLCipher database encryption. Keys are dynamically injected via Kubernetes Secrets.

---

## 🧬 FHIR & HL7 Integration Guide

*   **FHIR Models:** We support Patient, Observation, Device, Encounter, Practitioner, CarePlan, Condition, MedicationRequest, and DiagnosticReport (R4 Standard).
*   **Adapters:** Includes native integration adapters for Epic, Cerner, OpenEMR, and OpenMRS.
*   **HL7 v2:** Built-in high-speed parsers for ADT (Admissions), ORU (Results), ORM (Orders), and SIU (Scheduling).

---

## 🚨 Disaster Recovery & Monitoring

*   **Backups:** Execute `deployment/scripts/backup_db.sh` via CronJob to dump `pg_dump` to MinIO.
*   **Prometheus/Grafana:** Scrape targets configured in `deployment/monitoring/prometheus.yml`.
*   **Tracing:** OpenTelemetry initialized in `backend/core/telemetry.py`.

---

## 🛰️ System Telemetry Flow

Clinicians interact with the patient edge nodes through the following workflow:

```text
  Patient Telemetry
         │
         ▼
   Helios Device
         │  (Real-Time Monitoring / WebSockets)
         ▼
  SevraOS Platform ──────► Local Edge Kiosk UI
         │         ──────► Real-Time Clinical Alerts
         ▼
  FastAPI Backend  ──────► Electronic Health Records (EHR)
         │         ──────► Historical Secure Storage
         ▼
  Sevra AI Platform
```
