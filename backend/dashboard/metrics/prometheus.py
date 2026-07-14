"""
HELIOS OS + SEVRA AI
Dashboard Metrics (Section 21)
"""

from prometheus_client import Counter, Histogram, Gauge

class DashboardMetrics:
    def __init__(self):
        self.api_requests_total = Counter(
            'helios_dashboard_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status']
        )
        self.api_latency_seconds = Histogram(
            'helios_dashboard_api_latency_seconds',
            'API request latency in seconds',
            ['endpoint']
        )
        self.websocket_connections = Gauge(
            'helios_dashboard_ws_active_connections',
            'Currently active WebSocket connections'
        )

metrics = DashboardMetrics()
