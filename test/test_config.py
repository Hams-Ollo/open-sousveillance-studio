"""
Tests for configuration module.
"""

import os
import pytest
from pathlib import Path


class TestAPIKeys:
    """Tests for API key loading."""
    
    def test_load_api_keys_success(self, mock_env_vars):
        """Test successful API key loading."""
        from src.config import load_api_keys
        
        keys = load_api_keys()
        
        assert keys.google_api_key == "test-google-api-key"
        assert keys.tavily_api_key == "test-tavily-key"
        assert keys.firecrawl_api_key == "test-firecrawl-key"
        assert keys.supabase_url == "https://test.supabase.co"
        assert keys.supabase_key == "test-supabase-key"
    
    def test_load_api_keys_missing_google_key(self, monkeypatch):
        """Test error when GOOGLE_API_KEY is missing."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        
        from src.config import load_api_keys
        
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            load_api_keys()


class TestYAMLLoading:
    """Tests for YAML configuration loading."""
    
    def test_load_yaml_file_not_found(self):
        """Test error when YAML file doesn't exist."""
        from src.config import load_yaml_file
        
        with pytest.raises(FileNotFoundError):
            load_yaml_file("nonexistent.yaml")
    
    def test_load_instance_config(self):
        """Test loading instance configuration."""
        from src.config import load_instance_config
        
        config = load_instance_config()
        
        assert "instance" in config
        assert "jurisdiction" in config


class TestPydanticModels:
    """Tests for Pydantic configuration models."""
    
    def test_instance_identity_model(self):
        """Test InstanceIdentity model validation."""
        from src.config import InstanceIdentity
        
        instance = InstanceIdentity(
            id="test-id",
            name="Test Instance",
            timezone="America/New_York"
        )
        
        assert instance.id == "test-id"
        assert instance.name == "Test Instance"
        assert instance.timezone == "America/New_York"
    
    def test_jurisdiction_model(self):
        """Test Jurisdiction model validation."""
        from src.config import Jurisdiction
        
        jurisdiction = Jurisdiction(
            state="FL",
            county="Alachua"
        )
        
        assert jurisdiction.state == "FL"
        assert jurisdiction.county == "Alachua"
        assert jurisdiction.country == "US"  # default
    
    def test_source_config_model(self):
        """Test SourceConfig model validation."""
        from src.config import SourceConfig, ScrapingConfig
        
        source = SourceConfig(
            id="test-source",
            name="Test Source",
            jurisdiction="alachua-county",
            url="https://example.com",
            platform="civicplus",
            priority="critical",
            scraping=ScrapingConfig(method="firecrawl")
        )
        
        assert source.id == "test-source"
        assert source.priority == "critical"
        assert source.scraping.method == "firecrawl"
    
    def test_schedule_config_defaults(self):
        """Test ScheduleConfig default values."""
        from src.config import ScheduleConfig
        
        config = ScheduleConfig(cron="0 6 * * *")
        
        assert config.enabled is True
        assert config.retry_on_failure is True
        assert config.max_retries == 3
        assert config.requires_approval is False
