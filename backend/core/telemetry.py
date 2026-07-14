"""
HELIOS OS + SEVRA AI
Observability & OpenTelemetry (Section 17)
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI

def init_telemetry(app: FastAPI, service_name: str):
    """Initialize OpenTelemetry distributed tracing."""
    
    provider = TracerProvider()
    
    # Export to Jaeger / OpenTelemetry Collector
    otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    
    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    return provider
