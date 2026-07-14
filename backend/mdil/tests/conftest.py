"""
HELIOS OS + SEVRA AI
MDIL Test Configuration

Provides fixtures shared across all mdil/tests/*.py:
  - Ensures AdapterRegistry is cleared between tests that modify it.
  - Provides pre-built adapter instances for adapter tests.
  - Provides SimulatorTransport instances for transport tests.
"""

from __future__ import annotations

import pytest

from mdil.registry import AdapterRegistry
from mdil.transports.simulator_transport import SimulatorTransport


# ── Registry Isolation ────────────────────────────────────────────────────────

@pytest.fixture(autouse=False)
def clean_registry():
    """
    Clears the AdapterRegistry before and after tests that explicitly
    request registry isolation.

    Usage:
        def test_something(clean_registry):  # explicit opt-in
            ...
    """
    AdapterRegistry.clear()
    yield
    AdapterRegistry.clear()


@pytest.fixture(scope="session")
def discovered_registry():
    """
    Session-scoped registry with all 6 adapters auto-discovered.
    Safe to share because adapters are read-only after discovery.
    """
    AdapterRegistry.clear()
    registry = AdapterRegistry()
    registry.auto_discover()
    return registry


# ── Transport Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
async def connected_simulator():
    """
    Connected SimulatorTransport, disconnected after test.
    """
    t = SimulatorTransport(device_id="CONFTEST-SIM-001")
    await t.connect()
    yield t
    await t.disconnect()


# ── Adapter Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def ecg_adapter():
    from mdil.adapters.ecg_adapter import ECGAdapter
    return ECGAdapter(device_id="CONFTEST-ECG-001")


@pytest.fixture
def bp_adapter():
    from mdil.adapters.bp_adapter import BPAdapter
    return BPAdapter(device_id="CONFTEST-BP-001")


@pytest.fixture
def spo2_adapter():
    from mdil.adapters.spo2_adapter import SpO2Adapter
    return SpO2Adapter(device_id="CONFTEST-SPO2-001")


@pytest.fixture
def ventilator_adapter():
    from mdil.adapters.ventilator_adapter import VentilatorAdapter
    return VentilatorAdapter(device_id="CONFTEST-VENT-001")


@pytest.fixture
def infusion_adapter():
    from mdil.adapters.infusion_adapter import InfusionAdapter
    return InfusionAdapter(device_id="CONFTEST-INF-001")


@pytest.fixture
def glucometer_adapter():
    from mdil.adapters.glucometer_adapter import GlucometerAdapter
    return GlucometerAdapter(device_id="CONFTEST-GLU-001")
