# HELIOS OS + SEVRA AI Platform: Complete Deployment Guide

This document outlines the end-to-end steps required to launch the complete Helios Healthcare Platform from scratch. This includes standing up the core infrastructure, initializing the schemas, starting the background processors, and injecting simulated telemetry.

## Prerequisites
1. **Docker Desktop** installed and running on your host machine.
2. **Python 3.10+** installed locally for running the simulator.
3. **DBeaver** (or similar SQL client) installed for database verification.

---

## Step 1: Launch Core Infrastructure
The system uses Docker Compose to orchestrate multiple microservices, including PostgreSQL, Redis, MinIO, Grafana, Prometheus, and the Helios APIs.

1. Open a PowerShell terminal.
2. Navigate to your project root folder: `cd "D:\Sharvas Projects\SevraProject_sample"`
3. Create the local data directory to avoid read-only filesystem issues during build:
```bash
mkdir backend\data
```
4. Run the following command to build and launch all containers in the background:
```bash
docker compose up -d --build
```
*Wait for the containers to fully start. You can verify they are healthy by running `docker compose ps`.*

*Note: In Docker Desktop, these containers will be grouped under a stack. If you expand it, you will see the individual containers like `helios-backend`, `helios-postgres`, `helios-redis`, `helios-grafana`, `helios-minio`, etc.*

---

## Step 2: Initialize Database Schemas
Before data can be ingested, the PostgreSQL database schemas (`vitals`, `patients`, `devices`, etc.) must be programmatically created via SQLAlchemy.

1. The script is already mounted inside the container. Run it using:
```bash
docker compose exec helios-backend python /app/init_db.py
```
2. You should see an output indicating the tables were created successfully.

---

## Step 3: Start the Ingestion Worker
The ingestion worker is a background process that continuously listens to the Redis Event Bus (`helios.telemetry.raw`) and permanently saves incoming telemetry to the PostgreSQL database.

1. Launch the worker in detached mode (`-d`) inside the `helios-backend` container:
```bash
docker compose exec -d helios-backend python -u /app/ingestion_worker.py
```

---

## Step 4: Run the Telemetry Simulator
The simulator acts as a bedside medical device, generating real-time heart rate data and streaming it directly into the Redis Event Bus.

1. Open a **new** PowerShell terminal.
2. Ensure the `redis` library is installed locally:
```bash
pip install redis
```
3. Run the simulator script:
```bash
python simulations/simulate.py
```
*You will see terminal output showing live heart rates. Leave this terminal running.*

---

## Step 5: Validation & Access Points
With the system fully launched, you can interact with various interfaces to validate data flow.

### 1. Database Verification (DBeaver)
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `helios`
- **Username:** `helios`
- **Password:** `helios_dev_password`
- **Action:** Open the `vitals` table and click the "Data" tab. Click Refresh to see live simulator rows appearing.

### 2. API Documentation (Swagger)
- **URL:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **Action:** Interactive UI to test your REST endpoints (e.g., querying Patient Vitals).

### 3. System Monitoring (Grafana)
- **URL:** [http://localhost:3001](http://localhost:3001)
- **Action:** Visualize system health and throughput metrics. (User: `admin` / Password: `helios_grafana`)

### 4. MinIO Object Storage Console
- **URL:** [http://localhost:9001](http://localhost:9001)
- **Action:** View stored assets. (User: `helios` / Password: `helios_dev_password`)

### 5. Prometheus Metrics
- **URL:** [http://localhost:9090](http://localhost:9090)
- **Action:** Query the underlying metrics data.

---

## System Teardown
To safely stop the platform and preserve your database/Redis volumes:
```bash
docker compose stop
```
To stop the platform and wipe the databases entirely:
```bash
docker compose down -v
```
