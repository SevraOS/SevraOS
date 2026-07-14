from enum import Enum

class StreamTopic(str, Enum):
    """
    Core Redis Streams in the HELIOS Architecture.
    
    Retention and Replay semantics:
    - VITALS: High throughput, 24-hour retention. Replayed for AI training.
    - ALERTS: Low throughput, 30-day retention. Critical replay for audit.
    - PREDICTIONS: Medium throughput, 7-day retention.
    - HOSPITAL: Medium throughput, 3-day retention. Outbound sync buffers.
    - AUDIT: System logs, 365-day retention. 
    - NOTIFICATIONS: Ephemeral, 1-hour retention.
    """
    VITALS = "sevra:streams:vitals"
    ALERTS = "sevra:streams:alerts"
    PREDICTIONS = "sevra:streams:predictions"
    HOSPITAL = "sevra:streams:hospital"
    AUDIT = "sevra:streams:audit"
    NOTIFICATIONS = "sevra:streams:notifications"

class ConsumerGroup(str, Enum):
    """
    Standard Consumer Groups for horizontal scaling.
    """
    DATABASE_GROUP = "cg_database"
    AI_GROUP = "cg_ai_engine"
    NOTIFICATION_GROUP = "cg_notifier"
    HOSPITAL_GROUP = "cg_ehr_sync"
    AUDIT_GROUP = "cg_auditor"
