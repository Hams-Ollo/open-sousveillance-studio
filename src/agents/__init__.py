"""
Agents package for Alachua Civic Intelligence System.

Provides the agent classes:
- BaseAgent: Abstract base class with logging
- ScoutAgent: Layer 1 data collection agents
- AnalystAgent: Layer 2 deep research agents
"""

from src.agents.base import BaseAgent
from src.agents.scout import ScoutAgent
from src.agents.analyst import AnalystAgent

# Agent registry: maps agent IDs to (class, layer, description)
AGENT_REGISTRY = {
    "A1": {"class": ScoutAgent, "layer": 1, "description": "Meeting Intelligence Scout"},
    "A2": {"class": ScoutAgent, "layer": 1, "description": "Permit Application Scout"},
    "A3": {"class": ScoutAgent, "layer": 1, "description": "Legislative Code Monitor"},
    "A4": {"class": ScoutAgent, "layer": 1, "description": "Water Resource Scout"},
    "B1": {"class": AnalystAgent, "layer": 2, "description": "Impact Assessment Analyst"},
    "B2": {"class": AnalystAgent, "layer": 2, "description": "Procedural Integrity Analyst"},
}


def get_agent(agent_id: str, **kwargs) -> BaseAgent:
    """
    Create an agent instance by ID.

    Args:
        agent_id: Agent identifier (e.g., "A1", "B1")
        **kwargs: Additional keyword arguments passed to the agent constructor

    Returns:
        Initialized agent instance

    Raises:
        ValueError: If agent_id is not registered
    """
    entry = AGENT_REGISTRY.get(agent_id)
    if not entry:
        valid = ", ".join(sorted(AGENT_REGISTRY.keys()))
        raise ValueError(f"Unknown agent ID: {agent_id!r}. Valid IDs: {valid}")
    cls = entry["class"]
    return cls(name=agent_id, **kwargs)


def get_agent_info(agent_id: str) -> dict:
    """Get metadata about a registered agent."""
    entry = AGENT_REGISTRY.get(agent_id)
    if not entry:
        raise ValueError(f"Unknown agent ID: {agent_id!r}")
    return {"id": agent_id, "layer": entry["layer"], "description": entry["description"]}


def list_agents() -> list[dict]:
    """List all registered agents with metadata."""
    return [
        {"id": aid, "layer": e["layer"], "description": e["description"]}
        for aid, e in sorted(AGENT_REGISTRY.items())
    ]


__all__ = [
    "BaseAgent", "ScoutAgent", "AnalystAgent",
    "AGENT_REGISTRY", "get_agent", "get_agent_info", "list_agents",
]
