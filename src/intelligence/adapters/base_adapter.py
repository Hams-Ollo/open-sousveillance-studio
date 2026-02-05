"""
Base adapter class for source-to-CivicEvent conversion.

All source adapters inherit from this base class to ensure
consistent behavior and interface.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict

from src.intelligence.models import (
    CivicEvent,
    Entity,
    EntityType,
    Document,
    GeoLocation,
)
from src.logging_config import get_logger

logger = get_logger("intelligence.adapters")


class BaseAdapter(ABC):
    """
    Abstract base class for source adapters.
    
    Subclasses must implement:
    - adapt(): Convert source-specific items to CivicEvents
    - source_id: Property returning the source identifier
    """
    
    @property
    @abstractmethod
    def source_id(self) -> str:
        """Return the source identifier for this adapter."""
        pass
    
    @abstractmethod
    def adapt(self, items: List[Any]) -> List[CivicEvent]:
        """
        Convert source-specific items to CivicEvents.
        
        Args:
            items: List of source-specific data objects
            
        Returns:
            List of CivicEvent objects
        """
        pass
    
    def extract_entities_from_text(self, text: str) -> List[Entity]:
        """
        Extract entities from text using basic patterns.
        
        This is a simple implementation that can be enhanced
        with NLP/NER in Phase 3.6.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted Entity objects
        """
        entities = []
        
        if not text:
            return entities
        
        # Extract organization patterns (LLC, Inc, Corp, etc.)
        org_patterns = [
            r'\b([A-Z][A-Za-z\s]+(?:LLC|Inc|Corp|Corporation|Company|Co|Ltd|LP|LLP)\.?)\b',
            r'\b([A-Z][A-Za-z\s]+(?:Development|Properties|Builders|Construction|Realty))\b',
        ]
        
        for pattern in org_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                name = match.strip()
                if len(name) > 3:
                    entity_id = f"org-{self._normalize_for_id(name)}"
                    entities.append(Entity(
                        entity_id=entity_id,
                        entity_type=EntityType.ORGANIZATION,
                        name=name,
                    ))
        
        # Extract address patterns
        address_pattern = r'\b(\d+\s+[A-Z][A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct)\.?(?:\s+[A-Z]{2}\s+\d{5})?)\b'
        address_matches = re.findall(address_pattern, text, re.IGNORECASE)
        for match in address_matches:
            address = match.strip()
            if len(address) > 10:
                entity_id = f"addr-{self._normalize_for_id(address)}"
                entities.append(Entity(
                    entity_id=entity_id,
                    entity_type=EntityType.ADDRESS,
                    name=address,
                ))
        
        return entities
    
    def extract_tags_from_text(self, text: str) -> List[str]:
        """
        Extract relevant tags from text based on keywords.
        
        Args:
            text: Text to extract tags from
            
        Returns:
            List of tag strings
        """
        tags = []
        
        if not text:
            return tags
        
        text_lower = text.lower()
        
        # Civic watchdog keywords
        keyword_tags = {
            "rezoning": ["rezone", "rezoning", "zoning change", "land use change"],
            "development": ["development", "subdivision", "plat", "site plan"],
            "environmental": ["environmental", "wetland", "aquifer", "water quality", "stormwater"],
            "permit": ["permit", "application", "approval"],
            "public-hearing": ["public hearing", "public comment", "public notice"],
            "budget": ["budget", "appropriation", "funding", "expenditure"],
            "variance": ["variance", "exception", "waiver"],
            "annexation": ["annexation", "annex"],
            "comprehensive-plan": ["comprehensive plan", "comp plan", "future land use"],
            "water": ["water", "well", "aquifer", "groundwater", "santa fe river"],
        }
        
        for tag, keywords in keyword_tags.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def _normalize_for_id(self, text: str) -> str:
        """Normalize text for use in IDs."""
        normalized = text.lower().strip()
        normalized = re.sub(r'[^a-z0-9]+', '-', normalized)
        normalized = normalized.strip('-')
        return normalized[:50]
    
    def _create_document(
        self,
        doc_id: str,
        title: str,
        url: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> Document:
        """Helper to create a Document object."""
        return Document(
            document_id=doc_id,
            title=title,
            url=url,
            document_type=doc_type,
        )
