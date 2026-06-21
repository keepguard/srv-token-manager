"""Prometheus Metrics Implementation."""

from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Dict, Any

# Application info
app_info = Info('token_manager_app', 'Token Manager application info')

# Counters
token_refresh_total = Counter(
    'token_manager_refresh_total',
    'Total number of token refresh attempts',
    ['email', 'status', 'strategy']
)

token_fetch_total = Counter(
    'token_manager_fetch_total',
    'Total number of token fetch requests',
    ['email', 'source']  # source: cache ou redis
)

# Gauges
token_expiry_seconds = Gauge(
    'token_manager_expiry_seconds',
    'Seconds until token expiry',
    ['email']
)

token_refresh_count = Gauge(
    'token_manager_refresh_count',
    'Number of times token was refreshed',
    ['email']
)

active_tokens_count = Gauge(
    'token_manager_active_tokens',
    'Number of active tokens in cache'
)

# Histograms
token_refresh_duration = Histogram(
    'token_manager_refresh_duration_seconds',
    'Time taken to refresh token',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

token_fetch_duration = Histogram(
    'token_manager_fetch_duration_seconds',
    'Time taken to fetch token',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

redis_operation_duration = Histogram(
    'token_manager_redis_operation_duration_seconds',
    'Time taken for Redis operations',
    ['operation'],  # get, set, delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

# Cache metrics
cache_hits_total = Counter(
    'token_manager_cache_hits_total',
    'Total cache hits',
    ['cache_type']  # local ou redis
)

cache_misses_total = Counter(
    'token_manager_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# API metrics
http_requests_total = Counter(
    'token_manager_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration = Histogram(
    'token_manager_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)


def update_app_info(version: str, environment: str, python_version: str) -> None:
    """Update application info metrics."""
    app_info.info({
        'version': version,
        'environment': environment,
        'python_version': python_version
    })


def increment_token_refresh(email: str, status: str, strategy: str = "proactive") -> None:
    """Increment token refresh counter."""
    token_refresh_total.labels(email=email, status=status, strategy=strategy).inc()


def increment_token_fetch(email: str, source: str) -> None:
    """Increment token fetch counter."""
    token_fetch_total.labels(email=email, source=source).inc()


def update_token_expiry(email: str, seconds_until_expiry: int) -> None:
    """Update token expiry gauge."""
    token_expiry_seconds.labels(email=email).set(seconds_until_expiry)


def update_token_refresh_count(email: str, count: int) -> None:
    """Update token refresh count gauge."""
    token_refresh_count.labels(email=email).set(count)


def update_active_tokens_count(count: int) -> None:
    """Update active tokens count gauge."""
    active_tokens_count.set(count)


def increment_cache_hits(cache_type: str) -> None:
    """Increment cache hits counter."""
    cache_hits_total.labels(cache_type=cache_type).inc()


def increment_cache_misses(cache_type: str) -> None:
    """Increment cache misses counter."""
    cache_misses_total.labels(cache_type=cache_type).inc()


def increment_http_requests(method: str, endpoint: str, status_code: int) -> None:
    """Increment HTTP requests counter."""
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
