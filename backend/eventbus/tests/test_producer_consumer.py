import pytest
import asyncio
from eventbus.producer import EventProducer
from eventbus.streams import StreamTopic
from eventbus.schemas import VitalEvent
from eventbus.consumer import ConsumerWorker
from eventbus.idempotency import IdempotencyService
from eventbus.dead_letter import DeadLetterQueue
from eventbus.serializer import EventSerializer
from eventbus.metrics import EventBusMetrics
from eventbus.config import config


@pytest.fixture
def vital_event():
    return VitalEvent(
        patient_id="PAT-1001",
        metric="heart_rate",
        value=75.0,
        unit="bpm",
        loinc="8867-4",
        source_device="SIM-ECG-001"
    )


# ── Producer Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_producer_publishes_event(vital_event, fake_redis):
    m = EventBusMetrics()
    m.events_published_total = 0

    producer = EventProducer()
    msg_id = await producer.publish(StreamTopic.VITALS.value, vital_event)

    assert msg_id is not None

    stream_data = await fake_redis.xrange(StreamTopic.VITALS.value, min="-", max="+")
    assert len(stream_data) == 1


@pytest.mark.asyncio
async def test_producer_publishes_msgpack(vital_event, fake_redis):
    producer = EventProducer()
    msg_id = await producer.publish(StreamTopic.VITALS.value, vital_event, use_msgpack=True)
    assert msg_id is not None

    stream_data = await fake_redis.xrange(StreamTopic.VITALS.value, min="-", max="+")
    assert len(stream_data) == 1


# ── Serializer Tests ───────────────────────────────────────────────────────────

def test_serializer_json_roundtrip(vital_event):
    raw = EventSerializer.to_bytes(vital_event, use_msgpack=False)
    restored = EventSerializer.from_bytes(raw, is_msgpack=False)
    assert restored["patient_id"] == "PAT-1001"
    assert restored["value"] == 75.0


def test_serializer_msgpack_roundtrip(vital_event):
    raw = EventSerializer.to_bytes(vital_event, use_msgpack=True)
    restored = EventSerializer.from_bytes(raw, is_msgpack=True)
    assert restored["metric"] == "heart_rate"


# ── Consumer Unit Tests (direct _handle_message — no live loop) ────────────────

@pytest.mark.asyncio
async def test_consumer_handle_message_success(vital_event, fake_redis):
    """
    Test the consumer's message handling logic without running the blocking loop.
    """
    processed = []

    async def handler(msg_id: str, payload: bytes):
        processed.append(msg_id)

    worker = ConsumerWorker(
        stream=StreamTopic.VITALS.value,
        group_name="test_group",
        consumer_name="w1",
        process_func=handler,
    )

    # Manually create the group so XACK works
    await worker._ensure_group()

    # Publish an event so we have a real message ID
    producer = EventProducer()
    await producer.publish(StreamTopic.VITALS.value, vital_event)

    # Read it back with xreadgroup (non-blocking: no block arg)
    streams = await fake_redis.xreadgroup(
        groupname="test_group",
        consumername="w1",
        streams={StreamTopic.VITALS.value: ">"},
        count=1,
    )
    assert streams, "Expected at least one message"

    msg_id_bytes, msg_data = streams[0][1][0]
    payload = msg_data[b"payload"]

    # Drive _handle_message directly — this is the unit under test
    await worker._handle_message(msg_id_bytes.decode(), payload)

    assert len(processed) == 1


@pytest.mark.asyncio
async def test_consumer_sends_to_dlq_on_failure(vital_event, fake_redis):
    """
    When processing permanently fails, the message must land in the DLQ.
    """
    async def failing_handler(msg_id: str, payload: bytes):
        raise RuntimeError("Simulated failure")

    worker = ConsumerWorker(
        stream=StreamTopic.VITALS.value,
        group_name="dlq_group",
        consumer_name="w1",
        process_func=failing_handler,
    )
    await worker._ensure_group()

    producer = EventProducer()
    await producer.publish(StreamTopic.VITALS.value, vital_event)

    streams = await fake_redis.xreadgroup(
        groupname="dlq_group",
        consumername="w1",
        streams={StreamTopic.VITALS.value: ">"},
        count=1,
    )
    msg_id_bytes, msg_data = streams[0][1][0]
    payload = msg_data[b"payload"]

    # Should NOT raise — error is swallowed and sent to DLQ
    await worker._handle_message(msg_id_bytes.decode(), payload)

    dlq_data = await fake_redis.xrange(config.DLQ_STREAM_NAME, min="-", max="+")
    assert len(dlq_data) == 1


# ── Idempotency Tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idempotency_prevents_duplicates(vital_event):
    service = IdempotencyService()

    acquired = await service.acquire_lock(vital_event.event_id, "grp1")
    assert acquired is True

    acquired_again = await service.acquire_lock(vital_event.event_id, "grp1")
    assert acquired_again is False


@pytest.mark.asyncio
async def test_idempotency_release_allows_reprocess(vital_event):
    service = IdempotencyService()

    await service.acquire_lock(vital_event.event_id, "grp2")
    await service.release_lock(vital_event.event_id, "grp2")

    # After release, should be acquirable again
    reacquired = await service.acquire_lock(vital_event.event_id, "grp2")
    assert reacquired is True


# ── Dead Letter Queue Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dlq_stores_failure_metadata(fake_redis):
    await DeadLetterQueue.send_to_dlq(
        stream=StreamTopic.VITALS.value,
        group="test_group",
        message_id="12345-0",
        payload=b'{"event_id":"abc"}',
        reason="DB connection refused",
    )

    dlq_data = await fake_redis.xrange(config.DLQ_STREAM_NAME, min="-", max="+")
    assert len(dlq_data) == 1

    entry = dlq_data[0][1]
    assert entry[b"reason"] == b"DB connection refused"
    assert entry[b"consumer_group"] == b"test_group"
    assert entry[b"original_stream"] == StreamTopic.VITALS.value.encode()


# ── Retry Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """RetryPolicy must succeed when the callable eventually stops raising."""
    from eventbus.retry import RetryPolicy

    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("transient")
        return "ok"

    result = await RetryPolicy.execute(flaky, "msg-1")
    assert result == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausts_and_raises():
    """RetryPolicy must re-raise after all attempts are used."""
    from eventbus.retry import RetryPolicy
    from eventbus.config import config

    config.RETRY_MAX_ATTEMPTS = 2
    config.RETRY_BASE_DELAY = 0.01   # keep tests fast

    async def always_fail():
        raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        await RetryPolicy.execute(always_fail, "msg-2")


# ── Replay Tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_replay_from_dlq(vital_event, fake_redis):
    """Messages in the DLQ must be republished to their original stream."""
    from eventbus.replay import ReplayFramework

    # Seed DLQ
    payload = EventSerializer.to_bytes(vital_event)
    await DeadLetterQueue.send_to_dlq(
        stream=StreamTopic.VITALS.value,
        group="test_group",
        message_id="00000-0",
        payload=payload,
        reason="test",
    )

    replayed = await ReplayFramework.replay_dlq()
    assert replayed == 1

    # Original stream should now have the replayed message
    vitals = await fake_redis.xrange(StreamTopic.VITALS.value, min="-", max="+")
    assert len(vitals) >= 1

    # DLQ should be empty
    dlq = await fake_redis.xrange(config.DLQ_STREAM_NAME, min="-", max="+")
    assert len(dlq) == 0
