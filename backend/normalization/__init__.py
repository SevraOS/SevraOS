"""
HELIOS OS + SEVRA AI
Normalization Layer

Transforms validated readings into standard clinical semantics.
Applies UCUM unit conversion, LOINC mapping, patient resolution,
and creates Canonical Events ready for FHIR projection and Event Bus transmission.
"""

from normalization.canonical import CanonicalEvent
from normalization.normalizer import NormalizerEngine
from normalization.fhir_projection import FHIRProjector

__all__ = [
    "CanonicalEvent",
    "NormalizerEngine",
    "FHIRProjector"
]
