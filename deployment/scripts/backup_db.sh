#!/bin/bash
# HELIOS OS + SEVRA AI
# Disaster Recovery Backup Script (Section 18)

set -e

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="helios_central"

echo "Starting Database Backup for ${DB_NAME} at ${DATE}"

# 1. Dump Database
pg_dump -h postgres -U ${POSTGRES_USER} -F c -b -v -f "${BACKUP_DIR}/${DB_NAME}_${DATE}.backup" ${DB_NAME}

# 2. Upload to MinIO / S3
mc alias set helios_minio http://minio:9000 ${MINIO_USER} ${MINIO_PASSWORD}
mc cp "${BACKUP_DIR}/${DB_NAME}_${DATE}.backup" helios_minio/db-backups/

echo "Backup complete and uploaded to Object Storage."
