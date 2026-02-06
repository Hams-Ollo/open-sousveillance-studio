"""
Event Store for persisting and querying CivicEvents.

Provides storage, retrieval, and query capabilities for the unified
event model, enabling "what's new" queries and change detection.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from src.intelligence.models import CivicEvent, EventType, AlertSeverity
from src.logging_config import get_logger

logger = get_logger("intelligence.event_store")


class EventStore:
    """
    Persistent storage for CivicEvents.

    Currently uses file-based JSON storage for simplicity.
    Can be extended to use Supabase/PostgreSQL for production.

    Features:
    - Save and retrieve events by ID
    - Query events by time range, source, tags
    - Detect new vs updated events
    - "What's new" queries
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the event store.

        Args:
            storage_path: Path to JSON storage file. Defaults to
                         config/events.json
        """
        if storage_path is None:
            project_root = Path(__file__).parent.parent.parent
            storage_path = project_root / "config" / "events.json"

        self.storage_path = Path(storage_path)
        self._events: Dict[str, CivicEvent] = {}
        self._load()

    def _load(self) -> None:
        """Load events from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for event_data in data.get("events", []):
                    try:
                        event = CivicEvent.from_dict(event_data)
                        self._events[event.event_id] = event
                    except Exception as e:
                        logger.warning(
                            "Failed to load event",
                            event_id=event_data.get("event_id"),
                            error=str(e)
                        )

                logger.debug(
                    "Loaded events from storage",
                    count=len(self._events),
                    path=str(self.storage_path)
                )
            except Exception as e:
                logger.error("Failed to load event store", error=str(e))
                self._events = {}
        else:
            logger.debug("No existing event store found, starting fresh")

    def _save(self) -> None:
        """Save events to storage file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "last_updated": datetime.now().isoformat(),
                "event_count": len(self._events),
                "events": [e.to_dict() for e in self._events.values()]
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            logger.debug("Saved events to storage", count=len(self._events))
        except Exception as e:
            logger.error("Failed to save event store", error=str(e))

    def save_event(self, event: CivicEvent) -> tuple[bool, str]:
        """
        Save an event, detecting if it's new or updated.

        Args:
            event: CivicEvent to save

        Returns:
            Tuple of (is_new, status) where:
            - is_new: True if event is new, False if updated
            - status: "new", "updated", or "unchanged"
        """
        existing = self._events.get(event.event_id)

        if existing is None:
            # New event
            self._events[event.event_id] = event
            self._save()
            logger.info(
                "Saved new event",
                event_id=event.event_id,
                event_type=event.event_type.value
            )
            return True, "new"

        elif event.has_changed(existing):
            # Updated event
            event.discovered_at = existing.discovered_at  # Preserve original discovery
            event.updated_at = datetime.now()
            self._events[event.event_id] = event
            self._save()
            logger.info(
                "Updated existing event",
                event_id=event.event_id,
                old_hash=existing.content_hash,
                new_hash=event.content_hash
            )
            return False, "updated"

        else:
            # Unchanged
            return False, "unchanged"

    def save_events(self, events: List[CivicEvent]) -> Dict[str, int]:
        """
        Save multiple events, returning counts.

        Args:
            events: List of CivicEvents to save

        Returns:
            Dict with counts: {"new": N, "updated": N, "unchanged": N}
        """
        counts = {"new": 0, "updated": 0, "unchanged": 0}

        for event in events:
            _, status = self.save_event(event)
            counts[status] += 1

        logger.info(
            "Batch saved events",
            new=counts["new"],
            updated=counts["updated"],
            unchanged=counts["unchanged"]
        )

        return counts

    def get_event(self, event_id: str) -> Optional[CivicEvent]:
        """
        Get an event by ID.

        Args:
            event_id: Event identifier

        Returns:
            CivicEvent if found, None otherwise
        """
        return self._events.get(event_id)

    def get_events(
        self,
        source_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        tags: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[CivicEvent]:
        """
        Query events with filters.

        Args:
            source_id: Filter by source (e.g., "civicclerk-alachuafl")
            event_type: Filter by event type
            tags: Filter by tags (event must have ALL specified tags)
            since: Filter events with timestamp >= since
            until: Filter events with timestamp <= until
            limit: Maximum number of events to return

        Returns:
            List of matching CivicEvents, sorted by timestamp descending
        """
        results = list(self._events.values())

        # Apply filters
        if source_id:
            results = [e for e in results if e.source_id == source_id]

        if event_type:
            results = [e for e in results if e.event_type == event_type]

        if tags:
            results = [e for e in results if e.matches_tags(tags)]

        if since:
            results = [e for e in results if e.timestamp >= since]

        if until:
            results = [e for e in results if e.timestamp <= until]

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        if limit:
            results = results[:limit]

        return results

    def get_whats_new(
        self,
        hours: int = 24,
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[CivicEvent]:
        """
        Get events discovered in the last N hours.

        This is the primary "what's new" query for civic watchdog use.

        Args:
            hours: Number of hours to look back
            source_id: Optional source filter
            tags: Optional tag filter

        Returns:
            List of recently discovered events
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        results = [
            e for e in self._events.values()
            if e.discovered_at >= cutoff
        ]

        if source_id:
            results = [e for e in results if e.source_id == source_id]

        if tags:
            results = [e for e in results if e.matches_any_tag(tags)]

        results.sort(key=lambda e: e.discovered_at, reverse=True)

        return results

    def get_upcoming(
        self,
        days: int = 7,
        event_type: Optional[EventType] = None,
    ) -> List[CivicEvent]:
        """
        Get upcoming events (meetings, hearings) in the next N days.

        Args:
            days: Number of days to look ahead
            event_type: Optional event type filter

        Returns:
            List of upcoming events, sorted by timestamp ascending
        """
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        results = [
            e for e in self._events.values()
            if now <= e.timestamp <= cutoff
        ]

        if event_type:
            results = [e for e in results if e.event_type == event_type]

        results.sort(key=lambda e: e.timestamp)

        return results

    def get_by_entity(self, entity_name: str) -> List[CivicEvent]:
        """
        Find events mentioning a specific entity.

        Args:
            entity_name: Entity name to search for

        Returns:
            List of events with matching entities
        """
        normalized = entity_name.lower().strip()

        results = []
        for event in self._events.values():
            for entity in event.entities:
                if normalized in entity.normalized_name:
                    results.append(event)
                    break

        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results

    def get_by_county(self, county: str) -> List[CivicEvent]:
        """
        Find events in a specific county.

        Args:
            county: County name (e.g., "Alachua")

        Returns:
            List of events in that county
        """
        county_lower = county.lower()
        county_tag = county_lower.replace(" ", "-")

        results = []
        for event in self._events.values():
            # Check location
            if event.location and event.location.county:
                if event.location.county.lower() == county_lower:
                    results.append(event)
                    continue

            # Check tags
            if county_tag in event.tags or f"{county_tag}-county" in event.tags:
                results.append(event)

        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results

    def count_events(
        self,
        source_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
    ) -> int:
        """
        Count events matching filters.

        Args:
            source_id: Optional source filter
            event_type: Optional event type filter

        Returns:
            Number of matching events
        """
        count = 0
        for event in self._events.values():
            if source_id and event.source_id != source_id:
                continue
            if event_type and event.event_type != event_type:
                continue
            count += 1
        return count

    def get_sources(self) -> List[str]:
        """Get list of unique source IDs in the store."""
        return list(set(e.source_id for e in self._events.values()))

    def get_all_tags(self) -> List[str]:
        """Get list of all unique tags across events."""
        tags = set()
        for event in self._events.values():
            tags.update(event.tags)
        return sorted(tags)

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event by ID.

        Args:
            event_id: Event identifier

        Returns:
            True if deleted, False if not found
        """
        if event_id in self._events:
            del self._events[event_id]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Clear all events from the store."""
        self._events = {}
        self._save()
        logger.info("Cleared event store")

    def __len__(self) -> int:
        return len(self._events)

    def __contains__(self, event_id: str) -> bool:
        return event_id in self._events


# Singleton instance
import threading

_event_store: Optional[EventStore] = None
_event_store_lock = threading.Lock()


def get_event_store(storage_path: Optional[str] = None) -> EventStore:
    """
    Get the singleton EventStore instance.

    Args:
        storage_path: Optional custom storage path

    Returns:
        EventStore instance
    """
    global _event_store
    if _event_store is None:
        with _event_store_lock:
            if _event_store is None:
                _event_store = EventStore(storage_path)
    return _event_store
