from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class UrgencyLevel(str, Enum):
    RED = "RED"       # Function-calling trigger: SMS/Email alert
    YELLOW = "YELLOW" # Monitor
    GREEN = "GREEN"   # Log


class CivicCategory(str, Enum):
    """Universal civic categories applicable to any municipality."""
    BUDGET_FINANCE = "budget_finance"       # Budgets, taxes, appropriations, audits
    LAND_USE = "land_use"                   # Zoning, plats, comprehensive plan
    PUBLIC_SAFETY = "public_safety"         # Police, fire, emergency services
    INFRASTRUCTURE = "infrastructure"       # Roads, utilities, maintenance
    PERSONNEL = "personnel"                 # Hiring, salaries, HR matters
    CONTRACTS = "contracts"                 # Bids, RFPs, vendor agreements
    ENVIRONMENT = "environment"             # Environmental protection, permits
    PUBLIC_HEARING = "public_hearing"       # Quasi-judicial, public comment
    CONSENT = "consent"                     # Consent agenda items
    INTERGOVERNMENTAL = "intergovernmental" # County/state/federal coordination
    COMMUNITY = "community"                 # Events, proclamations, recognition
    OTHER = "other"                         # Uncategorized items


class Significance(str, Enum):
    """Civic significance level for agenda items."""
    ROUTINE = "routine"     # Standard business, no action needed
    NOTABLE = "notable"     # Worth knowing about, may have implications
    CRITICAL = "critical"   # Requires attention, action, or attendance

class UrgencyAlert(BaseModel):
    level: UrgencyLevel = Field(..., description="Urgency level based on immediate deadlines or threats")
    deadline: Optional[date] = Field(default=None, description="Specific deadline for action if applicable")
    action_item: str = Field(..., description="Specific action for citizens to take")
    context: str = Field(..., description="Context explaining why this is urgent")

class MeetingItem(BaseModel):
    """A single agenda item with comprehensive analysis."""
    agenda_id: Optional[str] = Field(default=None, description="Agenda item ID if available")
    topic: str = Field(..., description="Brief title of the agenda item")
    summary: str = Field(..., description="2-3 sentence summary explaining what this item is about")
    category: CivicCategory = Field(..., description="Civic category for this item")
    significance: Significance = Field(..., description="How significant is this for citizens")
    related_to: List[str] = Field(..., description="Related entities, projects, or keywords")
    outcome: Optional[str] = Field(default=None, description="Vote outcome or decision if meeting already occurred")

    # Priority flagging for watchlist matches
    priority_flag: bool = Field(..., description="True if this item matches watchlist entities/keywords")
    priority_reason: Optional[str] = Field(default=None, description="Why this item was flagged as priority")
    watchlist_matches: List[str] = Field(..., description="Which watchlist items this matches")

class BaseReport(BaseModel):
    """Base class for all report types with shared fields."""
    report_id: str = Field(..., description="Unique ID for the report (e.g., A1-2026-01-28)")
    period_covered: str = Field(..., description="Date range covered by the report")
    executive_summary: str = Field(..., description="Concise summary of the most critical findings")
    alerts: List[UrgencyAlert] = Field(default_factory=list, description="List of actionable alerts")

    @property
    def urgency_level(self) -> UrgencyLevel:
        """Derive overall urgency from the highest alert level."""
        if not self.alerts:
            return UrgencyLevel.GREEN
        priority = {UrgencyLevel.RED: 0, UrgencyLevel.YELLOW: 1, UrgencyLevel.GREEN: 2}
        return min((alert.level for alert in self.alerts), key=lambda x: priority.get(x, 2))


class ScoutReport(BaseReport):
    """Output from A1/A2 scouts - monitors government data sources."""
    items: List[MeetingItem] = Field(default_factory=list, description="List of relevant agenda items found")
    raw_markdown: Optional[str] = Field(default=None, description="Raw markdown content if available")
    date_generated: datetime = Field(default_factory=datetime.now, description="When this report was generated")


class AnalysisSection(BaseModel):
    """A section of analysis within an AnalystReport."""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Analysis content")
    sources: List[str] = Field(..., description="Source references")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")


class AnalystReport(BaseReport):
    """Output from B1/B2 analysts - synthesizes scout data into insights."""
    topic: str = Field(..., description="Primary topic of analysis")
    scout_report_ids: List[str] = Field(..., description="IDs of scout reports used")
    sections: List[AnalysisSection] = Field(..., description="Analysis sections")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    entities_mentioned: List[str] = Field(..., description="Key entities referenced")


class SynthesizerReport(BaseReport):
    """Output from C1-C4 synthesizers - produces final citizen-facing content."""
    report_type: str = Field(..., description="Type: daily_brief, weekly_digest, alert, deep_dive")
    analyst_report_ids: List[str] = Field(..., description="IDs of analyst reports used")
    target_audience: str = Field(..., description="Intended audience")
    headline: str = Field(..., description="Attention-grabbing headline")
    key_takeaways: List[str] = Field(..., description="Bullet-point takeaways")
    call_to_action: Optional[str] = Field(default=None, description="What citizens should do")
    distribution_channels: List[str] = Field(..., description="Where to publish")


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """Human-in-the-loop approval request for sensitive content."""
    id: str = Field(..., description="Unique approval request ID")
    created_at: datetime = Field(default_factory=datetime.now, description="When this request was created")
    expires_at: Optional[datetime] = Field(default=None, description="When this approval expires")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Current status")
    agent_id: str = Field(..., description="Agent that generated the content")
    report_id: str = Field(..., description="Associated report ID")
    reason: str = Field(..., description="Why approval is needed")
    summary: str = Field(..., description="Summary of content requiring approval")
    reviewer: Optional[str] = Field(default=None, description="Who reviewed this")
    decision_at: Optional[datetime] = Field(default=None, description="When decision was made")
    comments: Optional[str] = Field(default=None, description="Reviewer comments")
