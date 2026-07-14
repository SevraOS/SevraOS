"""
HELIOS OS + SEVRA AI
MDIL Registry Unit Tests

Tests:
  - AdapterRegistry.register (decorator + manual)
  - AdapterRegistry.auto_discover (loads all adapters)
  - AdapterRegistry.create (instantiation with config)
  - Duplicate registration detection
  - AdapterNotFoundError on unknown device_type
  - AdapterRegistry.clear (test isolation)
  - AdapterRegistry.is_registered
  - AdapterRegistry.all_registered
  - register_override (test and protocol variant scenarios)
"""

from __future__ import annotations

import pytest

from mdil.base import DeviceAdapter, AdapterConfigError
from mdil.registry import (
    AdapterRegistry,
    AdapterRegistryError,
    AdapterNotFoundError,
    get_registry,
)
from mdil.schema import DeviceType, RawReading


# ── Fixtures ──────────────────────────────────────────────────────────────────

class _MockAdapter(DeviceAdapter):
    """Minimal concrete adapter for registry testing."""
    device_type = DeviceType.SIMULATOR
    supported_protocols = ["Test-v1"]
    adapter_version = "0.0.1"

    def parse(self, raw_frame: str | bytes) -> list[RawReading]:
        return []


class _AnotherMockAdapter(DeviceAdapter):
    """Second mock adapter for override tests."""
    device_type = DeviceType.SIMULATOR
    supported_protocols = ["Test-v2"]
    adapter_version = "0.0.2"

    def parse(self, raw_frame: str | bytes) -> list[RawReading]:
        return []


class _ConfigRequiredAdapter(DeviceAdapter):
    device_type = DeviceType.UNKNOWN
    supported_protocols = []

    def _validate_config(self) -> None:
        if "required_key" not in self.config:
            raise AdapterConfigError("'required_key' is missing from adapter config.")

    def parse(self, raw_frame: str | bytes) -> list[RawReading]:
        return []


# ── Test Isolation ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Ensure a clean registry before and after every test."""
    AdapterRegistry.clear()
    yield
    AdapterRegistry.clear()


# ── Registration Tests ────────────────────────────────────────────────────────

