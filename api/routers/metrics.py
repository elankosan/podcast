"""Prometheus metrics endpoint for the podcast application.

Provides basic metrics for monitoring via /api/metrics.
Uses the prometheus-client library.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Info

router = APIRouter()

# Application info
app_info = Info("podcast_app", "Podcast application metadata")
app_info.info({"version": "1.0.0", "language": "python"})

# Request counters
requests_total = Counter(
    "podcast_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

# Request duration
request_duration = Histogram(
    "podcast_api_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Agent execution counters
agent_executions_total = Counter(
    "podcast_agent_executions_total",
    "Total agent executions",
    ["agent_id", "phase", "status"],
)


@router.get("/", response_class=PlainTextResponse)
async def metrics():
    """Expose Prometheus metrics."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
