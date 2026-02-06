import datetime
from typing import Dict, Any, Optional, List
from src.agents.base import BaseAgent
from src.schemas import ScoutReport
from src.models import get_gemini_pro
from src.tools import monitor_url
from src.prompts import get_alachua_context


class ScoutAgent(BaseAgent):
    """
    Layer 1 Scout agent for monitoring government data sources.

    Supports tiered analysis:
    1. PDF content (preferred) - Full agenda details
    2. Metadata fallback - When no PDF available yet

    Uses domain context from prompt_library for enhanced analysis.
    Uses native google.genai SDK to avoid PyTorch/transformers dependencies.
    """

    def __init__(self, name: str, prompt_template: str = None):
        super().__init__(name, role="Scout")
        self.prompt_template = prompt_template
        self.llm = get_gemini_pro()
        self.structured_llm = self.llm.with_structured_output(ScoutReport)
        self.context = get_alachua_context()

    def _build_pdf_prompt(
        self,
        agent_id: str,
        date: str,
        meeting_info: dict,
        pdf_content: str,
        watchlist: str
    ) -> str:
        """Build prompt for PDF content analysis (Tier 1 - Full analysis)."""
        meeting_date = meeting_info.get('meeting_date', 'Unknown')
        title = meeting_info.get('title', 'Unknown Meeting')
        board = meeting_info.get('board', 'Unknown Board')

        return f"""You are a **Civic Intelligence Scout** for the Open Sousveillance Studio.

{self.context.get_prompt_context()}

---
## CURRENT TASK

**Agent:** {agent_id}
**Current Date:** {date}
**Analysis Type:** FULL PDF ANALYSIS

### MEETING INFORMATION:
- **Title:** {title}
- **Date:** {meeting_date}
- **Board/Body:** {board}

### AGENDA PACKET CONTENT (PDF):
{pdf_content}

---

## INSTRUCTIONS

**IMPORTANT: Analyze ALL agenda items comprehensively.** This is the full agenda packet - extract every item.

Generate a ScoutReport with:

### 1. Report Metadata
- **report_id**: Format as "{agent_id}-{date}-001"
- **period_covered**: The meeting date
- **executive_summary**: 2-3 sentences summarizing the FULL scope of this agenda, highlighting any priority items

### 2. Items (COMPREHENSIVE - Document ALL agenda items)
For EACH agenda item found, create a MeetingItem with:
- **agenda_id**: The item number/ID (e.g., "5.A", "VII.2")
- **topic**: Brief title of the item
- **summary**: 2-3 sentences explaining what this item is about and why it matters to citizens
- **category**: Classify as one of: budget_finance, land_use, public_safety, infrastructure, personnel, contracts, environment, public_hearing, consent, intergovernmental, community, other
- **significance**: Rate as routine (standard business), notable (worth knowing), or critical (requires attention)
- **related_to**: List any related entities, projects, addresses, or keywords
- **outcome**: Vote result or decision if this is a past meeting

**Priority Flagging:** For each item, check against the watchlist below. If it matches:
- Set **priority_flag** = true
- Set **priority_reason** = explain why this is a priority item
- Set **watchlist_matches** = list which watchlist items it matches

### 3. Alerts (Only for items requiring citizen action)
Create UrgencyAlerts only for items that require specific citizen action:
- **RED**: Action needed within 48 hours (public hearing, comment deadline)
- **YELLOW**: Monitor closely, action may be needed soon
- **GREEN**: Informational, no immediate action required

---

## WATCHLIST (Flag matches, don't filter)
{watchlist}

---

## QUALITY STANDARDS
- Document ALL items, not just watchlist matches
- Include specific details: dollar amounts, addresses, names, dates
- Provide clear, factual summaries without editorializing
- Distinguish facts from inferences
"""

    def _build_metadata_prompt(
        self,
        agent_id: str,
        date: str,
        meeting_info: dict,
        watchlist: str
    ) -> str:
        """Build prompt for metadata-only analysis (Tier 2 - Minimal report)."""
        meeting_date = meeting_info.get('meeting_date', 'Unknown')
        title = meeting_info.get('title', 'Unknown Meeting')
        board = meeting_info.get('board', 'Unknown Board')
        metadata = meeting_info.get('metadata', {})
        time = metadata.get('time', 'Unknown')
        location = metadata.get('location', 'Unknown')

        return f"""You are a **Civic Intelligence Scout** for the Open Sousveillance Studio.

{self.context.get_prompt_context()}

---
## CURRENT TASK

**Agent:** {agent_id}
**Current Date:** {date}
**Analysis Type:** METADATA ONLY (No agenda available yet)

### MEETING INFORMATION:
- **Title:** {title}
- **Date:** {meeting_date}
- **Time:** {time}
- **Board/Body:** {board}
- **Location:** {location}

**NOTE:** The agenda for this meeting has not been posted yet. Generate a minimal awareness report.

---

## INSTRUCTIONS

Generate a minimal ScoutReport to track this upcoming meeting:

### 1. Report Metadata
- **report_id**: Format as "{agent_id}-{date}-001"
- **period_covered**: The meeting date
- **executive_summary**: Note that this meeting is scheduled but agenda is not yet available

### 2. Items
Create a SINGLE MeetingItem as a placeholder:
- **agenda_id**: "PENDING"
- **topic**: "{title}"
- **summary**: "Meeting scheduled. Agenda not yet posted. Check back for updates."
- **category**: Infer from meeting title if possible, otherwise use "other"
- **significance**: "notable" (citizens should be aware this meeting is happening)
- **related_to**: Extract any entities from the meeting title
- **priority_flag**: Check if meeting title matches watchlist
- **priority_reason**: If flagged, explain why

### 3. Alerts
- If this is an upcoming meeting within 7 days, create a GREEN alert noting the meeting date
- If the meeting title suggests a public hearing or important topic, create a YELLOW alert

---

## WATCHLIST
{watchlist}
"""

    def _build_url_prompt(self, agent_id: str, date: str, url: str, content: str, watchlist: str) -> str:
        """Build prompt for URL-based analysis (legacy mode)."""
        return f"""You are a **Civic Intelligence Scout** for the Open Sousveillance Studio.

{self.context.get_prompt_context()}

---
## CURRENT TASK

**Agent:** {agent_id}
**Current Date:** {date}
**Source URL:** {url}

### SOURCE CONTENT:
{content}

---

## INSTRUCTIONS

**IMPORTANT: Analyze ALL content comprehensively.** Do not filter or skip items. Citizens need complete awareness of government activity.

Generate a ScoutReport with:

### 1. Report Metadata
- **report_id**: Format as "{agent_id}-{date}-001"
- **period_covered**: The date range covered by this content
- **executive_summary**: 2-3 sentences summarizing the FULL scope of this content, highlighting any priority items

### 2. Items (COMPREHENSIVE - Document ALL agenda items)
For EACH agenda item found, create a MeetingItem with:
- **agenda_id**: The item number/ID if available
- **topic**: Brief title of the item
- **summary**: 2-3 sentences explaining what this item is about and why it matters
- **category**: Classify as one of: budget_finance, land_use, public_safety, infrastructure, personnel, contracts, environment, public_hearing, consent, intergovernmental, community, other
- **significance**: Rate as routine (standard business), notable (worth knowing), or critical (requires attention)
- **related_to**: List any related entities, projects, or keywords
- **outcome**: Vote result or decision if already occurred

**Priority Flagging:** For each item, check against the watchlist below. If it matches:
- Set **priority_flag** = true
- Set **priority_reason** = explain why this is a priority item
- Set **watchlist_matches** = list which watchlist items it matches

### 3. Alerts (Only for items requiring citizen action)
Create UrgencyAlerts only for items that require specific citizen action:
- **RED**: Action needed within 48 hours (public hearing, comment deadline)
- **YELLOW**: Monitor closely, action may be needed soon
- **GREEN**: Informational, no immediate action required

---

## WATCHLIST (Flag matches, don't filter)
{watchlist}

---

## QUALITY STANDARDS
- Document ALL items, not just watchlist matches
- Provide clear, factual summaries without editorializing
- Distinguish facts from inferences
- If information is unclear, note the uncertainty
"""

    def analyze_meeting(self, meeting: dict) -> ScoutReport:
        """
        Analyze a meeting using tiered approach.

        Tier 1: If PDF content available, do full analysis
        Tier 2: If no PDF, generate minimal awareness report from metadata

        Args:
            meeting: Dict with meeting data from database, including:
                - meeting_id, title, meeting_date, board
                - pdf_content (optional)
                - metadata (optional)

        Returns:
            ScoutReport with analysis results
        """
        current_date = datetime.date.today().isoformat()
        watchlist = self.context.get_keywords_string()

        pdf_content = meeting.get('pdf_content')

        if pdf_content:
            # Tier 1: Full PDF analysis
            self.logger.info(
                "Analyzing meeting with PDF content",
                meeting_id=meeting.get('meeting_id'),
                content_length=len(pdf_content)
            )

            # Truncate if needed
            max_chars = 60000
            if len(pdf_content) > max_chars:
                pdf_content = pdf_content[:max_chars]
                self.logger.warning("PDF content truncated", original=len(meeting.get('pdf_content')), truncated=max_chars)

            prompt = self._build_pdf_prompt(
                agent_id=self.name,
                date=current_date,
                meeting_info=meeting,
                pdf_content=pdf_content,
                watchlist=watchlist
            )

            analysis_type = "pdf"
        else:
            # Tier 2: Metadata-only analysis
            self.logger.info(
                "Analyzing meeting with metadata only (no PDF)",
                meeting_id=meeting.get('meeting_id'),
                title=meeting.get('title')
            )

            prompt = self._build_metadata_prompt(
                agent_id=self.name,
                date=current_date,
                meeting_info=meeting,
                watchlist=watchlist
            )

            analysis_type = "metadata"

        # Execute analysis
        result: ScoutReport = self.structured_llm.invoke(prompt)

        self.logger.info(
            "Scout analysis complete",
            meeting_id=meeting.get('meeting_id'),
            analysis_type=analysis_type,
            items_found=len(result.items),
            alerts_count=len(result.alerts)
        )

        return result

    def analyze_meetings_batch(self, meetings: List[dict]) -> List[ScoutReport]:
        """
        Analyze multiple meetings.

        Args:
            meetings: List of meeting dicts from database

        Returns:
            List of ScoutReports
        """
        reports = []

        for meeting in meetings:
            try:
                report = self.analyze_meeting(meeting)
                reports.append(report)
            except Exception as e:
                self.logger.error(
                    "Failed to analyze meeting",
                    meeting_id=meeting.get('meeting_id'),
                    error=str(e)
                )

        return reports

    def _execute(self, input_data: Dict[str, Any]) -> ScoutReport:
        """
        Execute Scout analysis.

        Supports two modes:
        1. Meeting mode: Pass 'meeting' dict for tiered analysis
        2. URL mode (legacy): Pass 'url' for direct page scraping

        Args:
            input_data: Dict with either 'meeting' or 'url'

        Returns:
            ScoutReport
        """
        # Check for meeting-based analysis (new tiered approach)
        if 'meeting' in input_data:
            return self.analyze_meeting(input_data['meeting'])

        # Legacy URL-based analysis
        target_url = input_data.get("url")
        if not target_url:
            raise ValueError("ScoutAgent requires either 'meeting' or 'url' in input_data")

        self.logger.info("Fetching URL content (legacy mode)", url=target_url)

        # Fetch Content
        page_content = monitor_url.invoke(target_url)

        # Prepare Prompt with domain context
        current_date = datetime.date.today().isoformat()

        # Limit content size
        max_content_chars = 50000
        truncated_content = page_content[:max_content_chars]
        if len(page_content) > max_content_chars:
            self.logger.warning(
                "Content truncated for analysis",
                original_length=len(page_content),
                truncated_length=max_content_chars
            )

        prompt = self._build_url_prompt(
            agent_id=self.name,
            date=current_date,
            url=target_url,
            content=truncated_content,
            watchlist=self.context.get_keywords_string()
        )

        # Execute with structured output
        result: ScoutReport = self.structured_llm.invoke(prompt)

        self.logger.info(
            "Scout analysis complete",
            items_found=len(result.items),
            alerts_count=len(result.alerts)
        )

        return result
