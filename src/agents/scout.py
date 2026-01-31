import datetime
from typing import Dict, Any
from src.agents.base import BaseAgent
from src.schemas import ScoutReport
from src.models import get_gemini_pro
from src.tools import monitor_url  # This imports from src/tools.py module
from src.prompts import get_alachua_context


class ScoutAgent(BaseAgent):
    """
    Layer 1 Scout agent for monitoring government data sources.

    Uses domain context from prompt_library for enhanced analysis.
    Uses native google.genai SDK to avoid PyTorch/transformers dependencies.
    """

    def __init__(self, name: str, prompt_template: str = None):
        super().__init__(name, role="Scout")
        self.prompt_template = prompt_template
        self.llm = get_gemini_pro()
        self.structured_llm = self.llm.with_structured_output(ScoutReport)
        self.context = get_alachua_context()

    def _build_prompt(self, agent_id: str, date: str, url: str, content: str, watchlist: str) -> str:
        """Build the analysis prompt with domain context."""
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

    def _execute(self, input_data: Dict[str, Any]) -> ScoutReport:
        """
        1. Identifies URL to monitor from input or registry.
        2. Fetches content using monitor_url tool.
        3. Passes content + domain context + Prompt to Gemini.
        4. Returns structured decision.
        """
        target_url = input_data.get("url")
        if not target_url:
            raise ValueError("ScoutAgent requires a 'url' in input_data")

        self.logger.info("Fetching URL content", url=target_url)

        # 1. Fetch Content
        page_content = monitor_url.invoke(target_url)

        # 2. Prepare Prompt with domain context
        current_date = datetime.date.today().isoformat()

        prompt = self._build_prompt(
            agent_id=self.name,
            date=current_date,
            url=target_url,
            content=page_content[:80000],
            watchlist=self.context.get_keywords_string()
        )

        # 3. Execute with structured output
        result: ScoutReport = self.structured_llm.invoke(prompt)

        self.logger.info(
            "Scout analysis complete",
            items_found=len(result.items),
            alerts_count=len(result.alerts)
        )

        return result
