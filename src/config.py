"""
Open Sousveillance Studio - Configuration Module
=================================================
Loads and validates YAML configuration files for modular multi-jurisdiction support.

Configuration Files:
- config/instance.yaml   : Instance identity, jurisdiction, scheduling
- config/sources.yaml    : Data sources to monitor
- config/entities.yaml   : Watchlist entities and keywords

Environment Variables:
- GOOGLE_API_KEY        : Required - Gemini API key
- TAVILY_API_KEY        : Optional - Tavily search API
- FIRECRAWL_API_KEY     : Optional - Firecrawl scraping
- SUPABASE_URL          : Required - Supabase project URL
- SUPABASE_KEY          : Required - Supabase anon/service key
- RESEND_API_KEY        : Optional - Email delivery via Resend
- DISCORD_WEBHOOK_URL   : Optional - Discord notifications
"""

import os
from pathlib import Path
from typing import Any, Optional
from functools import lru_cache

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load env vars from .env file
load_dotenv()


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
PROMPT_LIB_DIR = BASE_DIR / "prompt_library"
OUTPUT_DIR = BASE_DIR / "outputs"

# Ensure output directories exist
(OUTPUT_DIR / "daily").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "weekly").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "monthly").mkdir(parents=True, exist_ok=True)


# =============================================================================
# API KEYS (from environment variables)
# =============================================================================

class APIKeys(BaseModel):
    """API keys loaded from environment variables."""
    
    google_api_key: str = Field(description="Gemini API key (required)")
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily search API key")
    firecrawl_api_key: Optional[str] = Field(default=None, description="Firecrawl scraping API key")
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase anon/service key")
    resend_api_key: Optional[str] = Field(default=None, description="Resend email API key")
    discord_webhook_url: Optional[str] = Field(default=None, description="Discord webhook URL")


def load_api_keys() -> APIKeys:
    """Load API keys from environment variables."""
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    
    return APIKeys(
        google_api_key=google_key,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        resend_api_key=os.getenv("RESEND_API_KEY"),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
    )


# =============================================================================
# YAML CONFIGURATION LOADING
# =============================================================================

def load_yaml_file(filename: str) -> dict[str, Any]:
    """Load a YAML configuration file from the config directory."""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_instance_config() -> dict[str, Any]:
    """Load instance configuration (cached)."""
    return load_yaml_file("instance.yaml")


@lru_cache(maxsize=1)
def load_sources_config() -> dict[str, Any]:
    """Load sources configuration (cached)."""
    return load_yaml_file("sources.yaml")


@lru_cache(maxsize=1)
def load_entities_config() -> dict[str, Any]:
    """Load entities configuration (cached)."""
    return load_yaml_file("entities.yaml")


# =============================================================================
# PYDANTIC MODELS FOR CONFIGURATION
# =============================================================================

class InstanceOperator(BaseModel):
    """Operator/maintainer of this instance."""
    name: str
    email: Optional[str] = None
    website: Optional[str] = None


class InstanceIdentity(BaseModel):
    """Instance identity configuration."""
    id: str = Field(description="Unique instance identifier")
    name: str = Field(description="Human-readable instance name")
    description: Optional[str] = None
    timezone: str = Field(default="America/New_York")
    operator: Optional[InstanceOperator] = None


class Municipality(BaseModel):
    """A municipality within the jurisdiction."""
    name: str
    type: str = "city"
    population: Optional[int] = None
    primary: bool = False


class Jurisdiction(BaseModel):
    """Geographic scope of monitoring."""
    country: str = "US"
    state: str
    state_name: Optional[str] = None
    county: str
    county_fips: Optional[str] = None
    municipalities: list[Municipality] = []
    include_unincorporated: bool = True


class ScheduleConfig(BaseModel):
    """Schedule configuration for an agent type."""
    enabled: bool = True
    cron: str = Field(description="Cron expression for scheduling")
    retry_on_failure: bool = True
    max_retries: int = 3
    requires_approval: bool = False


class Schedule(BaseModel):
    """Scheduling configuration for all agent types."""
    scouts: ScheduleConfig = ScheduleConfig(cron="0 6 * * *")
    analysts: ScheduleConfig = ScheduleConfig(cron="0 9 * * 1", requires_approval=True)
    synthesizers: ScheduleConfig = ScheduleConfig(cron="0 10 1 * *", requires_approval=True)


class ScrapingConfig(BaseModel):
    """Scraping configuration for a source."""
    method: str = Field(description="playwright, beautifulsoup, firecrawl, api")
    requires_javascript: bool = False
    wait_for_selector: Optional[str] = None
    intercept_api: bool = False


class BoardConfig(BaseModel):
    """Configuration for a board/committee to monitor."""
    name: str
    keywords: list[str] = []
    priority: str = "medium"


class SourceConfig(BaseModel):
    """Configuration for a data source."""
    id: str
    name: str
    description: Optional[str] = None
    jurisdiction: str
    url: str
    platform: str
    priority: str = "medium"
    check_frequency: str = "daily"
    scraping: ScrapingConfig
    document_types: list[str] = []
    boards: list[BoardConfig] = []
    notes: Optional[str] = None


class ProjectEntity(BaseModel):
    """A project entity to watch."""
    id: str
    name: str
    description: Optional[str] = None
    urgency: str = "yellow"
    status: str = "active"
    aliases: list[str] = []
    keywords: list[str] = []
    related_organizations: list[str] = []
    related_people: list[str] = []
    related_locations: list[str] = []
    first_detected: Optional[str] = None
    notes: Optional[str] = None


