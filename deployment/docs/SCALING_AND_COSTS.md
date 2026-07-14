# HELIOS OS + SEVRA AI
# COST & RESOURCE OPTIMIZATION (Sections 13 & 14)

## Cost Estimation (AWS / Month)

| Scale | Compute (EKS) | Database (RDS) | Cache (ElastiCache) | Total Est. |
| :--- | :--- | :--- | :--- | :--- |
| **100 Patients** | $140 (2x t3.medium) | $30 (db.t4g.micro) | $16 (cache.t4g.micro) | **$186 / mo** |
| **1,000 Patients** | $280 (4x t3.medium) | $130 (db.t4g.large) | $60 (cache.m6g.large) | **$470 / mo** |
| **10,000 Patients** | $850 (6x c6g.xlarge) | $550 (Aurora Serverless) | $200 (Redis Cluster) | **$1,600 / mo** |
| **100k Patients** | $3,500 (GPU + Compute)| $1,800 (Aurora Cluster) | $800 (Redis Cluster) | **$6,100 / mo** |

## Resource Optimization Recommendations

1.  **AI Services (Compute Heavy):** Use ARM64 (Graviton) instances. They provide a 40% price-performance benefit for ONNX inference when running on CPU.
2.  **Database (Storage Heavy):** For data older than 90 days, implement a tiering strategy to export PostgreSQL historical records to Parquet files in S3/MinIO to avoid expensive block storage costs.
3.  **Network Data Transfer:** Enable WebSockets compression (`permessage-deflate`) to reduce the outbound bandwidth charges for the live vitals streams.
