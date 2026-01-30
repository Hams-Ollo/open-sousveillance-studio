"""
Tests for Pydantic schemas.
"""

import pytest
from datetime import datetime, date


class TestUrgencyAlert:
    """Tests for UrgencyAlert schema."""
    
    def test_urgency_alert_creation(self):
        """Test creating an UrgencyAlert."""
        from src.schemas import UrgencyAlert, UrgencyLevel
        
        alert = UrgencyAlert(
            level=UrgencyLevel.RED,
            action_item="Attend public hearing",
            context="Final vote on development"
        )
        
        assert alert.level == UrgencyLevel.RED
        assert alert.action_item == "Attend public hearing"
        assert alert.deadline is None
    
    def test_urgency_alert_with_deadline(self):
        """Test UrgencyAlert with deadline."""
        from src.schemas import UrgencyAlert, UrgencyLevel
        
        alert = UrgencyAlert(
            level=UrgencyLevel.YELLOW,
            deadline=date(2026, 2, 15),
            action_item="Submit public comment",
            context="Comment period ends"
        )
        
        assert alert.deadline == date(2026, 2, 15)


class TestScoutReport:
    """Tests for ScoutReport schema."""
    
    def test_scout_report_creation(self, sample_scout_report):
        """Test creating a ScoutReport."""
        assert sample_scout_report.report_id == "A1-2026-01-30"
        assert len(sample_scout_report.alerts) == 1
        assert len(sample_scout_report.items) == 1
    
    def test_scout_report_defaults(self):
        """Test ScoutReport default values."""
        from src.schemas import ScoutReport
        
        report = ScoutReport(
            report_id="A1-test",
            period_covered="2026-01-30",
            executive_summary="Test summary"
        )
        
        assert report.alerts == []
        assert report.items == []
        assert report.raw_markdown is None
        assert isinstance(report.date_generated, datetime)


class TestAnalystReport:
    """Tests for AnalystReport schema."""
    
    def test_analyst_report_creation(self, sample_analyst_report):
        """Test creating an AnalystReport."""
        assert sample_analyst_report.report_id == "B1-2026-01-30"
        assert sample_analyst_report.topic == "Tara Forest Development"
        assert len(sample_analyst_report.sections) == 1
    
    def test_analyst_report_section_confidence(self, sample_analyst_report):
        """Test AnalysisSection confidence bounds."""
        section = sample_analyst_report.sections[0]
        assert 0.0 <= section.confidence <= 1.0


class TestMeetingItem:
    """Tests for MeetingItem schema."""
    
    def test_meeting_item_creation(self):
        """Test creating a MeetingItem."""
        from src.schemas import MeetingItem
        
        item = MeetingItem(
            topic="Budget Discussion",
            related_to=["Finance", "Infrastructure"]
        )
        
        assert item.topic == "Budget Discussion"
        assert "Finance" in item.related_to
        assert item.agenda_id is None
        assert item.outcome is None


class TestApprovalRequest:
    """Tests for ApprovalRequest schema."""
    
    def test_approval_request_creation(self):
        """Test creating an ApprovalRequest."""
        from src.schemas import ApprovalRequest, ApprovalStatus
        
        request = ApprovalRequest(
            id="approval-123",
            agent_id="B1",
            report_id="B1-2026-01-30",
            reason="Sensitive content",
            summary="Report contains allegations"
        )
        
        assert request.status == ApprovalStatus.PENDING
        assert request.reviewer is None
    
    def test_approval_status_enum(self):
        """Test ApprovalStatus enum values."""
        from src.schemas import ApprovalStatus
        
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
