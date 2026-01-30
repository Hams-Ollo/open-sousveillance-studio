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

__all__ = ["BaseAgent", "ScoutAgent", "AnalystAgent"]
