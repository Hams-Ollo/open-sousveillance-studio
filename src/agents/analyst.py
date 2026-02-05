from typing import Dict, Any, Literal, Optional
from datetime import datetime
from enum import Enum

from src.agents.base import BaseAgent
from src.schemas import ScoutReport
from src.models import get_gemini_pro
from src.tools import deep_research
from src.prompts import get_alachua_context


class ResearchProvider(str, Enum):
    """Available research providers."""
    TAVILY = "tavily"
    GEMINI = "gemini"
    BOTH = "both"


class AnalystAgent(BaseAgent):
    """
    Layer 2 Analyst agent for deep research and pattern analysis.

    Supports multiple research providers:
    - Tavily: Fast web search, good for quick lookups
    - Gemini Deep Research: Comprehensive agentic research, slower but thorough
    - Both: Combines results from both providers

    Uses domain context from prompt_library for enhanced analysis.
    """

    def __init__(
        self,
        name: str,
        research_provider: ResearchProvider = ResearchProvider.BOTH
    ):
        super().__init__(name, role="Analyst")
        self.llm = get_gemini_pro()
        self.structured_llm = self.llm.with_structured_output(ScoutReport)
        self.context = get_alachua_context()
        self.research_provider = research_provider

        # Initialize Gemini Research client if needed
        self._gemini_research = None
        if research_provider in [ResearchProvider.GEMINI, ResearchProvider.BOTH]:
            try:
                from src.tools.gemini_research import get_gemini_research_client
                self._gemini_research = get_gemini_research_client()
            except Exception as e:
                self.logger.warning("Gemini Research not available", error=str(e))

    def _build_prompt(self, agent_id: str, date: str, topic: str,
                      research_context: str, keywords: str, entities: str) -> str:
        """Build the analysis prompt with domain context."""
        return f"""You are an **Impact Assessment Analyst** for the Alachua Civic Intelligence System.

{self.context.get_prompt_context()}

---
## CURRENT TASK

**Agent:** {agent_id}
**Current Date:** {date}
**Research Topic:** {topic}

### RESEARCH FINDINGS:
{research_context}

---

## INSTRUCTIONS

Analyze the research findings and generate a comprehensive Intelligence Report:

1. **report_id**: Format as "{agent_id}-{date}-001"
2. **period_covered**: The date range covered by this research
3. **executive_summary**: Key findings and their implications for citizens
4. **alerts**: UrgencyAlerts for any time-sensitive findings
5. **items**: Key topics identified with related entities

**Analysis Focus:**
- New development activity and permit applications
- Regulatory changes affecting environmental protection
- Hidden connections between developers, officials, and projects
- Procedural irregularities or Sunshine Law concerns
- Upcoming deadlines for public participation

**Priority Keywords:** {keywords}

**Entities to Track:** {entities}

Synthesize patterns across sources. Flag any contradictions or gaps in information.
"""

    def _research_with_tavily(self, query: str) -> str:
        """Execute research using Tavily."""
        self.logger.info("Running Tavily research", query=query[:100])
        try:
            result = deep_research.invoke(query)
            return f"## Tavily Search Results\n\n{result}"
        except Exception as e:
            self.logger.error("Tavily research failed", error=str(e))
            return f"Tavily search failed: {str(e)}"

    def _research_with_gemini(self, query: str, context: Optional[str] = None) -> str:
        """Execute research using Gemini Deep Research Agent."""
        if not self._gemini_research:
            return "Gemini Deep Research not available."

        self.logger.info("Running Gemini Deep Research", query=query[:100])
        try:
            from src.tools.gemini_research import ResearchStatus
            result = self._gemini_research.research(
                query=query,
                context=context,
                timeout_seconds=300  # 5 minute timeout
            )
            if result.status == ResearchStatus.COMPLETED and result.text:
                return f"## Gemini Deep Research Results\n\n{result.text}"
            else:
                return f"Gemini research failed: {result.error or 'Unknown error'}"
        except Exception as e:
            self.logger.error("Gemini research failed", error=str(e))
            return f"Gemini research failed: {str(e)}"

    def _execute_research(self, topic: str) -> str:
        """
        Execute research using configured provider(s).

        Args:
            topic: Research topic

        Returns:
            Combined research context string
        """
        search_query = f"Current news and development updates regarding {topic} Alachua County Florida"
        domain_context = f"""Focus Area: Alachua County, Florida
Keywords: {self.context.get_keywords_string()}
Entities of Interest: {self.context.get_entities_string()}"""

        results = []

        if self.research_provider in [ResearchProvider.TAVILY, ResearchProvider.BOTH]:
            tavily_result = self._research_with_tavily(search_query)
            results.append(tavily_result)

        if self.research_provider in [ResearchProvider.GEMINI, ResearchProvider.BOTH]:
            gemini_result = self._research_with_gemini(search_query, context=domain_context)
            results.append(gemini_result)

        return "\n\n---\n\n".join(results)

    def _execute(self, input_data: Dict[str, Any]) -> ScoutReport:
        """
        1. Formulate search queries based on topic.
        2. Execute Deep Research (Tavily and/or Gemini).
        3. Synthesize findings with domain context into a Report.
        """
        topic = input_data.get("topic")
        if not topic:
            raise ValueError("AnalystAgent requires a 'topic'")

        self.logger.info(
            "Starting deep research",
            topic=topic,
            provider=self.research_provider.value
        )

        # 1. Execute research with configured provider(s)
        research_context = self._execute_research(topic)

        self.logger.info("Research complete", context_length=len(research_context))

        # 2. Synthesis with domain context
        current_date = datetime.now().date().isoformat()

        prompt = self._build_prompt(
            agent_id=self.name,
            date=current_date,
            topic=topic,
            research_context=research_context[:60000],
            keywords=self.context.get_keywords_string(),
            entities=self.context.get_entities_string()
        )

        # 3. Execute with structured output
        result: ScoutReport = self.structured_llm.invoke(prompt)

        self.logger.info(
            "Analysis complete",
            alerts_count=len(result.alerts),
            items_count=len(result.items)
        )

        return result
