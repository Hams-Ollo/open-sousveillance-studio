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
