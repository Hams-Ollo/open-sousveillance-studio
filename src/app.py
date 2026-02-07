"""
FastAPI application for Open Sousveillance Studio System.

Provides REST API endpoints for:
- Running agents (POST /run)
- Checking status (GET /status/{run_id})
- Human-in-the-loop approvals (GET/POST /approvals)
- SSE streaming for real-time updates
"""

import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src import __version__
from src.config import build_app_config
from src.logging_config import configure_logging, get_logger, bind_context, clear_context
from src.intelligence.health import get_health_service, HealthStatus


# =============================================================================
# API KEY AUTHENTICATION
# =============================================================================

_API_KEY = os.getenv("API_KEY", "")


async def verify_api_key(x_api_key: str = Header(default=None)):
    """Verify API key for protected endpoints. Skipped if API_KEY is not configured."""
    if not _API_KEY:
        return  # Auth disabled — no key configured
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


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
# STATE STORE (Redis-backed with in-memory fallback)
# =============================================================================

from src.state import get_state_store

state = get_state_store()


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
    version=__version__,
    lifespan=lifespan
)

# CORS middleware
_cors_origins = [
    o.strip() for o in
    os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:8000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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
    state.update_run(run_id, status="running", started_at=datetime.now())

    try:
        from src.agents import get_agent, get_agent_info

        info = get_agent_info(agent)
        agent_instance = get_agent(agent, prompt_template="Standard Scout Prompt") if info["layer"] == 1 else get_agent(agent)

        if info["layer"] == 1:
            # Scout agents require a URL
            if not url:
                raise ValueError("URL required for Scout agents")

            report = agent_instance.run({"url": url})

            state.update_run(run_id, result={
                "report_id": report.report_id,
                "summary": report.executive_summary,
                "alerts_count": len(report.alerts)
            })

        elif info["layer"] == 2:
            # Analyst agents require a topic
            topic = topic or "Tara Forest Development"
            report = agent_instance.run({"topic": topic})

            state.update_run(run_id, result={
                "report_id": report.report_id,
                "summary": report.executive_summary
            })

            # Analysts require approval
            approval_id = str(uuid4())
            state.save_approval(approval_id, {
                "id": approval_id,
                "agent": agent,
                "created_at": datetime.now().isoformat(),
                "summary": report.executive_summary,
                "data": report.model_dump()
            })

        state.update_run(run_id, status="completed", completed_at=datetime.now())

        if save:
            try:
                from src.database import get_db
                get_db().save_report(report)
            except Exception as e:
                print(f"Warning: Failed to save report: {e}")

    except Exception as e:
        state.update_run(run_id, status="failed", error=str(e), completed_at=datetime.now())


@app.post("/run", response_model=RunResponse, dependencies=[Depends(verify_api_key)])
async def run_agent(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Start an agent run.

    - **agent**: Agent ID (A1, A2 for scouts; B1 for analyst)
    - **url**: Target URL (required for scouts)
    - **topic**: Research topic (optional for analysts)
    - **save**: Whether to save results to database
    """
    run_id = str(uuid4())

    # Initialize run status in state store
    state.save_run(run_id, {
        "run_id": run_id,
        "agent": request.agent,
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None
    })

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


@app.get("/status/{run_id}")
async def get_run_status(run_id: str):
    """Get the status of an agent run."""
    data = state.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return data


@app.get("/runs", dependencies=[Depends(verify_api_key)])
async def list_runs(limit: int = 10):
    """List recent agent runs."""
    return {"runs": state.list_runs(limit=limit)}


# =============================================================================
# ROUTES: Approvals
# =============================================================================

@app.get("/approvals/pending", dependencies=[Depends(verify_api_key)])
async def list_pending_approvals():
    """List all pending approval items."""
    return {
        "pending": state.list_approvals()
    }


@app.get("/approvals/{approval_id}", dependencies=[Depends(verify_api_key)])
async def get_approval(approval_id: str):
    """Get details of a pending approval."""
    data = state.get_approval(approval_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return data


@app.post("/approvals/{approval_id}/decide", dependencies=[Depends(verify_api_key)])
async def decide_approval(approval_id: str, request: ApprovalRequest):
    """
    Approve or reject a pending item.

    - **decision**: "approved" or "rejected"
    - **comments**: Optional reviewer comments
    """
    item = state.remove_approval(approval_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    return {
        "approval_id": approval_id,
        "decision": request.decision,
        "comments": request.comments,
        "item_summary": item.get("summary", "")
    }


# =============================================================================
# ROUTES: Cost Tracking
# =============================================================================

@app.get("/costs", dependencies=[Depends(verify_api_key)])
async def get_llm_costs():
    """Get daily LLM usage and cost summary."""
    from src.llm_cost import get_cost_tracker
    return get_cost_tracker().get_daily_summary()


# =============================================================================
# ROUTES: Agent Registry
# =============================================================================

@app.get("/agents")
async def list_registered_agents():
    """List all registered agents with metadata."""
    from src.agents import list_agents
    return {"agents": list_agents()}


# =============================================================================
# ROUTES: SSE Streaming
# =============================================================================

async def event_generator(run_id: str):
    """Generate SSE events for a run."""
    import asyncio

    while True:
        data = state.get_run(run_id)
        if data is not None:
            yield {
                "event": "status",
                "data": json.dumps(data, default=str)
            }

            if data.get("status") in ["completed", "failed"]:
                break

        await asyncio.sleep(1)


@app.get("/stream/{run_id}")
async def stream_run(run_id: str):
    """Stream real-time updates for an agent run via SSE."""
    if state.get_run(run_id) is None:
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
