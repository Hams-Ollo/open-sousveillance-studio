# TODO: Alachua Civic Intelligence Reporting Studio

**Last Updated:** 2026-02-01
**Status:** Phase 2 Complete - Active Development

---

## Priority Legend

- 🔴 **P0 - Critical:** Blocking issues, application won't run
- 🟠 **P1 - High:** Core functionality gaps, should fix before new features
- 🟡 **P2 - Medium:** Important improvements, can work around temporarily
- 🟢 **P3 - Low:** Nice to have, polish items

---

## ✅ Phase 2 Completed (2026-02-01)

### [x] Hybrid Scraping Pipeline
- Discovery phase (meeting/notice list scraping)
- Detail phase (PDF download and extraction)
- Database state tracking for incremental updates

### [x] SRWMD Permit Scraper
- `src/tools/srwmd_scraper.py` - 767 lines
- Scrapes permit applications and issuances
- E-Permitting portal detail page scraping
- Document list extraction
- County filtering (Alachua focus)

### [x] Orchestrator Implementation
- `src/orchestrator.py` - 630 lines
- Central pipeline coordinator
- Job scheduling based on source frequency
- Source-specific job runners
- Scout Agent integration
- CLI interface

### [x] Orchestrator UI
- `src/ui/pages/orchestrator_panel.py`
- Dashboard, Run Pipeline, History tabs

### [x] Code Review Fixes
- Removed unused `asyncio` import
- Fixed hardcoded `site_id` - now from config
- Added URL validation with domain allowlist
- Added `SourceType` constants

### [x] Streamlit Sidebar Cleanup
- Removed redundant navigation
- Added Target Data Sources links
- Created `.streamlit/config.toml`

---

## 🔴 P0 - Critical (Fix Immediately)

### [x] 1. Fix `src/tools.py` - Uses Removed Dependencies

**File:** `src/tools.py`
**Issue:** Imports `requests` and `BeautifulSoup` which were removed from `requirements.txt`
**Impact:** Application crashes on import
**Solution:** Replace with Firecrawl implementation

```python
# Current (broken):
import requests
from bs4 import BeautifulSoup

# Needed:
from firecrawl import Firecrawl
```

---

### [x] 2. Fix `src/models.py` - Invalid Gemini Model Names

**File:** `src/models.py`
**Issue:** Uses non-existent model identifiers `gemini-3.0-pro` and `gemini-3.0-flash`
**Impact:** API calls fail
**Solution:** Update to valid model names

```python
# Current (broken):
model="gemini-3.0-pro"
model="gemini-3.0-flash"

# Should be:
model="gemini-2.5-pro"
model="gemini-2.5-flash"
```

---

### [x] 3. Fix `src/config.py` - Module-Level Crash

**File:** `src/config.py` (lines 392-401)
**Issue:** Raises `ValueError` on import if `GOOGLE_API_KEY` not set
**Impact:** Cannot import any module that imports config without API key
**Solution:** Remove legacy exports or make validation lazy

---

## 🟠 P1 - High Priority (Core Functionality)

### [x] 4. Delete `src/registry.py` - Redundant Source Registry

**File:** `src/registry.py`
**Issue:** Hardcoded registry duplicates `config/sources.yaml`
**Impact:** Configuration drift, maintenance burden
**Solution:** Remove file, update `main.py` to use `config.get_all_sources()`

---

### [x] 5. Create `src/tools/firecrawl_client.py`

**Status:** File does not exist
**Required by:** README architecture, Scout agents
**Implementation:**

- Firecrawl wrapper with retry logic
- Actions support for React SPAs (wait, scroll, click)
- Batch scraping support
- Error handling and rate limiting

---

### [x] 6. Create `src/tools/docling_processor.py`

**Status:** File does not exist
**Required by:** README architecture, PDF processing
**Implementation:**

- Docling DocumentConverter wrapper
- Markdown export
- LangChain text splitting integration
- Table extraction handling

---

### [x] 7. Create `src/app.py` - FastAPI Application

**File:** `src/main.py`
**Issue:** Currently CLI-only with `argparse`, README documents FastAPI server
**Solution:** Create proper FastAPI application with:

- `POST /run` - Trigger agent runs
- `GET /status` - Check run status
- `GET /approvals/pending` - List pending approvals
- `POST /approvals/{id}/decide` - Approve/reject

---

