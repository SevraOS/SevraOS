# HELIOS OS + SEVRA AI — Deployment Configuration

This directory contains the production-grade deployment manifests, environment parameters, and setup automation for the [Sevra Healthcare Operating Ecosystem](file:///c:/Users/ThePC/SevraOS/README.md).

For the full deployment and architecture blueprint, refer to [Monitoring and Deployment Design](file:///c:/Users/ThePC/SevraOS/docs/architecture/S7_S8_monitoring_and_deployment.md).

## Folder Structure

```text
deployment/
├── docker/
│   ├── .env                    # Docker Compose environment parameters
│   └── docker-compose.yaml     # Single-node stack orchestration setup
├── kubernetes/
│   ├── namespaces/
│   ├── services/
│   │   ├── backend/
│   │   │   ├── deployment.yml  # K8s Backend Deployment
│   │   │   ├── service.yml     # K8s Service (ClusterIP)
│   │   │   ├── configmap.yml   # Non-sensitive config parameters
│   │   │   └── hpa.yml         # Horizontal Pod Autoscaler configuration
│   │   └── ...other services...
│   ├── infrastructure/
│   │   ├── redis-statefulset.yml
│   │   ├── postgres-statefulset.yml
│   │   └── minio-statefulset.yml
│   ├── monitoring/
│   │   ├── prometheus-deployment.yml
│   │   └── grafana-deployment.yml
│   ├── network-policies/
│   │   ├── device-zone.yml
│   │   ├── pipeline-zone.yml
│   │   ├── app-zone.yml
│   │   └── data-zone.yml
│   └── ingress/
│       └── ingress.yml
└── scripts/
    ├── deploy.sh               # Local environment installer
    ├── rollback.sh             # Fail-safe rollback driver
    └── health-check.sh         # Ingress service health verifier
```

Relevant files:
- 🐳 **Docker Compose Setup**: [docker-compose.yaml](file:///c:/Users/ThePC/SevraOS/deployment/docker/docker-compose.yaml) and [docker-compose environment variables](file:///c:/Users/ThePC/SevraOS/deployment/docker/.env)
- ⚙️ **Deployment automation scripts**: [deploy.sh](file:///c:/Users/ThePC/SevraOS/deployment/scripts/deploy.sh), [rollback.sh](file:///c:/Users/ThePC/SevraOS/deployment/scripts/rollback.sh), and [health-check.sh](file:///c:/Users/ThePC/SevraOS/deployment/scripts/health-check.sh)

## Note
Kubernetes manifests will be generated in a dedicated DevOps prompt. This directory is the designated home for all deployment artifacts.
