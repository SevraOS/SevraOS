"""
HELIOS OS + SEVRA AI — MDIL Package
Medical Device Integration Layer

The MDIL is the sole entry point for all device data.
It translates every device protocol into a unified RawReading.
Protocol complexity does not exist beyond this layer.
"""

from mdil.schema import DeviceType, RawReading
from mdil.base import DeviceAdapter
from mdil.registry import AdapterRegistry

__all__ = ["DeviceType", "RawReading", "DeviceAdapter", "AdapterRegistry"]