### [x] 8. Create `src/tasks/` Directory - Celery Integration

**Status:** Directory does not exist
**Required files:**

- `src/tasks/__init__.py`
- `src/tasks/celery_app.py` - Celery application configuration
- `src/tasks/beat_schedule.py` - Periodic task schedule
- `src/tasks/scout_tasks.py` - Scout agent task definitions

---

### [x] 9. Create `src/api/routes/` Directory - FastAPI Routes

**Status:** Directory does not exist
**Required files:**

- `src/api/__init__.py`
- `src/api/routes/__init__.py`
- `src/api/routes/workflows.py` - POST /run, GET /status
- `src/api/routes/approvals.py` - Human-in-the-loop endpoints
- `src/api/routes/streaming.py` - SSE for real-time updates

---

### [x] 10. Create `src/workflows/` Directory - LangGraph

**Status:** Directory does not exist
**Required files:**

- `src/workflows/__init__.py`
- `src/workflows/graphs.py` - LangGraph workflow definitions
- `src/workflows/checkpointer.py` - Supabase state persistence
- `src/workflows/nodes.py` - Reusable node functions

---

## 🟡 P2 - Medium Priority (Improvements)

### [x] 11. Fix `src/database.py` - Fragile Initialization

**File:** `src/database.py` (line 33)
**Issue:** Module-level `db = Database()` crashes if credentials missing
**Solution:** Lazy initialization pattern

```python
# Current:
db = Database()

# Better:
_db = None
def get_db():
    global _db
    if _db is None:
        _db = Database()
    return _db
```

---

### [x] 12. Create Additional Schemas

**File:** `src/schemas.py`
**Issue:** Only `ScoutReport` exists, Analyst reuses it
**Add:**

- `AnalystReport` - For B1/B2 agents
- `SynthesizerReport` - For C1-C4 agents
- `ApprovalRequest` - For human-in-the-loop

---

### [x] 13. Fix `src/agents/base.py` - Return Type

**File:** `src/agents/base.py`
**Issue:** Forces all agents to return `ScoutReport`
**Solution:** Use `Union[ScoutReport, AnalystReport, ...]` or generic

---

### [x] 14. Create `docs/DEVELOPER_GUIDE.md`

**Status:** Referenced in PROJECT-KNOWLEDGE-BASE.md but doesn't exist
**Content needed:**

- Local development setup
- Environment variables
- Running tests
- Contributing guidelines

---

### [x] 15. Add Embedding/Vector Support

**Status:** Not implemented
**Required for:** RAG, semantic search
**Implementation:**

- Gemini embeddings integration
- pgvector storage in Supabase
- Chunking pipeline with Docling + LangChain

---

## 🟢 P3 - Low Priority (Polish)

### [x] 16. Add Unit Tests

**Directory:** `test/`
**Implemented:**

- Config loading tests
- Schema validation tests
- Agent mock tests
- API endpoint tests
- Tools tests

---

### [x] 17. Create Docker Compose

**Status:** Implemented
**Services:**

- Redis
- Celery worker
- Celery Beat
- FastAPI app

---

### [x] 18. Add Logging Configuration

**Status:** ~~Using print statements~~ Implemented with structlog
**Solution:** Proper Python logging with structured output

---

### [x] 19. Update PROJECT-KNOWLEDGE-BASE.md

**File:** `docs/PROJECT-KNOWLEDGE-BASE.md`
**Status:** Created comprehensive knowledge base with current tech stack

---

### [x] 20. Clean Up Prompt Library

**Directory:** `prompt_library/`
**Status:** Integrated with automated agents via `src/prompts/` module

---

## Completed Items

### [x] Update README with Firecrawl integration

**Completed:** 2026-01-29

### [x] Update README with Celery (replaced APScheduler)

**Completed:** 2026-01-29

### [x] Update README with Docling integration

**Completed:** 2026-01-29

### [x] Clean up requirements.txt

**Completed:** 2026-01-29

### [x] P0-1: Fix src/tools.py - Replace requests/bs4 with Firecrawl

**Completed:** 2026-01-29

### [x] P0-2: Fix src/models.py - Update Gemini model names to 2.5

**Completed:** 2026-01-29

### [x] P0-3: Fix src/config.py - Remove module-level crash

**Completed:** 2026-01-29

### [x] P1-4: Delete src/registry.py - Use YAML config instead

**Completed:** 2026-01-29

