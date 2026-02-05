# Project Knowledge Base

**Alachua Civic Intelligence Reporting Studio — Technical Reference**

---

## Overview

The Alachua Civic Intelligence Reporting Studio is an AI-powered civic monitoring system that tracks government activities, development projects, and environmental issues in Alachua County, Florida. It uses a three-layer agent architecture to collect, analyze, and synthesize information for citizen awareness.

---

## Technology Stack

| Category | Technology | Purpose |
|:---------|:-----------|:--------|
| **Runtime** | Python 3.11+ | Application runtime |
| **Web Framework** | FastAPI | REST API & SSE streaming |
| **LLM** | Google Gemini 2.5 Pro/Flash | AI reasoning & analysis |
| **Orchestration** | LangChain + LangGraph | Agent workflows |
| **Task Queue** | Celery + Redis | Background job processing |
| **Database** | Supabase (PostgreSQL + pgvector) | Data storage & vector search |
| **Web Scraping** | Firecrawl | JavaScript-rendered page scraping |
| **Document Processing** | Docling | PDF parsing & extraction |
| **Research** | Tavily | Deep web research |
| **Logging** | Structlog | Structured JSON logging |
| **Containerization** | Docker + Docker Compose | Deployment |

---

## Architecture

### Three-Layer Agent Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LAYER 1: SCOUTS                              │
│  A1: Meeting Intelligence    A2: Permit Applications                │
│  A3: Legislative Monitor     A4: Document Tracker                   │
│  (Daily execution - automated)                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: ANALYSTS                             │
│  B1: Impact Assessment       B2: Procedural Integrity               │
│  (Weekly execution - requires approval for sensitive content)       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      LAYER 3: SYNTHESIZERS                           │
│  C1: Daily Brief    C2: Weekly Digest    C3: Alert    C4: Deep Dive │
│  (On-demand - requires human approval before publication)           │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Government Portal → Firecrawl → Scout Agent → ScoutReport → Supabase
                                                    ↓
                                        Analyst Agent → AnalystReport
                                                    ↓
                                            [Human Approval]
                                                    ↓
                                        Synthesizer → Newsletter/Alert
```

---

## Key Components

### Source Files

| File | Purpose |
|:-----|:--------|
| `src/app.py` | FastAPI application with logging middleware |
| `src/config.py` | YAML configuration loader & Pydantic models |
| `src/schemas.py` | Report schemas (ScoutReport, AnalystReport, etc.) |
| `src/database.py` | Supabase client wrapper |
| `src/models.py` | Gemini LLM initialization |
| `src/orchestrator.py` | Pipeline coordinator |
| `src/logging_config.py` | Structlog configuration |

### Agents

| File | Purpose |
|:-----|:--------|
| `src/agents/base.py` | BaseAgent with logging & timing |
| `src/agents/scout.py` | ScoutAgent for data collection |
| `src/agents/analyst.py` | AnalystAgent for deep research |

### Intelligence Layer (Phase 3)

| File | Purpose |
|:-----|:--------|
| `src/intelligence/models.py` | CivicEvent, Entity, Document, Alert dataclasses |
| `src/intelligence/event_store.py` | Event persistence + queries |
| `src/intelligence/rules_engine.py` | Watchdog alert generation |
| `src/intelligence/adapters/base_adapter.py` | Base adapter with entity extraction |
| `src/intelligence/adapters/civicclerk_adapter.py` | Meeting → CivicEvent |
| `src/intelligence/adapters/srwmd_adapter.py` | Permit → CivicEvent |
| `src/intelligence/adapters/florida_notices_adapter.py` | Notice → CivicEvent |

### Scrapers

| File | Purpose |
|:-----|:--------|
| `src/tools/civicclerk_scraper.py` | CivicClerk portal scraper |
| `src/tools/srwmd_scraper.py` | SRWMD permit scraper |
| `src/tools/florida_notices_scraper.py` | Florida public notices scraper |
| `src/tools/firecrawl_client.py` | Web scraping via Firecrawl API |
| `src/tools/resource_cache.py` | Discovered resources cache |
| `src/tools/docling_processor.py` | PDF document processing |

### Tasks

| File | Purpose |
|:-----|:--------|
| `src/tasks/celery_app.py` | Celery configuration |
| `src/tasks/beat_schedule.py` | Cron schedules |
| `src/tasks/scout_tasks.py` | Scout background tasks |

---

## Configuration

### YAML Files

| File | Purpose |
|:-----|:--------|
| `config/instance.yaml` | Instance identity, timezone, scheduling |
| `config/sources.yaml` | Government data sources to monitor |
| `config/entities.yaml` | Watchlist (projects, organizations, keywords) |
| `config/watchdog_rules.yaml` | Civic alert rules (14 rules) |
| `config/discovered_resources.yaml` | Resource ID cache |

### Environment Variables

| Variable | Required | Description |
|:---------|:---------|:------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase anon/service key |
| `TAVILY_API_KEY` | No | Tavily research API |
| `FIRECRAWL_API_KEY` | No | Firecrawl scraping API |
| `CELERY_BROKER_URL` | No | Redis URL (default: localhost) |
| `LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | No | console (dev) or json (prod) |

