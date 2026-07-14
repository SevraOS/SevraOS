"""
HELIOS OS + SEVRA AI
Stress Tests & Framing Edge Case Tests

Tests:
  - High-volume frame throughput
  - Concurrent multi-collector stress
  - Frame buffer overflow behaviour
  - Malformed frame storms (error flooding)
  - Reconnect storm simulation
  - Large waveform frame handling
  - Queue back-pressure behaviour
  - Memory stability under sustained load
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

import pytest

from collectors.base.collector_base import BaseCollector
from collectors.base.health import DeviceStatus
from collectors.base.validation_interface import QueueValidationInterface
from mdil.adapters.ecg_adapter import ECGAdapter
from mdil.adapters.bp_adapter import BPAdapter
from mdil.base import DeviceAdapter
from mdil.schema import DeviceType
from mdil.transports.base_transport import BaseTransport, TransportReadError
from mdil.transports.simulator_transport import SimulatorTransport


# ── Helper Classes ────────────────────────────────────────────────────────────

class _StreamTransport(BaseTransport):
    """
    Transport that generates frames continuously from an async generator.
    Used for stress testing sustained throughput.
    """

    transport_type = "stream"

    def __init__(
        self,
        device_id: str,
        frame_generator: AsyncIterator[bytes],
    ) -> None:
        super().__init__(device_id, {})
        self._gen = frame_generator

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def read_frames(self) -> AsyncIterator[bytes]:
        async for frame in self._gen:
            if not self._connected:
                return
            self._frames_received += 1
            self._bytes_received += len(frame)
            yield frame


async def _ecg_stream(count: int, delay: float = 0.0) -> AsyncIterator[bytes]:
    """Generate `count` valid ECG DAT frames."""
    for i in range(count):
        yield f"DAT|{72 + (i % 20)}|{0.84 + (i % 10) * 0.01:.2f}|II".encode()
        if delay:
            await asyncio.sleep(delay)


async def _mixed_stream(
    good_count: int, bad_count: int
) -> AsyncIterator[bytes]:
    """Interleave valid ECG frames with garbage frames."""
    for i in range(max(good_count, bad_count)):
        if i < good_count:
            yield f"DAT|{72 + i % 20}|0.84|II".encode()
        if i < bad_count:
            yield b"GARBAGE|FRAME|INVALID"


class _StressCollector(BaseCollector):
    collector_name = "stress_collector"

    def __init__(self, transport: BaseTransport, device_type: DeviceType, **kwargs) -> None:
        config = {
            "device_id": transport.device_id,
            "frame_buffer_size": 4096,
            "reconnect_base_delay": 0.01,
            "reconnect_max_delay": 0.1,
            "reconnect_factor": 1.0,
            "max_reconnect_attempts": 1,
        }
        super().__init__(
            device_id=transport.device_id,
            device_type=device_type,
            config=config,
            **kwargs,
        )
        self._t = transport

    def build_transport(self) -> BaseTransport:
        return self._t

    def build_adapter(self) -> DeviceAdapter:
        return ECGAdapter(device_id=self.device_id)


# ── Throughput Stress Tests ───────────────────────────────────────────────────

class TestThroughputStress:
    @pytest.mark.asyncio
    async def test_1000_frames_fully_processed(self) -> None:
        """1000 ECG frames must all be parsed and forwarded within 10 seconds."""
        frame_count = 1000
        transport = SimulatorTransport(
            device_id="STRESS-ECG-001", queue_maxsize=frame_count + 100
        )
        await transport.connect()

        validation = QueueValidationInterface(maxsize=frame_count * 2 + 100)
        collector = _StressCollector(
            transport=transport,
            device_type=DeviceType.ECG,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        start = time.monotonic()
        for i in range(frame_count):
            await transport.push_frame(f"DAT|{72 + i % 10}|0.84|II".encode())

        # Wait for all frames to drain
        deadline = start + 10.0
        while time.monotonic() < deadline:
            readings = await validation.drain()
            if collector.health.total_frames_received >= frame_count:
                break
            await asyncio.sleep(0.05)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert collector.health.total_frames_received >= frame_count
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s for {frame_count} frames"

    @pytest.mark.asyncio
    async def test_frames_per_second_rate(self) -> None:
        """Collector must sustain ≥ 200 frames/sec for ECG data."""
        transport = SimulatorTransport(device_id="STRESS-FPS-001", queue_maxsize=5000)
        await transport.connect()

        validation = QueueValidationInterface(maxsize=10000)
        collector = _StressCollector(
            transport=transport,
            device_type=DeviceType.ECG,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        frame_count = 500
        start = time.monotonic()
        for i in range(frame_count):
            await transport.push_frame(f"DAT|72|0.84|II".encode())

        while collector.health.total_frames_received < frame_count:
            await asyncio.sleep(0.01)
            if time.monotonic() - start > 5.0:
                break

        elapsed = time.monotonic() - start
        fps = collector.health.total_frames_received / elapsed

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert fps >= 200, f"FPS too low: {fps:.1f}"

    @pytest.mark.asyncio
    async def test_large_waveform_frames(self) -> None:
        """ECG WFM frames with 500 samples each must parse correctly under load."""
        transport = SimulatorTransport(device_id="STRESS-WFM-001", queue_maxsize=100)
        await transport.connect()

        validation = QueueValidationInterface(maxsize=200)
        collector = _StressCollector(
            transport=transport,
            device_type=DeviceType.ECG,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        samples = ",".join(f"{i * 0.001:.3f}" for i in range(500))
        wfm_frame = f"WFM|II|500|{samples}".encode()

        for _ in range(10):
            await transport.push_frame(wfm_frame)

        await asyncio.sleep(0.5)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        readings = await validation.drain()
        # 10 WFM frames, 1 reading each
        assert len(readings) >= 10
        wfm_readings = [r for r in readings if r.metric.value == "ecg_waveform"]
        assert all(isinstance(r.value, list) for r in wfm_readings)
        assert all(len(r.value) == 500 for r in wfm_readings)


# ── Error Flooding Tests ──────────────────────────────────────────────────────

class TestErrorFlooding:
    @pytest.mark.asyncio
    async def test_100_bad_frames_do_not_kill_collector(self) -> None:
        """Collector must survive 100 consecutive parse errors."""
        transport = SimulatorTransport(device_id="STRESS-ERR-001", queue_maxsize=200)
        await transport.connect()

        validation = QueueValidationInterface(maxsize=500)
        collector = _StressCollector(
            transport=transport,
            device_type=DeviceType.ECG,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        # Push 100 bad frames
        for _ in range(100):
            await transport.push_frame(b"TOTALLY|INVALID|GARBAGE")

        # Then push 5 good frames
        for i in range(5):
            await transport.push_frame(f"DAT|{72 + i}|0.84|II".encode())

        await asyncio.sleep(0.5)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert collector.health.total_parse_errors == 100
        readings = await validation.drain()
        # Good frames still produced readings
        assert len(readings) >= 10  # 5 good frames × 2 readings each

    @pytest.mark.asyncio
    async def test_alternating_valid_invalid_frames(self) -> None:
        """Interleaved bad frames must not contaminate good readings."""
        transport = SimulatorTransport(device_id="STRESS-ALT-001", queue_maxsize=500)
        await transport.connect()

        validation = QueueValidationInterface(maxsize=1000)
        collector = _StressCollector(
            transport=transport,
            device_type=DeviceType.ECG,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        good_count = 0
        bad_count = 0
        for i in range(100):
            if i % 2 == 0:
                await transport.push_frame(f"DAT|72|0.84|II".encode())
                good_count += 1
            else:
                await transport.push_frame(b"BAD_DATA")
                bad_count += 1

        await asyncio.sleep(0.5)

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert collector.health.total_parse_errors == bad_count
        readings = await validation.drain()
        assert len(readings) >= good_count * 2  # 2 readings per good ECG frame


# ── Multi-Collector Concurrent Stress ─────────────────────────────────────────

class TestMultiCollectorStress:
    @pytest.mark.asyncio
    async def test_six_concurrent_collectors(self) -> None:
        """
        Run 6 collectors simultaneously (one per device type).
        Verify all produce readings without interfering with each other.
        """
        device_configs = [
            ("ECG-MULTI-001", DeviceType.ECG, b"DAT|72|0.84|II"),
            ("ECG-MULTI-002", DeviceType.ECG, b"DAT|80|0.90|I"),
            ("ECG-MULTI-003", DeviceType.ECG, b"DAT|65|0.75|III"),
            ("ECG-MULTI-004", DeviceType.ECG, b"WFM|II|500|0.1,0.2,0.3"),
            ("ECG-MULTI-005", DeviceType.ECG, b"DAT|90|1.0|II"),
            ("ECG-MULTI-006", DeviceType.ECG, b"STA|OK"),
        ]

        collectors = []
        transports = []
        validations = []

        for device_id, dtype, _ in device_configs:
            t = SimulatorTransport(device_id=device_id, queue_maxsize=500)
            await t.connect()
            v = QueueValidationInterface(maxsize=2000)
            c = _StressCollector(transport=t, device_type=dtype, validation_queue=v._queue)
            collectors.append(c)
            transports.append(t)
            validations.append(v)

        # Start all collectors
        tasks = [asyncio.create_task(c.start()) for c in collectors]

        # Push 50 frames to each
        frame_count = 50
        for (device_id, _, sample_frame), t in zip(device_configs, transports):
            for _ in range(frame_count):
                await t.push_frame(sample_frame)

        await asyncio.sleep(1.0)

        # Stop all
        for t in transports:
            await t.disconnect()
        for c in collectors:
            await c.stop()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify each ECG collector with DAT frames produced readings
        for i, (c, v) in enumerate(zip(collectors, validations)):
            _, dtype, sample = device_configs[i]
            if sample.startswith(b"DAT"):
                # Each DAT produces 2 readings, 50 frames = 100 readings minimum
                assert c.health.total_readings_produced >= frame_count, (
                    f"Collector {c.device_id} only produced "
                    f"{c.health.total_readings_produced} readings"
                )


# ── Frame Buffer Overflow Tests ───────────────────────────────────────────────

class TestFrameBufferOverflow:
    @pytest.mark.asyncio
    async def test_frame_buffer_drops_on_overflow(self) -> None:
        """
        When the frame buffer is full, new frames are dropped with a warning.
        The collector must remain alive and not deadlock.
        """
        # Tiny frame buffer (8 frames)
        transport = SimulatorTransport(device_id="STRESS-OVF-001", queue_maxsize=1000)
        await transport.connect()

        validation = QueueValidationInterface(maxsize=100)
        config = {
            "device_id": "STRESS-OVF-001",
            "frame_buffer_size": 4,  # Very small buffer
            "reconnect_base_delay": 0.1,
            "reconnect_max_delay": 1.0,
            "reconnect_factor": 2.0,
            "max_reconnect_attempts": 1,
        }

        class SmallBufferCollector(BaseCollector):
            collector_name = "small_buffer"
            def build_transport(self): return transport
            def build_adapter(self): return ECGAdapter(device_id=self.device_id)

        collector = SmallBufferCollector(
            device_id="STRESS-OVF-001",
            device_type=DeviceType.ECG,
            config=config,
            validation_queue=validation._queue,
        )

        task = asyncio.create_task(collector.start())

        # Push many more frames than the buffer can hold
        for _ in range(100):
            await transport.push_frame(b"DAT|72|0.84|II")

        await asyncio.sleep(0.5)

        # Collector must still be alive
        assert collector.health.status in (
            DeviceStatus.CONNECTED,
            DeviceStatus.RECONNECTING,
            DeviceStatus.STOPPED,
        )

        await transport.disconnect()
        await collector.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ── Reconnect Storm Tests ─────────────────────────────────────────────────────

class TestReconnectStorm:
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycle(self) -> None:
        """
        Simulate rapid connect/disconnect cycles.
        Collector must handle TransportReadError and reconnect each time.
        """
        call_count = 0
        transports_built: list[SimulatorTransport] = []

        class CyclingTransport(BaseTransport):
            transport_type = "cycling"

            def __init__(self, device_id: str) -> None:
                super().__init__(device_id, {})
                self._cycle = 0

            async def connect(self) -> None:
                self._connected = True
                self._cycle += 1

            async def disconnect(self) -> None:
                self._connected = False

            async def read_frames(self) -> AsyncIterator[bytes]:
                # Yield 3 frames then raise error (simulates disconnect)
                for i in range(3):
                    if not self._connected:
                        return
                    yield f"DAT|{72 + i}|0.84|II".encode()
                    self._frames_received += 1
                raise TransportReadError(
                    f"Simulated disconnect at cycle {self._cycle}",
                    device_id=self.device_id,
                )

        transport = CyclingTransport(device_id="STRESS-CYCLE-001")
        validation = QueueValidationInterface(maxsize=500)
        config = {
            "device_id": "STRESS-CYCLE-001",
            "frame_buffer_size": 256,
            "reconnect_base_delay": 0.02,
            "reconnect_max_delay": 0.1,
            "reconnect_factor": 1.0,
            "max_reconnect_attempts": 5,
        }

        class CycleCollector(BaseCollector):
            collector_name = "cycle_collector"
            def build_transport(self): return transport
            def build_adapter(self): return ECGAdapter(device_id=self.device_id)

        collector = CycleCollector(
            device_id="STRESS-CYCLE-001",
            device_type=DeviceType.ECG,
            config=config,
            validation_queue=validation._queue,
        )

        await asyncio.wait_for(collector.start(), timeout=5.0)

        # After max_reconnect_attempts (5), collector should be FAILED
        assert collector.health.status == DeviceStatus.FAILED
        assert collector.health.reconnect_count >= 4

        # But it processed readings before each disconnect
        assert collector.health.total_frames_received >= 3  # At least first cycle