### [x] P1-5: Create src/tools/firecrawl_client.py

**Completed:** 2026-01-29

### [x] P1-6: Create src/tools/docling_processor.py

**Completed:** 2026-01-29

### [x] P1-7: Create src/app.py - FastAPI application

**Completed:** 2026-01-29

### [x] P1-8: Create src/tasks/ - Celery integration

**Completed:** 2026-01-29

### [x] P1-9: Create src/api/routes/ - FastAPI routes

**Completed:** 2026-01-29

### [x] P1-10: Create src/workflows/ - LangGraph workflows

**Completed:** 2026-01-29

### [x] P2-11: Fix src/database.py - Lazy initialization

**Completed:** 2026-01-30

### [x] P2-12: Create Additional Schemas (AnalystReport, SynthesizerReport, ApprovalRequest)

**Completed:** 2026-01-30

### [x] P2-13: Fix src/agents/base.py - Return type to BaseReport

**Completed:** 2026-01-30

### [x] P2-14: Create docs/DEVELOPER_GUIDE.md

**Completed:** 2026-01-30

### [x] P2-15: Add Embedding/Vector Support (RAG pipeline)

**Completed:** 2026-01-30

- `src/tools/embeddings.py` - Gemini embedding service (1536 dimensions)
- `src/tools/chunking.py` - LangChain text splitting
- `src/tools/vector_store.py` - Supabase pgvector operations
- `src/tools/rag_pipeline.py` - Unified RAG interface
- `migrations/001_vector_schema.sql` - Database schema

### [x] P3-18: Add Logging Configuration (structlog)

**Completed:** 2026-01-30

- `src/logging_config.py` - Centralized structlog configuration
- JSON output for production, colored console for development
- Request logging middleware in FastAPI
- Agent logging in BaseAgent with timing
- Celery task logging with context binding
- Environment variables: `LOG_LEVEL`, `LOG_FORMAT`

### [x] P3-16: Add Unit Tests

**Completed:** 2026-01-30

- `test/conftest.py` - Pytest fixtures and mocks
- `test/test_config.py` - Configuration loading tests
- `test/test_schemas.py` - Pydantic model validation tests
- `test/test_agents.py` - Agent class tests
- `test/test_api.py` - FastAPI endpoint tests
- `test/test_tools.py` - Tools module tests

### [x] P3-17: Create Docker Compose

**Completed:** 2026-01-30

- `docker-compose.yml` - Multi-service orchestration
- `Dockerfile` - Python 3.11 slim image
- Services: api, celery-worker, celery-beat, redis
- Health checks and volume mounts

### [x] P3-19: Create PROJECT-KNOWLEDGE-BASE.md

**Completed:** 2026-01-30

- `docs/PROJECT-KNOWLEDGE-BASE.md` - Comprehensive technical reference
- Updated `docs/DEVELOPER_GUIDE.md` with Docker Compose instructions

### [x] P3-20: Clean Up Prompt Library

**Completed:** 2026-01-30

- `src/prompts/__init__.py` - Prompt module initialization
- `src/prompts/loader.py` - PromptLoader utility for loading prompt files
- `src/prompts/context.py` - AgentContext with extracted domain context
- Updated `ScoutAgent` and `AnalystAgent` to use domain context
- Updated `prompt_library/README.md` with integration documentation

### [x] Security Scan and Vulnerability Fixes

**Completed:** 2026-01-30

- Ran pip-audit, bandit, and safety scans
- Fixed hardcoded host binding (0.0.0.0 → env var)
- Pinned all dependencies to specific versions
- Added HOST, PORT, RELOAD env vars to `.env.example`

### [x] Streamlit Dev Console

**Completed:** 2026-01-30

- `src/ui/app.py` - Main Streamlit application
- `src/ui/pages/agent_runner.py` - Test Scout/Analyst agents
- `src/ui/pages/prompt_inspector.py` - View prompt library
- `src/ui/pages/source_tester.py` - Test web scraping
- `src/ui/pages/config_viewer.py` - View YAML configs and env vars
- Added `streamlit==1.45.0` to requirements.txt

### [x] Native Google GenAI SDK Migration

**Completed:** 2026-01-30

- Replaced `langchain_google_genai` with native `google.genai` SDK
- Fixed PyTorch DLL loading issues on Windows
- Updated `src/models.py` with `GeminiModel` and `StructuredGeminiModel` classes
- Updated `src/agents/scout.py` and `src/agents/analyst.py` to use native SDK
- Fixed model names to `gemini-2.5-pro` and `gemini-2.5-flash`

