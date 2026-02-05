"""
CivicClerk adapter for converting meeting data to CivicEvents.

Transforms CivicClerkMeeting objects into the unified CivicEvent model.
"""

from datetime import datetime
from typing import List, Optional, Any

from src.intelligence.models import (
    CivicEvent,
    EventType,
    Entity,
    EntityType,
    Document,
)
from src.intelligence.adapters.base_adapter import BaseAdapter
from src.logging_config import get_logger

logger = get_logger("intelligence.adapters.civicclerk")


class CivicClerkAdapter(BaseAdapter):
    """
    Adapter for CivicClerk meeting portal data.
    
    Converts CivicClerkMeeting dataclass instances to CivicEvents,
    extracting entities and tags from meeting titles and descriptions.
    """
    
    def __init__(self, site_id: str = "alachuafl"):
        """
        Initialize the adapter.
        
        Args:
            site_id: CivicClerk site identifier (e.g., "alachuafl")
        """
        self.site_id = site_id
        self._source_id = f"civicclerk-{site_id}"
    
    @property
    def source_id(self) -> str:
        return self._source_id
    
    def adapt(self, meetings: List[Any]) -> List[CivicEvent]:
        """
        Convert CivicClerkMeeting objects to CivicEvents.
        
        Args:
            meetings: List of CivicClerkMeeting dataclass instances
            
        Returns:
            List of CivicEvent objects
        """
        events = []
        
        for meeting in meetings:
            try:
                event = self._convert_meeting(meeting)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(
                    "Failed to convert CivicClerk meeting",
                    meeting_id=getattr(meeting, 'meeting_id', 'unknown'),
                    error=str(e)
                )
        
        logger.info(
            "Adapted CivicClerk meetings to CivicEvents",
            input_count=len(meetings),
            output_count=len(events)
        )
        
        return events
    
    def _convert_meeting(self, meeting: Any) -> Optional[CivicEvent]:
        """Convert a single CivicClerkMeeting to CivicEvent."""
        # Extract meeting attributes
        meeting_id = getattr(meeting, 'meeting_id', None)
        title = getattr(meeting, 'title', 'Unknown Meeting')
        date = getattr(meeting, 'date', None)
        time = getattr(meeting, 'time', None)
        board = getattr(meeting, 'board', None)
        status = getattr(meeting, 'status', None)
        agenda_url = getattr(meeting, 'agenda_url', None)
        event_url = getattr(meeting, 'event_url', None)
        
        if not meeting_id:
            return None
        
        # Build event ID
        event_id = f"civicclerk-{self.site_id}-{meeting_id}"
        
        # Parse timestamp
        timestamp = self._parse_datetime(date, time)
        
        # Build description
        description_parts = []
        if board:
            description_parts.append(f"Board: {board}")
        if status:
            description_parts.append(f"Status: {status}")
        if time:
            description_parts.append(f"Time: {time}")
        description = " | ".join(description_parts) if description_parts else None
        
        # Extract entities from title
        entities = self.extract_entities_from_text(title)
        
        # Add board as government body entity
        if board:
            entities.append(Entity(
                entity_id=f"gov-{self._normalize_for_id(board)}",
                entity_type=EntityType.GOVERNMENT_BODY,
                name=board,
            ))
        
        # Extract tags
        tags = self.extract_tags_from_text(title)
        tags.append("meeting")
        tags.append("alachua-county")
        
        # Add board-specific tags
        if board:
            board_lower = board.lower()
            if "commission" in board_lower:
                tags.append("commission")
            if "planning" in board_lower:
                tags.append("planning")
            if "zoning" in board_lower:
                tags.append("zoning")
            if "school" in board_lower:
                tags.append("school-board")
        
        # Build documents list
        documents = []
        if agenda_url:
            documents.append(Document(
                document_id=f"agenda-{meeting_id}",
                title=f"Agenda - {title}",
                url=agenda_url,
                document_type="agenda",
            ))
        
        # Create CivicEvent
        event = CivicEvent(
            event_id=event_id,
            event_type=EventType.MEETING,
            source_id=self.source_id,
            timestamp=timestamp,
            title=title,
            description=description,
            entities=entities,
            documents=documents,
            tags=list(set(tags)),
            raw_data={
                "meeting_id": meeting_id,
                "board": board,
                "status": status,
                "time": time,
                "event_url": event_url,
            },
            metadata={
                "site_id": self.site_id,
                "has_agenda": agenda_url is not None,
            },
        )
        
        return event
    
    def _parse_datetime(self, date: Any, time: Optional[str] = None) -> datetime:
        """Parse date and optional time into datetime."""
        if isinstance(date, datetime):
            return date
        
        if isinstance(date, str):
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%B %d, %Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date, fmt)
                except ValueError:
                    continue
        
        # Fallback to now
        return datetime.now()
    
    def adapt_from_dict(self, meeting_dicts: List[dict]) -> List[CivicEvent]:
        """
        Convert meeting dictionaries to CivicEvents.
        
        Alternative entry point for when meetings are in dict form
        rather than dataclass instances.
        
        Args:
            meeting_dicts: List of meeting dictionaries
            
        Returns:
            List of CivicEvent objects
        """
        events = []
        
        for meeting_dict in meeting_dicts:
            try:
                event = self._convert_meeting_dict(meeting_dict)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(
                    "Failed to convert meeting dict",
                    error=str(e)
                )
        
        return events
    
    def _convert_meeting_dict(self, meeting: dict) -> Optional[CivicEvent]:
        """Convert a meeting dictionary to CivicEvent."""
        meeting_id = meeting.get('meeting_id') or meeting.get('id')
        if not meeting_id:
            return None
        
        title = meeting.get('title', 'Unknown Meeting')
        date = meeting.get('date')
        time = meeting.get('time')
        board = meeting.get('board')
        
        event_id = f"civicclerk-{self.site_id}-{meeting_id}"
        timestamp = self._parse_datetime(date, time)
        
        entities = self.extract_entities_from_text(title)
        if board:
            entities.append(Entity(
                entity_id=f"gov-{self._normalize_for_id(board)}",
                entity_type=EntityType.GOVERNMENT_BODY,
                name=board,
            ))
        
        tags = self.extract_tags_from_text(title)
        tags.extend(["meeting", "alachua-county"])
        
        documents = []
        if meeting.get('agenda_url'):
            documents.append(Document(
                document_id=f"agenda-{meeting_id}",
                title=f"Agenda - {title}",
                url=meeting['agenda_url'],
                document_type="agenda",
            ))
        
        return CivicEvent(
            event_id=event_id,
            event_type=EventType.MEETING,
            source_id=self.source_id,
            timestamp=timestamp,
            title=title,
            entities=entities,
            documents=documents,
            tags=list(set(tags)),
            raw_data=meeting,
        )