class OrganizationEntity(BaseModel):
    """An organization entity to watch."""
    id: str
    name: str
    type: str = "organization"
    urgency: str = "yellow"
    aliases: list[str] = []
    keywords: list[str] = []
    principals: list[str] = []
    sunbiz_id: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# UNIFIED CONFIGURATION CLASS
# =============================================================================

class AppConfig(BaseModel):
    """
    Unified application configuration.
    
    Combines all YAML configs and API keys into a single validated object.
    """
    
    # API keys from environment
    api_keys: APIKeys
    
    # Instance configuration
    instance: InstanceIdentity
    jurisdiction: Jurisdiction
    schedule: Schedule
    
    # Paths
    base_dir: Path = BASE_DIR
    config_dir: Path = CONFIG_DIR
    output_dir: Path = OUTPUT_DIR
    prompt_lib_dir: Path = PROMPT_LIB_DIR
    
    class Config:
        arbitrary_types_allowed = True


def build_app_config() -> AppConfig:
    """
    Build the complete application configuration.
    
    Loads all YAML files, validates with Pydantic, and combines with API keys.
    """
    api_keys = load_api_keys()
    instance_data = load_instance_config()
    
    return AppConfig(
        api_keys=api_keys,
        instance=InstanceIdentity(**instance_data.get("instance", {})),
        jurisdiction=Jurisdiction(**instance_data.get("jurisdiction", {})),
        schedule=Schedule(**instance_data.get("schedule", {})),
    )


def get_all_sources() -> list[SourceConfig]:
    """
    Get all configured sources across all tiers.
    
    Returns a flat list of SourceConfig objects.
    """
    sources_data = load_sources_config()
    all_sources = []
    
    # Iterate through all tier keys (updated to match sources.yaml structure)
    tier_keys = [
        "tier_1_municipal",     # City level
        "tier_2_county",        # County level
        "tier_3_regional",      # Water management districts
        "tier_4_legal",         # Legal notices & public records
        "tier_5_civic",         # News & civic organizations
        "tier_6_state",         # Florida state government
        "tier_7_federal",       # US federal government
    ]
    
    for tier_key in tier_keys:
        tier_sources = sources_data.get(tier_key, [])
        for source in tier_sources:
            # Make a copy to avoid mutating cached data
            source_copy = source.copy()
            # Parse scraping config
            if "scraping" in source_copy:
                source_copy["scraping"] = ScrapingConfig(**source_copy["scraping"])
            # Parse board configs
            if "boards" in source_copy:
                source_copy["boards"] = [BoardConfig(**b) for b in source_copy["boards"]]
            all_sources.append(SourceConfig(**source_copy))
    
    return all_sources


def get_sources_by_tier(tier: int) -> list[SourceConfig]:
    """
    Get sources filtered by tier number (1-7).
    
    Tier 1: Municipal, Tier 2: County, Tier 3: Regional,
    Tier 4: Legal, Tier 5: Civic, Tier 6: State, Tier 7: Federal
    """
    tier_map = {
        1: "tier_1_municipal",
        2: "tier_2_county",
        3: "tier_3_regional",
        4: "tier_4_legal",
        5: "tier_5_civic",
        6: "tier_6_state",
        7: "tier_7_federal",
    }
    tier_key = tier_map.get(tier)
    if not tier_key:
        return []
    
    sources_data = load_sources_config()
    tier_sources = sources_data.get(tier_key, [])
    result = []
    for source in tier_sources:
        source_copy = source.copy()
        if "scraping" in source_copy:
            source_copy["scraping"] = ScrapingConfig(**source_copy["scraping"])
        if "boards" in source_copy:
            source_copy["boards"] = [BoardConfig(**b) for b in source_copy["boards"]]
        result.append(SourceConfig(**source_copy))
    return result


def get_sources_by_priority(priority: str) -> list[SourceConfig]:
    """Get sources filtered by priority level."""
    return [s for s in get_all_sources() if s.priority == priority]


def get_projects() -> list[ProjectEntity]:
    """Get all project entities from the watchlist."""
    entities_data = load_entities_config()
    return [ProjectEntity(**p) for p in entities_data.get("projects", [])]


def get_organizations() -> list[OrganizationEntity]:
    """Get all organization entities from the watchlist."""
    entities_data = load_entities_config()
    return [OrganizationEntity(**o) for o in entities_data.get("organizations", [])]


def get_all_keywords() -> set[str]:
    """
    Get all keywords from projects and organizations for matching.
    
    Returns a deduplicated set of all keywords and aliases.
    """
    keywords = set()
    
    for project in get_projects():
        keywords.update(project.keywords)
        keywords.update(project.aliases)
    
    for org in get_organizations():
        keywords.update(org.keywords)
        keywords.update(org.aliases)
    
    return keywords


def clear_config_cache() -> None:
    """Clear cached configuration (useful for testing or hot-reload)."""
    load_instance_config.cache_clear()
    load_sources_config.cache_clear()
    load_entities_config.cache_clear()


# =============================================================================
# LEGACY EXPORTS (for backwards compatibility)
# =============================================================================
# These will be deprecated in favor of the unified AppConfig

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validate required key on import
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")
