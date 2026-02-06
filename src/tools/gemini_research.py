"""
Gemini Deep Research Client for Open Sousveillance Studio.

Provides access to Google's Deep Research Agent via the Interactions API.
This is a long-running, agentic research tool that performs autonomous
planning, searching, reading, and reasoning.

Usage:
    client = GeminiResearchClient()
    result = client.research("What are the latest developments in Alachua County?")
    print(result.text)
"""

import os
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

from src.logging_config import get_logger

logger = get_logger("tools.gemini_research")

# Agent model name for Deep Research
DEEP_RESEARCH_AGENT = "deep-research-pro-preview-12-2025"


class ResearchStatus(Enum):
    """Status of a research interaction."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchResult:
    """Result from a Gemini Deep Research query."""
    interaction_id: str
    status: ResearchStatus
    text: Optional[str] = None
    sources: List[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class GeminiResearchClient:
    """
    Client for Google Gemini Deep Research Agent.

    Uses the Interactions API to perform long-running research tasks.
    The agent autonomously plans, searches, reads, and synthesizes information.

    Usage:
        client = GeminiResearchClient()

        # Synchronous (blocking) research
        result = client.research("Research topic here")

        # Async research with polling
        interaction_id = client.start_research("Research topic")
        while True:
            result = client.get_result(interaction_id)
            if result.status in [ResearchStatus.COMPLETED, ResearchStatus.FAILED]:
                break
            time.sleep(10)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini Research client.

        Args:
            api_key: Google API key. If not provided, uses GOOGLE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found. Set environment variable or pass api_key.")

        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize the Google GenAI client."""
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            logger.info("Gemini Research client initialized")
        except ImportError:
            logger.error("google-genai package not installed. Run: pip install google-genai")
            raise ImportError("google-genai package required. Install with: pip install google-genai")

    def start_research(
        self,
        query: str,
        context: Optional[str] = None
    ) -> str:
        """
        Start a background research task.

        Args:
            query: The research question or topic
            context: Optional additional context to guide research

        Returns:
            Interaction ID for polling results
        """
        full_query = query
        if context:
            full_query = f"{context}\n\nResearch Question: {query}"

        logger.info("Starting Gemini Deep Research", query=query[:100])

        try:
            interaction = self._client.interactions.create(
                input=full_query,
                agent=DEEP_RESEARCH_AGENT,
                background=True
            )
            logger.info("Research started", interaction_id=interaction.id)
            return interaction.id

        except Exception as e:
            logger.error("Failed to start research", error=str(e))
            raise

    def get_result(self, interaction_id: str) -> ResearchResult:
        """
        Get the current status/result of a research interaction.

        Args:
            interaction_id: ID from start_research()

        Returns:
            ResearchResult with current status and any available output
        """
        try:
            interaction = self._client.interactions.get(interaction_id)

            status_map = {
                "pending": ResearchStatus.PENDING,
                "running": ResearchStatus.RUNNING,
                "completed": ResearchStatus.COMPLETED,
                "failed": ResearchStatus.FAILED,
            }
            status = status_map.get(interaction.status, ResearchStatus.RUNNING)

            result = ResearchResult(
                interaction_id=interaction_id,
                status=status
            )

            if status == ResearchStatus.COMPLETED and interaction.outputs:
                result.text = interaction.outputs[-1].text

            if status == ResearchStatus.FAILED:
                result.error = getattr(interaction, 'error', 'Unknown error')

            return result

        except Exception as e:
            logger.error("Failed to get research result", interaction_id=interaction_id, error=str(e))
            return ResearchResult(
                interaction_id=interaction_id,
                status=ResearchStatus.FAILED,
                error=str(e)
            )

    def research(
        self,
        query: str,
        context: Optional[str] = None,
        timeout_seconds: int = 300,
        poll_interval: int = 10
    ) -> ResearchResult:
        """
        Perform synchronous (blocking) research.

        Starts research and polls until completion or timeout.

        Args:
            query: The research question or topic
            context: Optional additional context
            timeout_seconds: Maximum time to wait (default 5 minutes)
            poll_interval: Seconds between status checks

        Returns:
            ResearchResult with final output
        """
        start_time = time.time()

        interaction_id = self.start_research(query, context)

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout_seconds:
                logger.warning("Research timed out", interaction_id=interaction_id, elapsed=elapsed)
                return ResearchResult(
                    interaction_id=interaction_id,
                    status=ResearchStatus.FAILED,
                    error=f"Research timed out after {timeout_seconds} seconds",
                    duration_seconds=elapsed
                )

            result = self.get_result(interaction_id)
            result.duration_seconds = elapsed

            if result.status == ResearchStatus.COMPLETED:
                logger.info(
                    "Research completed",
                    interaction_id=interaction_id,
                    duration_s=round(elapsed, 2),
                    output_length=len(result.text) if result.text else 0
                )
                return result

            if result.status == ResearchStatus.FAILED:
                logger.error("Research failed", interaction_id=interaction_id, error=result.error)
                return result

            logger.debug("Research in progress", interaction_id=interaction_id, elapsed=round(elapsed, 1))
            time.sleep(poll_interval)


# Singleton instance
import threading

_gemini_research_client: Optional[GeminiResearchClient] = None
_gemini_lock = threading.Lock()


def get_gemini_research_client() -> Optional[GeminiResearchClient]:
    """Get or create the Gemini Research client singleton."""
    global _gemini_research_client
    if _gemini_research_client is None:
        with _gemini_lock:
            if _gemini_research_client is None:
                try:
                    _gemini_research_client = GeminiResearchClient()
                except (ValueError, ImportError) as e:
                    logger.warning("Could not initialize Gemini Research client", error=str(e))
                    return None
    return _gemini_research_client


def gemini_deep_research(
    query: str,
    context: Optional[str] = None,
    timeout_seconds: int = 300
) -> str:
    """
    Convenience function for Gemini Deep Research.

    Args:
        query: Research question or topic
        context: Optional context to guide research
        timeout_seconds: Maximum wait time

    Returns:
        Research output text or error message
    """
    client = get_gemini_research_client()
    if not client:
        return "Error: Gemini Research client not available. Check GOOGLE_API_KEY."

    try:
        result = client.research(query, context=context, timeout_seconds=timeout_seconds)
        if result.status == ResearchStatus.COMPLETED and result.text:
            return result.text
        else:
            return f"Research failed: {result.error or 'Unknown error'}"
    except Exception as e:
        return f"Research error: {str(e)}"
