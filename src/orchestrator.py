"""
Orchestrator - Central Coordinator for Civic Intelligence Pipeline
===================================================================

The Orchestrator coordinates the entire scraping, analysis, and reporting workflow:

1. **Scheduling**: Determines which sources to check based on frequency
2. **Discovery**: Runs scrapers to find new/updated content
3. **Analysis**: Triggers Scout Agent for new items
4. **Reporting**: Generates and distributes reports
5. **State Management**: Tracks what's been processed

Pipeline Flow:
    Sources → Discovery → Database Sync → Analysis → Reports → Notifications
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from src.config import get_all_sources, SourceConfig, load_entities_config
from src.database import Database
from src.logging_config import get_logger
from src.agents.scout import ScoutAgent
from src.agents.analyst import AnalystAgent, ResearchProvider
from src.tools.civicclerk_scraper import CivicClerkScraper
from src.tools.florida_notices_scraper import FloridaNoticesScraper
from src.tools.srwmd_scraper import SRWMDScraper

logger = get_logger("orchestrator")


# Source type constants for consistent matching
class SourceType:
    """Constants for source type identification."""
    CIVICCLERK = "civicclerk"
    FLORIDA_NOTICES = "florida-public-notices"
    SRWMD = "srwmd"


class JobStatus(Enum):
    """Status of an orchestrator job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class JobResult:
    """Result from a single job execution."""
    source_id: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_discovered: int = 0
    items_new: int = 0
    items_analyzed: int = 0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass
