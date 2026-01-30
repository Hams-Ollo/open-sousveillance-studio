from typing import Dict, Any
from datetime import datetime

from src.agents.base import BaseAgent
from src.schemas import ScoutReport
from src.models import get_gemini_pro
from src.tools import deep_research
from src.prompts import get_alachua_context
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough


class AnalystAgent(BaseAgent):
    """
    Layer 2 Analyst agent for deep research and pattern analysis.
    
    Uses domain context from prompt_library for enhanced analysis.
    """
    
    def __init__(self, name: str):
        super().__init__(name, role="Analyst")
        self.llm = get_gemini_pro()
        self.structured_llm = self.llm.with_structured_output(ScoutReport)
        self.context = get_alachua_context()

    def _execute(self, input_data: Dict[str, Any]) -> ScoutReport:
        """
        1. Formulate search queries based on topic.
        2. Execute Deep Research (Tavily).
        3. Synthesize findings with domain context into a Report.
        """
        topic = input_data.get("topic")
        if not topic:
            raise ValueError("AnalystAgent requires a 'topic'")

        self.logger.info("Starting deep research", topic=topic)
        
        # 1. Deep Research with domain-aware query
        search_query = f"Current news and development updates regarding {topic} Alachua County Florida"
        research_context = deep_research.invoke(search_query)
        
        self.logger.info("Research complete", context_length=len(research_context))
        
        # 2. Synthesis with domain context
        current_date = datetime.now().date().isoformat()
        
        prompt = ChatPromptTemplate.from_template(
            """You are an **Impact Assessment Analyst** for the Alachua Civic Intelligence System.

{domain_context}

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
        )
        
        chain = prompt | self.structured_llm
        
        result = chain.invoke({
            "domain_context": self.context.get_prompt_context(),
            "agent_id": self.name,
            "date": current_date,
            "topic": topic,
            "research_context": research_context[:60000],  # Leave room for context
            "keywords": self.context.get_keywords_string(),
            "entities": self.context.get_entities_string(),
        })
        
        self.logger.info(
            "Analysis complete",
            alerts_count=len(result.alerts),
            items_count=len(result.items)
        )
        
        return result
