"""
Celery tasks for Scout agents.

Scout tasks run daily to monitor government data sources.
"""

from celery import shared_task
from typing import Optional

from src.tasks.celery_app import celery_app
from src.logging_config import get_logger, bind_context, clear_context

logger = get_logger("tasks.scout")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_scout(self, agent_id: str, url: str, save: bool = True) -> dict:
    """
    Run a Scout agent on a specific URL.

    Args:
        agent_id: Scout agent ID (e.g., "A1")
        url: Target URL to monitor
        save: Whether to save results to database

    Returns:
        Dict with report summary
    """
    bind_context(task_id=self.request.id, agent_id=agent_id)
    logger.info("Scout task started", url=url, save=save)

    try:
        from src.agents.scout import ScoutAgent

        agent = ScoutAgent(name=agent_id, prompt_template="Standard Scout Prompt")
        report = agent.run({"url": url})

        result = {
            "report_id": report.report_id,
            "agent": agent_id,
            "url": url,
            "summary": report.executive_summary,
            "alerts_count": len(report.alerts),
            "items_count": len(report.items),
            "success": True
        }

        if save:
            try:
                from src.database import get_db
                get_db().save_report(report)
                result["saved"] = True
                logger.info("Report saved to database", report_id=report.report_id)
            except Exception as e:
                result["saved"] = False
                result["save_error"] = str(e)
                logger.warning("Failed to save report", error=str(e))

        logger.info("Scout task completed", report_id=report.report_id)
        return result

    except Exception as e:
        logger.error("Scout task failed", error=str(e), retry_count=self.request.retries)
        raise self.retry(exc=e)
    finally:
        clear_context()


@celery_app.task(bind=True)
def run_all_critical_scouts(self, save: bool = True) -> dict:
    """
    Run Scout agents on all CRITICAL priority sources.

    This is the main daily task that monitors all critical government sources.

    Args:
        save: Whether to save results to database

    Returns:
        Dict with summary of all runs
    """
    bind_context(task_id=self.request.id)
    logger.info("Starting critical scouts batch")

    from src.config import get_sources_by_priority

    sources = get_sources_by_priority("critical")
    logger.info("Found critical sources", count=len(sources))

    results = {
        "total": len(sources),
        "successful": 0,
        "failed": 0,
        "reports": []
    }

    for source in sources:
        try:
            # Run scout synchronously within this task
            # In production, you might want to fan out to separate tasks
            result = run_scout.delay("A1", source.url, save=save)
            results["reports"].append({
                "source_id": source.id,
                "url": source.url,
                "task_id": result.id
            })
            results["successful"] += 1
        except Exception as e:
            results["failed"] += 1
            results["reports"].append({
                "source_id": source.id,
                "url": source.url,
                "error": str(e)
            })
            logger.warning("Failed to queue scout", source_id=source.id, error=str(e))

    logger.info(
        "Critical scouts batch completed",
        total=results["total"],
        successful=results["successful"],
        failed=results["failed"]
    )
    clear_context()
    return results


@celery_app.task
def run_scout_for_source(source_id: str, save: bool = True) -> dict:
    """
    Run a Scout agent for a specific source by ID.

    Args:
        source_id: Source ID from config/sources.yaml
        save: Whether to save results

    Returns:
        Dict with report summary
    """
    from src.config import get_all_sources

    sources = get_all_sources()
    source = next((s for s in sources if s.id == source_id), None)

    if not source:
        return {"error": f"Source not found: {source_id}"}

    return run_scout("A1", source.url, save=save)


# =============================================================================
# ORCHESTRATOR PIPELINE TASKS
# =============================================================================

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def run_orchestrator_pipeline(
    self,
    source_ids: Optional[list] = None,
    skip_analysis: bool = False,
    skip_deep_research: bool = False,
    force: bool = False
) -> dict:
    """
    Run the full Orchestrator pipeline.

    This is the main scheduled task that:
    1. Scrapes all due sources (or specified sources)
    2. Runs Scout Agent analysis on new items
    3. Runs Analyst deep research on high-relevance items

    Args:
        source_ids: Optional list of specific source IDs to run
        skip_analysis: Skip Scout Agent analysis
        skip_deep_research: Skip Analyst deep research
        force: Force run regardless of schedule

    Returns:
        Dict with pipeline run summary
    """
    bind_context(task_id=self.request.id, task_name="orchestrator_pipeline")
    logger.info(
        "Orchestrator pipeline task started",
        source_ids=source_ids,
        skip_analysis=skip_analysis,
        skip_deep_research=skip_deep_research,
        force=force
    )

    try:
        from src.orchestrator import Orchestrator
        from src.agents.analyst import ResearchProvider

        orchestrator = Orchestrator(research_provider=ResearchProvider.BOTH)

        pipeline_run = orchestrator.run_pipeline(
            source_ids=source_ids,
            skip_analysis=skip_analysis,
            force=force
        )

        result = {
            "run_id": pipeline_run.run_id,
            "status": "completed" if pipeline_run.failed_jobs == 0 else "partial",
            "jobs_total": len(pipeline_run.jobs),
            "jobs_successful": pipeline_run.successful_jobs,
            "jobs_failed": pipeline_run.failed_jobs,
            "items_discovered": pipeline_run.total_discovered,
            "items_new": pipeline_run.total_new,
            "items_analyzed": pipeline_run.total_analyzed,
            "duration_seconds": (
                pipeline_run.completed_at - pipeline_run.started_at
            ).total_seconds() if pipeline_run.completed_at else None,
            "success": True
        }

        logger.info(
            "Orchestrator pipeline completed",
            run_id=pipeline_run.run_id,
            discovered=pipeline_run.total_discovered,
            new=pipeline_run.total_new,
            analyzed=pipeline_run.total_analyzed
        )

        return result

    except Exception as e:
        logger.error("Orchestrator pipeline failed", error=str(e))
        raise self.retry(exc=e)
    finally:
        clear_context()


@celery_app.task(bind=True)
def run_single_source(
    self,
    source_id: str,
    skip_analysis: bool = False,
    skip_deep_research: bool = False
) -> dict:
    """
    Run the Orchestrator pipeline for a single source.

    Use this for manual triggers of specific sources.

    Args:
        source_id: Source ID to run
        skip_analysis: Skip Scout Agent analysis
        skip_deep_research: Skip Analyst deep research

    Returns:
        Dict with job result summary
    """
    bind_context(task_id=self.request.id, source_id=source_id)
    logger.info("Single source task started", source_id=source_id)

    try:
        from src.orchestrator import Orchestrator
        from src.agents.analyst import ResearchProvider

        orchestrator = Orchestrator(research_provider=ResearchProvider.BOTH)

        job = orchestrator.run_source(
            source_id=source_id,
            skip_analysis=skip_analysis,
            skip_deep_research=skip_deep_research
        )

        result = {
            "source_id": source_id,
            "status": job.status.value,
            "items_discovered": job.items_discovered,
            "items_new": job.items_new,
            "items_analyzed": job.items_analyzed,
            "duration_seconds": job.duration_seconds,
            "error": job.error,
            "success": job.status.value == "completed"
        }

        logger.info("Single source task completed", **result)
        return result

    except Exception as e:
        logger.error("Single source task failed", source_id=source_id, error=str(e))
        return {
            "source_id": source_id,
            "status": "failed",
            "error": str(e),
            "success": False
        }
    finally:
        clear_context()
