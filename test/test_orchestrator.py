"""
Tests for the Orchestrator module.

CR-18: Unit tests with mocked dependencies for the central pipeline coordinator.
Tests cover: initialization, source routing, job runners, intelligence bridge,
analysis pipeline, deep research, RAG integration, and summary generation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from src.orchestrator import (
    Orchestrator,
    JobResult,
    JobStatus,
    PipelineRun,
    SourceType,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Mock Database instance."""
    db = MagicMock()
    db.get_meetings_by_source.return_value = []
    db.get_unanalyzed_meetings.return_value = []
    db.get_high_relevance_reports.return_value = []
    db.save_report.return_value = None
    db.mark_meeting_analyzed.return_value = None
    db.save_deep_research_report.return_value = None
    return db


@pytest.fixture
def mock_sources():
    """Mock source configs."""
    civicclerk = MagicMock()
    civicclerk.id = "alachua-civicclerk"
    civicclerk.url = "https://alachuafl.portal.civicclerk.com/"
    civicclerk.priority = "critical"
    civicclerk.check_frequency = "daily"

    florida = MagicMock()
    florida.id = "florida-public-notices"
    florida.url = "https://floridapublicnotices.com"
    florida.priority = "high"
    florida.check_frequency = "daily"

    srwmd = MagicMock()
    srwmd.id = "srwmd-permit-applications"
    srwmd.url = "https://srwmd.example.com"
    srwmd.priority = "high"
    srwmd.check_frequency = "daily"

    return {
        "alachua-civicclerk": civicclerk,
        "florida-public-notices": florida,
        "srwmd-permit-applications": srwmd,
    }


@pytest.fixture
def orchestrator(mock_db, mock_sources):
    """Create an Orchestrator with all dependencies mocked."""
    with patch("src.orchestrator.Database", return_value=mock_db), \
         patch("src.orchestrator.get_all_sources") as mock_get_sources, \
         patch("src.orchestrator.ScoutAgent") as mock_scout_cls, \
         patch("src.orchestrator.AnalystAgent") as mock_analyst_cls, \
         patch("src.orchestrator.CivicClerkScraper") as mock_cc_cls, \
         patch("src.orchestrator.FloridaNoticesScraper") as mock_fn_cls, \
         patch("src.orchestrator.SRWMDScraper") as mock_srwmd_cls, \
         patch("src.orchestrator.get_event_store") as mock_es, \
         patch("src.orchestrator.get_rules_engine") as mock_re:

        mock_get_sources.return_value = list(mock_sources.values())

        mock_scout = MagicMock()
        mock_scout_cls.return_value = mock_scout

        mock_analyst = MagicMock()
        mock_analyst_cls.return_value = mock_analyst

        mock_cc = MagicMock()
        mock_cc_cls.return_value = mock_cc

        mock_fn = MagicMock()
        mock_fn_cls.return_value = mock_fn

        mock_srwmd = MagicMock()
        mock_srwmd_cls.return_value = mock_srwmd

        mock_event_store = MagicMock()
        mock_event_store.save_events.return_value = {"new": 0, "updated": 0, "unchanged": 0}
        mock_es.return_value = mock_event_store

        mock_rules = MagicMock()
        mock_rules.evaluate_batch.return_value = []
        mock_re.return_value = mock_rules

        orch = Orchestrator(db=mock_db)

        # Attach mocks for assertions in tests
        orch._mock_scout = mock_scout
        orch._mock_analyst = mock_analyst
        orch._mock_cc = mock_cc
        orch._mock_fn = mock_fn
        orch._mock_srwmd = mock_srwmd
        orch._mock_event_store = mock_event_store
        orch._mock_rules = mock_rules

        yield orch


# =============================================================================
# DATA MODEL TESTS
# =============================================================================

class TestJobResult:
    """Tests for JobResult dataclass."""

    def test_duration_seconds(self):
        start = datetime(2026, 2, 6, 10, 0, 0)
        end = datetime(2026, 2, 6, 10, 0, 30)
        job = JobResult(
            source_id="test",
            status=JobStatus.COMPLETED,
            started_at=start,
            completed_at=end,
        )
        assert job.duration_seconds == 30.0

    def test_duration_seconds_no_end(self):
        job = JobResult(
            source_id="test",
            status=JobStatus.RUNNING,
            started_at=datetime.now(),
        )
        assert job.duration_seconds == 0.0


