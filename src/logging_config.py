"""
Structured logging configuration for Open Sousveillance Studio System.

Uses structlog for structured JSON logging in production and
colored console output in development.

Features:
- Dual output: Console (colored) + File (JSON)
- Log rotation: Daily rotation, 30-day retention, 10MB max per file
- Run correlation: Bind run_id to trace operations across components
- Performance timing: Decorators for measuring operation duration

Configuration (Environment Variables):
- LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- LOG_FORMAT: "json" or "console" for console output (default: console)
- LOG_DIR: Directory for log files (default: logs/)
- LOG_FILE_ENABLED: "true" or "false" to enable file logging (default: true)
- LOG_RETENTION_DAYS: Days to keep old logs (default: 30)
- LOG_MAX_BYTES: Max bytes per log file before rotation (default: 10MB)
"""

import functools
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar

import structlog


# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "console").lower()  # "json" or "console"
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE_ENABLED = os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


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
    event_dict["timestamp_unix"] = time.time()
    return event_dict


def _ensure_log_dir() -> Path:
    """Ensure log directory exists and return path."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def _create_file_handler() -> logging.handlers.RotatingFileHandler:
    """
    Create a rotating file handler for JSON logs.

    Rotation strategy:
    - Rotates when file exceeds LOG_MAX_BYTES (default 10MB)
    - Keeps LOG_RETENTION_DAYS worth of backup files (default 30)
    - Uses .json extension for machine parsing
    """
    log_dir = _ensure_log_dir()
    log_file = log_dir / "app.log"

    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    handler.setLevel(get_log_level())

    # JSON format for file output (machine-readable)
    handler.setFormatter(logging.Formatter("%(message)s"))

    return handler


def _create_timed_file_handler() -> logging.handlers.TimedRotatingFileHandler:
    """
    Create a time-based rotating file handler for daily logs.

    Rotation strategy:
    - Rotates at midnight daily
    - Keeps LOG_RETENTION_DAYS worth of backup files
    - Adds date suffix to rotated files
    """
    log_dir = _ensure_log_dir()
    log_file = log_dir / "app.log"

    handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    handler.setLevel(get_log_level())
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.suffix = "%Y-%m-%d"

    return handler


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Call this once at application startup (e.g., in main.py or app.py).

    Sets up:
    - Console output (colored in dev, JSON in prod)
    - File output with daily rotation (JSON format)
    - Standard library logging integration
    """
    # Shared processors for all outputs
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Processors that prepare for final rendering
    pre_chain = shared_processors + [
        structlog.processors.format_exc_info,
    ]

    # Configure standard library logging with handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level())

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(get_log_level())

    if LOG_FORMAT == "json":
        # JSON console output for production
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=pre_chain,
            )
        )
    else:
        # Colored console output for development
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(colors=True),
                foreign_pre_chain=pre_chain,
            )
        )

    root_logger.addHandler(console_handler)

    # File handler (always JSON for machine parsing)
    if LOG_FILE_ENABLED:
        file_handler = _create_timed_file_handler()
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=pre_chain,
            )
        )
        root_logger.addHandler(file_handler)

    # Configure structlog to use stdlib logging
    structlog.configure(
        processors=pre_chain + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
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


def bind_run_context(run_id: str, **extra: Any) -> None:
    """
    Bind a run_id to all subsequent logs in this context.

    Use this at the start of a pipeline run to correlate all logs.

    Args:
        run_id: Unique identifier for this run
        **extra: Additional context (e.g., source_id, agent_id)

    Example:
        bind_run_context(run_id="abc-123", source_id="civicclerk", agent_id="A1")
    """
    bind_context(run_id=run_id, **extra)


def log_timing(operation: str | None = None) -> Callable[[F], F]:
    """
    Decorator to log function execution time.

    Args:
        operation: Optional name for the operation (defaults to function name)

    Example:
        @log_timing("scrape_meetings")
        def scrape_meetings(self):
            ...

    Logs:
        - Start of operation (DEBUG level)
        - End of operation with duration_ms (INFO level)
        - Errors with duration_ms (ERROR level)
    """
    def decorator(func: F) -> F:
        op_name = operation or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            start_time = time.perf_counter()

            logger.debug(f"Starting {op_name}")

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"Completed {op_name}",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    status="success",
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Failed {op_name}",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        return wrapper  # type: ignore
    return decorator


def log_timing_async(operation: str | None = None) -> Callable[[F], F]:
    """
    Async version of log_timing decorator.

    Example:
        @log_timing_async("fetch_data")
        async def fetch_data(self):
            ...
    """
    def decorator(func: F) -> F:
        op_name = operation or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            start_time = time.perf_counter()

            logger.debug(f"Starting {op_name}")

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"Completed {op_name}",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    status="success",
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Failed {op_name}",
                    operation=op_name,
                    duration_ms=round(duration_ms, 2),
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        return wrapper  # type: ignore
    return decorator


class LogContext:
    """
    Context manager for scoped logging with automatic timing.

    Example:
        with LogContext("process_meetings", source_id="civicclerk") as ctx:
            # do work
            ctx.log.info("Processing item", item_id=123)
        # Automatically logs duration on exit
    """

    def __init__(self, operation: str, **context: Any):
        self.operation = operation
        self.context = context
        self.log = get_logger(operation, **context)
        self.start_time: float = 0

    def __enter__(self) -> "LogContext":
        self.start_time = time.perf_counter()
        self.log.info(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type is None:
            self.log.info(
                f"Completed {self.operation}",
                duration_ms=round(duration_ms, 2),
                status="success",
            )
        else:
            self.log.error(
                f"Failed {self.operation}",
                duration_ms=round(duration_ms, 2),
                status="error",
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None,
            )


def get_log_stats() -> dict[str, Any]:
    """
    Get current logging configuration stats.

    Useful for debugging and health checks.
    """
    return {
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT,
        "log_dir": str(LOG_DIR),
        "file_enabled": LOG_FILE_ENABLED,
        "retention_days": LOG_RETENTION_DAYS,
        "max_bytes": LOG_MAX_BYTES,
        "configured": _configured,
    }


# Auto-configure on import if not already configured
_configured = False


def ensure_configured() -> None:
    """Ensure logging is configured (idempotent)."""
    global _configured
    if not _configured:
        configure_logging()
        _configured = True
