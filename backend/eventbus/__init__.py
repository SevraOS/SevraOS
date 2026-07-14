"""
HELIOS OS + SEVRA AI
Event Bus Architecture (Redis Streams)

Provides the distributed, fault-tolerant, async backbone for the platform.
Handles exactly-once semantics via consumer groups, idempotency, and DLQs.
"""

from eventbus.config import config
from eventbus.client import RedisClientManager
from eventbus.streams import StreamTopic, ConsumerGroup
from eventbus.schemas import VitalEvent, AlertEvent, EventType
from eventbus.producer import EventProducer
from eventbus.groups import DatabaseConsumer, AIConsumer, NotificationConsumer
from eventbus.replay import ReplayFramework

__all__ = [
    "config",
    "RedisClientManager",
    "StreamTopic",
    "ConsumerGroup",
    "VitalEvent",
    "AlertEvent",
    "EventType",
    "EventProducer",
    "DatabaseConsumer",
    "AIConsumer",
    "NotificationConsumer",
    "ReplayFramework",
]
