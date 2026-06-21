"""Structured Logging Configuration."""

import structlog
import logging
import sys
from typing import Any, Dict


def configure_logging(level: str = "info", format_type: str = "json") -> None:
    """Configure structured logging."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get structured logger."""
    return structlog.get_logger(name)


def log_token_refresh_started(email: str, expires_in_seconds: int, strategy: str) -> None:
    """Log token refresh started."""
    logger = get_logger()
    logger.info(
        "token_refresh_started",
        email=email,
        expires_in_seconds=expires_in_seconds,
        strategy=strategy
    )


def log_token_refresh_success(
    email: str,
    old_expiry: str,
    new_expiry: str,
    refresh_duration_ms: int,
    is_leader: bool
) -> None:
    """Log token refresh success."""
    logger = get_logger()
    logger.info(
        "token_refresh_success",
        email=email,
        old_expiry=old_expiry,
        new_expiry=new_expiry,
        refresh_duration_ms=refresh_duration_ms,
        is_leader=is_leader
    )


def log_token_refresh_failed(
    email: str,
    error_type: str,
    error_message: str,
    retry_attempt: int
) -> None:
    """Log token refresh failure."""
    logger = get_logger()
    logger.error(
        "token_refresh_failed",
        email=email,
        error_type=error_type,
        error_message=error_message,
        retry_attempt=retry_attempt
    )


def log_cache_hit(email: str, cache_type: str) -> None:
    """Log cache hit."""
    logger = get_logger()
    logger.debug(
        "cache_hit",
        email=email,
        cache_type=cache_type
    )


def log_cache_miss(email: str, cache_type: str) -> None:
    """Log cache miss."""
    logger = get_logger()
    logger.debug(
        "cache_miss",
        email=email,
        cache_type=cache_type
    )


def log_api_request(method: str, endpoint: str, status_code: int, duration_ms: int) -> None:
    """Log API request."""
    logger = get_logger()
    logger.info(
        "api_request",
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms
    )
