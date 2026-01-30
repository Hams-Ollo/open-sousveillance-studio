"""
LangGraph workflow definitions for Alachua Civic Intelligence System.

Provides multi-agent workflows with:
- State management
- Human-in-the-loop checkpoints
- Conditional routing
"""

from typing import TypedDict, Annotated, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.schemas import ScoutReport, UrgencyLevel


# =============================================================================
# STATE DEFINITIONS
# =============================================================================

class ScoutState(TypedDict):
    """State for Scout workflow."""
    url: str
    agent_id: str
    content: str
    report: ScoutReport | None
    error: str | None
    status: str


class AnalystState(TypedDict):
    """State for Analyst workflow."""
    topic: str
    agent_id: str
    scout_reports: list[dict]
    research_context: str
    report: ScoutReport | None
    requires_approval: bool
    approved: bool | None
    error: str | None
    status: str


# =============================================================================
# SCOUT WORKFLOW NODES
# =============================================================================

def fetch_content(state: ScoutState) -> ScoutState:
    """Fetch content from URL using Firecrawl."""
    from src.tools import monitor_url
    
    try:
        content = monitor_url.invoke(state["url"])
        return {
            **state,
            "content": content,
            "status": "content_fetched"
        }
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "status": "failed"
        }


def analyze_content(state: ScoutState) -> ScoutState:
    """Analyze content and generate Scout report."""
    from src.agents.scout import ScoutAgent
    
    if state.get("error"):
        return state
    
    try:
        agent = ScoutAgent(name=state["agent_id"], prompt_template="Standard Scout Prompt")
        report = agent.run({"url": state["url"]})
        
        return {
            **state,
            "report": report,
            "status": "completed"
        }
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "status": "failed"
        }


def save_report(state: ScoutState) -> ScoutState:
    """Save report to database."""
    if state.get("error") or not state.get("report"):
        return state
    
    try:
        from src.database import get_db
        get_db().save_report(state["report"])
        return {
            **state,
            "status": "saved"
        }
    except Exception as e:
        return {
            **state,
            "error": f"Save failed: {e}",
            "status": "save_failed"
        }


def should_continue(state: ScoutState) -> Literal["analyze", "end"]:
    """Determine if workflow should continue or end."""
    if state.get("error"):
        return "end"
    if state.get("status") == "content_fetched":
        return "analyze"
    return "end"


# =============================================================================
# ANALYST WORKFLOW NODES
# =============================================================================

def gather_context(state: AnalystState) -> AnalystState:
    """Gather research context using Tavily."""
    from src.tools import deep_research
    
    try:
        context = deep_research.invoke(f"Recent news about {state['topic']}")
        return {
            **state,
            "research_context": context,
            "status": "context_gathered"
        }
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "status": "failed"
        }


def synthesize_analysis(state: AnalystState) -> AnalystState:
    """Synthesize analysis from context and scout reports."""
    from src.agents.analyst import AnalystAgent
    
    if state.get("error"):
        return state
    
    try:
        agent = AnalystAgent(name=state["agent_id"])
        report = agent.run({"topic": state["topic"]})
        
        # Check if any alerts are RED - requires approval
        has_red_alerts = any(
            alert.level == UrgencyLevel.RED 
            for alert in report.alerts
        )
        
        return {
            **state,
            "report": report,
            "requires_approval": has_red_alerts,
            "status": "analysis_complete"
        }
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "status": "failed"
        }


def check_approval(state: AnalystState) -> Literal["approve", "publish", "end"]:
    """Check if approval is needed."""
    if state.get("error"):
        return "end"
    if state.get("requires_approval") and not state.get("approved"):
        return "approve"
    return "publish"


def request_approval(state: AnalystState) -> AnalystState:
    """Request human approval (interrupt point)."""
    # This is where LangGraph's interrupt() would be called
    # For now, we just mark the state
    return {
        **state,
        "status": "awaiting_approval"
    }


def publish_report(state: AnalystState) -> AnalystState:
    """Publish the approved report."""
    if state.get("error"):
        return state
    
    try:
        from src.database import get_db
        if state.get("report"):
            get_db().save_report(state["report"])
        
        return {
            **state,
            "status": "published"
        }
    except Exception as e:
        return {
            **state,
            "error": f"Publish failed: {e}",
            "status": "publish_failed"
        }


# =============================================================================
# WORKFLOW BUILDERS
# =============================================================================

def create_scout_workflow() -> StateGraph:
    """
    Create a Scout workflow graph.
    
    Flow: fetch_content -> analyze_content -> save_report
    """
    workflow = StateGraph(ScoutState)
    
    # Add nodes
    workflow.add_node("fetch", fetch_content)
    workflow.add_node("analyze", analyze_content)
    workflow.add_node("save", save_report)
    
    # Add edges
    workflow.set_entry_point("fetch")
    workflow.add_conditional_edges(
        "fetch",
        should_continue,
        {
            "analyze": "analyze",
            "end": END
        }
    )
    workflow.add_edge("analyze", "save")
    workflow.add_edge("save", END)
    
    return workflow.compile(checkpointer=MemorySaver())


def create_analyst_workflow() -> StateGraph:
    """
    Create an Analyst workflow graph with human-in-the-loop.
    
    Flow: gather_context -> synthesize -> [approval if needed] -> publish
    """
    workflow = StateGraph(AnalystState)
    
    # Add nodes
    workflow.add_node("gather", gather_context)
    workflow.add_node("synthesize", synthesize_analysis)
    workflow.add_node("approve", request_approval)
    workflow.add_node("publish", publish_report)
    
    # Add edges
    workflow.set_entry_point("gather")
    workflow.add_edge("gather", "synthesize")
    workflow.add_conditional_edges(
        "synthesize",
        check_approval,
        {
            "approve": "approve",
            "publish": "publish",
            "end": END
        }
    )
    workflow.add_edge("approve", "publish")  # After approval, publish
    workflow.add_edge("publish", END)
    
    return workflow.compile(checkpointer=MemorySaver())


# =============================================================================
# WORKFLOW RUNNERS
# =============================================================================

def run_scout_workflow(url: str, agent_id: str = "A1") -> ScoutState:
    """
    Run the Scout workflow on a URL.
    
    Args:
        url: URL to monitor
        agent_id: Scout agent ID
    
    Returns:
        Final workflow state
    """
    workflow = create_scout_workflow()
    
    initial_state: ScoutState = {
        "url": url,
        "agent_id": agent_id,
        "content": "",
        "report": None,
        "error": None,
        "status": "started"
    }
    
    config = {"configurable": {"thread_id": f"scout-{datetime.now().isoformat()}"}}
    result = workflow.invoke(initial_state, config)
    
    return result


def run_analyst_workflow(topic: str, agent_id: str = "B1") -> AnalystState:
    """
    Run the Analyst workflow on a topic.
    
    Args:
        topic: Research topic
        agent_id: Analyst agent ID
    
    Returns:
        Final workflow state
    """
    workflow = create_analyst_workflow()
    
    initial_state: AnalystState = {
        "topic": topic,
        "agent_id": agent_id,
        "scout_reports": [],
        "research_context": "",
        "report": None,
        "requires_approval": False,
        "approved": None,
        "error": None,
        "status": "started"
    }
    
    config = {"configurable": {"thread_id": f"analyst-{datetime.now().isoformat()}"}}
    result = workflow.invoke(initial_state, config)
    
    return result
