"""
HELIOS OS + SEVRA AI
Collector Integration & Failure Tests

Tests:
  - BaseCollector lifecycle (start/stop)
  - Frame buffering and consumer loop
  - Reconnect with exponential backoff
  - Failure isolation (one frame error does not kill collector)
  - Supervisor start/stop/restart
  - Health monitoring state transitions
  - SimulatorTransport integration
  - End-to-end: Simulator → Transport → Collector → Adapter → RawReading
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio

from collectors.base.collector_base import BaseCollector
from collectors.base.health import CollectorHealth, DeviceStatus
from collectors.base.supervisor import CollectorSupervisor
from collectors.base.validation_interface import (
    QueueValidationInterface,
    NullValidationInterface,
)
from mdil.adapters.ecg_adapter import ECGAdapter
from mdil.adapters.bp_adapter import BPAdapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType, RawReading
from mdil.transports.base_transport import BaseTransport, TransportConnectionError, TransportReadError
from mdil.transports.simulator_transport import SimulatorTransport


# ── Test Helpers ──────────────────────────────────────────────────────────────

class _FakeTransport(BaseTransport):
    """Transport that yields a fixed set of frames then stops."""

    transport_type = "fake"

    def __init__(self, device_id: str, frames: list[bytes], error_after: int = 0) -> None:
        super().__init__(device_id, {})
        self._frames = frames
        self._error_after = error_after

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def read_frames(self) -> AsyncIterator[bytes]:
        for i, frame in enumerate(self._frames):
            if self._error_after and i >= self._error_after:
                raise TransportReadError("Simulated read error", device_id=self.device_id)
            yield frame
            self._frames_received += 1
            self._bytes_received += len(frame)


class _FailConnectTransport(BaseTransport):
    """Transport that always fails to connect."""

    transport_type = "fail_connect"

    def __init__(self, device_id: str) -> None:
        super().__init__(device_id, {})
        self.connect_attempts = 0

    async def connect(self) -> None:
        self.connect_attempts += 1
        raise TransportConnectionError("Simulated connect failure", device_id=self.device_id)

    async def disconnect(self) -> None:
        self._connected = False

    async def read_frames(self) -> AsyncIterator[bytes]:
        return
        yield  # Make it an async generator


class _ECGCollector(BaseCollector):
    """Test ECG collector with injectable transport."""

    collector_name = "test_ecg_collector"

    def __init__(self, transport: BaseTransport, **kwargs) -> None:
        config = {
            "device_id": transport.device_id,
            "frame_buffer_size": 512,
            "reconnect_base_delay": 0.05,
            "reconnect_max_delay": 0.2,
            "reconnect_factor": 2.0,
            "max_reconnect_attempts": 3,
        }
        kwargs.setdefault("device_type", DeviceType.ECG)
        super().__init__(
            device_id=transport.device_id,
            device_type=DeviceType.ECG,
            config=config,
            **kwargs,
        )
        self._transport = transport

    def build_transport(self) -> BaseTransport:
        return self._transport

    def build_adapter(self) -> DeviceAdapter:
        return ECGAdapter(device_id=self.device_id)


# ── Health Tests ──────────────────────────────────────────────────────────────

class TestCollectorHealth:
    @pytest.mark.asyncio
    async def test_initial_status_is_initializing(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        assert h.status == DeviceStatus.INITIALIZING

    @pytest.mark.asyncio
    async def test_mark_connected_updates_status(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        await h.mark_connected()
        assert h.status == DeviceStatus.CONNECTED
        assert h.last_connected_at is not None

    @pytest.mark.asyncio
    async def test_mark_reconnecting_increments_counters(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        await h.mark_reconnecting("lost connection")
        assert h.status == DeviceStatus.RECONNECTING
        assert h.reconnect_count == 1
        assert h.failure_count == 1
        assert h.last_error_message == "lost connection"

    @pytest.mark.asyncio
    async def test_record_frame_updates_counters(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        await h.mark_connected()
        await h.record_frame(readings_count=2)
        assert h.total_frames_received == 1
        assert h.total_readings_produced == 2
        assert h.last_reading_at is not None

    @pytest.mark.asyncio
    async def test_record_parse_error_increments_counter(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        await h.mark_connected()
        await h.record_parse_error()
        assert h.total_parse_errors == 1

    @pytest.mark.asyncio
    async def test_high_error_rate_marks_degraded(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        await h.mark_connected()
        # Record 2 frames and 1 error (50% error rate → degraded)
        await h.record_frame(1)
        await h.record_frame(1)
        h.total_frames_received = 10
        h.total_parse_errors = 3  # 30% — triggers degraded
        await h.record_parse_error()
        assert h.status == DeviceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_mark_stopped(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        await h.mark_stopped()
        assert h.status == DeviceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_to_dict_has_required_keys(self) -> None:
        h = CollectorHealth(device_id="D1", device_type="ecg")
        d = h.to_dict()
        assert "device_id" in d
        assert "status" in d
        assert "counters" in d
        assert d["counters"]["frames_received"] == 0


# ── Simulator Transport Tests ─────────────────────────────────────────────────

class TestSimulatorTransport:
    @pytest.mark.asyncio
    async def test_connect_succeeds(self) -> None:
        t = SimulatorTransport(device_id="SIM-001")
        await t.connect()
        assert t.is_connected

    @pytest.mark.asyncio
    async def test_push_and_read_frame(self) -> None:
        t = SimulatorTransport(device_id="SIM-001")
        await t.connect()
        await t.push_frame(b"DAT|72|0.84|II")

        frames = []
        async def consume() -> None:
            async for frame in t.read_frames():
                frames.append(frame)
                break  # Read one frame only

        await asyncio.wait_for(consume(), timeout=1.0)
        assert frames == [b"DAT|72|0.84|II"]

    @pytest.mark.asyncio
    async def test_push_frame_nowait(self) -> None:
        t = SimulatorTransport(device_id="SIM-002")
        await t.connect()
        t.push_frame_nowait(b"STA|OK")
        assert t._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_disconnect_stops_read_frames(self) -> None:
        t = SimulatorTransport(device_id="SIM-003")
        await t.connect()

        frames: list[bytes] = []
        async def consume() -> None:
            async for frame in t.read_frames():
                frames.append(frame)

        task = asyncio.create_task(consume())
        await t.push_frame(b"DAT|72|0.84|II")
        await asyncio.sleep(0.05)
        await t.disconnect()
        await asyncio.wait_for(task, timeout=1.0)
        assert len(frames) == 1

    @pytest.mark.asyncio
    async def test_stats_tracked(self) -> None:
        t = SimulatorTransport(device_id="SIM-004")
        await t.connect()
        await t.push_frame(b"ABC")
        assert t.stats["bytes_received"] == 3
        assert t.stats["frames_received"] == 1


# ── BaseCollector Lifecycle Tests ─────────────────────────────────────────────

class TestBaseCollectorLifecycle:
    @pytest.mark.asyncio
    async def test_collector_starts_and_processes_frames(self) -> None:
        transport = _FakeTransport(
            device_id="ECG-001",
            frames=[b"DAT|72|0.84|II", b"DAT|80|0.90|I"],
        )
        validation = QueueValidationInterface()
        collector = _ECGCollector(transport=transport, validation_queue=validation._queue)

        task = asyncio.create_task(collector.start())
        await asyncio.sleep(0.3)
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        readings = await validation.drain()
        assert len(readings) >= 2  # 2 frames × 2 readings each = 4

    @pytest.mark.asyncio
    async def test_parse_error_does_not_kill_collector(self) -> None:
        """A bad frame must not crash the collector — it increments error count."""
        transport = _FakeTransport(
            device_id="ECG-ERR-001",
            frames=[b"INVALID_FRAME", b"DAT|72|0.84|II"],
        )
        validation = QueueValidationInterface()
        collector = _ECGCollector(transport=transport, validation_queue=validation._queue)

        task = asyncio.create_task(collector.start())
        await asyncio.sleep(0.3)
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert collector.health.total_parse_errors >= 1
        readings = await validation.drain()
        # Good frame still produced readings
        assert len(readings) >= 2

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts_marks_failed(self) -> None:
        transport = _FailConnectTransport(device_id="ECG-FAIL-001")
        validation = NullValidationInterface()
        config = {
            "device_id": "ECG-FAIL-001",
            "frame_buffer_size": 64,
            "reconnect_base_delay": 0.01,
            "reconnect_max_delay": 0.1,
            "reconnect_factor": 1.0,
            "max_reconnect_attempts": 3,
        }

        class FailCollector(BaseCollector):
            collector_name = "fail_collector"
            def build_transport(self): return transport
            def build_adapter(self): return ECGAdapter(device_id=self.device_id)

        collector = FailCollector(
            device_id="ECG-FAIL-001",
            device_type=DeviceType.ECG,
            config=config,
        )
        await asyncio.wait_for(collector.start(), timeout=2.0)
        assert collector.health.status == DeviceStatus.FAILED
        assert transport.connect_attempts == 3

    @pytest.mark.asyncio
    async def test_stop_during_backoff_exits_cleanly(self) -> None:
        transport = _FailConnectTransport(device_id="ECG-STOP-001")
        config = {
            "device_id": "ECG-STOP-001",
            "frame_buffer_size": 64,
            "reconnect_base_delay": 10.0,   # Long backoff
            "reconnect_max_delay": 60.0,
            "reconnect_factor": 1.0,
            "max_reconnect_attempts": 0,    # Infinite
        }

        class StopCollector(BaseCollector):
            collector_name = "stop_collector"
            def build_transport(self): return transport
            def build_adapter(self): return ECGAdapter(device_id=self.device_id)

        collector = StopCollector(
            device_id="ECG-STOP-001",
            device_type=DeviceType.ECG,
            config=config,
        )
        task = asyncio.create_task(collector.start())
        await asyncio.sleep(0.1)  # Let first connect attempt fail
        await collector.stop()    # Stop during backoff
        await asyncio.wait_for(task, timeout=1.0)
        assert collector.health.status == DeviceStatus.STOPPED


# ── Supervisor Tests ──────────────────────────────────────────────────────────

class TestCollectorSupervisor:
    def _make_collector(self, device_id: str) -> _ECGCollector:
        transport = _FakeTransport(device_id=device_id, frames=[])
        return _ECGCollector(transport=transport)

    def test_register_collector(self) -> None:
        supervisor = CollectorSupervisor()
        col = self._make_collector("ECG-SUP-001")
        supervisor.register(col)
        assert "ECG-SUP-001" in supervisor._collectors

    def test_duplicate_registration_raises(self) -> None:
        supervisor = CollectorSupervisor()
        col = self._make_collector("ECG-SUP-002")
        supervisor.register(col)
        col2 = self._make_collector("ECG-SUP-002")
        with pytest.raises(ValueError, match="already registered"):
            supervisor.register(col2)

    @pytest.mark.asyncio
    async def test_shutdown_stops_all_collectors(self) -> None:
        supervisor = CollectorSupervisor(shutdown_timeout=1.0)
        col1 = self._make_collector("ECG-SHUT-001")
        col2 = self._make_collector("ECG-SHUT-002")
        supervisor.register(col1)
        supervisor.register(col2)

        # Start in background
        start_task = asyncio.create_task(supervisor.start_all())
        await asyncio.sleep(0.2)
        await supervisor.shutdown()

        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        assert not supervisor.is_running

    def test_health_report_structure(self) -> None:
        supervisor = CollectorSupervisor()
        col = self._make_collector("ECG-HEALTH-001")
        supervisor.register(col)
        report = supervisor.health_report()
        assert "overall_status" in report
        assert "collector_count" in report
        assert "collectors" in report
        assert "ECG-HEALTH-001" in report["collectors"]


# ── End-to-End Simulator Integration Tests ────────────────────────────────────

class TestSimulatorEndToEnd:
    @pytest.mark.asyncio
    async def test_ecg_simulator_to_readings(self) -> None:
        """
        End-to-end: ECG frames pushed via SimulatorTransport
        → ECGCollector → ECGAdapter → RawReadings
        """
        transport = SimulatorTransport(device_id="SIM-ECG-E2E")
        await transport.connect()

        validation = QueueValidationInterface()
        await validation.start()

        config = {
            "device_id": "SIM-ECG-E2E",
            "frame_buffer_size": 256,
            "reconnect_base_delay": 0.1,
            "reconnect_max_delay": 1.0,
            "reconnect_factor": 2.0,
            "max_reconnect_attempts": 1,
        }

        class SimCollector(BaseCollector):
            collector_name = "sim_ecg"
            def build_transport(self): return transport
            def build_adapter(self): return ECGAdapter(device_id=self.device_id)

        collector = SimCollector(
            device_id="SIM-ECG-E2E",
            device_type=DeviceType.ECG,
            config=config,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        # Push 3 ECG frames
        for i in range(3):
            await transport.push_frame(f"DAT|{72+i}|0.84|II".encode())
        await asyncio.sleep(0.3)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        readings = await validation.drain()
        assert len(readings) >= 6  # 3 frames × 2 readings each

        metrics = {r.metric.value for r in readings}
        assert "heart_rate" in metrics
        assert "ecg_lead_ii" in metrics

    @pytest.mark.asyncio
    async def test_bp_simulator_to_readings(self) -> None:
        """BP frames → BPCollector → BPAdapter → 3 RawReadings per frame."""
        transport = SimulatorTransport(device_id="SIM-BP-E2E")
        await transport.connect()

        validation = QueueValidationInterface()

        config = {
            "device_id": "SIM-BP-E2E",
            "frame_buffer_size": 256,
            "reconnect_base_delay": 0.1,
            "reconnect_max_delay": 1.0,
            "reconnect_factor": 2.0,
            "max_reconnect_attempts": 1,
        }

        class BPSimCollector(BaseCollector):
            collector_name = "sim_bp"
            def build_transport(self): return transport
            def build_adapter(self): return BPAdapter(device_id=self.device_id)

        collector = BPSimCollector(
            device_id="SIM-BP-E2E",
            device_type=DeviceType.BLOOD_PRESSURE,
            config=config,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        await transport.push_frame(b"SYS=120 DIA=80 MAP=93 PR=72")
        await asyncio.sleep(0.2)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        readings = await validation.drain()
        assert len(readings) == 4  # SYS + DIA + MAP + PR

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_frames(self) -> None:
        """Bad frames are dropped, good frames still produce readings."""
        transport = SimulatorTransport(device_id="SIM-MIX-E2E")
        await transport.connect()

        validation = QueueValidationInterface()

        config = {
            "device_id": "SIM-MIX-E2E",
            "frame_buffer_size": 256,
            "reconnect_base_delay": 0.1,
            "reconnect_max_delay": 1.0,
            "reconnect_factor": 2.0,
            "max_reconnect_attempts": 1,
        }

        class MixCollector(BaseCollector):
            collector_name = "sim_mix"
            def build_transport(self): return transport
            def build_adapter(self): return ECGAdapter(device_id=self.device_id)

        collector = MixCollector(
            device_id="SIM-MIX-E2E",
            device_type=DeviceType.ECG,
            config=config,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        await transport.push_frame(b"DAT|72|0.84|II")   # Good
        await transport.push_frame(b"GARBAGE_FRAME")    # Bad
        await transport.push_frame(b"DAT|80|0.90|I")    # Good
        await asyncio.sleep(0.3)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        readings = await validation.drain()
        assert len(readings) == 4  # 2 good frames × 2 readings
        assert collector.health.total_parse_errors == 1


# ── Validation Interface Tests ────────────────────────────────────────────────

class TestQueueValidationInterface:
    @pytest.mark.asyncio
    async def test_forward_enqueues_reading(self) -> None:
        from datetime import datetime, timezone
        from mdil.schema import MetricType, Unit

        vi = QueueValidationInterface(maxsize=10)
        reading = RawReading(
            device_type=DeviceType.ECG,
            device_id="ECG-001",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.HEART_RATE,
            value=72.0,
            unit=Unit.BPM,
            raw_payload="DAT|72|0.84|II",
        )
        await vi.forward(reading)
        drained = await vi.drain()
        assert len(drained) == 1
        assert drained[0].device_id == "ECG-001"

    @pytest.mark.asyncio
    async def test_forward_drops_when_full(self) -> None:
        from datetime import datetime, timezone
        from mdil.schema import MetricType, Unit

        vi = QueueValidationInterface(maxsize=1)
        reading = RawReading(
            device_type=DeviceType.ECG, device_id="ECG-001",
            captured_at=datetime.now(timezone.utc),
            metric=MetricType.HEART_RATE, value=72.0,
            unit=Unit.BPM, raw_payload="x",
        )
        await vi.forward(reading)  # Fills queue
        await vi.forward(reading)  # Should drop
        assert vi.stats["total_dropped"] == 1

    @pytest.mark.asyncio
    async def test_get_next_timeout_returns_none(self) -> None:
        vi = QueueValidationInterface()
        result = await vi.get_next(timeout=0.05)
        assert result is None
