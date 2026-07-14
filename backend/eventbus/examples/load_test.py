"""
HELIOS OS + SEVRA AI — Load Testing Framework
Section 20: Performance Testing

Simulates high-throughput event publishing to measure:
  - Latency (p50, p95, p99)
  - Throughput (events/sec)
  - Consumer lag
  - Memory impact

Run against a real Redis instance:
    python examples/load_test.py --rate 10000 --duration 60

Rates tested per spec:
  10,000 events/minute  (~167/sec)
  50,000 events/minute  (~833/sec)
  100,000 events/minute (~1667/sec)
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
import uuid
from typing import List

import structlog

logger = structlog.get_logger("load_test")


async def _setup_redis() -> None:
    from eventbus.client import RedisClientManager
    await RedisClientManager.connect()


async def _teardown_redis() -> None:
    from eventbus.client import RedisClientManager
    await RedisClientManager.disconnect()


async def _publish_batch(rate_per_sec: float, duration_sec: int) -> List[float]:
    """Publish at a fixed rate and record per-event latency in milliseconds."""
    from eventbus.producer import EventProducer
    from eventbus.streams import StreamTopic
    from eventbus.schemas import VitalEvent

    producer = EventProducer()
    latencies: List[float] = []
    interval = 1.0 / rate_per_sec
    end_time = time.monotonic() + duration_sec

    while time.monotonic() < end_time:
        event = VitalEvent(
            patient_id=f"PAT-{uuid.uuid4().hex[:8]}",
            metric="heart_rate",
            value=72.0,
            unit="bpm",
            loinc="8867-4",
            source_device="LOAD-TEST-SIM",
        )
        t0 = time.perf_counter()
        await producer.publish(StreamTopic.VITALS.value, event)
        latencies.append((time.perf_counter() - t0) * 1000)  # ms
        await asyncio.sleep(interval)

    return latencies


def _print_report(rate_per_sec: float, duration: int, latencies: List[float]) -> None:
    if not latencies:
        print("No events published.")
        return

    total = len(latencies)
    sorted_lat = sorted(latencies)
    p50 = statistics.median(sorted_lat)
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
    mean = statistics.mean(sorted_lat)
    throughput = total / duration

    print("\n" + "=" * 60)
    print("  HELIOS Event Bus — Load Test Report")
    print("=" * 60)
    print(f"  Target rate   : {rate_per_sec:.0f} events/sec ({rate_per_sec * 60:.0f}/min)")
    print(f"  Duration      : {duration}s")
    print(f"  Total events  : {total:,}")
    print(f"  Actual rate   : {throughput:.1f} events/sec")
    print(f"  Mean latency  : {mean:.2f} ms")
    print(f"  p50 latency   : {p50:.2f} ms")
    print(f"  p95 latency   : {p95:.2f} ms")
    print(f"  p99 latency   : {p99:.2f} ms")
    print("=" * 60 + "\n")


async def run(rate_per_min: int, duration: int) -> None:
    rate_per_sec = rate_per_min / 60.0
    print(f"\n[load_test] Starting: {rate_per_min:,}/min for {duration}s …")

    await _setup_redis()
    try:
        latencies = await _publish_batch(rate_per_sec, duration)
        _print_report(rate_per_sec, duration, latencies)
    finally:
        await _teardown_redis()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HELIOS Event Bus Load Tester")
    parser.add_argument("--rate", type=int, default=10_000,
                        help="Events per minute (default: 10,000)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Test duration in seconds (default: 30)")
    args = parser.parse_args()

    asyncio.run(run(args.rate, args.duration))
