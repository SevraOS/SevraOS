"""
HELIOS OS + SEVRA AI — End-to-End Flow Walkthrough
Section 21: Complete pipeline demonstration

Shows the full journey of a single vital reading:

    Normalized Reading
      → EventBusBridge.publish()
        → EventProducer
          → Redis Stream (vitals)
            → DatabaseConsumer (XREADGROUP)
              → ACK on success
              → DLQ on permanent failure
              → Replay on recovery

Run with a real Redis instance:
    python examples/e2e_walkthrough.py
"""
from __future__ import annotations

import asyncio
import structlog

logger = structlog.get_logger("e2e")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_canonical_event():
    """Build a synthetic CanonicalEvent as if it came from the Normalizer."""
    from normalization.canonical import CanonicalEvent
    from datetime import datetime, timezone

    return CanonicalEvent(
        patient_id="PAT-9001",
        device_id="SIM-ECG-001",
        metric="heart_rate",
        value=78.5,
        unit="bpm",
        loinc="8867-4",
        normalized_at=datetime.now(timezone.utc),
        flagged=False,
    )


async def step1_publish(event) -> str:
    """Step 1 — Normalization publishes to Event Bus."""
    from eventbus.integration import EventBusBridge

    bridge = EventBusBridge()
    logger.info("step_1_publishing", patient_id=event.patient_id, metric=event.metric)
    await bridge.publish(event)
    logger.info("step_1_published_to_redis_stream")
    return "ok"


async def step2_consume(fake_process: bool = True) -> None:
    """Step 2 — Database consumer group reads and ACKs."""
    from eventbus.client import RedisClientManager
    from eventbus.streams import StreamTopic
    from eventbus.serializer import EventSerializer

    client = RedisClientManager.get_client()
    group = "cg_database"
    stream = StreamTopic.VITALS.value

    try:
        await client.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        pass  # group already exists

    messages = await client.xreadgroup(
        groupname=group,
        consumername="db_worker_demo",
        streams={stream: ">"},
        count=1,
    )

    if not messages:
        logger.warning("step_2_no_messages_found")
        return

    msg_id, msg_data = messages[0][1][0]
    payload = msg_data[b"payload"]
    event_dict = EventSerializer.from_bytes(payload)

    logger.info("step_2_consumed",
                msg_id=msg_id.decode(),
                patient_id=event_dict.get("patient_id"),
                metric=event_dict.get("metric"),
                value=event_dict.get("value"))

    # Simulate DB write
    if fake_process:
        await asyncio.sleep(0.01)

    await client.xack(stream, group, msg_id)
    logger.info("step_2_acknowledged", msg_id=msg_id.decode())


async def step3_failure_and_dlq() -> None:
    """Step 3 — Show DLQ routing on permanent failure."""
    from eventbus.dead_letter import DeadLetterQueue
    from eventbus.streams import StreamTopic

    logger.info("step_3_simulating_permanent_failure")
    await DeadLetterQueue.send_to_dlq(
        stream=StreamTopic.VITALS.value,
        group="cg_database",
        message_id="synthetic-fail-0",
        payload=b'{"demo": true}',
        reason="DB connection refused (demo)",
    )
    logger.info("step_3_message_in_dlq")


async def step4_replay() -> None:
    """Step 4 — Replay DLQ back to original stream."""
    from eventbus.replay import ReplayFramework

    logger.info("step_4_starting_dlq_replay")
    count = await ReplayFramework.replay_dlq()
    logger.info("step_4_replay_complete", messages_replayed=count)


async def main() -> None:
    from eventbus.client import RedisClientManager
    await RedisClientManager.connect()

    print("\n" + "=" * 60)
    print("  HELIOS — End-to-End Event Bus Walkthrough")
    print("=" * 60)

    event = _make_canonical_event()

    print("\n[1] Publishing normalized vital to Redis Stream …")
    await step1_publish(event)

    print("\n[2] Database Consumer Group reading and ACKing …")
    await step2_consume()

    print("\n[3] Simulating permanent failure → DLQ …")
    await step3_failure_and_dlq()

    print("\n[4] Replaying DLQ back to stream …")
    await step4_replay()

    print("\n✅  Walkthrough complete. All stages passed.\n")

    await RedisClientManager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
