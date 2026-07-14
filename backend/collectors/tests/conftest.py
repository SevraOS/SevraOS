"""
HELIOS OS + SEVRA AI
Collector Test Configuration

Provides shared fixtures for all collectors/tests/*.py:
  - Validation interface instances
  - SimulatorTransport factories
  - Pre-built collector instances
  - Supervisor fixtures
"""

from __future__ import annotations

import asyncio

import pytest

from collectors.base.health import CollectorHealth
from collectors.base.supervisor import CollectorSupervisor
from collectors.base.validation_interface import (
    QueueValidationInterface,
    NullValidationInterface,
)
from mdil.transports.simulator_transport import SimulatorTransport


# ── Validation Interface Fixtures ─────────────────────────────────────────────

@pytest.fixture
async def validation_queue():
    """Running QueueValidationInterface, stopped after test."""
    vi = QueueValidationInterface(maxsize=10_000)
    await vi.start()
    yield vi
    await vi.stop()


@pytest.fixture
def null_validation():
    """NullValidationInterface that discards all readings."""
    return NullValidationInterface()


# ── Transport Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
async def simulator_transport():
    """Connected SimulatorTransport for a generic test device."""
    t = SimulatorTransport(device_id="TEST-SIM-001", queue_maxsize=1000)
    await t.connect()
    yield t
    if t.is_connected:
        await t.disconnect()


@pytest.fixture
def make_simulator_transport():
    """Factory fixture: creates and connects a SimulatorTransport by device_id."""
    transports = []

    async def _make(device_id: str, queue_maxsize: int = 1000) -> SimulatorTransport:
        t = SimulatorTransport(device_id=device_id, queue_maxsize=queue_maxsize)
        await t.connect()
        transports.append(t)
        return t

    yield _make

    # Cleanup all created transports
    async def _cleanup():
        for t in transports:
            if t.is_connected:
                await t.disconnect()

    asyncio.get_event_loop().run_until_complete(_cleanup())


# ── Supervisor Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def supervisor():
    """Fresh CollectorSupervisor instance."""
    return CollectorSupervisor(shutdown_timeout=2.0)


# ── Health Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def ecg_health():
    return CollectorHealth(device_id="TEST-ECG-001", device_type="ecg")


@pytest.fixture
def bp_health():
    return CollectorHealth(device_id="TEST-BP-001", device_type="blood_pressure")
