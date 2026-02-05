"""
FastAPI application for Open Sousveillance Studio System.

Provides REST API endpoints for:
- Running agents (POST /run)
- Checking status (GET /status/{run_id})
- Human-in-the-loop approvals (GET/POST /approvals)
- SSE streaming for real-time updates
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.config import build_app_config
from src.logging_config import configure_logging, get_logger, bind_context, clear_context
from src.intelligence.health import get_health_service, HealthStatus


# =============================================================================
# MODELS
# =============================================================================

class RunRequest(BaseModel):
    """Request to run an agent."""
    agent: str = Field(..., description="Agent ID (e.g., A1, B1)")
    url: Optional[str] = Field(None, description="Target URL for scouts")
    topic: Optional[str] = Field(None, description="Topic for analysts")
    save: bool = Field(False, description="Save results to database")


class RunResponse(BaseModel):
    """Response from starting an agent run."""
    run_id: str
    agent: str
    status: str
    message: str


class RunStatus(BaseModel):
    """Status of an agent run."""
    run_id: str
    agent: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request to approve/reject a pending item."""
    decision: str = Field(..., description="approved or rejected")
    comments: Optional[str] = None


class ApprovalItem(BaseModel):
    """A pending approval item."""
    id: str
    agent: str
    created_at: datetime
    summary: str
    data: dict


# =============================================================================
# IN-MEMORY STATE (Replace with Redis/DB in production)
# =============================================================================

runs: dict[str, RunStatus] = {}
pending_approvals: dict[str, ApprovalItem] = {}


# =============================================================================
# LIFESPAN
# =============================================================================