class TestPipelineRun:
    """Tests for PipelineRun dataclass."""

    def test_aggregation_properties(self):
        run = PipelineRun(run_id="test-run", started_at=datetime.now())
        run.jobs = [
            JobResult(
                source_id="a", status=JobStatus.COMPLETED,
                started_at=datetime.now(),
                items_discovered=10, items_new=3, items_analyzed=2,
            ),
            JobResult(
                source_id="b", status=JobStatus.FAILED,
                started_at=datetime.now(),
                items_discovered=5, items_new=1, items_analyzed=0,
                error="test error",
            ),
        ]
        assert run.total_discovered == 15
        assert run.total_new == 4
        assert run.total_analyzed == 2
        assert run.successful_jobs == 1
        assert run.failed_jobs == 1


# =============================================================================
# ORCHESTRATOR INITIALIZATION TESTS
# =============================================================================

class TestOrchestratorInit:
    """Tests for Orchestrator initialization."""

    def test_sources_loaded(self, orchestrator):
        assert len(orchestrator.sources) == 3
        assert "alachua-civicclerk" in orchestrator.sources

    def test_scrapers_initialized(self, orchestrator):
        assert SourceType.CIVICCLERK in orchestrator.scrapers
        assert SourceType.FLORIDA_NOTICES in orchestrator.scrapers
        assert SourceType.SRWMD in orchestrator.scrapers

    def test_adapters_initialized(self, orchestrator):
        assert SourceType.CIVICCLERK in orchestrator.adapters
        assert SourceType.FLORIDA_NOTICES in orchestrator.adapters
        assert SourceType.SRWMD in orchestrator.adapters


# =============================================================================
# SOURCE ROUTING TESTS
# =============================================================================

class TestSourceRouting:
    """Tests for source-to-scraper routing."""

    def test_extract_civicclerk_site_id(self, orchestrator):
        assert orchestrator._extract_civicclerk_site_id(
            "https://alachuafl.portal.civicclerk.com/"
        ) == "alachuafl"

    def test_extract_civicclerk_site_id_fallback(self, orchestrator):
        assert orchestrator._extract_civicclerk_site_id(
            "https://example.com"
        ) == "alachuafl"

    def test_get_scraper_civicclerk(self, orchestrator):
        source = orchestrator.sources["alachua-civicclerk"]
        scraper = orchestrator._get_scraper_for_source(source)
        assert scraper is not None

    def test_get_scraper_florida(self, orchestrator):
        source = orchestrator.sources["florida-public-notices"]
        scraper = orchestrator._get_scraper_for_source(source)
        assert scraper is not None

    def test_get_scraper_unknown(self, orchestrator):
        source = MagicMock()
        source.id = "unknown-source-xyz"
        scraper = orchestrator._get_scraper_for_source(source)
        assert scraper is None

    def test_frequency_to_timedelta(self, orchestrator):
        assert orchestrator._frequency_to_timedelta("hourly") == timedelta(hours=1)
        assert orchestrator._frequency_to_timedelta("daily") == timedelta(days=1)
        assert orchestrator._frequency_to_timedelta("weekly") == timedelta(weeks=1)
        assert orchestrator._frequency_to_timedelta("monthly") == timedelta(days=30)
        assert orchestrator._frequency_to_timedelta("unknown") == timedelta(days=1)


# =============================================================================
# RUN SOURCE TESTS
# =============================================================================

