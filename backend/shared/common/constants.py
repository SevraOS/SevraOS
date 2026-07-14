"""
HELIOS OS + SEVRA AI
Shared Constants

Platform-wide constants shared across all services.
Do not hardcode these values in individual services.
"""

from __future__ import annotations

# ── Stream Names (Event Bus Contract) ────────────────────────────────────────
# Contract: Architecture Section C5.1 — stream naming convention

class StreamNames:
    """Redis Stream names. Never hardcode stream names in service code."""
    MDIL_RAW = "stream:mdil.raw"
    MDIL_PARSE_ERRORS = "stream:mdil.parse_errors"
    COLLECTOR_RAW = "stream:collector.raw"
    VALIDATION_PASSED = "stream:validation.passed"
    VALIDATION_FAILED = "stream:validation.failed"
    NORMALIZED_EVENTS = "stream:normalized.events"
    AI_INSIGHTS = "stream:ai.insights"
    HOSPITAL_OUTBOUND = "stream:hospital.outbound"
    HOSPITAL_DELIVERY_FAILED = "stream:hospital.delivery_failed"
    DEVICE_LIFECYCLE = "stream:device.lifecycle"
    AUDIT_EVENTS = "stream:audit.events"
    SYSTEM_ALERTS = "stream:system.alerts"


# ── Consumer Group Names ──────────────────────────────────────────────────────

class ConsumerGroups:
    """Consumer group names. Contract: Architecture Section C5.2."""
    COLLECTORS = "collectors-group"
    VALIDATION = "validation-group"
    NORMALIZATION = "normalization-group"
    DB_SERVICE = "db-service-group"
    DASHBOARD = "dashboard-group"
    AI_SERVICE = "ai-service-group"
    HOSPITAL = "hospital-group"
    HOSPITAL_DELIVERY = "hospital-delivery-group"
    MONITORING = "monitoring-group"
    SECURITY_AUDIT = "security-audit-group"
    REVIEW = "review-group"
    OPS = "ops-group"


# ── FHIR / Clinical Constants ─────────────────────────────────────────────────

class FHIRSystems:
    """FHIR canonical system URIs."""
    LOINC = "http://loinc.org"
    SNOMED = "http://snomed.info/sct"
    UCUM = "http://unitsofmeasure.org"
    OBSERVATION_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category"
    ICD10 = "http://hl7.org/fhir/sid/icd-10"


class LOINCCodes:
    """Common vital sign LOINC codes."""
    HEART_RATE = "8867-4"
    SPO2 = "59408-5"
    BLOOD_PRESSURE_PANEL = "55284-4"
    SYSTOLIC_BP = "8480-6"
    DIASTOLIC_BP = "8462-4"
    BODY_TEMPERATURE = "8310-5"
    RESPIRATORY_RATE = "9279-1"
    GCS_TOTAL = "9269-2"
    WEIGHT = "29463-7"
    HEIGHT = "8302-2"


# ── Clinical Plausibility Ranges ──────────────────────────────────────────────

class ClinicalRanges:
    """
    Physiologically valid ranges for vital signs.
    Values OUTSIDE these ranges are rejected by Validation Service.
    """
    HEART_RATE_MIN = 0
    HEART_RATE_MAX = 300
    HEART_RATE_WARN_MIN = 40
    HEART_RATE_WARN_MAX = 180

    SPO2_MIN = 50
    SPO2_MAX = 100
    SPO2_WARN_MIN = 92

    SYSTOLIC_BP_MIN = 40
    SYSTOLIC_BP_MAX = 300

    DIASTOLIC_BP_MIN = 20
    DIASTOLIC_BP_MAX = 200

    TEMPERATURE_MIN_C = 25.0
    TEMPERATURE_MAX_C = 45.0

    RESPIRATORY_RATE_MIN = 0
    RESPIRATORY_RATE_MAX = 80

    GCS_MIN = 3
    GCS_MAX = 15


# ── Schema Versions ───────────────────────────────────────────────────────────

class SchemaVersions:
    """Internal event schema versions."""
    INTERNAL_ENVELOPE_V1 = "1.0.0"
    FHIR_R4_V1 = "fhir-r4-1.0.0"
    AI_INSIGHT_V1 = "ai-insight-1.0.0"


# ── HTTP Header Names ─────────────────────────────────────────────────────────

class Headers:
    REQUEST_ID = "X-Request-ID"
    CORRELATION_ID = "X-Correlation-ID"
    RATELIMIT_LIMIT = "X-RateLimit-Limit"
    RATELIMIT_REMAINING = "X-RateLimit-Remaining"
    RATELIMIT_RESET = "X-RateLimit-Reset"


# ── Pagination Defaults ───────────────────────────────────────────────────────

class Pagination:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 1000


# ── Timeout Constants (seconds) ───────────────────────────────────────────────

class Timeouts:
    REDIS_SOCKET = 5.0
    POSTGRES_POOL = 30.0
    HEALTH_CHECK = 5.0
    AI_INFERENCE_SLA = 0.5       # 500ms — P99 SLA from Architecture Contract
    PIPELINE_END_TO_END = 0.2    # 200ms — device to dashboard SLA


# ── Retention Constants (hours) ───────────────────────────────────────────────

class StreamRetentionHours:
    MDIL_RAW = 24
    COLLECTOR_RAW = 24
    VALIDATION_PASSED = 48
    VALIDATION_FAILED = 720       # 30 days
    NORMALIZED_EVENTS = 72
    AI_INSIGHTS = 72
    AUDIT_EVENTS = 8760           # 365 days
    HOSPITAL_OUTBOUND = 168       # 7 days
    HOSPITAL_DLQ = 2160           # 90 days