### [x] Documentation Restructure

**Completed:** 2026-01-30

- Simplified `README.md` to project overview and quick start
- Created `docs/ARCHITECTURE.md` with technical diagrams and system design
- Created `docs/SYSTEM_OVERVIEW.md` for workflow brainstorming
- Updated `docs/PROJECT_PLAN.md` with future agents, features, epics, user stories

### [x] Coding Standards & Tooling

**Completed:** 2026-01-30

- Created `docs/CODING_STANDARDS.md` - comprehensive development standards
- Created `pyproject.toml` - Black, Ruff, mypy, pytest configuration
- Created `.pre-commit-config.yaml` - automated quality checks
- Created `.vscode/settings.json` - IDE workspace settings
- Created `src/exceptions.py` - custom exception classes

### [x] Startup Script Fix & Documentation

**Completed:** 2026-01-30

- Fixed `start-all.ps1` - `$projectRoot` variable now properly interpolated
- Added startup script documentation to `README.md`
- Added startup script documentation to `docs/DEVELOPER_GUIDE.md`

---

## 🔜 Next Priority Items

### [ ] Add Scraper Unit Tests (P1)

- Mock Firecrawl responses for CivicClerk scraper
- Mock Firecrawl responses for Florida Notices scraper
- Mock Firecrawl responses for SRWMD scraper
- Test hybrid pipeline with mocked database

### [ ] Add Database FK Constraints (P2)

- Add foreign key from `documents.meeting_id` to `scraped_meetings`
- Update migration file

### [ ] Implement Async/Parallel Scraping (P2)

- Convert Orchestrator to use asyncio
- Run independent source scrapes in parallel
- Add concurrency limits

### [ ] Supabase Integration Testing (P2)

- Test database writes with real Supabase instance
- Implement document storage for PDFs
- Test vector embeddings with pgvector

### [ ] Human-in-the-Loop Approval Flow (P3)

- Implement LangGraph interrupt/resume
- Build approval UI in Streamlit
- Email notifications for pending approvals

### [ ] Phase 3: Intelligent Evolution (Future)

- Pattern detection across meetings
- Learning from historical data
- Anomaly detection for unusual items

---

## Notes

- **Current State:** Phase 2 complete - Hybrid scraping pipeline, Orchestrator, 3 scrapers working
- **LLM:** Using native `google.genai` SDK (not LangChain) to avoid PyTorch dependency issues
- **Testing:** 37 tests passing, 7 skipped (docling/NumPy compatibility)
- **Next Focus:** Add scraper tests, test full pipeline with real data

---

## Quick Reference: File Status

| File | Status | Notes |
|:-----|:-------|:------|
| `src/tools.py` | ✅ Working | Firecrawl + Tavily tools |
| `src/models.py` | ✅ Working | Native google.genai SDK |
| `src/config.py` | ✅ Working | YAML config loader |
| `src/database.py` | ✅ Working | Meeting state tracking |
| `src/schemas.py` | ✅ Working | All report types |
| `src/exceptions.py` | ✅ Working | Custom exception classes |
| `src/orchestrator.py` | ✅ New | Pipeline orchestrator (630 lines) |
| `src/agents/base.py` | ✅ Working | BaseReport return type |
| `src/agents/scout.py` | ✅ Working | Tiered PDF/metadata analysis |
| `src/agents/analyst.py` | ✅ Working | Tested via Streamlit |
| `src/tools/civicclerk_scraper.py` | ✅ Working | Hybrid pipeline support |
| `src/tools/florida_notices_scraper.py` | ✅ Working | Hybrid pipeline support |
| `src/tools/srwmd_scraper.py` | ✅ New | Permit scraper (767 lines) |
| `src/tools/firecrawl_client.py` | ✅ Updated | URL validation added |
| `src/ui/app.py` | ✅ Updated | Orchestrator tab, sidebar cleanup |
| `src/ui/pages/orchestrator_panel.py` | ✅ New | Orchestrator control panel |
| `config/sources.yaml` | ✅ Updated | SRWMD sources added |
| `.streamlit/config.toml` | ✅ New | Hide sidebar nav |
| `start-all.ps1` | ✅ Working | Starts FastAPI + Streamlit |
