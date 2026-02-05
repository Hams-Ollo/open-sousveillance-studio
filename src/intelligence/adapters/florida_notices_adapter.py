"""
Florida Notices adapter for converting public notice data to CivicEvents.

Transforms PublicNotice objects into the unified CivicEvent model.
"""

from datetime import datetime
from typing import List, Optional, Any

from src.intelligence.models import (
    CivicEvent,
    EventType,
    Entity,
    EntityType,
    Document,
    GeoLocation,
)
from src.intelligence.adapters.base_adapter import BaseAdapter
from src.logging_config import get_logger

logger = get_logger("intelligence.adapters.florida_notices")


class FloridaNoticesAdapter(BaseAdapter):
    """
    Adapter for Florida Public Notices data.
    
    Converts PublicNotice dataclass instances to CivicEvents,
    extracting entities and tags from notice content.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self._source_id = "florida-public-notices"
    
    @property
    def source_id(self) -> str:
        return self._source_id
    
    def adapt(self, notices: List[Any]) -> List[CivicEvent]:
        """
        Convert PublicNotice objects to CivicEvents.
        
        Args:
            notices: List of PublicNotice dataclass instances
            
        Returns:
            List of CivicEvent objects
        """
        events = []
        
        for notice in notices:
            try:
                event = self._convert_notice(notice)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(
                    "Failed to convert Florida notice",
                    notice_id=getattr(notice, 'notice_id', 'unknown'),
                    error=str(e)
                )
        
        logger.info(
            "Adapted Florida notices to CivicEvents",
            input_count=len(notices),
            output_count=len(events)
        )
        
        return events
    
    def _convert_notice(self, notice: Any) -> Optional[CivicEvent]:
        """Convert a single PublicNotice to CivicEvent."""
        # Extract notice attributes
        notice_id = getattr(notice, 'notice_id', None)
        title = getattr(notice, 'title', None)
        newspaper = getattr(notice, 'newspaper', None)
        county = getattr(notice, 'county', None)
        publication_date = getattr(notice, 'publication_date', None)
        category = getattr(notice, 'category', None)
        keywords = getattr(notice, 'keywords', [])
        content = getattr(notice, 'content', None)
        pdf_url = getattr(notice, 'pdf_url', None)
        detail_url = getattr(notice, 'detail_url', None)
        
        if not notice_id:
            return None
        
        # Build event ID
        event_id = f"florida-notice-{notice_id}"
        
        # Parse timestamp
        timestamp = self._parse_date(publication_date)
        
        # Build title (use notice title or generate from category)
        if not title:
            title = f"Public Notice - {category or 'General'}"
        
        # Build description
        description_parts = []
        if newspaper:
            description_parts.append(f"Published in: {newspaper}")
        if category:
            description_parts.append(f"Category: {category}")
        if keywords:
            description_parts.append(f"Keywords: {', '.join(keywords[:5])}")
        description = " | ".join(description_parts) if description_parts else None
        
        # Extract entities from title and content
        entities = []
        if title:
            entities.extend(self.extract_entities_from_text(title))
        if content:
            entities.extend(self.extract_entities_from_text(content[:1000]))
        
        # Build location
        location = None
        if county:
            location = GeoLocation(
                latitude=0.0,
                longitude=0.0,
                county=county,
            )
        
        # Build tags
        tags = ["public-notice", "legal-notice"]
        if county:
            tags.append(county.lower().replace(" ", "-"))
        if county and county.lower() == "alachua":
            tags.append("alachua-county")
        
        # Add category as tag
        if category:
            tags.append(self._normalize_for_id(category))
        
        # Add keyword-based tags
        if keywords:
            for kw in keywords[:10]:
                tag = self._normalize_for_id(kw)
                if len(tag) > 2:
                    tags.append(tag)
        
        # Extract additional tags from content
        if title:
            tags.extend(self.extract_tags_from_text(title))
        if content:
            tags.extend(self.extract_tags_from_text(content[:500]))
        
        # Build documents
        documents = []
        if pdf_url:
            documents.append(Document(
                document_id=f"pdf-{notice_id}",
                title=f"Notice PDF - {title[:50]}",
                url=pdf_url,
                document_type="pdf",
            ))
        
        # Create CivicEvent
        event = CivicEvent(
            event_id=event_id,
            event_type=EventType.PUBLIC_NOTICE,
            source_id=self.source_id,
            timestamp=timestamp,
            title=title,
            description=description,
            location=location,
            entities=entities,
            documents=documents,
            tags=list(set(tags)),
            raw_data={
                "notice_id": notice_id,
                "newspaper": newspaper,
                "county": county,
                "category": category,
                "keywords": keywords,
                "detail_url": detail_url,
            },
            metadata={
                "has_pdf": pdf_url is not None,
                "newspaper": newspaper,
            },
        )
        
        return event
    
    def _parse_date(self, date: Any) -> datetime:
        """Parse date into datetime."""
        if isinstance(date, datetime):
            return date
        
        if isinstance(date, str):
            formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%B %d, %Y",
                "%b %d, %Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date, fmt)
                except ValueError:
                    continue
        
        return datetime.now()
    
    def adapt_from_dict(self, notice_dicts: List[dict]) -> List[CivicEvent]:
        """
        Convert notice dictionaries to CivicEvents.
        
        Args:
            notice_dicts: List of notice dictionaries
            
        Returns:
            List of CivicEvent objects
        """
        events = []
        
        for notice_dict in notice_dicts:
            try:
                event = self._convert_notice_dict(notice_dict)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(
                    "Failed to convert notice dict",
                    error=str(e)
                )
        
        return events
    
    def _convert_notice_dict(self, notice: dict) -> Optional[CivicEvent]:
        """Convert a notice dictionary to CivicEvent."""
        notice_id = notice.get('notice_id') or notice.get('id')
        if not notice_id:
            return None
        
        title = notice.get('title', 'Public Notice')
        county = notice.get('county')
        publication_date = notice.get('publication_date')
        
        event_id = f"florida-notice-{notice_id}"
        timestamp = self._parse_date(publication_date)
        
        entities = self.extract_entities_from_text(title)
        
        tags = ["public-notice", "legal-notice"]
        if county:
            tags.append(county.lower().replace(" ", "-"))
        tags.extend(self.extract_tags_from_text(title))
        
        documents = []
        if notice.get('pdf_url'):
            documents.append(Document(
                document_id=f"pdf-{notice_id}",
                title=f"Notice PDF",
                url=notice['pdf_url'],
                document_type="pdf",
            ))
        
        location = None
        if county:
            location = GeoLocation(
                latitude=0.0,
                longitude=0.0,
                county=county,
            )
        
        return CivicEvent(
            event_id=event_id,
            event_type=EventType.PUBLIC_NOTICE,
            source_id=self.source_id,
            timestamp=timestamp,
            title=title,
            location=location,
            entities=entities,
            documents=documents,
            tags=list(set(tags)),
            raw_data=notice,
        )
