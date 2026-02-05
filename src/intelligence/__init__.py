"""
Intelligence Layer for Open Sousveillance Studio.

This module provides the event-driven intelligence capabilities:
- CivicEvent: Unified event model normalizing all scraper output
- Adapters: Convert source-specific data to CivicEvents
- EventStore: Persist and query events
- RulesEngine: Watchdog alerts based on configurable rules
- Health: Scraper health monitoring
"""

from src.intelligence.models import (
    CivicEvent,
    EventType,
    Entity,
    EntityType,
    Document,
    GeoLocation,
    Alert,
    AlertSeverity,
)
from src.intelligence.event_store import EventStore, get_event_store
from src.intelligence.rules_engine import Rule, RulesEngine, get_rules_engine
from src.intelligence.health import (
    HealthService,
    HealthStatus,
    ScraperHealth,
    ScrapeAttempt,
    HealthAlert,
    get_health_service,
    with_retry,
)

__all__ = [
    "CivicEvent",
    "EventType",
    "Entity",
    "EntityType",
    "Document",
    "GeoLocation",
    "Alert",
    "AlertSeverity",
    "EventStore",
    "get_event_store",
    "Rule",
    "RulesEngine",
    "get_rules_engine",
    "HealthService",
    "HealthStatus",
    "ScraperHealth",
    "ScrapeAttempt",
    "HealthAlert",
    "get_health_service",
    "with_retry",
]