class TestRunSource:
    """Tests for run_source method."""

    def test_unknown_source_fails(self, orchestrator):
        result = orchestrator.run_source("nonexistent-source")
        assert result.status == JobStatus.FAILED
        assert "not found" in result.error

    def test_civicclerk_job_routed(self, orchestrator):
        orchestrator.scrapers[SourceType.CIVICCLERK].run_hybrid_pipeline.return_value = {
            "phase1_discovery": {"total_discovered": 5, "new": ["a", "b"]},
            "raw_meetings": [],
        }
        result = orchestrator.run_source("alachua-civicclerk", skip_analysis=True)
        assert result.status == JobStatus.COMPLETED
        assert result.items_discovered == 5
        assert result.items_new == 2

    def test_florida_notices_job_routed(self, orchestrator):
        orchestrator.scrapers[SourceType.FLORIDA_NOTICES].run_hybrid_pipeline.return_value = {
            "phase1_discovery": {"total_discovered": 3, "new": ["x"]},
            "raw_notices": [],
        }
        result = orchestrator.run_source("florida-public-notices", skip_analysis=True)
        assert result.status == JobStatus.COMPLETED
        assert result.items_discovered == 3
        assert result.items_new == 1

    def test_srwmd_job_routed(self, orchestrator):
        orchestrator.scrapers[SourceType.SRWMD].run_hybrid_pipeline.return_value = {
            "phase1_discovery": {"total_discovered": 7, "new": []},
            "permits_ready_for_analysis": ["p1", "p2"],
            "raw_notices": [],
        }
        result = orchestrator.run_source("srwmd-permit-applications", skip_analysis=True)
        assert result.status == JobStatus.COMPLETED
        assert result.items_discovered == 7
        assert result.items_new == 2

    def test_scraper_exception_caught(self, orchestrator):
        orchestrator.scrapers[SourceType.CIVICCLERK].run_hybrid_pipeline.side_effect = \
            RuntimeError("Network error")
        result = orchestrator.run_source("alachua-civicclerk")
        assert result.status == JobStatus.FAILED
        assert "Network error" in result.error

    def test_analysis_runs_when_new_items(self, orchestrator, mock_db):
        orchestrator.scrapers[SourceType.CIVICCLERK].run_hybrid_pipeline.return_value = {
            "phase1_discovery": {"total_discovered": 1, "new": ["m1"]},
            "raw_meetings": [],
        }
        mock_db.get_unanalyzed_meetings.return_value = [
            {"meeting_id": "m1", "title": "Test Meeting", "pdf_content": ""}
        ]
        with patch.object(orchestrator, "_run_analysis", return_value=1) as mock_analysis:
            result = orchestrator.run_source("alachua-civicclerk")
            mock_analysis.assert_called_once_with("alachua-civicclerk")
            assert result.items_analyzed == 1

    def test_analysis_skipped_when_no_new_items(self, orchestrator):
        orchestrator.scrapers[SourceType.CIVICCLERK].run_hybrid_pipeline.return_value = {
            "phase1_discovery": {"total_discovered": 5, "new": []},
            "raw_meetings": [],
        }
        with patch.object(orchestrator, "_run_analysis") as mock_analysis:
            orchestrator.run_source("alachua-civicclerk")
            mock_analysis.assert_not_called()

    def test_analysis_skipped_when_flag_set(self, orchestrator):
        orchestrator.scrapers[SourceType.CIVICCLERK].run_hybrid_pipeline.return_value = {
            "phase1_discovery": {"total_discovered": 1, "new": ["m1"]},
            "raw_meetings": [],
        }
        with patch.object(orchestrator, "_run_analysis") as mock_analysis:
            orchestrator.run_source("alachua-civicclerk", skip_analysis=True)
            mock_analysis.assert_not_called()


# =============================================================================
# PIPELINE TESTS
# =============================================================================

class TestRunPipeline:
    """Tests for run_pipeline method."""

    def test_pipeline_with_specific_sources(self, orchestrator):
        with patch.object(orchestrator, "run_source") as mock_run:
            mock_run.return_value = JobResult(
                source_id="alachua-civicclerk",
                status=JobStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )
            result = orchestrator.run_pipeline(source_ids=["alachua-civicclerk"])
            assert len(result.jobs) == 1
            mock_run.assert_called_once()

    def test_pipeline_force_runs_all(self, orchestrator):
        with patch.object(orchestrator, "run_source") as mock_run:
            mock_run.return_value = JobResult(
                source_id="test", status=JobStatus.COMPLETED,
                started_at=datetime.now(), completed_at=datetime.now(),
            )
            result = orchestrator.run_pipeline(force=True)
            assert len(result.jobs) == 3  # All 3 sources

    def test_pipeline_run_id_format(self, orchestrator):
        with patch.object(orchestrator, "run_source") as mock_run:
            mock_run.return_value = JobResult(
                source_id="test", status=JobStatus.COMPLETED,
                started_at=datetime.now(), completed_at=datetime.now(),
            )
            result = orchestrator.run_pipeline(force=True)
            assert result.run_id.startswith("run-")

    def test_pipeline_unknown_source_ignored(self, orchestrator):
        with patch.object(orchestrator, "run_source") as mock_run:
            result = orchestrator.run_pipeline(source_ids=["nonexistent"])
            mock_run.assert_not_called()
            assert len(result.jobs) == 0


# =============================================================================
# INTELLIGENCE LAYER TESTS
# =============================================================================