class TestAdapterRegistration:
    def test_register_class_decorator_works(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        assert AdapterRegistry.is_registered(DeviceType.SIMULATOR)

    def test_register_returns_the_class(self) -> None:
        result = AdapterRegistry.register(_MockAdapter)
        assert result is _MockAdapter

    def test_duplicate_registration_raises(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        with pytest.raises(AdapterRegistryError, match="already registered"):
            AdapterRegistry.register(_MockAdapter)

    def test_duplicate_different_class_same_type_raises(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        with pytest.raises(AdapterRegistryError):
            AdapterRegistry.register(_AnotherMockAdapter)

    def test_register_override_replaces_existing(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        AdapterRegistry.register_override(_AnotherMockAdapter)
        registered = AdapterRegistry.all_registered()
        assert registered[DeviceType.SIMULATOR.value] == "_AnotherMockAdapter"

    def test_register_override_on_empty_registry_works(self) -> None:
        AdapterRegistry.register_override(_MockAdapter)
        assert AdapterRegistry.is_registered(DeviceType.SIMULATOR)

    def test_register_without_device_type_raises(self) -> None:
        class BadAdapter:
            pass

        with pytest.raises(AdapterRegistryError, match="device_type"):
            AdapterRegistry.register(BadAdapter)  # type: ignore[arg-type]

    def test_all_registered_returns_correct_map(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        result = AdapterRegistry.all_registered()
        assert isinstance(result, dict)
        assert "simulator" in result
        assert result["simulator"] == "_MockAdapter"

    def test_is_registered_string_key(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        assert AdapterRegistry.is_registered("simulator")

    def test_is_registered_enum_key(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        assert AdapterRegistry.is_registered(DeviceType.SIMULATOR)

    def test_is_registered_false_for_unknown(self) -> None:
        assert not AdapterRegistry.is_registered("unknown_device_xyz")

    def test_clear_removes_all_registrations(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        AdapterRegistry.clear()
        assert not AdapterRegistry.is_registered(DeviceType.SIMULATOR)


# ── Auto-Discovery Tests ──────────────────────────────────────────────────────

class TestAutoDiscovery:
    def test_auto_discover_registers_all_six_adapters(self) -> None:
        registry = AdapterRegistry()
        registry.auto_discover()
        registered = AdapterRegistry.all_registered()

        expected = {
            "ecg", "blood_pressure", "spo2",
            "ventilator", "infusion_pump", "glucometer",
        }
        assert expected.issubset(registered.keys())

    def test_auto_discover_idempotent(self) -> None:
        registry = AdapterRegistry()
        registry.auto_discover()
        count_first = len(AdapterRegistry.all_registered())
        registry.auto_discover()  # Second call should be no-op
        count_second = len(AdapterRegistry.all_registered())
        assert count_first == count_second

    def test_auto_discover_sets_discovered_flag(self) -> None:
        registry = AdapterRegistry()
        assert not registry._discovered
        registry.auto_discover()
        assert registry._discovered


# ── Create (Instantiation) Tests ──────────────────────────────────────────────

class TestAdapterCreate:
    def test_create_returns_adapter_instance(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        registry = AdapterRegistry()
        adapter = registry.create("simulator", device_id="SIM-001")
        assert isinstance(adapter, _MockAdapter)

    def test_create_with_device_type_enum(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        registry = AdapterRegistry()
        adapter = registry.create(DeviceType.SIMULATOR, device_id="SIM-002")
        assert isinstance(adapter, _MockAdapter)

    def test_create_passes_device_id(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        registry = AdapterRegistry()
        adapter = registry.create("simulator", device_id="SIM-TEST-001")
        assert adapter.device_id == "SIM-TEST-001"

    def test_create_passes_config(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        registry = AdapterRegistry()
        config = {"key": "value", "timeout": 5}
        adapter = registry.create("simulator", device_id="SIM-003", config=config)
        assert adapter.config == config

    def test_create_unknown_type_raises_not_found(self) -> None:
        registry = AdapterRegistry()
        with pytest.raises(AdapterNotFoundError, match="unknown_type_xyz"):
            registry.create("unknown_type_xyz", device_id="X")

    def test_create_config_validation_error_propagates(self) -> None:
        AdapterRegistry.register(_ConfigRequiredAdapter)
        registry = AdapterRegistry()
        with pytest.raises(AdapterConfigError, match="required_key"):
            registry.create("unknown", device_id="X", config={})

    def test_create_ecg_adapter_via_auto_discover(self) -> None:
        from mdil.adapters.ecg_adapter import ECGAdapter
        registry = AdapterRegistry()
        registry.auto_discover()
        adapter = registry.create("ecg", device_id="ECG-DISC-001")
        assert isinstance(adapter, ECGAdapter)
        assert adapter.device_id == "ECG-DISC-001"

    def test_create_all_six_adapters_via_auto_discover(self) -> None:
        registry = AdapterRegistry()
        registry.auto_discover()

        device_types = [
            ("ecg", "ECG-001"),
            ("blood_pressure", "BP-001"),
            ("spo2", "SPO2-001"),
            ("ventilator", "VENT-001"),
            ("infusion_pump", "INF-001"),
            ("glucometer", "GLU-001"),
        ]

        for dtype, dev_id in device_types:
            adapter = registry.create(dtype, device_id=dev_id)
            assert adapter.device_id == dev_id


# ── Singleton Tests ───────────────────────────────────────────────────────────

class TestRegistrySingleton:
    def test_get_registry_returns_same_instance(self) -> None:
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_registry_class_state_is_shared(self) -> None:
        AdapterRegistry.register(_MockAdapter)
        # A new instance of AdapterRegistry sees the same class-level state
        r2 = AdapterRegistry()
        assert AdapterRegistry.is_registered(DeviceType.SIMULATOR)