class PipelineRun:
    """Result from a full pipeline run."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    jobs: List[JobResult] = field(default_factory=list)

    @property
    def total_discovered(self) -> int:
        return sum(j.items_discovered for j in self.jobs)

    @property
    def total_new(self) -> int:
        return sum(j.items_new for j in self.jobs)

    @property
    def total_analyzed(self) -> int:
        return sum(j.items_analyzed for j in self.jobs)

    @property
    def successful_jobs(self) -> int:
        return len([j for j in self.jobs if j.status == JobStatus.COMPLETED])

    @property
    def failed_jobs(self) -> int:
        return len([j for j in self.jobs if j.status == JobStatus.FAILED])


class Orchestrator:
    """
    Central coordinator for the Civic Intelligence pipeline.

    Usage:
        orchestrator = Orchestrator()

        # Run full pipeline for all due sources
        result = orchestrator.run_pipeline()

        # Run specific source
        result = orchestrator.run_source("alachua-civicclerk")

        # Run with filters
        result = orchestrator.run_pipeline(
            source_ids=["alachua-civicclerk", "srwmd-permit-applications"],
            skip_analysis=False
        )
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        research_provider: ResearchProvider = ResearchProvider.BOTH
    ):
        """
        Initialize the Orchestrator.

        Args:
            db: Optional Database instance (creates one if not provided)
            research_provider: Research provider for AnalystAgent (tavily, gemini, or both)
        """
        self.db = db or Database()
        self.sources = self._load_sources()
        self.scout = ScoutAgent(name="OrchestratorScout")
        self.analyst = AnalystAgent(name="OrchestratorAnalyst", research_provider=research_provider)
        self.scrapers = self._init_scrapers()

        logger.info(
            "Orchestrator initialized",
            sources_count=len(self.sources),
            scrapers=list(self.scrapers.keys()),
            research_provider=research_provider.value
        )

    def _load_sources(self) -> Dict[str, SourceConfig]:
        """Load all configured sources."""
        sources = {}
        for source in get_all_sources():
            sources[source.id] = source
        return sources

    def _init_scrapers(self) -> Dict[str, Any]:
        """Initialize scraper instances based on configured sources."""
        scrapers = {}

        # Find CivicClerk source and extract site_id from URL
        for source in self.sources.values():
            if SourceType.CIVICCLERK in source.id.lower():
                # Extract site_id from URL like https://alachuafl.portal.civicclerk.com/
                site_id = self._extract_civicclerk_site_id(source.url)
                scrapers[SourceType.CIVICCLERK] = CivicClerkScraper(site_id=site_id)
                break

        # Default if no CivicClerk source found
        if SourceType.CIVICCLERK not in scrapers:
            scrapers[SourceType.CIVICCLERK] = CivicClerkScraper(site_id="alachuafl")

        scrapers[SourceType.FLORIDA_NOTICES] = FloridaNoticesScraper()
        scrapers[SourceType.SRWMD] = SRWMDScraper()

        return scrapers

    def _extract_civicclerk_site_id(self, url: str) -> str:
        """Extract site_id from CivicClerk URL."""
        # URL format: https://{site_id}.portal.civicclerk.com/
        import re
        match = re.search(r'https?://([^.]+)\.portal\.civicclerk\.com', url)
        if match:
            return match.group(1)
        return "alachuafl"  # Default fallback

    def _get_scraper_for_source(self, source: SourceConfig) -> Optional[Any]:
        """Get the appropriate scraper for a source."""
        source_id = source.id.lower()

        if SourceType.CIVICCLERK in source_id:
            return self.scrapers.get(SourceType.CIVICCLERK)
        elif SourceType.FLORIDA_NOTICES in source_id:
            return self.scrapers.get(SourceType.FLORIDA_NOTICES)
        elif SourceType.SRWMD in source_id:
            return self.scrapers.get(SourceType.SRWMD)

        return None

    def get_due_sources(self) -> List[SourceConfig]:
        """
        Get sources that are due for checking based on their frequency.

        Returns:
            List of SourceConfig objects due for scraping
        """
        due_sources = []
        now = datetime.now()

        for source_id, source in self.sources.items():
            # Get last check time from database
            last_check = self._get_last_check_time(source_id)

            # Determine check interval
            frequency = source.check_frequency or "daily"
            interval = self._frequency_to_timedelta(frequency)

            # Check if due
            if last_check is None or (now - last_check) >= interval:
                due_sources.append(source)

        logger.info(
            "Determined due sources",
            total_sources=len(self.sources),
            due_count=len(due_sources)
        )

        return due_sources

    def _get_last_check_time(self, source_id: str) -> Optional[datetime]:
        """Get the last time a source was checked."""
        try:
            meetings = self.db.get_meetings_by_source(source_id)
            if meetings:
                # Find most recent scraped_at
                latest = max(
                    (m.get('scraped_at') for m in meetings if m.get('scraped_at')),
                    default=None
                )
                if latest:
                    return datetime.fromisoformat(latest.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning("Could not get last check time", source_id=source_id, error=str(e))
        return None

    def _frequency_to_timedelta(self, frequency: str) -> timedelta:
        """Convert frequency string to timedelta."""
        mapping = {
            'hourly': timedelta(hours=1),
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30),
        }
        return mapping.get(frequency.lower(), timedelta(days=1))

    # =========================================================================
    # PIPELINE EXECUTION
    # =========================================================================

    def run_pipeline(
        self,
        source_ids: Optional[List[str]] = None,
        skip_analysis: bool = False,
        force: bool = False
    ) -> PipelineRun:
        """
        Run the full pipeline for specified or due sources.

        Args:
            source_ids: Optional list of specific source IDs to run
            skip_analysis: If True, skip Scout Agent analysis
            force: If True, run even if not due

        Returns:
            PipelineRun with results from all jobs
        """
        run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        pipeline_run = PipelineRun(
            run_id=run_id,
            started_at=datetime.now()
        )

        logger.info(
            "Starting pipeline run",
            run_id=run_id,
            source_ids=source_ids,
            skip_analysis=skip_analysis,
            force=force
        )

        # Determine which sources to run
        if source_ids:
            sources_to_run = [
                self.sources[sid] for sid in source_ids
                if sid in self.sources
            ]
        elif force:
            sources_to_run = list(self.sources.values())
        else:
            sources_to_run = self.get_due_sources()

        # Run each source
        for source in sources_to_run:
            job_result = self.run_source(
                source.id,
                skip_analysis=skip_analysis
            )
            pipeline_run.jobs.append(job_result)

        pipeline_run.completed_at = datetime.now()

        logger.info(
            "Pipeline run completed",
            run_id=run_id,
            total_jobs=len(pipeline_run.jobs),
            successful=pipeline_run.successful_jobs,
            failed=pipeline_run.failed_jobs,
            total_discovered=pipeline_run.total_discovered,
            total_new=pipeline_run.total_new,
            total_analyzed=pipeline_run.total_analyzed
        )

        return pipeline_run

    def run_source(
        self,
        source_id: str,
        skip_analysis: bool = False,
        skip_deep_research: bool = False
    ) -> JobResult:
        """
        Run the pipeline for a single source.

        Args:
            source_id: ID of the source to run
            skip_analysis: If True, skip Scout Agent analysis (Layer 1)
            skip_deep_research: If True, skip Analyst deep research (Layer 2)

        Returns:
            JobResult with execution details
        """
        job = JobResult(
            source_id=source_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now()
        )

        logger.info("Starting source job", source_id=source_id)

        try:
            source = self.sources.get(source_id)
            if not source:
                job.status = JobStatus.FAILED
                job.error = f"Source not found: {source_id}"
                job.completed_at = datetime.now()
                return job

            # Get appropriate scraper
            scraper = self._get_scraper_for_source(source)
            if not scraper:
                job.status = JobStatus.SKIPPED
                job.error = f"No scraper available for source: {source_id}"
                job.completed_at = datetime.now()
                return job

            # Run discovery and sync based on source type
            if 'civicclerk' in source_id.lower():
                result = self._run_civicclerk_job(scraper, source, job)
            elif 'florida-public-notices' in source_id.lower():
                result = self._run_florida_notices_job(scraper, source, job)
            elif 'srwmd' in source_id.lower():
                result = self._run_srwmd_job(scraper, source, job)
            else:
                job.status = JobStatus.SKIPPED
                job.error = f"Unknown source type: {source_id}"
                job.completed_at = datetime.now()
                return job

            # Run analysis if not skipped and we have new items
            if not skip_analysis and job.items_new > 0:
                analyzed = self._run_analysis(source_id)
                job.items_analyzed = analyzed

                # Run deep research on high-relevance items (Layer 2)
                if not skip_deep_research and analyzed > 0:
                    deep_researched = self._run_deep_research(source_id)
                    job.details['deep_researched'] = deep_researched

            job.status = JobStatus.COMPLETED

        except Exception as e:
            logger.error("Source job failed", source_id=source_id, error=str(e))
            job.status = JobStatus.FAILED
            job.error = str(e)

        job.completed_at = datetime.now()

        logger.info(
            "Source job completed",
            source_id=source_id,
            status=job.status.value,
            discovered=job.items_discovered,
            new=job.items_new,
            analyzed=job.items_analyzed,
            duration_s=round(job.duration_seconds, 2)
        )

        return job

    # =========================================================================
    # SOURCE-SPECIFIC JOB RUNNERS
    # =========================================================================

    def _run_civicclerk_job(
        self,
        scraper: CivicClerkScraper,
        source: SourceConfig,
        job: JobResult
    ) -> JobResult:
        """Run CivicClerk scraping job."""
        logger.info("Running CivicClerk job", source_id=source.id)

        # Run hybrid pipeline
        result = scraper.run_hybrid_pipeline(
            db=self.db,
            days_back=30,
            download_pdfs=True
        )

        job.items_discovered = result.get('phase1_discovery', {}).get('total_discovered', 0)
        job.items_new = len(result.get('phase1_discovery', {}).get('new', []))
        job.details = result

        return job

    def _run_florida_notices_job(
        self,
        scraper: FloridaNoticesScraper,
        source: SourceConfig,
        job: JobResult
    ) -> JobResult:
        """Run Florida Public Notices scraping job."""
        logger.info("Running Florida Notices job", source_id=source.id)

        # Run hybrid pipeline
        result = scraper.run_hybrid_pipeline(
            db=self.db,
            days_back=30
        )

        job.items_discovered = result.get('phase1_discovery', {}).get('total_discovered', 0)
        job.items_new = len(result.get('phase1_discovery', {}).get('new', []))
        job.details = result

        return job

    def _run_srwmd_job(
        self,
        scraper: SRWMDScraper,
        source: SourceConfig,
        job: JobResult
    ) -> JobResult:
        """Run SRWMD permit scraping job."""
        logger.info("Running SRWMD job", source_id=source.id)

        # Determine if applications or issuances based on source ID
        include_apps = 'application' in source.id.lower()
        include_issued = 'issuance' in source.id.lower()

        # If neither specified, include both
        if not include_apps and not include_issued:
            include_apps = True
            include_issued = True

        # Run hybrid pipeline
        result = scraper.run_hybrid_pipeline(
            db=self.db,
            county_filter="Alachua",
            include_applications=include_apps,
            include_issuances=include_issued
        )

        job.items_discovered = result.get('phase1_discovery', {}).get('total_discovered', 0)
        job.items_new = len(result.get('permits_ready_for_analysis', []))
        job.details = result

        return job

    # =========================================================================
    # ANALYSIS
    # =========================================================================

    def _run_analysis(self, source_id: str) -> int:
        """
        Run Scout Agent analysis on unanalyzed items.

        Args:
            source_id: Source ID to analyze items for

        Returns:
            Number of items analyzed
        """
        logger.info("Running analysis", source_id=source_id)

        try:
            # Get unanalyzed meetings
            unanalyzed = self.db.get_unanalyzed_meetings(source_id)

            analyzed_count = 0
            for meeting in unanalyzed[:10]:  # Limit to 10 per run
                try:
                    # Build watchlist from entities config
                    entities = load_entities_config()
                    watchlist = self._build_watchlist(entities)

                    # Run Scout Agent
                    report = self.scout.run({
                        'meeting': meeting,
                        'watchlist': watchlist
                    })

                    # Save report
                    self.db.save_report(report)

                    # Mark as analyzed
                    self.db.mark_meeting_analyzed(
                        meeting['meeting_id'],
                        source_id,
                        report.report_id
                    )

                    analyzed_count += 1

                except Exception as e:
                    logger.error(
                        "Failed to analyze meeting",
                        meeting_id=meeting.get('meeting_id'),
                        error=str(e)
                    )

            return analyzed_count

        except Exception as e:
            logger.error("Analysis failed", source_id=source_id, error=str(e))
            return 0

    def _build_watchlist(self, entities: dict) -> str:
        """Build watchlist string from entities config."""
        watchlist_items = []

        # Projects
        for project in entities.get('projects', []):
            watchlist_items.append(f"- {project.get('name')}: {project.get('description', '')}")
            for alias in project.get('aliases', []):
                watchlist_items.append(f"  - Alias: {alias}")

        # Organizations
        for org in entities.get('organizations', []):
            watchlist_items.append(f"- {org.get('name')} ({org.get('type', 'org')})")
            for principal in org.get('principals', []):
                watchlist_items.append(f"  - Principal: {principal}")

        # People
        for person in entities.get('people', []):
            watchlist_items.append(f"- {person.get('name')} ({person.get('role', '')})")

        return "\n".join(watchlist_items) if watchlist_items else "No specific watchlist configured."

    def _run_deep_research(self, source_id: str, relevance_threshold: float = 0.7) -> int:
        """
        Run AnalystAgent deep research on high-relevance items.

        This is Layer 2 analysis - triggered after Scout (Layer 1) identifies
        items of interest. Uses both Tavily and Gemini Deep Research.

        Args:
            source_id: Source ID to research items for
            relevance_threshold: Minimum relevance score to trigger deep research

        Returns:
            Number of items researched
        """
        logger.info(
            "Running deep research",
            source_id=source_id,
            threshold=relevance_threshold
        )

        try:
            # Get high-relevance reports that haven't had deep research
            high_relevance_reports = self.db.get_high_relevance_reports(
                source_id=source_id,
                min_relevance=relevance_threshold,
                needs_deep_research=True
            )

            if not high_relevance_reports:
                logger.info("No high-relevance items need deep research")
                return 0

            researched_count = 0
            for report in high_relevance_reports[:3]:  # Limit to 3 per run (expensive)
                try:
                    # Extract topic from report
                    topic = report.get('executive_summary', '')[:200]
                    if not topic:
                        continue

                    logger.info(
                        "Running deep research on topic",
                        report_id=report.get('report_id'),
                        topic=topic[:50]
                    )

                    # Run Analyst Agent with both providers
                    deep_report = self.analyst.run({'topic': topic})

                    # Save deep research report
                    self.db.save_deep_research_report(
                        original_report_id=report.get('report_id'),
                        deep_report=deep_report
                    )

                    researched_count += 1

                except Exception as e:
                    logger.error(
                        "Deep research failed for report",
                        report_id=report.get('report_id'),
                        error=str(e)
                    )

            return researched_count

        except Exception as e:
            logger.error("Deep research failed", source_id=source_id, error=str(e))
            return 0

    # =========================================================================
    # REPORTING
    # =========================================================================

    def generate_summary(self, pipeline_run: PipelineRun) -> str:
        """
        Generate a human-readable summary of a pipeline run.

        Args:
            pipeline_run: The completed pipeline run

        Returns:
            Formatted summary string
        """
        lines = [
            f"# Pipeline Run Summary",
            f"**Run ID:** {pipeline_run.run_id}",
            f"**Started:** {pipeline_run.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Completed:** {pipeline_run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pipeline_run.completed_at else 'In Progress'}",
            "",
            "## Results",
            f"- **Jobs Run:** {len(pipeline_run.jobs)}",
            f"- **Successful:** {pipeline_run.successful_jobs}",
            f"- **Failed:** {pipeline_run.failed_jobs}",
            f"- **Items Discovered:** {pipeline_run.total_discovered}",
            f"- **New Items:** {pipeline_run.total_new}",
            f"- **Items Analyzed:** {pipeline_run.total_analyzed}",
            "",
            "## Job Details",
        ]

        for job in pipeline_run.jobs:
            status_emoji = {
                JobStatus.COMPLETED: "✅",
                JobStatus.FAILED: "❌",
                JobStatus.SKIPPED: "⏭️",
                JobStatus.RUNNING: "🔄",
                JobStatus.PENDING: "⏳"
            }.get(job.status, "❓")

            lines.append(f"### {status_emoji} {job.source_id}")
            lines.append(f"- Status: {job.status.value}")
            lines.append(f"- Duration: {job.duration_seconds:.1f}s")
            lines.append(f"- Discovered: {job.items_discovered}")
            lines.append(f"- New: {job.items_new}")
            lines.append(f"- Analyzed: {job.items_analyzed}")
            if job.error:
                lines.append(f"- Error: {job.error}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def run_cli():
    """Command-line interface for the Orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="Civic Intelligence Orchestrator")
    parser.add_argument(
        "--sources",
        nargs="*",
        help="Specific source IDs to run (default: all due sources)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force run all sources regardless of schedule"
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip Scout Agent analysis"
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List all configured sources and exit"
    )

    args = parser.parse_args()

    orchestrator = Orchestrator()

    if args.list_sources:
        print("\nConfigured Sources:")
        print("-" * 60)
        for source_id, source in orchestrator.sources.items():
            print(f"  {source_id}")
            print(f"    Priority: {source.priority}")
            print(f"    Frequency: {source.check_frequency}")
            print(f"    URL: {source.url}")
            print()
        return

    # Run pipeline
    result = orchestrator.run_pipeline(
        source_ids=args.sources,
        skip_analysis=args.skip_analysis,
        force=args.force
    )

    # Print summary
    print(orchestrator.generate_summary(result))


if __name__ == "__main__":
    run_cli()