class TestProcessIntelligence:
    """Tests for the intelligence bridge."""

    def test_no_adapter_logs_warning(self, orchestrator):
        job = JobResult(source_id="test", status=JobStatus.RUNNING, started_at=datetime.now())
        orchestrator._process_intelligence("unknown-type", [MagicMock()], job)
        assert job.events_created == 0

    def test_empty_items_noop(self, orchestrator):
        job = JobResult(source_id="test", status=JobStatus.RUNNING, started_at=datetime.now())
        orchestrator._process_intelligence(SourceType.CIVICCLERK, [], job)
        orchestrator.event_store.save_events.assert_not_called()

    def test_events_saved_and_evaluated(self, orchestrator):
        mock_event = MagicMock()
        with patch.object(orchestrator.adapters[SourceType.CIVICCLERK], "adapt", return_value=[mock_event]):
            orchestrator.event_store.save_events.return_value = {"new": 1, "updated": 0, "unchanged": 0}
            orchestrator.rules_engine.evaluate_batch.return_value = []

            job = JobResult(source_id="test", status=JobStatus.RUNNING, started_at=datetime.now())
            orchestrator._process_intelligence(SourceType.CIVICCLERK, [MagicMock()], job)

            orchestrator.event_store.save_events.assert_called_once_with([mock_event])
            orchestrator.rules_engine.evaluate_batch.assert_called_once_with([mock_event])
            assert job.events_created == 1

    def test_alerts_attached_to_job(self, orchestrator):
        mock_event = MagicMock()
        mock_alert = MagicMock()
        mock_alert.severity.value = "warning"
        with patch.object(orchestrator.adapters[SourceType.CIVICCLERK], "adapt", return_value=[mock_event]):
            orchestrator.event_store.save_events.return_value = {"new": 1, "updated": 0, "unchanged": 0}
            orchestrator.rules_engine.evaluate_batch.return_value = [mock_alert]

            job = JobResult(source_id="test", status=JobStatus.RUNNING, started_at=datetime.now())
            orchestrator._process_intelligence(SourceType.CIVICCLERK, [MagicMock()], job)

            assert job.alerts_generated == [mock_alert]

    def test_intelligence_exception_caught(self, orchestrator):
        with patch.object(orchestrator.adapters[SourceType.CIVICCLERK], "adapt", side_effect=RuntimeError("Adapter error")):
            job = JobResult(source_id="test", status=JobStatus.RUNNING, started_at=datetime.now())
            # Should not raise
            orchestrator._process_intelligence(SourceType.CIVICCLERK, [MagicMock()], job)
            assert job.events_created == 0


# =============================================================================
# RAG PIPELINE TESTS
# =============================================================================

class TestRAGIntegration:
    """Tests for RAG pipeline integration."""

    def test_get_rag_returns_none_on_failure(self, orchestrator):
        orchestrator._rag_pipeline = None
        with patch("src.tools.rag_pipeline.get_rag_pipeline", side_effect=ImportError("no module")):
            result = orchestrator._get_rag()
            assert result is None

    def test_get_rag_caches_failure(self, orchestrator):
        orchestrator._rag_pipeline = None
        with patch("src.tools.rag_pipeline.get_rag_pipeline", side_effect=Exception("unavailable")):
            orchestrator._get_rag()
            assert orchestrator._rag_pipeline is False

    def test_retrieve_rag_context_empty_when_unavailable(self, orchestrator):
        orchestrator._rag_pipeline = False  # Sentinel for failed init
        result = orchestrator._retrieve_rag_context("test query")
        assert result == ""

    def test_ingest_to_rag_noop_when_unavailable(self, orchestrator):
        orchestrator._rag_pipeline = False
        # Should not raise
        orchestrator._ingest_to_rag(text="hello", document_id="doc-1")

    def test_retrieve_rag_context_returns_content(self, orchestrator):
        mock_rag = MagicMock()
        mock_rag.retrieve_context.return_value = "Related meeting about zoning."
        orchestrator._rag_pipeline = mock_rag

        result = orchestrator._retrieve_rag_context("zoning amendment")
        assert result == "Related meeting about zoning."

    def test_retrieve_rag_context_ignores_no_results(self, orchestrator):
        mock_rag = MagicMock()
        mock_rag.retrieve_context.return_value = "No relevant context found."
        orchestrator._rag_pipeline = mock_rag

        result = orchestrator._retrieve_rag_context("obscure topic")
        assert result == ""


# =============================================================================
# BUILD WATCHLIST TESTS
# =============================================================================

