"""
Tests for the Intelligence Layer.

Tests CivicEvent model, adapters, and entity extraction.
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List

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
from src.intelligence.adapters import (
    CivicClerkAdapter,
    SRWMDAdapter,
    FloridaNoticesAdapter,
)
from src.intelligence.event_store import EventStore
from src.intelligence.rules_engine import Rule, RulesEngine


class TestCivicEventModel:
    """Tests for CivicEvent dataclass."""

    def test_create_basic_event(self):
        """Test creating a basic CivicEvent."""
        event = CivicEvent(
            event_id="test-1",
            event_type=EventType.MEETING,
            source_id="test-source",
            timestamp=datetime(2026, 2, 1, 10, 0),
            title="Test Meeting",
        )

        assert event.event_id == "test-1"
        assert event.event_type == EventType.MEETING
        assert event.source_id == "test-source"
        assert event.title == "Test Meeting"
        assert event.content_hash is not None

    def test_event_with_entities(self):
        """Test CivicEvent with entities."""
        entity = Entity(
            entity_id="org-1",
            entity_type=EntityType.ORGANIZATION,
            name="ABC Development LLC",
        )

        event = CivicEvent(
            event_id="test-2",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Permit Application",
            entities=[entity],
        )

        assert len(event.entities) == 1
        assert event.entities[0].name == "ABC Development LLC"

    def test_event_with_documents(self):
        """Test CivicEvent with documents."""
        doc = Document(
            document_id="doc-1",
            title="Agenda PDF",
            url="https://example.com/agenda.pdf",
            document_type="pdf",
        )

        event = CivicEvent(
            event_id="test-3",
            event_type=EventType.MEETING,
            source_id="civicclerk",
            timestamp=datetime.now(),
            title="City Commission Meeting",
            documents=[doc],
        )

        assert len(event.documents) == 1
        assert event.documents[0].url == "https://example.com/agenda.pdf"

    def test_event_with_location(self):
        """Test CivicEvent with geographic location."""
        location = GeoLocation(
            latitude=29.6516,
            longitude=-82.3248,
            county="Alachua",
        )

        event = CivicEvent(
            event_id="test-4",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Permit near Gainesville",
            location=location,
        )

        assert event.location is not None
        assert event.location.county == "Alachua"

    def test_event_to_dict(self):
        """Test serialization to dictionary."""
        event = CivicEvent(
            event_id="test-5",
            event_type=EventType.PUBLIC_NOTICE,
            source_id="florida-notices",
            timestamp=datetime(2026, 2, 1),
            title="Public Notice",
            tags=["rezoning", "alachua-county"],
        )

        data = event.to_dict()

        assert data["event_id"] == "test-5"
        assert data["event_type"] == "public_notice"
        assert "rezoning" in data["tags"]

    def test_event_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "event_id": "test-6",
            "event_type": "meeting",
            "source_id": "civicclerk",
            "timestamp": "2026-02-01T10:00:00",
            "title": "Board Meeting",
            "tags": ["meeting", "planning"],
        }

        event = CivicEvent.from_dict(data)

        assert event.event_id == "test-6"
        assert event.event_type == EventType.MEETING
        assert "planning" in event.tags

    def test_content_hash_changes(self):
        """Test that content hash changes when content changes."""
        event1 = CivicEvent(
            event_id="test-7",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Original Title",
        )

        event2 = CivicEvent(
            event_id="test-7",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Modified Title",
        )

        assert event1.content_hash != event2.content_hash
        assert event1.has_changed(event2)

    def test_add_tag(self):
        """Test adding tags to event."""
        event = CivicEvent(
            event_id="test-8",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Test",
        )

        event.add_tag("rezoning")
        event.add_tag("REZONING")  # Should not duplicate

        assert "rezoning" in event.tags
        assert event.tags.count("rezoning") == 1

    def test_matches_tags(self):
        """Test tag matching."""
        event = CivicEvent(
            event_id="test-9",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Permit",
            tags=["permit", "alachua-county", "erp"],
        )

        assert event.matches_tags(["permit", "alachua-county"])
        assert not event.matches_tags(["permit", "columbia-county"])
        assert event.matches_any_tag(["columbia-county", "alachua-county"])


class TestEntityModel:
    """Tests for Entity dataclass."""

    def test_entity_normalization(self):
        """Test entity name normalization."""
        entity = Entity(
            entity_id="org-1",
            entity_type=EntityType.ORGANIZATION,
            name="ABC Development, LLC.",
        )

        assert entity.normalized_name == "abc development llc"

    def test_entity_matching(self):
        """Test entity matching logic."""
        entity1 = Entity(
            entity_id="org-1",
            entity_type=EntityType.ORGANIZATION,
            name="ABC Development LLC",
        )

        entity2 = Entity(
            entity_id="org-2",
            entity_type=EntityType.ORGANIZATION,
            name="ABC Development, LLC.",
        )

        entity3 = Entity(
            entity_id="person-1",
            entity_type=EntityType.PERSON,
            name="ABC Development LLC",
        )

        assert entity1.matches(entity2)  # Same normalized name
        assert not entity1.matches(entity3)  # Different type


class TestCivicClerkAdapter:
    """Tests for CivicClerk adapter."""

    def test_adapter_source_id(self):
        """Test adapter source ID."""
        adapter = CivicClerkAdapter("alachuafl")
        assert adapter.source_id == "civicclerk-alachuafl"

    def test_entity_extraction_from_text(self):
        """Test entity extraction from text."""
        adapter = CivicClerkAdapter()

        entities = adapter.extract_entities_from_text(
            "ABC Development LLC proposes project at 123 Main Street"
        )

        org_entities = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]
        addr_entities = [e for e in entities if e.entity_type == EntityType.ADDRESS]

        assert len(org_entities) >= 1
        assert any("ABC" in e.name for e in org_entities)

    def test_tag_extraction_from_text(self):
        """Test tag extraction from text."""
        adapter = CivicClerkAdapter()

        tags = adapter.extract_tags_from_text(
            "Public hearing on rezoning for residential development"
        )

        assert "rezoning" in tags
        assert "development" in tags
        assert "public-hearing" in tags

    def test_adapt_meeting_dict(self):
        """Test adapting meeting dictionary."""
        adapter = CivicClerkAdapter("alachuafl")

        meeting_dict = {
            "meeting_id": "123",
            "title": "City Commission Meeting",
            "date": "2026-02-01",
            "time": "5:00 PM",
            "board": "City Commission",
            "agenda_url": "https://example.com/agenda.pdf",
        }

        events = adapter.adapt_from_dict([meeting_dict])

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.MEETING
        assert "City Commission" in event.title
        assert len(event.documents) == 1
        assert "meeting" in event.tags
        assert "alachua-county" in event.tags


class TestSRWMDAdapter:
    """Tests for SRWMD adapter."""

    def test_adapter_source_id(self):
        """Test adapter source ID."""
        adapter = SRWMDAdapter()
        assert adapter.source_id == "srwmd"

    def test_tag_extraction_water_keywords(self):
        """Test water-related tag extraction."""
        adapter = SRWMDAdapter()

        tags = adapter.extract_tags_from_text(
            "Project near Santa Fe River affecting groundwater and aquifer"
        )

        assert "water" in tags
        assert "environmental" in tags


class TestFloridaNoticesAdapter:
    """Tests for Florida Notices adapter."""

    def test_adapter_source_id(self):
        """Test adapter source ID."""
        adapter = FloridaNoticesAdapter()
        assert adapter.source_id == "florida-public-notices"

    def test_adapt_notice_dict(self):
        """Test adapting notice dictionary."""
        adapter = FloridaNoticesAdapter()

        notice_dict = {
            "notice_id": "456",
            "title": "Notice of Public Hearing - Rezoning",
            "county": "Alachua",
            "publication_date": "2026-02-01",
            "newspaper": "Gainesville Sun",
            "pdf_url": "https://example.com/notice.pdf",
        }

        events = adapter.adapt_from_dict([notice_dict])

        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.PUBLIC_NOTICE
        assert event.location.county == "Alachua"
        assert "alachua" in event.tags
        assert "public-notice" in event.tags
        assert len(event.documents) == 1


class TestEventStore:
    """Tests for EventStore."""

    def test_save_new_event(self, tmp_path):
        """Test saving a new event."""
        store = EventStore(tmp_path / "events.json")

        event = CivicEvent(
            event_id="test-1",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Test Meeting",
        )

        is_new, status = store.save_event(event)

        assert is_new is True
        assert status == "new"
        assert len(store) == 1

    def test_save_updated_event(self, tmp_path):
        """Test updating an existing event."""
        store = EventStore(tmp_path / "events.json")

        event1 = CivicEvent(
            event_id="test-2",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Original Title",
        )
        store.save_event(event1)

        event2 = CivicEvent(
            event_id="test-2",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Updated Title",
        )
        is_new, status = store.save_event(event2)

        assert is_new is False
        assert status == "updated"
        assert len(store) == 1

    def test_save_unchanged_event(self, tmp_path):
        """Test saving unchanged event."""
        store = EventStore(tmp_path / "events.json")

        event = CivicEvent(
            event_id="test-3",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Same Title",
        )
        store.save_event(event)

        # Save same event again
        is_new, status = store.save_event(event)

        assert is_new is False
        assert status == "unchanged"

    def test_get_event(self, tmp_path):
        """Test retrieving event by ID."""
        store = EventStore(tmp_path / "events.json")

        event = CivicEvent(
            event_id="test-get",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Test Permit",
        )
        store.save_event(event)

        retrieved = store.get_event("test-get")
        assert retrieved is not None
        assert retrieved.title == "Test Permit"

        missing = store.get_event("nonexistent")
        assert missing is None

    def test_get_events_by_source(self, tmp_path):
        """Test filtering events by source."""
        store = EventStore(tmp_path / "events.json")

        store.save_event(CivicEvent(
            event_id="e1",
            event_type=EventType.MEETING,
            source_id="civicclerk",
            timestamp=datetime.now(),
            title="Meeting 1",
        ))
        store.save_event(CivicEvent(
            event_id="e2",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Permit 1",
        ))

        civicclerk_events = store.get_events(source_id="civicclerk")
        assert len(civicclerk_events) == 1
        assert civicclerk_events[0].event_id == "e1"

    def test_get_events_by_tags(self, tmp_path):
        """Test filtering events by tags."""
        store = EventStore(tmp_path / "events.json")

        store.save_event(CivicEvent(
            event_id="e1",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Rezoning Meeting",
            tags=["rezoning", "alachua-county"],
        ))
        store.save_event(CivicEvent(
            event_id="e2",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Budget Meeting",
            tags=["budget", "alachua-county"],
        ))

        rezoning_events = store.get_events(tags=["rezoning"])
        assert len(rezoning_events) == 1

        alachua_events = store.get_events(tags=["alachua-county"])
        assert len(alachua_events) == 2

    def test_get_whats_new(self, tmp_path):
        """Test what's new query."""
        store = EventStore(tmp_path / "events.json")

        # Add recent event
        store.save_event(CivicEvent(
            event_id="recent",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Recent Event",
        ))

        new_events = store.get_whats_new(hours=24)
        assert len(new_events) == 1
        assert new_events[0].event_id == "recent"

    def test_get_upcoming(self, tmp_path):
        """Test upcoming events query."""
        store = EventStore(tmp_path / "events.json")

        # Add future event
        future_time = datetime.now() + timedelta(days=3)
        store.save_event(CivicEvent(
            event_id="future",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=future_time,
            title="Future Meeting",
        ))

        # Add past event
        past_time = datetime.now() - timedelta(days=3)
        store.save_event(CivicEvent(
            event_id="past",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=past_time,
            title="Past Meeting",
        ))

        upcoming = store.get_upcoming(days=7)
        assert len(upcoming) == 1
        assert upcoming[0].event_id == "future"

    def test_persistence(self, tmp_path):
        """Test that events persist across store instances."""
        storage_path = tmp_path / "persist.json"

        # Save event
        store1 = EventStore(storage_path)
        store1.save_event(CivicEvent(
            event_id="persist-test",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Persistent Event",
        ))

        # Create new store instance
        store2 = EventStore(storage_path)

        assert len(store2) == 1
        assert store2.get_event("persist-test") is not None

    def test_get_sources(self, tmp_path):
        """Test getting unique sources."""
        store = EventStore(tmp_path / "events.json")

        store.save_event(CivicEvent(
            event_id="e1", event_type=EventType.MEETING,
            source_id="civicclerk", timestamp=datetime.now(), title="M1"
        ))
        store.save_event(CivicEvent(
            event_id="e2", event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd", timestamp=datetime.now(), title="P1"
        ))

        sources = store.get_sources()
        assert "civicclerk" in sources
        assert "srwmd" in sources


