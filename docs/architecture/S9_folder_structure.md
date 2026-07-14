# HELIOS OS + SEVRA AI — Architecture
# Section 9: Master Folder Structure

---

## Repository Root

```
helios-sevra/
│
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docker-compose.staging.yml
├── docker-compose.prod.yml
├── Makefile
│
├── docs/
│   ├── architecture/
│   │   ├── S1_system_overview.md
│   │   ├── S2_backend_service_architecture.md
│   │   ├── S3_data_flow_architecture.md
│   │   ├── S4_event_driven_architecture.md
│   │   ├── S5_database_architecture.md
│   │   ├── S6_security_architecture.md
│   │   ├── S7_S8_monitoring_and_deployment.md
│   │   ├── S9_folder_structure.md
│   │   └── S10_project_contract.md
│   ├── api/
│   │   └── (future: OpenAPI specs per service)
│   ├── runbooks/
│   │   ├── incident-response.md
│   │   ├── dlq-handling.md
│   │   ├── device-onboarding.md
│   │   └── model-deployment.md
│   └── compliance/
│       ├── hipaa-controls.md
│       ├── fhir-r4-compliance.md
│       └── data-retention-policy.md
│
├── services/
│   │
│   ├── mdil/                          # Medical Device Integration Layer
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── .env.example
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── adapters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_adapter.py
│   │   │   │   ├── hl7v2_adapter.py
│   │   │   │   ├── mqtt_adapter.py
│   │   │   │   ├── dicom_adapter.py
│   │   │   │   ├── serial_adapter.py
│   │   │   │   ├── fhir_adapter.py
│   │   │   │   └── simulator_adapter.py
│   │   │   ├── registry/
│   │   │   │   ├── __init__.py
│   │   │   │   └── device_registry.py
│   │   │   ├── producers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── redis_producer.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── device_payload.py
│   │   │   └── health/
│   │   │       ├── __init__.py
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_hl7v2_adapter.py
│   │       ├── test_mqtt_adapter.py
│   │       └── test_device_registry.py
│   │
│   ├── collectors/                    # Collectors Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumer/
│   │   │   │   ├── __init__.py
│   │   │   │   └── mdil_consumer.py
│   │   │   ├── envelope/
│   │   │   │   ├── __init__.py
│   │   │   │   └── event_envelope.py
│   │   │   ├── resolver/
│   │   │   │   ├── __init__.py
│   │   │   │   └── patient_resolver.py
│   │   │   ├── producers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── redis_producer.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── test_event_envelope.py
│   │       └── test_patient_resolver.py
│   │
│   ├── validation/                    # Validation Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumer/
│   │   │   │   └── collector_consumer.py
│   │   │   ├── validators/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_validator.py
│   │   │   │   ├── structural_validator.py
│   │   │   │   ├── domain_validator.py
│   │   │   │   └── clinical_validator.py
│   │   │   ├── rules/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── clinical_rules.py
│   │   │   │   └── clinical_rules.json
│   │   │   ├── schemas/
│   │   │   │   └── event_envelope_schema.json
│   │   │   ├── producers/
│   │   │   │   └── redis_producer.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── test_structural_validator.py
│   │       ├── test_domain_validator.py
│   │       └── test_clinical_validator.py
│   │
│   ├── normalization/                 # Normalization Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumer/
│   │   │   │   └── validation_consumer.py
│   │   │   ├── normalizers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── unit_normalizer.py
│   │   │   │   ├── code_normalizer.py
│   │   │   │   └── timestamp_normalizer.py
│   │   │   ├── fhir/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── observation_builder.py
│   │   │   │   └── provenance_builder.py
│   │   │   ├── mappings/
│   │   │   │   ├── loinc_mappings.json
│   │   │   │   └── ucum_mappings.json
│   │   │   ├── producers/
│   │   │   │   └── redis_producer.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── test_unit_normalizer.py
│   │       ├── test_code_normalizer.py
│   │       └── test_fhir_builder.py
│   │
│   ├── database/                      # Database Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumers/
│   │   │   │   ├── normalized_consumer.py
│   │   │   │   └── insights_consumer.py
│   │   │   ├── writers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── sqlite_writer.py
│   │   │   │   └── postgres_writer.py
│   │   │   ├── sync/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── sync_worker.py
│   │   │   │   └── conflict_resolver.py
│   │   │   ├── migrations/
│   │   │   │   ├── sqlite/
│   │   │   │   │   ├── 001_initial_schema.sql
│   │   │   │   │   └── 002_sync_status_column.sql
│   │   │   │   └── postgres/
│   │   │   │       ├── 001_initial_schema.sql
│   │   │   │       └── 002_audit_log_table.sql
│   │   │   ├── retention/
│   │   │   │   └── retention_worker.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── test_sqlite_writer.py
│   │       ├── test_sync_worker.py
│   │       └── test_conflict_resolver.py
│   │
│   ├── dashboard/                     # Dashboard Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumers/
│   │   │   │   ├── normalized_consumer.py
│   │   │   │   └── insights_consumer.py
│   │   │   ├── websocket/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connection_manager.py
│   │   │   │   └── event_pusher.py
│   │   │   ├── projection/
│   │   │   │   ├── __init__.py
│   │   │   │   └── patient_state_projection.py
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── historical_queries.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── test_connection_manager.py
│   │       └── test_state_projection.py
│   │
│   ├── ai/                            # SEVRA AI Service
│   │   ├── Dockerfile
│   │   ├── Dockerfile.gpu
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumers/
│   │   │   │   └── normalized_consumer.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_model.py
│   │   │   │   ├── news2_model.py
│   │   │   │   ├── mews_model.py
│   │   │   │   ├── sofa_model.py
│   │   │   │   ├── anomaly_detector.py
│   │   │   │   └── sepsis_risk_model.py
│   │   │   ├── registry/
│   │   │   │   ├── __init__.py
│   │   │   │   └── model_registry.py
│   │   │   ├── context/
│   │   │   │   ├── __init__.py
│   │   │   │   └── patient_context_window.py
│   │   │   ├── insights/
│   │   │   │   ├── __init__.py
│   │   │   │   └── insight_builder.py
│   │   │   ├── producers/
│   │   │   │   └── redis_producer.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   ├── model_artifacts/
│   │   │   ├── anomaly_detector_v1/
│   │   │   │   ├── model.pkl
│   │   │   │   └── metadata.json
│   │   │   └── sepsis_risk_v1/
│   │   │       ├── model.pkl
│   │   │       └── metadata.json
│   │   └── tests/
│   │       ├── test_news2_model.py
│   │       ├── test_anomaly_detector.py
│   │       └── test_insight_builder.py
│   │
│   ├── hospital-integration/          # Hospital Integration Layer
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── consumers/
│   │   │   │   ├── insights_consumer.py
│   │   │   │   └── normalized_consumer.py
│   │   │   ├── translators/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── fhir_bundle_translator.py
│   │   │   │   └── hl7v2_translator.py
│   │   │   ├── delivery/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── fhir_rest_delivery.py
│   │   │   │   ├── mllp_delivery.py
│   │   │   │   └── retry_worker.py
│   │   │   ├── registry/
│   │   │   │   ├── __init__.py
│   │   │   │   └── hospital_registry.py
│   │   │   └── health/
│   │   │       └── health_server.py
│   │   └── tests/
│   │       ├── test_fhir_translator.py
│   │       └── test_retry_worker.py
│   │
│   └── security/                      # Security Service
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── pyproject.toml
│       ├── src/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── auth/
│       │   │   ├── __init__.py
│       │   │   ├── jwt_manager.py
│       │   │   ├── password_manager.py
│       │   │   └── session_manager.py
│       │   ├── rbac/
│       │   │   ├── __init__.py
│       │   │   ├── role_definitions.py
│       │   │   └── permission_checker.py
│       │   ├── audit/
│       │   │   ├── __init__.py
│       │   │   └── audit_logger.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── auth_router.py
│       │   │   └── user_router.py
│       │   └── health/
│       │       └── health_server.py
│       └── tests/
│           ├── test_jwt_manager.py
│           ├── test_permission_checker.py
│           └── test_audit_logger.py
│
├── simulator/                         # Medical Device Simulator
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── generators/
│   │   │   ├── vital_generator.py
│   │   │   ├── patient_generator.py
│   │   │   └── scenario_runner.py
│   │   └── scenarios/
│   │       ├── healthy_patient.json
│   │       ├── deteriorating_patient.json
│   │       └── sepsis_scenario.json
│   └── tests/
│       └── test_vital_generator.py
│
├── shared/                            # Shared Libraries
│   ├── helios-common/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── helios_common/
│   │           ├── __init__.py
│   │           ├── redis_client.py
│   │           ├── stream_producer.py
│   │           ├── stream_consumer.py
│   │           ├── idempotency.py
│   │           ├── retry.py
│   │           ├── health.py
│   │           └── logging.py
│
├── infrastructure/                    # Infrastructure as Code
│   ├── redis/
│   │   ├── redis.conf
│   │   └── sentinel.conf
│   ├── postgres/
│   │   ├── postgresql.conf
│   │   └── pg_hba.conf
│   ├── minio/
│   │   └── minio.env
│   ├── vault/
│   │   ├── vault.hcl
│   │   └── policies/
│   │       ├── mdil-policy.hcl
│   │       ├── database-policy.hcl
│   │       └── security-policy.hcl
│   └── nginx/
│       └── nginx.conf
│
├── monitoring/                        # Observability Stack
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── rules/
│   │       ├── infrastructure_alerts.yml
│   │       ├── pipeline_alerts.yml
│   │       ├── ai_service_alerts.yml
│   │       └── security_alerts.yml
│   ├── grafana/
│   │   ├── grafana.ini
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   ├── prometheus.yml
│   │   │   │   └── loki.yml
│   │   │   └── dashboards/
│   │   │       ├── dashboard.yml
│   │   └── dashboards/
│   │       ├── system_overview.json
│   │       ├── clinical_pipeline.json
│   │       ├── ai_service.json
│   │       ├── database_health.json
│   │       └── security_audit.json
│   ├── loki/
│   │   └── loki-config.yml
│   ├── promtail/
│   │   └── promtail-config.yml
│   └── alertmanager/
│       └── alertmanager.yml
│
├── deployment/                        # Deployment Configs
│   ├── kubernetes/
│   │   ├── namespaces/
│   │   │   └── helios.yml
│   │   ├── services/
│   │   │   ├── mdil/
│   │   │   │   ├── deployment.yml
│   │   │   │   ├── service.yml
│   │   │   │   ├── configmap.yml
│   │   │   │   └── hpa.yml
│   │   │   ├── collectors/
│   │   │   ├── validation/
│   │   │   ├── normalization/
│   │   │   ├── database/
│   │   │   ├── dashboard/
│   │   │   ├── ai/
│   │   │   ├── hospital-integration/
│   │   │   └── security/
│   │   ├── infrastructure/
│   │   │   ├── redis-statefulset.yml
│   │   │   ├── postgres-statefulset.yml
│   │   │   └── minio-statefulset.yml
│   │   ├── monitoring/
│   │   │   ├── prometheus-deployment.yml
│   │   │   └── grafana-deployment.yml
│   │   ├── network-policies/
│   │   │   ├── device-zone.yml
│   │   │   ├── pipeline-zone.yml
│   │   │   ├── app-zone.yml
│   │   │   └── data-zone.yml
│   │   └── ingress/
│   │       └── ingress.yml
│   └── scripts/
│       ├── deploy.sh
│       ├── rollback.sh
│       ├── health-check.sh
│       └── seed-vault.sh
│
├── tests/                             # Integration and E2E Tests
│   ├── integration/
│   │   ├── test_full_pipeline.py
│   │   ├── test_offline_sync.py
│   │   ├── test_ai_insights.py
│   │   └── test_hospital_delivery.py
│   ├── e2e/
│   │   ├── test_device_to_dashboard.py
│   │   └── test_critical_alert_flow.py
│   ├── performance/
│   │   ├── test_pipeline_throughput.py
│   │   └── test_ai_inference_latency.py
│   └── fixtures/
│       ├── sample_hl7v2_message.txt
│       ├── sample_mqtt_payload.json
│       └── sample_fhir_observation.json
│
└── .github/                           # CI/CD
    └── workflows/
        ├── ci.yml
        ├── build-and-push.yml
        ├── deploy-staging.yml
        └── deploy-production.yml
```
