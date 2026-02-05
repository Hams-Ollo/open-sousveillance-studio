"""
Source adapters for converting scraper output to CivicEvents.

Each adapter transforms source-specific data structures into the
unified CivicEvent model, enabling cross-source queries and analysis.
"""

from src.intelligence.adapters.civicclerk_adapter import CivicClerkAdapter
from src.intelligence.adapters.srwmd_adapter import SRWMDAdapter
from src.intelligence.adapters.florida_notices_adapter import FloridaNoticesAdapter

__all__ = [
    "CivicClerkAdapter",
    "SRWMDAdapter",
    "FloridaNoticesAdapter",
]
