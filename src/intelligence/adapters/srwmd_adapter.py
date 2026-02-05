"""
SRWMD adapter for converting permit data to CivicEvents.

Transforms PermitNotice and PermitDetail objects into the unified CivicEvent model.
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

logger = get_logger("intelligence.adapters.srwmd")


class SRWMDAdapter(BaseAdapter):
    """
    Adapter for SRWMD (Suwannee River Water Management District) permit data.
    
    Converts PermitNotice dataclass instances to CivicEvents,
    distinguishing between applications and issuances.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self._source_id = "srwmd"
    
    @property
    def source_id(self) -> str:
        return self._source_id
    
    def adapt(self, notices: List[Any]) -> List[CivicEvent]:
        """
        Convert PermitNotice objects to CivicEvents.
        
        Args:
            notices: List of PermitNotice dataclass instances
            
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
                    "Failed to convert SRWMD notice",
                    notice_id=getattr(notice, 'notice_id', 'unknown'),
                    error=str(e)
                )
        
        logger.info(
            "Adapted SRWMD notices to CivicEvents",
            input_count=len(notices),
            output_count=len(events)
        )
        
        return events
    
    def _convert_notice(self, notice: Any) -> Optional[CivicEvent]:
        """Convert a single PermitNotice to CivicEvent."""
        # Extract notice attributes
        notice_id = getattr(notice, 'notice_id', None)
        notice_type = getattr(notice, 'notice_type', None)
        permit_number = getattr(notice, 'permit_number', None)
        project_name = getattr(notice, 'project_name', None)
        county = getattr(notice, 'county', None)
        rule_type = getattr(notice, 'rule_type', None)
        permit_type = getattr(notice, 'permit_type', None)
        date = getattr(notice, 'date', None)
        permit_url = getattr(notice, 'permit_url', None)
        
        if not notice_id or not permit_number:
            return None
        
        # Determine event type based on notice type
        notice_type_value = notice_type.value if hasattr(notice_type, 'value') else str(notice_type)
        if "issuance" in notice_type_value.lower():
            event_type = EventType.PERMIT_ISSUED
            source_suffix = "issuances"
        else:
            event_type = EventType.PERMIT_APPLICATION
            source_suffix = "applications"
        
        # Build event ID
        event_id = f"srwmd-{source_suffix}-{permit_number}"
        
        # Parse timestamp
        timestamp = date if isinstance(date, datetime) else datetime.now()
        
        # Build title
        title = f"{project_name or 'Permit'} ({permit_number})"
        
        # Build description
        description_parts = []
        if rule_type:
            description_parts.append(f"Type: {rule_type}")
        if county:
            description_parts.append(f"County: {county}")
        if permit_type:
            permit_type_value = permit_type.value if hasattr(permit_type, 'value') else str(permit_type)
            description_parts.append(f"Permit Type: {permit_type_value}")
        description = " | ".join(description_parts) if description_parts else None
        
        # Extract entities
        entities = []
        if project_name:
            entities.extend(self.extract_entities_from_text(project_name))
            # Add project as entity
            entities.append(Entity(
                entity_id=f"project-{self._normalize_for_id(project_name)}",
                entity_type=EntityType.PROJECT,
                name=project_name,
                metadata={"permit_number": permit_number},
            ))
        
        # Build location
        location = None
        if county:
            location = GeoLocation(
                latitude=0.0,
                longitude=0.0,
                county=county,
            )
        
        # Extract tags
        tags = ["permit", "srwmd", "water"]
        if county:
            tags.append(county.lower().replace(" ", "-"))
        if county and county.lower() == "alachua":
            tags.append("alachua-county")
        
        # Add permit type tags
        if rule_type:
            rule_lower = rule_type.lower()
            if "erp" in rule_lower:
                tags.append("erp")
            if "general" in rule_lower:
                tags.append("general-permit")
            if "individual" in rule_lower:
                tags.append("individual-permit")
        
        # Add environmental tags based on project name
        if project_name:
            tags.extend(self.extract_tags_from_text(project_name))
        
        # Build documents
        documents = []
        if permit_url:
            documents.append(Document(
                document_id=f"permit-{permit_number}",
                title=f"Permit Details - {permit_number}",
                url=permit_url,
                document_type="permit",
            ))
        
        # Create CivicEvent
        event = CivicEvent(
            event_id=event_id,
            event_type=event_type,
            source_id=f"{self.source_id}-{source_suffix}",
            timestamp=timestamp,
            title=title,
            description=description,
            location=location,
            entities=entities,
            documents=documents,
            tags=list(set(tags)),
            raw_data={
                "notice_id": notice_id,
                "permit_number": permit_number,
                "project_name": project_name,
                "county": county,
                "rule_type": rule_type,
                "notice_type": notice_type_value,
            },
            metadata={
                "permit_url": permit_url,
            },
        )
        
        return event
    
    def adapt_with_details(self, notices: List[Any], details: dict) -> List[CivicEvent]:
        """
        Convert notices with enriched detail data.
        
        Args:
            notices: List of PermitNotice objects
            details: Dict mapping permit_number to PermitDetail objects
            
        Returns:
            List of CivicEvent objects with enriched data
        """
        events = []
        
        for notice in notices:
            try:
                event = self._convert_notice(notice)
                if not event:
                    continue
                
                # Enrich with detail data if available
                permit_number = getattr(notice, 'permit_number', None)
                if permit_number and permit_number in details:
                    detail = details[permit_number]
                    event = self._enrich_with_detail(event, detail)
                
                events.append(event)
                
            except Exception as e:
                logger.warning(
                    "Failed to convert SRWMD notice with details",
                    error=str(e)
                )
        
        return events
    
    def _enrich_with_detail(self, event: CivicEvent, detail: Any) -> CivicEvent:
        """Enrich a CivicEvent with PermitDetail data."""
        # Extract detail attributes
        description = getattr(detail, 'description', None)
        applicant = getattr(detail, 'applicant', None)
        owner = getattr(detail, 'owner', None)
        consultant = getattr(detail, 'consultant', None)
        documents = getattr(detail, 'documents', [])
        
        # Update description
        if description:
            event.description = description
        
        # Add entities from detail
        if applicant:
            event.add_entity(Entity(
                entity_id=f"org-{self._normalize_for_id(applicant)}",
                entity_type=EntityType.ORGANIZATION,
                name=applicant,
                metadata={"role": "applicant"},
            ))
        
        if owner:
            event.add_entity(Entity(
                entity_id=f"person-{self._normalize_for_id(owner)}",
                entity_type=EntityType.PERSON,
                name=owner,
                metadata={"role": "owner"},
            ))
        
        if consultant:
            event.add_entity(Entity(
                entity_id=f"org-{self._normalize_for_id(consultant)}",
                entity_type=EntityType.ORGANIZATION,
                name=consultant,
                metadata={"role": "consultant"},
            ))
        
        # Add documents from detail
        for doc in documents:
            doc_title = getattr(doc, 'title', None) or doc.get('title', 'Document')
            doc_url = getattr(doc, 'url', None) or doc.get('url')
            doc_id = getattr(doc, 'document_id', None) or doc.get('document_id', f"doc-{len(event.documents)}")
            
            event.documents.append(Document(
                document_id=doc_id,
                title=doc_title,
                url=doc_url,
                document_type="permit_document",
            ))
        
        # Recompute content hash
        event.content_hash = event._compute_hash()
        
        return event