# Configure logging on module load
configure_logging()
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Open Sousveillance Studio API")
    try:
        config = build_app_config()
        logger.info(
            "Configuration loaded",
            instance=config.instance.name,
            county=config.jurisdiction.county,
            state=config.jurisdiction.state
        )
    except Exception as e:
        logger.warning("Config warning", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down")


# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Open Sousveillance Studio API",
    description="AI-powered civic monitoring for Alachua County, Florida",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with timing and context."""
    request_id = str(uuid4())[:8]
    bind_context(request_id=request_id)

    start_time = time.time()

    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2)
        )

        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=round(duration_ms, 2)
        )
        raise
    finally:
        clear_context()


# =============================================================================
# ROUTES: Health & Info
# =============================================================================

@app.get("/")
async def root():
    """API root - health check."""
    return {
        "status": "healthy",
        "service": "Open Sousveillance Studio API",
        "version": "2.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/health/scrapers")
async def scraper_health():
    """
    Get health status of all scrapers.

    Returns summary of scraper health including:
    - Status counts (healthy, degraded, failing)
    - Per-scraper metrics (success rate, last attempt, etc.)
    - List of scrapers needing attention
    """
    health_service = get_health_service()
    return health_service.get_summary()


@app.get("/health/scrapers/{scraper_id}")
async def scraper_health_detail(scraper_id: str):
    """
    Get detailed health status for a specific scraper.

    Args:
        scraper_id: Scraper identifier (e.g., "civicclerk-alachuafl", "srwmd-applications")

    Returns:
        Detailed health metrics including recent attempts
    """
    health_service = get_health_service()
    health = health_service.get_health(scraper_id)

    if health.status == HealthStatus.UNKNOWN:
        raise HTTPException(status_code=404, detail=f"Scraper '{scraper_id}' not found")

    return health.to_dict()


@app.post("/health/scrapers/{scraper_id}/reset")
async def reset_scraper_health(scraper_id: str):
    """
    Reset health data for a scraper.

    Use after manual intervention to give the scraper a fresh start.

    Args:
        scraper_id: Scraper identifier
    """
    health_service = get_health_service()
    health_service.reset_health(scraper_id)
    return {"message": f"Health data reset for {scraper_id}"}


@app.get("/health/alerts")
async def health_alerts():
    """
    Get pending health alerts.

    Returns list of status change alerts (degradations and recoveries).
    """
    health_service = get_health_service()
    alerts = health_service.get_alerts()
    return {
        "count": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    }


@app.delete("/health/alerts")
async def clear_health_alerts():
    """Clear all pending health alerts."""
    health_service = get_health_service()
    health_service.clear_alerts()
    return {"message": "Alerts cleared"}


@app.get("/info")
async def info():
    """Get instance information."""
    try:
        config = build_app_config()
        return {
            "instance": {
                "id": config.instance.id,
                "name": config.instance.name,
                "timezone": config.instance.timezone
            },
            "jurisdiction": {
                "state": config.jurisdiction.state,
                "county": config.jurisdiction.county
            }
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# ROUTES: Agent Runs
# =============================================================================

def run_agent_task(run_id: str, agent: str, url: Optional[str], topic: Optional[str], save: bool):
    """Background task to run an agent."""
    runs[run_id].status = "running"
    runs[run_id].started_at = datetime.now()

    try:
        if agent.startswith("A"):
            from src.agents.scout import ScoutAgent
            agent_instance = ScoutAgent(name=agent, prompt_template="Standard Scout Prompt")

            if not url:
                raise ValueError("URL required for Scout agents")

            report = agent_instance.run({"url": url})

            runs[run_id].result = {
                "report_id": report.report_id,
                "summary": report.executive_summary,
                "alerts_count": len(report.alerts)
            }

        elif agent.startswith("B"):
            from src.agents.analyst import AnalystAgent
            agent_instance = AnalystAgent(name=agent)

            topic = topic or "Tara Forest Development"
            report = agent_instance.run({"topic": topic})

            runs[run_id].result = {
                "report_id": report.report_id,
                "summary": report.executive_summary
            }

            # Analysts require approval
            approval_id = str(uuid4())
            pending_approvals[approval_id] = ApprovalItem(
                id=approval_id,
                agent=agent,
                created_at=datetime.now(),
                summary=report.executive_summary,
                data=report.model_dump()
            )

        runs[run_id].status = "completed"
        runs[run_id].completed_at = datetime.now()

        if save:
            try:
                from src.database import get_db
                get_db().save_report(report)
            except Exception as e:
                print(f"Warning: Failed to save report: {e}")

    except Exception as e:
        runs[run_id].status = "failed"
        runs[run_id].error = str(e)
        runs[run_id].completed_at = datetime.now()


@app.post("/run", response_model=RunResponse)
async def run_agent(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Start an agent run.

    - **agent**: Agent ID (A1, A2 for scouts; B1 for analyst)
    - **url**: Target URL (required for scouts)
    - **topic**: Research topic (optional for analysts)
    - **save**: Whether to save results to database
    """
    run_id = str(uuid4())

    # Initialize run status
    runs[run_id] = RunStatus(
        run_id=run_id,
        agent=request.agent,
        status="pending"
    )

    # Start background task
    background_tasks.add_task(
        run_agent_task,
        run_id,
        request.agent,
        request.url,
        request.topic,
        request.save
    )

    return RunResponse(
        run_id=run_id,
        agent=request.agent,
        status="pending",
        message=f"Agent {request.agent} run started"
    )


@app.get("/status/{run_id}", response_model=RunStatus)
async def get_run_status(run_id: str):
    """Get the status of an agent run."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs[run_id]


@app.get("/runs")
async def list_runs(limit: int = 10):
    """List recent agent runs."""
    sorted_runs = sorted(
        runs.values(),
        key=lambda r: r.started_at or datetime.min,
        reverse=True
    )
    return {"runs": [r.model_dump() for r in sorted_runs[:limit]]}


# =============================================================================
# ROUTES: Approvals
# =============================================================================

@app.get("/approvals/pending")
async def list_pending_approvals():
    """List all pending approval items."""
    return {
        "pending": [item.model_dump() for item in pending_approvals.values()]
    }


@app.get("/approvals/{approval_id}")
async def get_approval(approval_id: str):
    """Get details of a pending approval."""
    if approval_id not in pending_approvals:
        raise HTTPException(status_code=404, detail="Approval not found")
    return pending_approvals[approval_id]


@app.post("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, request: ApprovalRequest):
    """
    Approve or reject a pending item.

    - **decision**: "approved" or "rejected"
    - **comments**: Optional reviewer comments
    """
    if approval_id not in pending_approvals:
        raise HTTPException(status_code=404, detail="Approval not found")

    item = pending_approvals.pop(approval_id)

    return {
        "approval_id": approval_id,
        "decision": request.decision,
        "comments": request.comments,
        "item_summary": item.summary
    }


# =============================================================================
# ROUTES: SSE Streaming
# =============================================================================

async def event_generator(run_id: str):
    """Generate SSE events for a run."""
    import asyncio

    while True:
        if run_id in runs:
            status = runs[run_id]
            yield {
                "event": "status",
                "data": status.model_dump_json()
            }

            if status.status in ["completed", "failed"]:
                break

        await asyncio.sleep(1)


@app.get("/stream/{run_id}")
async def stream_run(run_id: str):
    """Stream real-time updates for an agent run via SSE."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")

    return EventSourceResponse(event_generator(run_id))


# =============================================================================
# CLI COMPATIBILITY
# =============================================================================

def main():
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(
        "src.app:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true"
    )


if __name__ == "__main__":
    main()
