"""
HELIOS OS + SEVRA AI
Adapter Registry

Dynamic adapter registration and discovery.
Collectors look up the correct adapter by device_type at runtime.

Design:
  - Adapters self-register using the @register decorator, or
  - The registry auto-discovers all adapters in mdil/adapters/ on startup.
  - Duplicate registrations raise AdapterRegistryError (fails fast).
  - Unknown device_type lookup raises AdapterNotFoundError.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any, TYPE_CHECKING

import structlog

from mdil.base import DeviceAdapter, AdapterConfigError
from mdil.schema import DeviceType

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# ── Registry Exceptions ───────────────────────────────────────────────────────

class AdapterRegistryError(Exception):
    """Raised on registry configuration errors (duplicate registration, etc.)."""


class AdapterNotFoundError(Exception):
    """Raised when no adapter is registered for the requested device type."""


# ── Adapter Registry ──────────────────────────────────────────────────────────

class AdapterRegistry:
    """
    Central registry mapping DeviceType → DeviceAdapter class.

    Usage:
        # Self-register via decorator
        @AdapterRegistry.register
        class ECGAdapter(DeviceAdapter): ...

        # Look up and instantiate at runtime
        registry = AdapterRegistry()
        registry.auto_discover()
        adapter = registry.create("ecg", device_id="DEV-001", config={})
    """

    _registry: dict[str, type[DeviceAdapter]] = {}

    def __init__(self) -> None:
        self._discovered: bool = False

    @classmethod
    def register(cls, adapter_class: type[DeviceAdapter]) -> type[DeviceAdapter]:
        """
        Class decorator for registering an adapter.
        Raises AdapterRegistryError if the device_type is already registered.
        """
        if not hasattr(adapter_class, "device_type"):
            raise AdapterRegistryError(
                f"{adapter_class.__name__} must define a 'device_type' class attribute."
            )
        key = adapter_class.device_type.value
        if key in cls._registry:
            existing = cls._registry[key].__name__
            raise AdapterRegistryError(
                f"Adapter for device_type='{key}' already registered by '{existing}'. "
                f"Cannot register '{adapter_class.__name__}' again."
            )
        cls._registry[key] = adapter_class
        logger.debug("adapter_registered", device_type=key, adapter=adapter_class.__name__)
        return adapter_class

    @classmethod
    def register_override(cls, adapter_class: type[DeviceAdapter]) -> type[DeviceAdapter]:
        """
        Force-register an adapter, overriding any existing registration.
        Use for testing or protocol variant overrides.
        """
        key = adapter_class.device_type.value
        if key in cls._registry:
            logger.warning(
                "adapter_override",
                device_type=key,
                old=cls._registry[key].__name__,
                new=adapter_class.__name__,
            )
        cls._registry[key] = adapter_class
        return adapter_class

    def auto_discover(self) -> None:
        """
        Auto-import all adapter modules in mdil/adapters/.
        Each module's import triggers @register decorator calls.
        Safe to call multiple times — skips if already discovered.
        """
        if self._discovered:
            return

        adapters_dir = Path(__file__).parent / "adapters"
        for py_file in sorted(adapters_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"mdil.adapters.{py_file.stem}"
            try:
                importlib.import_module(module_name)
                logger.debug("adapter_module_loaded", module=module_name)
            except Exception as exc:
                logger.error(
                    "adapter_module_load_failed",
                    module=module_name,
                    error=str(exc),
                    exc_info=True,
                )

        self._discovered = True
        logger.info(
            "adapter_discovery_complete",
            registered_count=len(self._registry),
            device_types=list(self._registry.keys()),
        )

    def create(
        self,
        device_type: str | DeviceType,
        device_id: str,
        config: dict[str, Any] | None = None,
    ) -> DeviceAdapter:
        """
        Instantiate an adapter for the given device_type.

        Args:
            device_type: DeviceType enum value or string key.
            device_id: The device's registered ID.
            config: Optional adapter configuration dict.

        Returns:
            A configured DeviceAdapter instance.

        Raises:
            AdapterNotFoundError: if no adapter is registered for the type.
            AdapterConfigError: if the adapter config is invalid.
        """
        key = device_type.value if isinstance(device_type, DeviceType) else device_type

        adapter_class = self._registry.get(key)
        if adapter_class is None:
            raise AdapterNotFoundError(
                f"No adapter registered for device_type='{key}'. "
                f"Registered types: {list(self._registry.keys())}"
            )

        try:
            instance = adapter_class(device_id=device_id, config=config)
            logger.info(
                "adapter_created",
                device_type=key,
                device_id=device_id,
                adapter=adapter_class.__name__,
            )
            return instance
        except AdapterConfigError:
            raise
        except Exception as exc:
            raise AdapterRegistryError(
                f"Failed to instantiate {adapter_class.__name__}: {exc}"
            ) from exc

    @classmethod
    def all_registered(cls) -> dict[str, str]:
        """Return a dict of device_type → adapter class name for all registered adapters."""
        return {k: v.__name__ for k, v in cls._registry.items()}

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations. Use only in tests."""
        cls._registry.clear()

    @classmethod
    def is_registered(cls, device_type: str | DeviceType) -> bool:
        """Check if an adapter is registered for the given device type."""
        key = device_type.value if isinstance(device_type, DeviceType) else device_type
        return key in cls._registry


# ── Module-level singleton ────────────────────────────────────────────────────

_default_registry = AdapterRegistry()


def get_registry() -> AdapterRegistry:
    """Get the default adapter registry singleton."""
    return _default_registry