---

## Logging

The system uses **structlog** for structured logging:

### Development (Console)
```
LOG_FORMAT=console
```
```
2026-01-30T13:00:00Z [info] Request completed  request_id=abc123 method=GET path=/health status_code=200
```

### Production (JSON)
```
LOG_FORMAT=json
```
```json
{"timestamp": "2026-01-30T13:00:00Z", "level": "info", "event": "Request completed", "request_id": "abc123", "app": "alachua-civic-intel"}
```

### Usage in Code
```python
from src.logging_config import get_logger

logger = get_logger("my.module", agent_id="A1")
logger.info("Processing started", url="https://example.com")
```

---

## Database Schema

### Core Tables

| Table | Purpose |
|:------|:--------|
| `reports` | Stored ScoutReport/AnalystReport data |
| `approvals` | Human-in-the-loop approval requests |
| `document_chunks` | RAG vector embeddings (pgvector) |

### Vector Search

The system uses pgvector for semantic search:
- Embedding model: `gemini-embedding-001`
- Dimensions: 1536
- Similarity function: Cosine distance

---

## API Endpoints

| Method | Path | Description |
|:-------|:-----|:------------|
| GET | `/` | Health check |
| GET | `/health` | Health status |
| GET | `/info` | Instance information |
| POST | `/run` | Start agent run |
| GET | `/status/{run_id}` | Get run status |
| GET | `/runs` | List recent runs |
| GET | `/approvals` | List pending approvals |
| POST | `/approvals/{id}/decide` | Approve/reject |
| GET | `/stream/{run_id}` | SSE real-time updates |

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest test/test_config.py

# Run tests matching pattern
pytest -k "test_scout"
```

### Test Files

| File | Coverage |
|:-----|:---------|
| `test/conftest.py` | Fixtures & mocks |
| `test/test_config.py` | Configuration loading |
| `test/test_schemas.py` | Pydantic models |
| `test/test_agents.py` | Agent classes |
| `test/test_api.py` | FastAPI endpoints |
| `test/test_tools.py` | Tool modules |
| `test/test_scrapers.py` | Scraper tests (39 passing) |
| `test/test_intelligence.py` | Intelligence layer tests (39 passing) |

**Total: 78 tests passing**

---

## Deployment

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Services

| Service | Port | Description |
|:--------|:-----|:------------|
| `api` | 8000 | FastAPI server |
| `celery-worker` | - | Background tasks |
| `celery-beat` | - | Scheduled tasks |
| `redis` | 6379 | Message broker |

---

## Prompt Library

Agent prompts are stored in `prompt_library/`:

```
prompt_library/
├── config/
│   ├── agent-behavioral-standards.md
│   ├── alachua-context.md
│   └── geographic-scope.md
├── layer-1-scouts/
│   ├── A1-meeting-intelligence-scout.md
│   ├── A2-permit-application-scout.md
│   └── A3-legislative-code-monitor.md
├── layer-2-analysts/
│   ├── B1-impact-assessment-analyst.md
│   └── B2-procedural-integrity-analyst.md
└── examples/
    └── sample-outputs.md
```

---

## Related Documentation

- [README.md](../README.md) - Project overview
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Development setup
- [SOURCE_DIRECTORY.md](SOURCE_DIRECTORY.md) - Data sources
- [SPEC.md](SPEC.md) - Technical specification
- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Roadmap

---

*Last updated: 2026-02-02*
