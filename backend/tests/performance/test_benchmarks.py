"""
HELIOS OS + SEVRA AI
Pytest Benchmarking Suite (Section 17)
"""

import pytest
from datetime import datetime, timezone
from normalization.canonical import CanonicalEvent
from integration.fhir.mapping import FHIRMapper
import json

@pytest.mark.benchmark(group="fhir")
def test_benchmark_fhir_serialization(benchmark):
    """Benchmark FHIR Observation serialization throughput."""
    event = CanonicalEvent(
        client_event_id="evt-123",
        patient_id="pt-123",
        metric="heart_rate",
        value=85.0,
        unit="bpm",
        loinc="8867-4",
        captured_at=datetime.now(timezone.utc),
        source_device="dev-1",
        flagged=False
    )
    
    def serialize():
        obs = FHIRMapper.vital_to_observation(event, "ehr-123")
        return obs.model_dump_json()
        
    result = benchmark(serialize)
    assert "8867-4" in result

@pytest.mark.benchmark(group="ai")
def test_benchmark_mews_scoring(benchmark):
    """Benchmark Risk Engine MEWS calculation latency."""
    from ai.risk_scoring.engine import RiskEngine
    
    vitals = {
        "heart_rate": 120,
        "systolic_bp": 90,
        "respiratory_rate": 25,
        "temperature": 39.0
    }
    
    def calculate():
        return RiskEngine.calculate_mews(vitals).value
        
    score = benchmark(calculate)
    assert score > 0
