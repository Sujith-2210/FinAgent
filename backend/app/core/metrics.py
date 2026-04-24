"""
Performance Metrics Module
Prometheus metrics for agent and system monitoring.
Validates: Requirements 8.3, 12.1, 12.2, 12.3, 12.5
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from fastapi.responses import Response
import time
from functools import wraps
from typing import Callable


# === RED Metrics (Rate, Errors, Duration) ===

REQUEST_COUNT = Counter(
    'finagent_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'finagent_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUEST_ERRORS = Counter(
    'finagent_http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'error_type']
)


# === Agent-Specific Metrics ===

AGENT_INVOCATIONS = Counter(
    'finagent_agent_invocations_total',
    'Total agent invocations',
    ['agent_name']
)

AGENT_DURATION = Histogram(
    'finagent_agent_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

AGENT_SUCCESS_RATE = Gauge(
    'finagent_agent_success_rate',
    'Agent success rate (0-1)',
    ['agent_name']
)

AGENT_CONFIDENCE = Gauge(
    'finagent_agent_confidence',
    'Agent average confidence',
    ['agent_name']
)


# === LLM Metrics ===

LLM_TOKEN_USAGE = Counter(
    'finagent_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']  # type = input/output
)

LLM_INFERENCE_DURATION = Histogram(
    'finagent_llm_inference_seconds',
    'LLM inference duration in seconds',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]
)


# === Cache Metrics ===

CACHE_HITS = Counter(
    'finagent_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'finagent_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

CACHE_SIZE = Gauge(
    'finagent_cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)


# === System Info ===

SYSTEM_INFO = Info(
    'finagent_system',
    'FinAgent system information'
)


# === Active metrics ===

ACTIVE_CONNECTIONS = Gauge(
    'finagent_active_connections',
    'Number of active connections'
)

ACTIVE_QUERIES = Gauge(
    'finagent_active_queries',
    'Number of active queries being processed'
)


# === Agent Statistics Tracking ===

class AgentMetricsTracker:
    """Tracks agent performance metrics."""

    def __init__(self):
        self._success_counts = {}
        self._total_counts = {}
        self._confidence_sums = {}

    def track_invocation(
        self,
        agent_name: str,
        success: bool,
        duration: float,
        confidence: float = 0.8
    ):
        """Track a single agent invocation."""
        # Increment invocation counter
        AGENT_INVOCATIONS.labels(agent_name=agent_name).inc()

        # Record duration
        AGENT_DURATION.labels(agent_name=agent_name).observe(duration)

        # Track success rate
        if agent_name not in self._total_counts:
            self._total_counts[agent_name] = 0
            self._success_counts[agent_name] = 0
            self._confidence_sums[agent_name] = 0

        self._total_counts[agent_name] += 1
        if success:
            self._success_counts[agent_name] += 1

        self._confidence_sums[agent_name] += confidence

        # Update gauges
        success_rate = self._success_counts[agent_name] / self._total_counts[agent_name]
        avg_confidence = self._confidence_sums[agent_name] / self._total_counts[agent_name]

        AGENT_SUCCESS_RATE.labels(agent_name=agent_name).set(success_rate)
        AGENT_CONFIDENCE.labels(agent_name=agent_name).set(avg_confidence)

    def track_llm_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration: float
    ):
        """Track LLM usage metrics."""
        LLM_TOKEN_USAGE.labels(model=model, type='input').inc(input_tokens)
        LLM_TOKEN_USAGE.labels(model=model, type='output').inc(output_tokens)
        LLM_INFERENCE_DURATION.labels(model=model).observe(duration)

    def check_performance_degradation(self, agent_name: str) -> bool:
        """
        Check if agent success rate is below threshold (70%).
        Validates: Requirement 12.2
        """
        if agent_name not in self._total_counts:
            return False

        success_rate = self._success_counts[agent_name] / self._total_counts[agent_name]
        return success_rate < 0.70


# Singleton tracker
metrics_tracker = AgentMetricsTracker()


# === Metrics Endpoint ===

metrics_router = APIRouter()


@metrics_router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Validates: Requirement 8.3
    """
    # Update system info
    SYSTEM_INFO.info({
        'version': '1.0.0',
        'environment': 'development'
    })

    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# === Decorator for tracking agent execution ===

def track_agent_execution(agent_name: str):
    """Decorator to track agent execution metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            confidence = 0.8

            try:
                result = await func(*args, **kwargs)

                # Try to extract confidence from result
                if isinstance(result, dict):
                    confidence = result.get('confidence', 0.8)

                return result

            except Exception:
                success = False
                raise

            finally:
                duration = time.time() - start_time
                metrics_tracker.track_invocation(
                    agent_name=agent_name,
                    success=success,
                    duration=duration,
                    confidence=confidence
                )

        return wrapper
    return decorator
