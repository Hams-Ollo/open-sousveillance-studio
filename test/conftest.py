"""
Pytest configuration and fixtures for Alachua Civic Intelligence tests.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set test environment variables before importing app modules
os.environ.setdefault("GOOGLE_API_KEY", "test-api-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("LOG_FORMAT", "console")


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-api-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-firecrawl-key")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/test")


@pytest.fixture
def sample_scout_report():
    """Create a sample ScoutReport for testing."""
    from src.schemas import (
        ScoutReport, UrgencyAlert, UrgencyLevel, MeetingItem,
        CivicCategory, Significance,
    )

    return ScoutReport(
        report_id="A1-2026-01-30",
        period_covered="2026-01-30",
        executive_summary="Test summary of scout findings.",
        alerts=[
            UrgencyAlert(
                level=UrgencyLevel.YELLOW,
                action_item="Monitor upcoming meeting",
                context="Development proposal on agenda"
            )
        ],
        items=[
            MeetingItem(
                topic="Zoning Amendment Discussion",
                summary="Discussion of proposed zoning amendment for Tara Forest area.",
                category=CivicCategory.LAND_USE,
                significance=Significance.NOTABLE,
                related_to=["Tara Forest", "Development"],
                outcome=None,
                priority_flag=True,
                priority_reason="Matches watchlist keyword: Tara Forest",
                watchlist_matches=["Tara Forest"],
            )
        ]
    )


@pytest.fixture
def sample_analyst_report():
    """Create a sample AnalystReport for testing."""
    from src.schemas import AnalystReport, AnalysisSection, UrgencyAlert, UrgencyLevel

    return AnalystReport(
        report_id="B1-2026-01-30",
        period_covered="2026-01-25 to 2026-01-30",
        executive_summary="Analysis of development patterns.",
        topic="Tara Forest Development",
        scout_report_ids=["A1-2026-01-30"],
        sections=[
            AnalysisSection(
                title="Development Timeline",
                content="Analysis of project timeline and milestones.",
                sources=["County records", "Public meetings"],
                confidence=0.85
            )
        ],
        recommendations=["Monitor next BOCC meeting"],
        entities_mentioned=["Tara Development LLC"],
        alerts=[
            UrgencyAlert(
                level=UrgencyLevel.RED,
                action_item="Attend public hearing",
                context="Final vote scheduled"
            )
        ]
    )


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini LLM response."""
    mock = MagicMock()
    mock.content = "Test LLM response content"
    return mock


@pytest.fixture
def mock_firecrawl_response():
    """Mock Firecrawl scraping response."""
    return {
        "success": True,
        "data": {
            "markdown": "# Test Page\n\nThis is test content from a scraped page.",
            "metadata": {
                "title": "Test Page Title",
                "sourceURL": "https://example.com/test"
            }
        }
    }


@pytest.fixture
def config_dir(tmp_path):
    """Create temporary config directory with test YAML files."""
    config_path = tmp_path / "config"
    config_path.mkdir()

    # Create instance.yaml
    instance_yaml = """
instance:
  id: test-instance
  name: Test Instance
  timezone: America/New_York

jurisdiction:
  country: US
  state: FL
  state_name: Florida
  county: Test County

schedule:
  scouts:
    enabled: true
    cron: "0 6 * * *"
  analysts:
    enabled: true
    cron: "0 9 * * 1"
  synthesizers:
    enabled: true
    cron: "0 10 1 * *"
"""
    (config_path / "instance.yaml").write_text(instance_yaml)

    # Create sources.yaml
    sources_yaml = """
sources:
  - id: test-source
    name: Test Source
    jurisdiction: test-county
    url: https://example.com/meetings
    platform: civicplus
    priority: critical
    check_frequency: daily
    scraping:
      method: firecrawl
      requires_javascript: false
"""
    (config_path / "sources.yaml").write_text(sources_yaml)

    # Create entities.yaml
    entities_yaml = """
projects:
  - id: test-project
    name: Test Development
    urgency: yellow
    status: active
    keywords:
      - test
      - development
"""
    (config_path / "entities.yaml").write_text(entities_yaml)

    return config_path


@pytest.fixture
def app_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from src.app import app

    return TestClient(app)
