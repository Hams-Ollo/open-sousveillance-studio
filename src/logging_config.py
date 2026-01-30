"""
Structured logging configuration for Alachua Civic Intelligence System.

Uses structlog for structured JSON logging in production and
colored console output in development.

Configuration:
- LOG_LEVEL: Set via environment variable (default: INFO)
- LOG_FORMAT: "json" for production, "console" for development (default: console)
"""

import logging
import os
import sys
from typing import Any

import structlog


# Environment configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "console").lower()  # "json" or "console"


def get_log_level() -> int:
    """Convert LOG_LEVEL string to logging constant."""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return levels.get(LOG_LEVEL, logging.INFO)


def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application-level context to all log entries."""
    event_dict["app"] = "alachua-civic-intel"
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.
    
    Call this once at application startup (e.g., in main.py or app.py).
    """
    # Shared processors for both dev and prod
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if LOG_FORMAT == "json":
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(get_log_level()),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(get_log_level()),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Also configure standard library logging to use structlog
    # This captures logs from third-party libraries (uvicorn, celery, etc.)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=get_log_level(),
    )


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (e.g., "agents.scout", "tools.firecrawl")
        **initial_context: Key-value pairs to bind to all log entries
    
    Returns:
        A bound structlog logger.
    
    Example:
        logger = get_logger("agents.scout", agent_id="A1")
        logger.info("Starting scout run", source_id="alachua-city")
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


def bind_context(**context: Any) -> None:
    """
    Bind context variables that will be included in all subsequent logs.
    
    Useful for request-scoped context like request_id.
    
    Args:
        **context: Key-value pairs to bind
    
    Example:
        bind_context(request_id="abc-123", user_id="user-456")
    """
    structlog.contextvars.bind_contextvars(**context)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# Auto-configure on import if not already configured
_configured = False


def ensure_configured() -> None:
    """Ensure logging is configured (idempotent)."""
    global _configured
    if not _configured:
        configure_logging()
        _configured = True
