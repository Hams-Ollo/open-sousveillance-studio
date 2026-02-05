"""
Scraper Health Monitoring System.

Provides health tracking for scrapers with:
- Success/failure recording
- Health status computation (healthy/degraded/failing)
- Automatic retry with exponential backoff
- JSON persistence for survival across restarts
- Alert generation for degraded scrapers

Configuration:
- HEALTH_FILE: Path to health persistence file (default: config/scraper_health.json)
- HEALTH_WINDOW_HOURS: Hours to consider for success rate (default: 24)
- HEALTH_WINDOW_ATTEMPTS: Max attempts to consider (default: 20)
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Callable, TypeVar
import functools

from src.logging_config import get_logger

logger = get_logger("intelligence.health")


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_HEALTH_FILE = Path("config/scraper_health.json")
HEALTH_WINDOW_HOURS = 24
HEALTH_WINDOW_ATTEMPTS = 20

# Health thresholds
HEALTHY_SUCCESS_RATE = 0.90  # 90%+ = healthy
DEGRADED_SUCCESS_RATE = 0.50  # 50-90% = degraded, <50% = failing
MAX_CONSECUTIVE_FAILURES = 5  # More than this = failing

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 60.0
BACKOFF_MULTIPLIER = 2.0


# =============================================================================
# ENUMS
# =============================================================================

class HealthStatus(str, Enum):
    """Health status of a scraper."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"  # No data yet


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ScrapeAttempt:
    """Record of a single scrape attempt."""
    timestamp: datetime
    success: bool
    items_found: int = 0
    duration_ms: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "items_found": self.items_found,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScrapeAttempt":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            success=data["success"],
            items_found=data.get("items_found", 0),
            duration_ms=data.get("duration_ms", 0.0),
            error_type=data.get("error_type"),
            error_message=data.get("error_message"),
        )


@dataclass
class ScraperHealth:
    """Health status and metrics for a scraper."""
    scraper_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    consecutive_failures: int = 0
    total_attempts: int = 0
    attempts: list[ScrapeAttempt] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scraper_id": self.scraper_id,
            "status": self.status.value,
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "consecutive_failures": self.consecutive_failures,
            "total_attempts": self.total_attempts,
            "attempts": [a.to_dict() for a in self.attempts],
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScraperHealth":
        """Create from dictionary."""
        return cls(
            scraper_id=data["scraper_id"],
            status=HealthStatus(data.get("status", "unknown")),
            success_rate=data.get("success_rate", 0.0),
            avg_duration_ms=data.get("avg_duration_ms", 0.0),
            last_success=datetime.fromisoformat(data["last_success"]) if data.get("last_success") else None,
            last_failure=datetime.fromisoformat(data["last_failure"]) if data.get("last_failure") else None,
            last_attempt=datetime.fromisoformat(data["last_attempt"]) if data.get("last_attempt") else None,
            consecutive_failures=data.get("consecutive_failures", 0),
            total_attempts=data.get("total_attempts", 0),
            attempts=[ScrapeAttempt.from_dict(a) for a in data.get("attempts", [])],
        )
    
    @property
    def recent_errors(self) -> list[str]:
        """Get recent error messages."""
        return [
            a.error_message for a in self.attempts[-5:]
            if not a.success and a.error_message
        ]
    
    @property
    def needs_attention(self) -> bool:
        """Check if scraper needs manual attention."""
        return self.status == HealthStatus.FAILING


@dataclass
class HealthAlert:
    """Alert generated when scraper health degrades."""
    scraper_id: str
    previous_status: HealthStatus
    current_status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scraper_id": self.scraper_id,
            "previous_status": self.previous_status.value,
            "current_status": self.current_status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# HEALTH SERVICE
# =============================================================================

