"""
Celery application configuration for Open Sousveillance Studio System.

Usage:
    # Start worker
    celery -A src.tasks.celery_app worker --loglevel=info

    # Start beat scheduler
    celery -A src.tasks.celery_app beat --loglevel=info
"""

import os
from celery import Celery
from celery.schedules import crontab

# Load broker URL from environment
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "alachua_civic",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "src.tasks.scout_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result settings
    result_expires=86400,  # 24 hours

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    # Daily orchestrator pipeline at 4 AM Eastern
    # Runs all scrapers, Scout analysis, and Analyst deep research
    "daily-orchestrator-pipeline": {
        "task": "src.tasks.scout_tasks.run_orchestrator_pipeline",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {
            "skip_analysis": False,
            "skip_deep_research": False,
            "force": True  # Force run regardless of individual source schedules
        },
        "options": {"queue": "orchestrator"}
    },
    # Legacy: Daily scout runs at 6 AM Eastern (kept for backwards compatibility)
    "daily-scout-run": {
        "task": "src.tasks.scout_tasks.run_all_critical_scouts",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "scouts"}
    },
}

# Task routing
celery_app.conf.task_routes = {
    "src.tasks.scout_tasks.run_orchestrator_pipeline": {"queue": "orchestrator"},
    "src.tasks.scout_tasks.run_single_source": {"queue": "orchestrator"},
    "src.tasks.scout_tasks.*": {"queue": "scouts"},
}


if __name__ == "__main__":
    celery_app.start()