class TestRulesEngine:
    """Tests for RulesEngine."""

    def test_rule_matches_event_type(self):
        """Test rule matching by event type."""
        rule = Rule(
            name="permit-rule",
            description="Match permits",
            severity=AlertSeverity.INFO,
            message_template="Permit: {title}",
            event_types=[EventType.PERMIT_APPLICATION],
        )

        permit_event = CivicEvent(
            event_id="p1",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Test Permit",
        )

        meeting_event = CivicEvent(
            event_id="m1",
            event_type=EventType.MEETING,
            source_id="civicclerk",
            timestamp=datetime.now(),
            title="Test Meeting",
        )

        assert rule.matches(permit_event)
        assert not rule.matches(meeting_event)

    def test_rule_matches_tags(self):
        """Test rule matching by tags."""
        rule = Rule(
            name="rezoning-rule",
            description="Match rezoning",
            severity=AlertSeverity.NOTABLE,
            message_template="Rezoning: {title}",
            required_tags=["rezoning"],
        )

        rezoning_event = CivicEvent(
            event_id="r1",
            event_type=EventType.MEETING,
            source_id="civicclerk",
            timestamp=datetime.now(),
            title="Rezoning Hearing",
            tags=["rezoning", "public-hearing"],
        )

        other_event = CivicEvent(
            event_id="o1",
            event_type=EventType.MEETING,
            source_id="civicclerk",
            timestamp=datetime.now(),
            title="Budget Meeting",
            tags=["budget"],
        )

        assert rule.matches(rezoning_event)
        assert not rule.matches(other_event)

    def test_rule_matches_any_tag(self):
        """Test rule matching with any_tags."""
        rule = Rule(
            name="environmental-rule",
            description="Match environmental",
            severity=AlertSeverity.WARNING,
            message_template="Environmental: {title}",
            any_tags=["water", "aquifer", "wetland"],
        )

        water_event = CivicEvent(
            event_id="w1",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Water Permit",
            tags=["water", "permit"],
        )

        assert rule.matches(water_event)

    def test_rule_matches_county(self):
        """Test rule matching by county."""
        rule = Rule(
            name="alachua-rule",
            description="Match Alachua County",
            severity=AlertSeverity.INFO,
            message_template="Alachua: {title}",
            counties=["Alachua"],
        )

        alachua_event = CivicEvent(
            event_id="a1",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Alachua Permit",
            location=GeoLocation(latitude=0, longitude=0, county="Alachua"),
        )

        other_event = CivicEvent(
            event_id="o1",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="Columbia Permit",
            location=GeoLocation(latitude=0, longitude=0, county="Columbia"),
        )

        assert rule.matches(alachua_event)
        assert not rule.matches(other_event)

    def test_rule_generates_alert(self):
        """Test alert generation from rule."""
        rule = Rule(
            name="test-rule",
            description="Test",
            severity=AlertSeverity.WARNING,
            message_template="Alert for: {title}",
        )

        event = CivicEvent(
            event_id="e1",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Important Meeting",
        )

        alert = rule.generate_alert(event)

        assert alert.rule_name == "test-rule"
        assert alert.severity == AlertSeverity.WARNING
        assert "Important Meeting" in alert.message

    def test_engine_evaluates_events(self, tmp_path):
        """Test engine evaluating events against rules."""
        engine = RulesEngine(tmp_path / "rules.yaml")

        # Add a custom rule
        engine.add_rule(Rule(
            name="custom-rule",
            description="Custom test rule",
            severity=AlertSeverity.NOTABLE,
            message_template="Custom: {title}",
            required_tags=["custom-tag"],
        ))

        event = CivicEvent(
            event_id="c1",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Custom Event",
            tags=["custom-tag"],
        )

        alerts = engine.evaluate(event)

        assert len(alerts) >= 1
        assert any(a.rule_name == "custom-rule" for a in alerts)

    def test_engine_loads_yaml_rules(self):
        """Test engine loads rules from YAML."""
        # Use the actual config file
        engine = RulesEngine()

        assert len(engine.rules) > 0

        # Check that known rules exist
        rule_names = [r.name for r in engine.rules]
        assert "new-alachua-permit" in rule_names
        assert "rezoning-alert" in rule_names

    def test_disabled_rule_not_matched(self):
        """Test that disabled rules don't match."""
        rule = Rule(
            name="disabled-rule",
            description="Disabled",
            severity=AlertSeverity.INFO,
            message_template="Should not match",
            enabled=False,
        )

        event = CivicEvent(
            event_id="e1",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Any Event",
        )

        assert not rule.matches(event)


class TestAlertModel:
    """Tests for Alert dataclass."""

    def test_create_alert(self):
        """Test creating an alert."""
        event = CivicEvent(
            event_id="test-alert",
            event_type=EventType.PERMIT_APPLICATION,
            source_id="srwmd",
            timestamp=datetime.now(),
            title="New Permit",
        )

        alert = Alert(
            alert_id="alert-1",
            rule_name="New Alachua Permit",
            severity=AlertSeverity.NOTABLE,
            message="New permit application in Alachua County",
            event=event,
        )

        assert alert.severity == AlertSeverity.NOTABLE
        assert not alert.acknowledged

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        event = CivicEvent(
            event_id="test-ack",
            event_type=EventType.MEETING,
            source_id="test",
            timestamp=datetime.now(),
            title="Test",
        )

        alert = Alert(
            alert_id="alert-2",
            rule_name="Test Rule",
            severity=AlertSeverity.INFO,
            message="Test message",
            event=event,
        )

        alert.acknowledge("user@example.com")

        assert alert.acknowledged
        assert alert.acknowledged_by == "user@example.com"
        assert alert.acknowledged_at is not None
