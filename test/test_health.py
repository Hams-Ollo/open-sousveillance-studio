"""
Unit tests for the Scraper Health Monitoring System.

Tests cover:
- ScrapeAttempt and ScraperHealth dataclasses
- HealthService recording and status computation
- Health status transitions (healthy → degraded → failing)
- Alert generation on status changes
- Persistence (save/load from JSON)
- Retry decorator with backoff
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.intelligence.health import (
    ScrapeAttempt,
    ScraperHealth,
    HealthService,
    HealthStatus,
    HealthAlert,
    with_retry,
    get_health_service,
    reset_health_service,
    HEALTHY_SUCCESS_RATE,
    DEGRADED_SUCCESS_RATE,
    MAX_CONSECUTIVE_FAILURES,
)


class TestScrapeAttempt:
    """Tests for ScrapeAttempt dataclass."""
    
    def test_create_successful_attempt(self):
        """Test creating a successful scrape attempt."""
        attempt = ScrapeAttempt(
            timestamp=datetime.now(),
            success=True,
            items_found=15,
            duration_ms=1234.5,
        )
        
        assert attempt.success is True
        assert attempt.items_found == 15
        assert attempt.duration_ms == 1234.5
        assert attempt.error_type is None
        assert attempt.error_message is None
    
    def test_create_failed_attempt(self):
        """Test creating a failed scrape attempt."""
        attempt = ScrapeAttempt(
            timestamp=datetime.now(),
            success=False,
            duration_ms=500.0,
            error_type="TimeoutError",
            error_message="Connection timed out",
        )
        
        assert attempt.success is False
        assert attempt.items_found == 0
        assert attempt.error_type == "TimeoutError"
        assert attempt.error_message == "Connection timed out"
    
    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        original = ScrapeAttempt(
            timestamp=datetime(2026, 2, 2, 12, 0, 0),
            success=True,
            items_found=10,
            duration_ms=999.9,
        )
        
        data = original.to_dict()
        restored = ScrapeAttempt.from_dict(data)
        
        assert restored.timestamp == original.timestamp
        assert restored.success == original.success
        assert restored.items_found == original.items_found
        assert restored.duration_ms == original.duration_ms


class TestScraperHealth:
    """Tests for ScraperHealth dataclass."""
    
    def test_create_empty_health(self):
        """Test creating health record with no attempts."""
        health = ScraperHealth(scraper_id="test-scraper")
        
        assert health.scraper_id == "test-scraper"
        assert health.status == HealthStatus.UNKNOWN
        assert health.success_rate == 0.0
        assert health.total_attempts == 0
        assert len(health.attempts) == 0
    
    def test_recent_errors_property(self):
        """Test recent_errors extracts error messages."""
        health = ScraperHealth(scraper_id="test")
        health.attempts = [
            ScrapeAttempt(datetime.now(), success=True, items_found=5),
            ScrapeAttempt(datetime.now(), success=False, error_message="Error 1"),
            ScrapeAttempt(datetime.now(), success=False, error_message="Error 2"),
            ScrapeAttempt(datetime.now(), success=True, items_found=3),
        ]
        
        errors = health.recent_errors
        assert len(errors) == 2
        assert "Error 1" in errors
        assert "Error 2" in errors
    
    def test_needs_attention_when_failing(self):
        """Test needs_attention is True when status is FAILING."""
        health = ScraperHealth(scraper_id="test", status=HealthStatus.FAILING)
        assert health.needs_attention is True
        
        health.status = HealthStatus.HEALTHY
        assert health.needs_attention is False
    
    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        original = ScraperHealth(
            scraper_id="test-scraper",
            status=HealthStatus.HEALTHY,
            success_rate=0.95,
            avg_duration_ms=500.0,
            last_success=datetime(2026, 2, 2, 12, 0, 0),
            consecutive_failures=0,
            total_attempts=20,
        )
        
        data = original.to_dict()
        restored = ScraperHealth.from_dict(data)
        
        assert restored.scraper_id == original.scraper_id
        assert restored.status == original.status
        assert restored.success_rate == original.success_rate


class TestHealthService:
    """Tests for HealthService."""
    
    @pytest.fixture
    def temp_health_file(self, tmp_path):
        """Create a temporary health file path."""
        return tmp_path / "test_health.json"
    
    @pytest.fixture
    def health_service(self, temp_health_file):
        """Create a fresh HealthService for testing."""
        return HealthService(health_file=temp_health_file)
    
    def test_record_successful_scrape(self, health_service):
        """Test recording a successful scrape."""
        health = health_service.record_scrape(
            scraper_id="test-scraper",
            success=True,
            items_found=10,
            duration_ms=500.0,
        )
        
        assert health.total_attempts == 1
        assert health.consecutive_failures == 0
        assert health.last_success is not None
        assert len(health.attempts) == 1
    
    def test_record_failed_scrape(self, health_service):
        """Test recording a failed scrape."""
        health = health_service.record_scrape(
            scraper_id="test-scraper",
            success=False,
            duration_ms=100.0,
            error_type="ConnectionError",
            error_message="Failed to connect",
        )
        
        assert health.total_attempts == 1
        assert health.consecutive_failures == 1
        assert health.last_failure is not None
        assert health.attempts[0].error_type == "ConnectionError"
    
    def test_consecutive_failures_reset_on_success(self, health_service):
        """Test that consecutive failures reset after success."""
        # Record some failures
        for _ in range(3):
            health_service.record_scrape("test", success=False)
        
        health = health_service.get_health("test")
        assert health.consecutive_failures == 3
        
        # Record a success
        health = health_service.record_scrape("test", success=True, items_found=5)
        assert health.consecutive_failures == 0
    
    def test_status_healthy_when_high_success_rate(self, health_service):
        """Test status is HEALTHY with high success rate."""
        # Record 10 successes
        for _ in range(10):
            health_service.record_scrape("test", success=True, items_found=5)
        
        health = health_service.get_health("test")
        assert health.status == HealthStatus.HEALTHY
        assert health.success_rate >= HEALTHY_SUCCESS_RATE
    
    def test_status_degraded_with_some_failures(self, health_service):
        """Test status is DEGRADED with moderate failure rate."""
        # Record 7 successes and 3 failures (70% success rate)
        for _ in range(7):
            health_service.record_scrape("test", success=True, items_found=5)
        for _ in range(3):
            health_service.record_scrape("test", success=False)
        
        health = health_service.get_health("test")
        assert health.status == HealthStatus.DEGRADED
    
    def test_status_failing_with_many_consecutive_failures(self, health_service):
        """Test status is FAILING with many consecutive failures."""
        # Record successes first
        for _ in range(5):
            health_service.record_scrape("test", success=True, items_found=5)
        
        # Then many consecutive failures
        for _ in range(MAX_CONSECUTIVE_FAILURES + 1):
            health_service.record_scrape("test", success=False)
        
        health = health_service.get_health("test")
        assert health.status == HealthStatus.FAILING
    
    def test_alert_generated_on_status_change(self, health_service):
        """Test that alerts are generated when status changes."""
        # Start healthy
        for _ in range(10):
            health_service.record_scrape("test", success=True, items_found=5)
        
        assert len(health_service.get_alerts()) == 0
        
        # Degrade to failing
        for _ in range(MAX_CONSECUTIVE_FAILURES + 1):
            health_service.record_scrape("test", success=False)
        
        alerts = health_service.get_alerts()
        assert len(alerts) > 0
        assert any(a.scraper_id == "test" for a in alerts)
    
    def test_get_all_health(self, health_service):
        """Test getting health for all scrapers."""
        health_service.record_scrape("scraper-1", success=True, items_found=5)
        health_service.record_scrape("scraper-2", success=True, items_found=3)
        health_service.record_scrape("scraper-3", success=False)
        
        all_health = health_service.get_all_health()
        
        assert len(all_health) == 3
        assert "scraper-1" in all_health
        assert "scraper-2" in all_health
        assert "scraper-3" in all_health
    
    def test_get_scrapers_needing_attention(self, health_service):
        """Test identifying scrapers that need attention."""
        # Create a healthy scraper
        for _ in range(10):
            health_service.record_scrape("healthy-scraper", success=True, items_found=5)
        
        # Create a failing scraper
        for _ in range(MAX_CONSECUTIVE_FAILURES + 1):
            health_service.record_scrape("failing-scraper", success=False)
        
        needing_attention = health_service.get_scrapers_needing_attention()
        
        assert "failing-scraper" in needing_attention
        assert "healthy-scraper" not in needing_attention
    
    def test_reset_health(self, health_service):
        """Test resetting health data for a scraper."""
        health_service.record_scrape("test", success=True, items_found=5)
        assert "test" in health_service.get_all_health()
        
        health_service.reset_health("test")
        
        health = health_service.get_health("test")
        assert health.status == HealthStatus.UNKNOWN
    
    def test_persistence_save_and_load(self, temp_health_file):
        """Test that health data persists across service instances."""
        # Create service and record data
        service1 = HealthService(health_file=temp_health_file)
        service1.record_scrape("test", success=True, items_found=10, duration_ms=500)
        service1.record_scrape("test", success=True, items_found=8, duration_ms=600)
        
        # Create new service instance (simulates restart)
        service2 = HealthService(health_file=temp_health_file)
        
        health = service2.get_health("test")
        assert health.total_attempts == 2
        assert len(health.attempts) == 2
    
    def test_get_summary(self, health_service):
        """Test getting health summary."""
        health_service.record_scrape("scraper-1", success=True, items_found=5)
        health_service.record_scrape("scraper-2", success=False)
        
        summary = health_service.get_summary()
        
        assert "total_scrapers" in summary
        assert "status_counts" in summary
        assert "scrapers" in summary
        assert summary["total_scrapers"] == 2


class TestHealthAlert:
    """Tests for HealthAlert dataclass."""
    
    def test_create_alert(self):
        """Test creating a health alert."""
        alert = HealthAlert(
            scraper_id="test-scraper",
            previous_status=HealthStatus.HEALTHY,
            current_status=HealthStatus.DEGRADED,
            message="Scraper degraded",
        )
        
        assert alert.scraper_id == "test-scraper"
        assert alert.previous_status == HealthStatus.HEALTHY
        assert alert.current_status == HealthStatus.DEGRADED
    
    def test_to_dict(self):
        """Test alert serialization."""
        alert = HealthAlert(
            scraper_id="test",
            previous_status=HealthStatus.HEALTHY,
            current_status=HealthStatus.FAILING,
            message="Test message",
        )
        
        data = alert.to_dict()
        
        assert data["scraper_id"] == "test"
        assert data["previous_status"] == "healthy"
        assert data["current_status"] == "failing"


class TestWithRetryDecorator:
    """Tests for the with_retry decorator."""
    
    def test_successful_function_no_retry(self, tmp_path):
        """Test that successful functions don't retry."""
        health_service = HealthService(health_file=tmp_path / "health.json")
        call_count = 0
        
        @with_retry("test-scraper", health_service=health_service, max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return ["item1", "item2"]
        
        result = successful_function()
        
        assert call_count == 1
        assert result == ["item1", "item2"]
        
        health = health_service.get_health("test-scraper")
        assert health.total_attempts == 1
        assert health.consecutive_failures == 0
    
    def test_failing_function_retries(self, tmp_path):
        """Test that failing functions retry."""
        health_service = HealthService(health_file=tmp_path / "health.json")
        call_count = 0
        
        @with_retry(
            "test-scraper",
            health_service=health_service,
            max_retries=2,
            initial_backoff=0.01,  # Fast for testing
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Should have tried 3 times (1 initial + 2 retries)
        assert call_count == 3
        
        health = health_service.get_health("test-scraper")
        assert health.total_attempts == 3
        assert health.consecutive_failures == 3
    
    def test_function_succeeds_after_retry(self, tmp_path):
        """Test that function can succeed after initial failures."""
        health_service = HealthService(health_file=tmp_path / "health.json")
        call_count = 0
        
        @with_retry(
            "test-scraper",
            health_service=health_service,
            max_retries=3,
            initial_backoff=0.01,
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return ["success"]
        
        result = flaky_function()
        
        assert call_count == 3
        assert result == ["success"]
        
        health = health_service.get_health("test-scraper")
        # 2 failures + 1 success
        assert health.total_attempts == 3


class TestGlobalHealthService:
    """Tests for global health service singleton."""
    
    def test_get_health_service_singleton(self):
        """Test that get_health_service returns singleton."""
        reset_health_service()
        
        service1 = get_health_service()
        service2 = get_health_service()
        
        assert service1 is service2
        
        reset_health_service()
    
    def test_reset_health_service(self):
        """Test that reset clears the singleton."""
        reset_health_service()
        
        service1 = get_health_service()
        reset_health_service()
        service2 = get_health_service()
        
        assert service1 is not service2
        
        reset_health_service()
