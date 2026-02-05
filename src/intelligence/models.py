"""
Core data models for the Intelligence Layer.

Defines the unified CivicEvent model that normalizes output from all scrapers,
enabling cross-source queries, change detection, and watchdog alerts.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class EventType(str, Enum):
    """Types of civic events tracked by the system."""
    MEETING = "meeting"
    PERMIT_APPLICATION = "permit_application"
    PERMIT_ISSUED = "permit_issued"
    PUBLIC_NOTICE = "public_notice"
    AGENDA_POSTED = "agenda_posted"
    DOCUMENT_ADDED = "document_added"


class EntityType(str, Enum):
    """Types of entities that can be extracted from events."""
    PERSON = "person"
    ORGANIZATION = "organization"
    ADDRESS = "address"
    PARCEL = "parcel"
    PROJECT = "project"
    GOVERNMENT_BODY = "government_body"


class AlertSeverity(str, Enum):
    """Severity levels for watchdog alerts."""
    INFO = "info"
    NOTABLE = "notable"
    WARNING = "warning"
    URGENT = "urgent"


@dataclass
class GeoLocation:
    """Geographic location for spatial queries."""
    latitude: float
    longitude: float
    address: Optional[str] = None
    county: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "county": self.county,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeoLocation":
        return cls(
            latitude=data["latitude"],
            longitude=data["longitude"],
            address=data.get("address"),
            county=data.get("county"),
        )


@dataclass
class Entity:
    """
    An entity extracted from civic events.
    
    Entities enable cross-source linking by identifying people,
    organizations, addresses, and projects across different sources.
    """
    entity_id: str
    entity_type: EntityType
    name: str
    normalized_name: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.normalized_name is None:
            self.normalized_name = self._normalize(self.name)
    
    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize entity name for matching."""
        return name.lower().strip().replace(",", "").replace(".", "")
    
    def matches(self, other: "Entity") -> bool:
        """Check if this entity matches another (fuzzy)."""
        if self.entity_type != other.entity_type:
            return False
        if self.normalized_name == other.normalized_name:
            return True
        if self.normalized_name in other.aliases or other.normalized_name in self.aliases:
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "aliases": self.aliases,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            entity_id=data["entity_id"],
            entity_type=EntityType(data["entity_type"]),
            name=data["name"],
            normalized_name=data.get("normalized_name"),
            aliases=data.get("aliases", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Document:
    """A document attached to a civic event."""
    document_id: str
    title: str
    url: Optional[str] = None
    document_type: Optional[str] = None
    file_size: Optional[int] = None
    content_hash: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "url": self.url,
            "document_type": self.document_type,
            "file_size": self.file_size,
            "content_hash": self.content_hash,
            "extracted_text": self.extracted_text,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        return cls(
            document_id=data["document_id"],
            title=data["title"],
            url=data.get("url"),
            document_type=data.get("document_type"),
            file_size=data.get("file_size"),
            content_hash=data.get("content_hash"),
            extracted_text=data.get("extracted_text"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CivicEvent:
    """
    Unified event model for all civic data sources.
    
    This is the core data structure that normalizes output from all scrapers,
    enabling:
    - Cross-source queries ("show me all events this week")
    - Change detection (compare content_hash)
    - Watchdog alerts (match against rules)
    - Entity linking (connect related events)
    
    Attributes:
        event_id: Unique identifier (source-specific format)
        event_type: Category of event (meeting, permit, notice)
        source_id: Which source this came from
        timestamp: When the event occurs/occurred
        discovered_at: When we first found this event
        updated_at: When we last updated this event
        title: Human-readable title
        description: Detailed description
        location: Geographic location if available
        entities: Extracted entities (people, orgs, addresses)
        documents: Attached documents
        tags: Classification tags for filtering
        content_hash: Hash of content for change detection
        raw_data: Original source-specific data
        metadata: Additional source-specific metadata
    """
    event_id: str
    event_type: EventType
    source_id: str
    timestamp: datetime
    title: str
    
    discovered_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    description: Optional[str] = None
    location: Optional[GeoLocation] = None
    
    entities: List[Entity] = field(default_factory=list)
    documents: List[Document] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    content_hash: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.content_hash is None:
            self.content_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute content hash for change detection."""
        content = f"{self.title}|{self.description}|{len(self.documents)}|{len(self.entities)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def has_changed(self, other: "CivicEvent") -> bool:
        """Check if this event has changed compared to another version."""
        return self.content_hash != other.content_hash
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        tag_lower = tag.lower().strip()
        if tag_lower not in self.tags:
            self.tags.append(tag_lower)
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity, merging if duplicate."""
        for existing in self.entities:
            if existing.matches(entity):
                existing.aliases.extend(entity.aliases)
                return
        self.entities.append(entity)
    
    def matches_tags(self, required_tags: List[str]) -> bool:
        """Check if event has all required tags."""
        return all(tag.lower() in self.tags for tag in required_tags)
    
    def matches_any_tag(self, tags: List[str]) -> bool:
        """Check if event has any of the specified tags."""
        return any(tag.lower() in self.tags for tag in tags)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_id": self.source_id,
            "timestamp": self.timestamp.isoformat(),
            "discovered_at": self.discovered_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "description": self.description,
            "location": self.location.to_dict() if self.location else None,
            "entities": [e.to_dict() for e in self.entities],
            "documents": [d.to_dict() for d in self.documents],
            "tags": self.tags,
            "content_hash": self.content_hash,
            "raw_data": self.raw_data,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CivicEvent":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            source_id=data["source_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            discovered_at=datetime.fromisoformat(data.get("discovered_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            title=data["title"],
            description=data.get("description"),
            location=GeoLocation.from_dict(data["location"]) if data.get("location") else None,
            entities=[Entity.from_dict(e) for e in data.get("entities", [])],
            documents=[Document.from_dict(d) for d in data.get("documents", [])],
            tags=data.get("tags", []),
            content_hash=data.get("content_hash"),
            raw_data=data.get("raw_data", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Alert:
    """
    A watchdog alert generated by the rules engine.
    
    Alerts are created when events match configured rules,
    enabling citizens to be notified of concerning activity.
    """
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    event: CivicEvent
    
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def acknowledge(self, user: str) -> None:
        """Mark alert as acknowledged."""
        self.acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "event": self.event.to_dict(),
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
        }
