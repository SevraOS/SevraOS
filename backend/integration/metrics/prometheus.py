"""
HELIOS OS + SEVRA AI
Integration Metrics (Section 22)
"""

from prometheus_client import Counter, Histogram

# Section 22 specific metrics
hospital_sync_total = Counter(
    "hospital_sync_total",
    "Total number of synchronization events to hospital systems",
    ["system", "status"]
)

fhir_requests_total = Counter(
    "fhir_requests_total",
    "Total FHIR API requests made",
    ["resource_type", "status"]
)

hl7_messages_total = Counter(
    "hl7_messages_total",
    "Total HL7 v2 messages parsed or sent",
    ["message_type", "direction"]
)

sync_failures_total = Counter(
    "sync_failures_total",
    "Total number of sync failures",
    ["reason"]
)

notification_delivery_total = Counter(
    "notification_delivery_total",
    "Total notifications delivered",
    ["channel", "status"]
)

compliance_events_total = Counter(
    "compliance_events_total",
    "Total auditable compliance events logged",
    ["event_type"]
)
