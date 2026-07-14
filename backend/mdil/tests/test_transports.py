"""
HELIOS OS + SEVRA AI
MDIL Transport Unit Tests

Tests:
  - SimulatorTransport (in-memory, no hardware)
  - BaseTransport interface contracts
  - Transport error classes
  - Frame yielding behaviour
  - Stats tracking
  - Async context manager protocol
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest
import pytest_asyncio

from mdil.transports.base_transport import (
    BaseTransport,
    TransportConnectionError,
    TransportReadError,
    TransportConfigError,
)
from mdil.transports.simulator_transport import SimulatorTransport


# ── SimulatorTransport Tests ──────────────────────────────────────────────────

class TestSimulatorTransportBasics:
    @pytest.mark.asyncio
    async def test_connect_sets_connected_true(self) -> None:
        t = SimulatorTransport(device_id="SIM-001")
        assert not t.is_connected
        await t.connect()
        assert t.is_connected

    @pytest.mark.asyncio
    async def test_disconnect_sets_connected_false(self) -> None:
        t = SimulatorTransport(device_id="SIM-002")
        await t.connect()
        await t.disconnect()
        assert not t.is_connected

    @pytest.mark.asyncio
    async def test_push_and_read_single_frame(self) -> None:
        t = SimulatorTransport(device_id="SIM-003")
        await t.connect()
        await t.push_frame(b"DAT|72|0.84|II")

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                break

        await asyncio.wait_for(consume(), timeout=1.0)
        assert received == [b"DAT|72|0.84|II"]

    @pytest.mark.asyncio
    async def test_push_multiple_frames_all_received_in_order(self) -> None:
        t = SimulatorTransport(device_id="SIM-004")
        await t.connect()
        frames = [b"FRAME-1", b"FRAME-2", b"FRAME-3"]
        for f in frames:
            await t.push_frame(f)

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                if len(received) == len(frames):
                    break

        await asyncio.wait_for(consume(), timeout=1.0)
        assert received == frames

    @pytest.mark.asyncio
    async def test_disconnect_sentinel_stops_read_frames(self) -> None:
        t = SimulatorTransport(device_id="SIM-005")
        await t.connect()

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)

        task = asyncio.create_task(consume())
        await t.push_frame(b"DATA-A")
        await t.push_frame(b"DATA-B")
        await asyncio.sleep(0.05)
        await t.disconnect()  # Sends sentinel

        await asyncio.wait_for(task, timeout=1.0)
        assert received == [b"DATA-A", b"DATA-B"]

    @pytest.mark.asyncio
    async def test_push_frame_nowait_does_not_block(self) -> None:
        t = SimulatorTransport(device_id="SIM-006")
        await t.connect()
        t.push_frame_nowait(b"NOWAIT-FRAME")
        assert t._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_push_frame_nowait_drops_when_full(self) -> None:
        t = SimulatorTransport(device_id="SIM-007", queue_maxsize=1)
        await t.connect()
        t.push_frame_nowait(b"FRAME-1")  # Fills queue
        t.push_frame_nowait(b"FRAME-2")  # Should drop silently

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                break

        await asyncio.wait_for(consume(), timeout=0.5)
        assert received == [b"FRAME-1"]
        assert t.stats["frames_received"] == 1  # Only 1 counted (nowait dropped)

    @pytest.mark.asyncio
    async def test_read_frames_raises_when_not_connected(self) -> None:
        t = SimulatorTransport(device_id="SIM-008")
        # Not connected
        with pytest.raises(TransportConnectionError):
            async for _ in t.read_frames():
                break

    @pytest.mark.asyncio
    async def test_stats_bytes_received(self) -> None:
        t = SimulatorTransport(device_id="SIM-009")
        await t.connect()
        await t.push_frame(b"ABC")    # 3 bytes
        await t.push_frame(b"DEFG")  # 4 bytes
        assert t.stats["bytes_received"] == 7
        assert t.stats["frames_received"] == 2

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        async with SimulatorTransport(device_id="SIM-010") as t:
            assert t.is_connected
        assert not t.is_connected

    @pytest.mark.asyncio
    async def test_multiple_pushes_concurrent(self) -> None:
        t = SimulatorTransport(device_id="SIM-011", queue_maxsize=100)
        await t.connect()

        async def producer() -> None:
            for i in range(10):
                await t.push_frame(f"FRAME-{i}".encode())

        received: list[bytes] = []

        async def consumer() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                if len(received) == 10:
                    break

        await asyncio.gather(producer(), consumer())
        assert len(received) == 10

    @pytest.mark.asyncio
    async def test_empty_frame_accepted_and_readable(self) -> None:
        t = SimulatorTransport(device_id="SIM-012")
        await t.connect()
        await t.push_frame(b"")
        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                break

        await asyncio.wait_for(consume(), timeout=0.5)
        assert received == [b""]


# ── TransportError Hierarchy Tests ────────────────────────────────────────────

class TestTransportErrors:
    def test_transport_connection_error_has_device_id(self) -> None:
        err = TransportConnectionError("failed", device_id="DEV-001")
        assert err.device_id == "DEV-001"
        assert "failed" in str(err)

    def test_transport_read_error_has_device_id(self) -> None:
        err = TransportReadError("read failed", device_id="DEV-002")
        assert err.device_id == "DEV-002"

    def test_transport_config_error_inherits_transport_error(self) -> None:
        err = TransportConfigError("bad config", device_id="DEV-003")
        assert isinstance(err, TransportConnectionError.__bases__[0])  # TransportError

    def test_connection_error_is_transport_error(self) -> None:
        from mdil.transports.base_transport import TransportError
        err = TransportConnectionError("x", device_id="D")
        assert isinstance(err, TransportError)

    def test_read_error_is_transport_error(self) -> None:
        from mdil.transports.base_transport import TransportError
        err = TransportReadError("x", device_id="D")
        assert isinstance(err, TransportError)


# ── BaseTransport Interface Contract Tests ────────────────────────────────────

class TestBaseTransportInterface:
    """Verify that BaseTransport abstract contract is enforced."""

    def test_cannot_instantiate_base_transport_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseTransport(device_id="X", config={})  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_all_methods(self) -> None:
        """A partial subclass missing abstract methods cannot be instantiated."""

        class PartialTransport(BaseTransport):
            transport_type = "partial"

            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass
            # Missing read_frames

        with pytest.raises(TypeError):
            PartialTransport(device_id="X", config={})  # type: ignore[abstract]

    def test_is_connected_property_reflects_state(self) -> None:
        t = SimulatorTransport(device_id="SIM-CON-001")
        assert t.is_connected is False

    def test_stats_initial_values(self) -> None:
        t = SimulatorTransport(device_id="SIM-STAT-001")
        stats = t.stats
        assert stats["bytes_received"] == 0
        assert stats["frames_received"] == 0

    def test_transport_type_attribute(self) -> None:
        t = SimulatorTransport(device_id="SIM-TYPE-001")
        assert t.transport_type == "simulator"


# ── Simulator Transport Framing Tests ─────────────────────────────────────────

class TestSimulatorFraming:
    """Verify the simulator correctly handles various frame sizes and types."""

    @pytest.mark.asyncio
    async def test_binary_frames_preserved_exactly(self) -> None:
        t = SimulatorTransport(device_id="SIM-BIN-001")
        await t.connect()
        binary_payload = bytes([0xAA, 0xBB, 0x01, 0x00, 0x00, 0x00, 0x64, 0x00])
        await t.push_frame(binary_payload)

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                break

        await asyncio.wait_for(consume(), timeout=0.5)
        assert received[0] == binary_payload

    @pytest.mark.asyncio
    async def test_large_frame_handled(self) -> None:
        t = SimulatorTransport(device_id="SIM-LARGE-001")
        await t.connect()
        large_frame = b"WFM|II|500|" + b",".join(
            f"{i * 0.001:.3f}".encode() for i in range(500)
        )
        await t.push_frame(large_frame)

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                break

        await asyncio.wait_for(consume(), timeout=0.5)
        assert received[0] == large_frame

    @pytest.mark.asyncio
    async def test_high_frequency_frames(self) -> None:
        """Push 1000 frames rapidly — all must be received."""
        t = SimulatorTransport(device_id="SIM-HF-001", queue_maxsize=2000)
        await t.connect()

        frame_count = 1000
        for i in range(frame_count):
            await t.push_frame(f"FRAME-{i:04d}".encode())

        received: list[bytes] = []

        async def consume() -> None:
            async for frame in t.read_frames():
                received.append(frame)
                if len(received) == frame_count:
                    break

        await asyncio.wait_for(consume(), timeout=5.0)
        assert len(received) == frame_count
        # Verify order preserved
        assert received[0] == b"FRAME-0000"
        assert received[-1] == f"FRAME-{frame_count - 1:04d}".encode()
