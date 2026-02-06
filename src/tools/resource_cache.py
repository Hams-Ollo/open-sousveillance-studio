"""
Discovered Resources Cache
===========================

Simple utility for scrapers to read and update discovered resources.
Scrapers use this to:
1. Start with known event/permit IDs (faster than full discovery)
2. Persist newly discovered IDs for future runs

Usage:
    from src.tools.resource_cache import ResourceCache

    cache = ResourceCache()

    # Get known event IDs for CivicClerk
    event_ids = cache.get_ids("alachua-civicclerk", "event_ids")

    # After scraping, add newly discovered IDs
    cache.add_ids("alachua-civicclerk", "event_ids", [842, 843, 844])
    cache.save()
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import yaml

from src.logging_config import get_logger

logger = get_logger(__name__)


class ResourceCache:
    """Manages discovered resources cache for scrapers."""

    DEFAULT_PATH = Path(__file__).parent.parent.parent / "config" / "discovered_resources.yaml"

    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize resource cache.

        Args:
            cache_path: Path to cache file (defaults to config/discovered_resources.yaml)
        """
        self.cache_path = cache_path or self.DEFAULT_PATH
        self._data: Dict[str, Any] = {}
        self._dirty = False
        self._load()

    def _load(self):
        """Load cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self._data = yaml.safe_load(f) or {}
                logger.debug(f"Loaded resource cache from {self.cache_path}")
            except Exception as e:
                logger.warning(f"Failed to load resource cache: {e}")
                self._data = {}
        else:
            logger.info(f"No resource cache found at {self.cache_path}, starting fresh")
            self._data = {}

    def save(self):
        """Save cache to disk if modified."""
        if not self._dirty:
            return

        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)
            self._dirty = False
            logger.debug(f"Saved resource cache to {self.cache_path}")
        except Exception as e:
            logger.error(f"Failed to save resource cache: {e}")

    def get_source(self, source_id: str) -> Dict[str, Any]:
        """Get all data for a source."""
        return self._data.get(source_id, {})

    def get_ids(self, source_id: str, id_type: str) -> List[Any]:
        """
        Get list of IDs for a source.

        Args:
            source_id: Source identifier (e.g., "alachua-civicclerk")
            id_type: Type of IDs (e.g., "event_ids", "permit_ids", "document_ids")

        Returns:
            List of IDs, empty list if not found
        """
        source = self._data.get(source_id, {})
        return source.get(id_type, [])

    def get_pattern(self, source_id: str, pattern_name: str = "url_pattern") -> Optional[str]:
        """
        Get URL pattern for a source.

        Args:
            source_id: Source identifier
            pattern_name: Pattern key (e.g., "url_pattern", "document_pattern")

        Returns:
            URL pattern string or None
        """
        source = self._data.get(source_id, {})
        return source.get(pattern_name)

    def add_ids(self, source_id: str, id_type: str, new_ids: List[Any]):
        """
        Add new IDs to cache (deduplicates automatically).

        Args:
            source_id: Source identifier
            id_type: Type of IDs
            new_ids: List of new IDs to add
        """
        if source_id not in self._data:
            self._data[source_id] = {}

        existing = set(self._data[source_id].get(id_type, []))
        new_set = set(new_ids)
        added = new_set - existing

        if added:
            self._data[source_id][id_type] = list(existing | new_set)
            self._data[source_id]["last_updated"] = datetime.now().isoformat()
            self._dirty = True
            logger.info(f"Added {len(added)} new {id_type} to {source_id}")

    def set_ids(self, source_id: str, id_type: str, ids: List[Any]):
        """
        Replace all IDs for a source (use for full refresh).

        Args:
            source_id: Source identifier
            id_type: Type of IDs
            ids: Complete list of IDs
        """
        if source_id not in self._data:
            self._data[source_id] = {}

        self._data[source_id][id_type] = ids
        self._data[source_id]["last_updated"] = datetime.now().isoformat()
        self._dirty = True

    def build_url(self, source_id: str, pattern_name: str = "url_pattern", **kwargs) -> Optional[str]:
        """
        Build a URL from pattern and parameters.

        Args:
            source_id: Source identifier
            pattern_name: Pattern key
            **kwargs: Parameters to substitute (e.g., id=838)

        Returns:
            Formatted URL or None if pattern not found

        Example:
            cache.build_url("alachua-civicclerk", id=838)
            # Returns: https://alachuafl.portal.civicclerk.com/event/838/files
        """
        pattern = self.get_pattern(source_id, pattern_name)
        if not pattern:
            return None

        try:
            return pattern.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing parameter {e} for pattern {pattern}")
            return None

    def build_urls(self, source_id: str, id_type: str, pattern_name: str = "url_pattern", id_param: str = "id") -> List[str]:
        """
        Build URLs for all known IDs.

        Args:
            source_id: Source identifier
            id_type: Type of IDs to use
            pattern_name: Pattern key
            id_param: Parameter name for ID in pattern

        Returns:
            List of formatted URLs

        Example:
            cache.build_urls("alachua-civicclerk", "event_ids")
            # Returns: [
            #   "https://alachuafl.portal.civicclerk.com/event/838/files",
            #   "https://alachuafl.portal.civicclerk.com/event/795/files",
            #   ...
            # ]
        """
        ids = self.get_ids(source_id, id_type)
        pattern = self.get_pattern(source_id, pattern_name)

        if not pattern or not ids:
            return []

        urls = []
        for id_val in ids:
            try:
                urls.append(pattern.format(**{id_param: id_val}))
            except KeyError:
                continue

        return urls

    def get_last_updated(self, source_id: str) -> Optional[str]:
        """Get last updated timestamp for a source."""
        source = self._data.get(source_id, {})
        return source.get("last_updated")

    def list_sources(self) -> List[str]:
        """List all source IDs in cache."""
        return [k for k in self._data.keys() if not k.startswith("_")]


# Singleton instance for convenience
import threading

_cache_instance: Optional[ResourceCache] = None
_cache_lock = threading.Lock()


def get_resource_cache() -> ResourceCache:
    """Get singleton ResourceCache instance."""
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = ResourceCache()
    return _cache_instance
