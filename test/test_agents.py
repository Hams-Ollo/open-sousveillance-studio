"""
Tests for agent classes.

Mocks google.generativeai and prompt context so tests run without
real API keys or LLM calls.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.schemas import (
    ScoutReport, AnalystReport, AnalysisSection,
    UrgencyAlert, UrgencyLevel, MeetingItem,
    CivicCategory, Significance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scout_report(**overrides) -> ScoutReport:
    """Build a minimal valid ScoutReport for mock returns."""
    defaults = dict(
        report_id="A1-2026-01-30-001",
        period_covered="2026-01-30",
        executive_summary="Test summary",
        alerts=[],
        items=[
            MeetingItem(
                agenda_id=None,
                topic="Test item",
                summary="A test agenda item.",
                category=CivicCategory.OTHER,
                significance=Significance.ROUTINE,
                related_to=[],
                outcome=None,
                priority_flag=False,
                priority_reason=None,
                watchlist_matches=[],
            )
        ],
    )
    defaults.update(overrides)
    return ScoutReport(**defaults)


def _make_analyst_report(**overrides) -> AnalystReport:
    """Build a minimal valid AnalystReport for mock returns."""
    defaults = dict(
        report_id="B1-2026-01-30-001",
        period_covered="2026-01-25 to 2026-01-30",
        executive_summary="Analysis summary",
        alerts=[],
        topic="Test Topic",
        scout_report_ids=[],
        sections=[
            AnalysisSection(
                title="Overview",
                content="Test content",
                sources=["test-source"],
                confidence=0.9,
            )
        ],
        recommendations=["Monitor situation"],
        entities_mentioned=["Test Entity"],
    )
    defaults.update(overrides)
    return AnalystReport(**defaults)


def _mock_prompt_context():
    """Return a mock AlachuaContext with the methods agents call."""
    ctx = MagicMock()
    ctx.get_prompt_context.return_value = "Mock domain context"
    ctx.get_keywords_string.return_value = "test, keywords"
    ctx.get_entities_string.return_value = "Test Entity"
    return ctx


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    def test_base_agent_logging_setup(self):
        """Test that BaseAgent sets up logging correctly."""
        from src.agents.base import BaseAgent

        class DummyAgent(BaseAgent):
            def _execute(self, input_data):
                return _make_scout_report()

        agent = DummyAgent(name="TestAgent", role="Tester")
        assert agent.name == "TestAgent"
        assert agent.role == "Tester"
        assert agent.logger is not None

    def test_base_agent_run_returns_report(self):
        """Test that run() delegates to _execute and returns a report."""
        from src.agents.base import BaseAgent

        expected = _make_scout_report()

        class DummyAgent(BaseAgent):
            def _execute(self, input_data):
                return expected

        agent = DummyAgent(name="TestAgent", role="Tester")
        result = agent.run({"key": "value"})
        assert result.report_id == expected.report_id

    def test_base_agent_run_raises_on_failure(self):
        """Test that run() propagates exceptions from _execute."""
        from src.agents.base import BaseAgent

        class FailAgent(BaseAgent):
            def _execute(self, input_data):
                raise ValueError("Intentional failure")

        agent = FailAgent(name="FailAgent", role="Tester")
        with pytest.raises(ValueError, match="Intentional failure"):
            agent.run({})


# ---------------------------------------------------------------------------
# ScoutAgent
# ---------------------------------------------------------------------------

class TestScoutAgent:
    """Tests for ScoutAgent class."""

    @patch("src.agents.scout.get_alachua_context")
    @patch("src.agents.scout.get_gemini_pro")
    def test_scout_agent_initialization(self, mock_gemini, mock_ctx):
        """Test ScoutAgent initializes with LLM and context."""
        mock_ctx.return_value = _mock_prompt_context()
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        mock_gemini.return_value = mock_llm

        from src.agents.scout import ScoutAgent
        agent = ScoutAgent(name="TestScout")

        assert agent.name == "TestScout"
        assert agent.role == "Scout"
        mock_gemini.assert_called_once()
        mock_llm.with_structured_output.assert_called_once_with(ScoutReport)

    @patch("src.agents.scout.get_alachua_context")
    @patch("src.agents.scout.get_gemini_pro")
    def test_scout_requires_meeting_or_url(self, mock_gemini, mock_ctx):
        """Test that ScoutAgent raises when neither 'meeting' nor 'url' is given."""
        mock_ctx.return_value = _mock_prompt_context()
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        mock_gemini.return_value = mock_llm

        from src.agents.scout import ScoutAgent
        agent = ScoutAgent(name="TestScout")

        with pytest.raises(ValueError, match="requires either"):
            agent.run({})

    @patch("src.agents.scout.get_alachua_context")
    @patch("src.agents.scout.get_gemini_pro")
    def test_scout_meeting_mode_pdf(self, mock_gemini, mock_ctx):
        """Test ScoutAgent analyzes a meeting with PDF content."""
        mock_ctx.return_value = _mock_prompt_context()
        expected = _make_scout_report()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = expected
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_gemini.return_value = mock_llm

        from src.agents.scout import ScoutAgent
        agent = ScoutAgent(name="TestScout")

        meeting = {
            "meeting_id": "12345",
            "title": "BOCC Regular Meeting",
            "meeting_date": "2026-01-30",
            "board": "Board of County Commissioners",
            "pdf_content": "Agenda item 1: Zoning amendment...",
        }
        result = agent.run({"meeting": meeting})

        assert result.report_id == expected.report_id
        mock_structured.invoke.assert_called_once()
        prompt_arg = mock_structured.invoke.call_args[0][0]
        assert "FULL PDF ANALYSIS" in prompt_arg

    @patch("src.agents.scout.get_alachua_context")
    @patch("src.agents.scout.get_gemini_pro")
    def test_scout_meeting_mode_metadata_only(self, mock_gemini, mock_ctx):
        """Test ScoutAgent falls back to metadata when no PDF available."""
        mock_ctx.return_value = _mock_prompt_context()
        expected = _make_scout_report()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = expected
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_gemini.return_value = mock_llm

        from src.agents.scout import ScoutAgent
        agent = ScoutAgent(name="TestScout")

        meeting = {
            "meeting_id": "12345",
            "title": "BOCC Regular Meeting",
            "meeting_date": "2026-01-30",
            "board": "Board of County Commissioners",
        }
        result = agent.run({"meeting": meeting})

        assert result.report_id == expected.report_id
        mock_structured.invoke.assert_called_once()
        prompt_arg = mock_structured.invoke.call_args[0][0]
        assert "METADATA ONLY" in prompt_arg


# ---------------------------------------------------------------------------
# AnalystAgent
# ---------------------------------------------------------------------------

class TestAnalystAgent:
    """Tests for AnalystAgent class."""

    @patch("src.agents.analyst.get_alachua_context")
    @patch("src.agents.analyst.get_gemini_pro")
    def test_analyst_agent_initialization(self, mock_gemini, mock_ctx):
        """Test AnalystAgent initializes with AnalystReport schema."""
        mock_ctx.return_value = _mock_prompt_context()
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        mock_gemini.return_value = mock_llm

        from src.agents.analyst import AnalystAgent, ResearchProvider
        agent = AnalystAgent(name="TestAnalyst", research_provider=ResearchProvider.TAVILY)

        assert agent.name == "TestAnalyst"
        assert agent.role == "Analyst"
        mock_llm.with_structured_output.assert_called_once_with(AnalystReport)

    @patch("src.agents.analyst.get_alachua_context")
    @patch("src.agents.analyst.get_gemini_pro")
    def test_analyst_requires_topic(self, mock_gemini, mock_ctx):
        """Test that AnalystAgent raises when 'topic' is missing."""
        mock_ctx.return_value = _mock_prompt_context()
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        mock_gemini.return_value = mock_llm

        from src.agents.analyst import AnalystAgent, ResearchProvider
        agent = AnalystAgent(name="TestAnalyst", research_provider=ResearchProvider.TAVILY)

        with pytest.raises(ValueError, match="requires a 'topic'"):
            agent.run({})

    @patch("src.agents.analyst.deep_research")
    @patch("src.agents.analyst.get_alachua_context")
    @patch("src.agents.analyst.get_gemini_pro")
    def test_analyst_tavily_research_flow(self, mock_gemini, mock_ctx, mock_tavily):
        """Test AnalystAgent runs Tavily research and returns AnalystReport."""
        mock_ctx.return_value = _mock_prompt_context()
        expected = _make_analyst_report()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = expected
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_gemini.return_value = mock_llm
        mock_tavily.invoke.return_value = "Tavily research results..."

        from src.agents.analyst import AnalystAgent, ResearchProvider
        agent = AnalystAgent(name="TestAnalyst", research_provider=ResearchProvider.TAVILY)

        result = agent.run({"topic": "Alachua County development"})

        assert isinstance(result, AnalystReport)
        assert result.report_id == expected.report_id
        assert len(result.sections) == 1
        mock_tavily.invoke.assert_called_once()
        mock_structured.invoke.assert_called_once()
        prompt_arg = mock_structured.invoke.call_args[0][0]
        assert "AnalystReport" in prompt_arg

    @patch("src.agents.analyst.deep_research")
    @patch("src.agents.analyst.get_alachua_context")
    @patch("src.agents.analyst.get_gemini_pro")
    def test_analyst_handles_tavily_failure(self, mock_gemini, mock_ctx, mock_tavily):
        """Test AnalystAgent gracefully handles Tavily failure."""
        mock_ctx.return_value = _mock_prompt_context()
        expected = _make_analyst_report()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = expected
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        mock_gemini.return_value = mock_llm
        mock_tavily.invoke.side_effect = Exception("Tavily API error")

        from src.agents.analyst import AnalystAgent, ResearchProvider
        agent = AnalystAgent(name="TestAnalyst", research_provider=ResearchProvider.TAVILY)

        result = agent.run({"topic": "Test topic"})

        assert isinstance(result, AnalystReport)
        mock_structured.invoke.assert_called_once()
        prompt_arg = mock_structured.invoke.call_args[0][0]
        assert "Tavily search failed" in prompt_arg