class HealthService:
    """
    Central service for tracking scraper health.
    
    Features:
    - Records scrape attempts (success/failure)
    - Computes health status based on recent history
    - Persists health data to JSON file
    - Generates alerts on status changes
    - Provides retry logic with exponential backoff
    
    Example:
        health = HealthService()
        
        # Record a successful scrape
        health.record_scrape(
            scraper_id="civicclerk",
            success=True,
            items_found=15,
            duration_ms=1234.5
        )
        
        # Check health
        status = health.get_health("civicclerk")
        print(status.status)  # HealthStatus.HEALTHY
    """
    
    def __init__(self, health_file: Path | str | None = None):
        """
        Initialize health service.
        
        Args:
            health_file: Path to JSON file for persistence.
                        Defaults to config/scraper_health.json
        """
        self.health_file = Path(health_file) if health_file else DEFAULT_HEALTH_FILE
        self._health_data: dict[str, ScraperHealth] = {}
        self._alerts: list[HealthAlert] = []
        self._load()
    
    def _load(self) -> None:
        """Load health data from file."""
        if self.health_file.exists():
            try:
                data = json.loads(self.health_file.read_text(encoding="utf-8"))
                for scraper_id, health_dict in data.get("scrapers", {}).items():
                    self._health_data[scraper_id] = ScraperHealth.from_dict(health_dict)
                logger.info(
                    "Loaded health data",
                    scrapers=len(self._health_data),
                    file=str(self.health_file)
                )
            except Exception as e:
                logger.warning(
                    "Failed to load health data, starting fresh",
                    error=str(e)
                )
                self._health_data = {}
    
    def _save(self) -> None:
        """Save health data to file."""
        try:
            self.health_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "scrapers": {
                    scraper_id: health.to_dict()
                    for scraper_id, health in self._health_data.items()
                },
                "last_updated": datetime.now().isoformat(),
            }
            self.health_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error("Failed to save health data", error=str(e))
    
    def _prune_old_attempts(self, health: ScraperHealth) -> None:
        """Remove attempts outside the health window."""
        cutoff = datetime.now() - timedelta(hours=HEALTH_WINDOW_HOURS)
        
        # Keep attempts within time window, up to max count
        recent = [a for a in health.attempts if a.timestamp > cutoff]
        health.attempts = recent[-HEALTH_WINDOW_ATTEMPTS:]
    
    def _compute_status(self, health: ScraperHealth) -> HealthStatus:
        """Compute health status from recent attempts."""
        if not health.attempts:
            return HealthStatus.UNKNOWN
        
        # Check consecutive failures first (immediate signal)
        if health.consecutive_failures > MAX_CONSECUTIVE_FAILURES:
            return HealthStatus.FAILING
        
        # Compute success rate
        successes = sum(1 for a in health.attempts if a.success)
        health.success_rate = successes / len(health.attempts)
        
        # Compute average duration
        durations = [a.duration_ms for a in health.attempts if a.duration_ms > 0]
        health.avg_duration_ms = sum(durations) / len(durations) if durations else 0.0
        
        # Determine status
        if health.success_rate >= HEALTHY_SUCCESS_RATE and health.consecutive_failures < 3:
            return HealthStatus.HEALTHY
        elif health.success_rate >= DEGRADED_SUCCESS_RATE:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.FAILING
    
    def record_scrape(
        self,
        scraper_id: str,
        success: bool,
        items_found: int = 0,
        duration_ms: float = 0.0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> ScraperHealth:
        """
        Record a scrape attempt and update health status.
        
        Args:
            scraper_id: Identifier for the scraper
            success: Whether the scrape succeeded
            items_found: Number of items found (0 for failures)
            duration_ms: How long the scrape took
            error_type: Exception type if failed
            error_message: Error message if failed
        
        Returns:
            Updated ScraperHealth for this scraper
        """
        # Get or create health record
        if scraper_id not in self._health_data:
            self._health_data[scraper_id] = ScraperHealth(scraper_id=scraper_id)
        
        health = self._health_data[scraper_id]
        previous_status = health.status
        
        # Create attempt record
        attempt = ScrapeAttempt(
            timestamp=datetime.now(),
            success=success,
            items_found=items_found,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message,
        )
        
        # Update health record
        health.attempts.append(attempt)
        health.total_attempts += 1
        health.last_attempt = attempt.timestamp
        
        if success:
            health.last_success = attempt.timestamp
            health.consecutive_failures = 0
        else:
            health.last_failure = attempt.timestamp
            health.consecutive_failures += 1
        
        # Prune old attempts and recompute status
        self._prune_old_attempts(health)
        health.status = self._compute_status(health)
        
        # Log the attempt
        log_method = logger.info if success else logger.warning
        log_method(
            "Scrape attempt recorded",
            scraper_id=scraper_id,
            success=success,
            items_found=items_found,
            duration_ms=round(duration_ms, 2),
            status=health.status.value,
            consecutive_failures=health.consecutive_failures,
        )
        
        # Check for status change and generate alert
        if previous_status != health.status and previous_status != HealthStatus.UNKNOWN:
            self._generate_alert(scraper_id, previous_status, health.status)
        
        # Persist
        self._save()
        
        return health
    
    def _generate_alert(
        self,
        scraper_id: str,
        previous: HealthStatus,
        current: HealthStatus
    ) -> None:
        """Generate alert for status change."""
        # Determine if this is a degradation or recovery
        status_order = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.FAILING: 2,
            HealthStatus.UNKNOWN: -1,
        }
        
        is_degradation = status_order[current] > status_order[previous]
        
        if is_degradation:
            message = f"Scraper '{scraper_id}' degraded from {previous.value} to {current.value}"
            logger.warning(
                "Scraper health degraded",
                scraper_id=scraper_id,
                previous_status=previous.value,
                current_status=current.value,
            )
        else:
            message = f"Scraper '{scraper_id}' recovered from {previous.value} to {current.value}"
            logger.info(
                "Scraper health recovered",
                scraper_id=scraper_id,
                previous_status=previous.value,
                current_status=current.value,
            )
        
        alert = HealthAlert(
            scraper_id=scraper_id,
            previous_status=previous,
            current_status=current,
            message=message,
        )
        self._alerts.append(alert)
    
    def get_health(self, scraper_id: str) -> ScraperHealth:
        """
        Get health status for a scraper.
        
        Args:
            scraper_id: Identifier for the scraper
        
        Returns:
            ScraperHealth with current status and metrics
        """
        if scraper_id not in self._health_data:
            return ScraperHealth(scraper_id=scraper_id, status=HealthStatus.UNKNOWN)
        return self._health_data[scraper_id]
    
    def get_all_health(self) -> dict[str, ScraperHealth]:
        """Get health status for all known scrapers."""
        return self._health_data.copy()
    
    def get_alerts(self, since: Optional[datetime] = None) -> list[HealthAlert]:
        """
        Get health alerts.
        
        Args:
            since: Only return alerts after this time
        
        Returns:
            List of HealthAlert objects
        """
        if since:
            return [a for a in self._alerts if a.timestamp > since]
        return self._alerts.copy()
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self._alerts.clear()
    
    def get_scrapers_needing_attention(self) -> list[str]:
        """Get list of scrapers that need manual attention."""
        return [
            scraper_id
            for scraper_id, health in self._health_data.items()
            if health.needs_attention
        ]
    
    def reset_health(self, scraper_id: str) -> None:
        """
        Reset health data for a scraper.
        
        Use after manual intervention to give scraper a fresh start.
        """
        if scraper_id in self._health_data:
            del self._health_data[scraper_id]
            self._save()
            logger.info("Reset health data", scraper_id=scraper_id)
    
    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of all scraper health.
        
        Returns:
            Dictionary with health summary for API/dashboard
        """
        scrapers = []
        for scraper_id, health in self._health_data.items():
            scrapers.append({
                "scraper_id": scraper_id,
                "status": health.status.value,
                "success_rate": round(health.success_rate * 100, 1),
                "avg_duration_ms": round(health.avg_duration_ms, 2),
                "last_attempt": health.last_attempt.isoformat() if health.last_attempt else None,
                "consecutive_failures": health.consecutive_failures,
                "needs_attention": health.needs_attention,
            })
        
        # Count by status
        status_counts = {s.value: 0 for s in HealthStatus}
        for health in self._health_data.values():
            status_counts[health.status.value] += 1
        
        return {
            "total_scrapers": len(self._health_data),
            "status_counts": status_counts,
            "scrapers": scrapers,
            "alerts_pending": len(self._alerts),
            "scrapers_needing_attention": self.get_scrapers_needing_attention(),
        }


# =============================================================================
# RETRY DECORATOR
# =============================================================================

F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    scraper_id: str,
    health_service: Optional[HealthService] = None,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF_SECONDS,
    max_backoff: float = MAX_BACKOFF_SECONDS,
    backoff_multiplier: float = BACKOFF_MULTIPLIER,
) -> Callable[[F], F]:
    """
    Decorator for automatic retry with exponential backoff.
    
    Records attempts to health service and retries on failure.
    
    Args:
        scraper_id: Identifier for health tracking
        health_service: HealthService instance (uses global if None)
        max_retries: Maximum retry attempts
        initial_backoff: Initial wait time in seconds
        max_backoff: Maximum wait time in seconds
        backoff_multiplier: Multiplier for each retry
    
    Example:
        @with_retry("civicclerk")
        def scrape_meetings(self):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            service = health_service or get_health_service()
            backoff = initial_backoff
            last_error: Optional[Exception] = None
            
            for attempt in range(max_retries + 1):
                start_time = time.perf_counter()
                
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Record success
                    items_found = len(result) if hasattr(result, "__len__") else 1
                    service.record_scrape(
                        scraper_id=scraper_id,
                        success=True,
                        items_found=items_found,
                        duration_ms=duration_ms,
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    last_error = e
                    
                    # Record failure
                    service.record_scrape(
                        scraper_id=scraper_id,
                        success=False,
                        duration_ms=duration_ms,
                        error_type=type(e).__name__,
                        error_message=str(e)[:500],  # Truncate long messages
                    )
                    
                    # Check if we should retry
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} after {backoff:.1f}s",
                            scraper_id=scraper_id,
                            error=str(e)[:200],
                        )
                        time.sleep(backoff)
                        backoff = min(backoff * backoff_multiplier, max_backoff)
                    else:
                        logger.error(
                            "Max retries exceeded",
                            scraper_id=scraper_id,
                            attempts=max_retries + 1,
                            error=str(e),
                        )
            
            # All retries exhausted
            raise last_error  # type: ignore
        
        return wrapper  # type: ignore
    return decorator


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_health_service: Optional[HealthService] = None


def get_health_service(health_file: Path | str | None = None) -> HealthService:
    """
    Get the global HealthService instance.
    
    Args:
        health_file: Optional path to health file (only used on first call)
    
    Returns:
        HealthService singleton
    """
    global _health_service
    if _health_service is None:
        _health_service = HealthService(health_file)
    return _health_service


def reset_health_service() -> None:
    """Reset the global HealthService (for testing)."""
    global _health_service
    _health_service = None
