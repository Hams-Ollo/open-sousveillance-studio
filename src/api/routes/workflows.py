"""
Workflow API routes for Alachua Civic Intelligence System.

Provides endpoints for:
- POST /run - Start an agent run
- GET /status/{run_id} - Check run status
- GET /runs - List recent runs
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

router = APIRouter(prefix="/workflows", tags=["workflows"])


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


# =============================================================================
# IN-MEMORY STATE (Replace with Redis/DB in production)
# =============================================================================

runs: dict[str, RunStatus] = {}


# =============================================================================
# BACKGROUND TASK
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


# =============================================================================
# ROUTES
# =============================================================================

@router.post("/run", response_model=RunResponse)
async def run_agent(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Start an agent run.
    
    - **agent**: Agent ID (A1, A2 for scouts; B1 for analyst)
    - **url**: Target URL (required for scouts)
    - **topic**: Research topic (optional for analysts)
    - **save**: Whether to save results to database
    """
    run_id = str(uuid4())
    
    runs[run_id] = RunStatus(
        run_id=run_id,
        agent=request.agent,
        status="pending"
    )
    
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


@router.get("/status/{run_id}", response_model=RunStatus)
async def get_run_status(run_id: str):
    """Get the status of an agent run."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs[run_id]


@router.get("/runs")
async def list_runs(limit: int = 10):
    """List recent agent runs."""
    sorted_runs = sorted(
        runs.values(),
        key=lambda r: r.started_at or datetime.min,
        reverse=True
    )
    return {"runs": [r.model_dump() for r in sorted_runs[:limit]]}