class TestBuildWatchlist:
    """Tests for _build_watchlist helper."""

    def test_empty_entities(self, orchestrator):
        result = orchestrator._build_watchlist({})
        assert result == "No specific watchlist configured."

    def test_builds_from_projects(self, orchestrator):
        entities = {
            "projects": [
                {"name": "Tara Forest", "description": "Dev project", "aliases": ["TF"]},
            ]
        }
        result = orchestrator._build_watchlist(entities)
        assert "Tara Forest" in result
        assert "Dev project" in result
        assert "Alias: TF" in result

    def test_builds_from_organizations(self, orchestrator):
        entities = {
            "organizations": [
                {"name": "Acme LLC", "type": "developer", "principals": ["John Doe"]},
            ]
        }
        result = orchestrator._build_watchlist(entities)
        assert "Acme LLC" in result
        assert "Principal: John Doe" in result

    def test_builds_from_people(self, orchestrator):
        entities = {
            "people": [
                {"name": "Jane Smith", "role": "Commissioner"},
            ]
        }
        result = orchestrator._build_watchlist(entities)
        assert "Jane Smith" in result
        assert "Commissioner" in result


# =============================================================================
# DEEP RESEARCH TESTS
# =============================================================================

class TestDeepResearch:
    """Tests for _run_deep_research method."""

    def test_no_high_relevance_returns_zero(self, orchestrator, mock_db):
        mock_db.get_high_relevance_reports.return_value = []
        result = orchestrator._run_deep_research("alachua-civicclerk")
        assert result == 0

    def test_deep_research_runs_analyst(self, orchestrator, mock_db):
        mock_db.get_high_relevance_reports.return_value = [
            {"report_id": "r1", "executive_summary": "Important zoning change"},
        ]
        mock_report = MagicMock()
        orchestrator.analyst.run.return_value = mock_report

        result = orchestrator._run_deep_research("alachua-civicclerk")
        assert result == 1
        orchestrator.analyst.run.assert_called_once()
        mock_db.save_deep_research_report.assert_called_once()

    def test_deep_research_limited_to_three(self, orchestrator, mock_db):
        mock_db.get_high_relevance_reports.return_value = [
            {"report_id": f"r{i}", "executive_summary": f"Topic {i}"}
            for i in range(10)
        ]
        orchestrator.analyst.run.return_value = MagicMock()

        result = orchestrator._run_deep_research("alachua-civicclerk")
        assert result == 3

    def test_deep_research_exception_returns_zero(self, orchestrator, mock_db):
        mock_db.get_high_relevance_reports.side_effect = RuntimeError("DB error")
        result = orchestrator._run_deep_research("alachua-civicclerk")
        assert result == 0

    def test_deep_research_skips_empty_topic(self, orchestrator, mock_db):
        mock_db.get_high_relevance_reports.return_value = [
            {"report_id": "r1", "executive_summary": ""},
        ]
        result = orchestrator._run_deep_research("alachua-civicclerk")
        assert result == 0


# =============================================================================
# SUMMARY GENERATION TESTS
# =============================================================================

class TestGenerateSummary:
    """Tests for generate_summary method."""

    def test_basic_summary_format(self, orchestrator):
        run = PipelineRun(
            run_id="test-run",
            started_at=datetime(2026, 2, 6, 10, 0, 0),
            completed_at=datetime(2026, 2, 6, 10, 5, 0),
        )
        run.jobs = [
            JobResult(
                source_id="alachua-civicclerk",
                status=JobStatus.COMPLETED,
                started_at=datetime(2026, 2, 6, 10, 0, 0),
                completed_at=datetime(2026, 2, 6, 10, 2, 0),
                items_discovered=10,
                items_new=3,
                items_analyzed=2,
                events_created=5,
            ),
        ]
        summary = orchestrator.generate_summary(run)
        assert "test-run" in summary
        assert "Items Discovered" in summary
        assert "10" in summary
        assert "alachua-civicclerk" in summary

    def test_summary_includes_errors(self, orchestrator):
        run = PipelineRun(
            run_id="err-run",
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        run.jobs = [
            JobResult(
                source_id="bad-source",
                status=JobStatus.FAILED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error="Connection timeout",
            ),
        ]
        summary = orchestrator.generate_summary(run)
        assert "Connection timeout" in summary


# =============================================================================
# DUE SOURCES TESTS
# =============================================================================

class TestGetDueSources:
    """Tests for get_due_sources scheduling."""

    def test_all_due_when_never_checked(self, orchestrator, mock_db):
        mock_db.get_meetings_by_source.return_value = []
        due = orchestrator.get_due_sources()
        assert len(due) == 3

    def test_recently_checked_not_due(self, orchestrator, mock_db):
        recent = datetime.now().isoformat()
        mock_db.get_meetings_by_source.return_value = [
            {"scraped_at": recent}
        ]
        due = orchestrator.get_due_sources()
        assert len(due) == 0
