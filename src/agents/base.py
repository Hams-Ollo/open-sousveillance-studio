import time
from typing import Any, Dict
from abc import ABC, abstractmethod

from src.schemas import BaseReport
from src.logging_config import get_logger


class BaseAgent(ABC):
    """Base class for all agents with built-in logging."""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.logger = get_logger(f"agents.{name.lower()}", agent_id=name, role=role)

    def run(self, input_data: Dict[str, Any]) -> BaseReport:
        """
        Executes the agent's logic with logging wrapper.
        
        Subclasses should implement _execute() instead of overriding run().
        """
        self.logger.info("Agent run started", input_keys=list(input_data.keys()))
        start_time = time.time()
        
        try:
            result = self._execute(input_data)
            duration_ms = (time.time() - start_time) * 1000
            
            self.logger.info(
                "Agent run completed",
                report_id=result.report_id,
                alerts_count=len(result.alerts),
                duration_ms=round(duration_ms, 2)
            )
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Agent run failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2)
            )
            raise

    @abstractmethod
    def _execute(self, input_data: Dict[str, Any]) -> BaseReport:
        """
        Implement agent logic here.
        
        Must return a structured report (ScoutReport, AnalystReport, or SynthesizerReport).
        """
        pass
