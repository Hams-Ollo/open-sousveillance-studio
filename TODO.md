# TODO: Alachua Civic Intelligence Reporting Studio

**Last Updated:** 2026-02-05
**Status:** P0 Remediation Complete - P1 Sprint Next

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

## ✅ Recently Completed (2026-02-02)

### [x] Add Scraper Unit Tests (P1)

- 39 tests passing for CivicClerk, Florida Notices, SRWMD scrapers
- Mock Firecrawl responses
- URL validation tests
- Integration workflow tests

### [x] Source Discovery & Playbooks

- `scripts/discover_sitemaps.py` - Firecrawl map_site API integration
- `scripts/analyze_sources.py` - Deep content sampling, playbook generation
- `config/source_playbooks/` - 5 YAML playbooks generated

### [x] Resource Cache System

- `config/discovered_resources.yaml` - Persistent cache of discovered IDs
- `src/tools/resource_cache.py` - Read/write utility for scrapers
- Integrated into all 3 scrapers (auto-update after scrapes)

---

## ✅ Recently Completed (2026-02-05)

### [x] Two-Layer Agent Architecture

- ScoutAgent (Layer 1): Analyzes scraped content against watchlist
- AnalystAgent (Layer 2): Deep research on high-relevance items (≥0.7 score)
- Dual research providers: Tavily (fast) + Gemini Deep Research (thorough)
- `ResearchProvider` enum: TAVILY, GEMINI, BOTH

### [x] Orchestrator Pipeline

- Daily scheduled runs at 4 AM EST via Celery Beat
- Manual runs via Streamlit Orchestrator Panel
- `run_orchestrator_pipeline` and `run_single_source` Celery tasks
- Skip analysis / skip deep research options

### [x] Gemini Deep Research Integration

- `src/tools/gemini_research.py` - Client wrapper for Interactions API
- Uses `deep-research-pro-preview-12-2025` agent
- Async polling with configurable timeout
- Added `google-genai==1.60.0` to requirements.txt

### [x] Database Deep Research Methods

- `get_high_relevance_reports()` - Find reports needing deep research
- `save_deep_research_report()` - Save and link deep research results

### [x] Documentation Updates

- Updated ARCHITECTURE.md with two-layer agent framework
- Updated DEVELOPER_GUIDE.md with current architecture
- Updated SYSTEM_OVERVIEW.md with dual research providers
- Updated USER_GUIDE.md with 4 AM schedule info

---

## ✅ P0 - Critical: Code Review Findings (Completed 2026-02-05)

### [x] CR-01: Bridge Intelligence Layer to Orchestrator

**Completed:** 2026-02-05
**Impact:** The entire intelligence layer (EventStore, RulesEngine, watchdog alerts) was dead code
**Fix Applied:**
- [x] Modified 3 scrapers to expose raw items in pipeline results (`raw_meetings`, `raw_notices`)
- [x] Added `_process_intelligence()` method to orchestrator
- [x] Initialized adapters, EventStore, and RulesEngine in orchestrator `__init__`
- [x] Wired intelligence processing into all 3 job runners
- [x] Added `events_created` and `alerts_generated` fields to `JobResult`
- [x] Updated `generate_summary()` with event/alert stats and alert details

### [x] CR-02: Fix AnalystAgent Schema (Uses ScoutReport Instead of AnalystReport)

**Completed:** 2026-02-05
**Fix Applied:**
- [x] Changed `self.structured_llm = self.llm.with_structured_output(AnalystReport)`
- [x] Updated prompt to reference AnalystReport fields (topic, sections, recommendations, entities_mentioned)
- [x] Updated `database.py` `save_deep_research_report` to accept AnalystReport

### [x] CR-03: Fix Missing Import and Dependency Bugs

**Completed:** 2026-02-05
**Fix Applied:**
- [x] Added `import os` to `src/app.py`
- [x] Added `sse-starlette==2.2.1` to `requirements.txt`
- [x] Fixed `any` → `Any` type annotation in `src/exceptions.py`
- [x] Removed duplicate `import json` inside `src/database.py`
- [x] Removed unused `field_validator` import in `src/config.py`

### [x] CR-04: Implement Real Agent Tests

**Completed:** 2026-02-05
**Fix Applied:**
- [x] 11 real agent tests replacing 7 skipped stubs
- [x] BaseAgent: init, run returns report, error propagation
- [x] ScoutAgent: init, validation, PDF analysis mode, metadata-only mode
- [x] AnalystAgent: init, validation, Tavily research flow, Tavily failure handling
- [x] Fixed `MeetingItem` fixture in `conftest.py` (missing required fields)
- [x] Fixed all `Optional` fields in `src/schemas.py` for Pydantic 2.x (`default=None`)
- [x] Fixed `test_schemas.py` failures (MeetingItem, UrgencyAlert, ApprovalRequest)

---

## 🟠 P1 - High Priority: Code Review Findings

### [x] CR-05: Eliminate `src/tools.py` / `src/tools/` Package Collision

**Completed:** 2026-02-05
**Fix Applied:**
- [x] Moved `src/tools.py` contents to `src/tools/langchain_tools.py`
- [x] Replaced `importlib` hack in `src/tools/__init__.py` with clean import
- [x] Deleted `src/tools.py`
- [x] Updated comment in `src/agents/scout.py`

### [x] CR-06: Create Agent Registry/Factory Pattern

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Created `AGENT_REGISTRY` dict in `src/agents/__init__.py` mapping all 6 agent IDs to classes
- [x] Created `get_agent()`, `get_agent_info()`, `list_agents()` factory functions
- [x] Replaced string-prefix checks in `src/app.py` and `src/main.py` with layer-based routing
- [x] Added `--list-agents` and `--topic` CLI flags to `src/main.py`
- [x] Added `/agents` API endpoint

### [x] CR-07: Unify Version Numbers

**Completed:** 2026-02-05
**Fix Applied:**
- [x] Created `src/__init__.py` with `__version__ = "0.4.0-alpha"`
- [x] Updated `pyproject.toml` version to `0.4.0-alpha`
- [x] Updated `src/app.py` to import `__version__` from `src`
- [x] Updated `src/ui/app.py` to import `__version__` from `src`

### [x] CR-08: Move Run State to Redis

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Created `src/state.py` with `RedisStateStore` class (in-memory fallback if Redis unavailable)
- [x] Replaced all `runs: dict` and `pending_approvals: dict` in `src/app.py` with `state` store
- [x] Updated SSE event generator and all route handlers to use state store
- [x] Added TTL (24h for runs, 7d for approvals)

### [x] CR-09: Add API Authentication

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Created `verify_api_key` dependency in `src/app.py` checking `X-API-Key` header
- [x] Protected `/run`, `/runs`, `/approvals/*`, `/costs` endpoints
- [x] `/health`, `/info`, `/status`, `/agents`, `/stream` remain public
- [x] Added `API_KEY` to `.env.example` (blank = auth disabled for dev)

### [x] CR-10: Wire RAG Pipeline Into Production

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Added `_get_rag()`, `_ingest_to_rag()`, `_retrieve_rag_context()` to `src/orchestrator.py`
- [x] Wired ingestion into `_run_analysis()` — ingests PDF content before Scout analysis
- [x] Wired retrieval into both `_run_analysis()` and `_run_deep_research()` for cross-document context
- [x] All RAG calls wrapped in try/except — failures are non-blocking

### [x] CR-11: Fix Thread Safety for Singletons

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Added `threading.Lock()` with double-checked locking to all 12 singleton getters:
  - `database.py`, `state.py`, `langchain_tools.py`, `resource_cache.py`, `gemini_research.py`
  - `embeddings.py`, `vector_store.py`, `chunking.py`, `rag_pipeline.py`
  - `event_store.py`, `rules_engine.py`, `health.py`
- [x] `reset_health_service()` also uses lock for safe test teardown

### [x] CR-12: Add LLM Rate Limiting and Cost Controls

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Created `src/llm_cost.py` with `CostTracker`, model pricing table, `BudgetExceededError`
- [x] Wired into `GeminiModel.invoke()` and `StructuredGeminiModel.invoke()` in `src/models.py`
- [x] Tracks input/output tokens per model from `usage_metadata`
- [x] Enforces configurable daily budget (`LLM_DAILY_BUDGET_USD`), warns at 80%
- [x] Added `/costs` API endpoint for daily summary
- [x] Added `LLM_DAILY_BUDGET_USD` to `.env.example`

### [x] CR-13: Add Graceful Shutdown and Process Management

**Completed:** 2026-02-06
**Fix Applied:**
- [x] Created `stop-all.ps1` — reads PIDs from `.pids/`, stops processes + children
- [x] Updated `start-all.ps1` — writes PIDs to `.pids/`, checks for existing processes
- [x] Added `.pids/` to `.gitignore`

---

## 🟡 P2 - Medium Priority: Code Review Findings

### [ ] CR-14: Fix CORS Configuration

**File:** `src/app.py` lines 124-130
**Impact:** `allow_origins=["*"]` + `allow_credentials=True` is an anti-pattern
**Fix:** Configure explicit allowed origins from environment variable

### [ ] CR-15: Move Runtime State Files Out of `config/`

**Impact:** `config/events.json`, `config/scraper_health.json`, `config/discovered_resources.yaml` conflate config with runtime state
**Fix:**
- [ ] Move to `data/state/` directory
- [ ] Update all paths in `EventStore`, `HealthService`, `ResourceCache`
- [ ] Add `data/state/` to `.gitignore`

### [ ] CR-16: Fix `lru_cache` Mutable Return Values

**File:** `src/config.py` lines 96-99
**Impact:** Cached dicts can be mutated by callers, corrupting cache
**Fix:** Return deep copies or use frozen/immutable structures

### [ ] CR-17: Consolidate Persistence Layer

**Impact:** Two overlapping stores — file-based `EventStore` and Supabase `Database`
**Fix:**
- [ ] Decide primary persistence (Supabase for production)
- [ ] Add Supabase backend to EventStore (replace JSON file)
- [ ] Ensure single source of truth for event data

### [ ] CR-18: Add Orchestrator Tests

**Impact:** Most complex component has zero test coverage
**Fix:**
- [ ] Create `test/test_orchestrator.py`
- [ ] Test source routing logic
- [ ] Test pipeline run with mocked scrapers
- [ ] Test error handling (one source fails, others continue)
- [ ] Test deep research triggering on high-relevance items

### [ ] CR-19: Add LangGraph Workflow Tests

**Impact:** `src/workflows/graphs.py` has no test coverage
**Fix:**
- [ ] Create `test/test_workflows.py`
- [ ] Test Scout workflow state transitions
- [ ] Test Analyst workflow with approval checkpoint
- [ ] Test error handling in workflow nodes

### [ ] CR-20: Fix EventStore Concurrency Issues

**Impact:** Full JSON rewrite per event, no file locking, batch save calls `_save()` per event
**Fix:**
- [ ] Implement atomic writes (write to temp file + rename)
- [ ] Defer `_save()` in `save_events()` batch method to end
- [ ] Add file locking for multi-process safety

### [ ] CR-21: Fix Sequential `embed_batch` in Embeddings Service

**File:** `src/tools/embeddings.py` lines 124-128
**Impact:** Individual API calls in a loop; slow and expensive for large documents
**Fix:** Use Gemini batch embedding API

### [ ] CR-22: Extract Hardcoded Alachua-Specific Logic to Config

**Impact:** Project claims location-agnostic but has hardcoded Alachua entities, domains, keywords
**Fix:**
- [ ] Move `ALLOWED_DOMAINS` in `firecrawl_client.py` to config
- [ ] Move hardcoded entities in `src/prompts/context.py` to `entities.yaml`
- [ ] Move Alachua-specific keywords in `base_adapter.py` to config
- [ ] Make `civicclerk_scraper.py` source_id dynamic from config

### [ ] CR-23: Add Celery Worker Health Endpoint

**Impact:** No visibility into whether Celery workers/beat are running
**Fix:**
- [ ] Add `/health/celery` endpoint that pings Celery
- [ ] Add health checks for Celery containers in `docker-compose.yml`

### [ ] CR-24: Fix Database Migration Gaps

**Impact:** `deep_research_reports` table referenced but never created; duplicate migration numbering
**Fix:**
- [ ] Create `002_deep_research_reports.sql` migration
- [ ] Rename `001_vector_schema.sql` to `002_vector_schema.sql`
- [ ] Add FK constraints (documents → scraped_meetings, etc.)
- [ ] Consider migration runner tool (dbmate, Alembic)

### [ ] CR-25: Fix Custom `TimeoutError` Shadowing Builtin

**File:** `src/exceptions.py` line 87
**Fix:** Rename to `OperationTimeoutError` or similar

---

## 🟢 P3 - Low Priority: Code Review Findings

### [ ] CR-26: Evaluate LangChain/LangGraph Necessity

**Impact:** Heavy deps (`langchain`, `langgraph`) barely used in production pipeline
**Analysis:**
- LangChain only used for `@tool` decorators and `RecursiveCharacterTextSplitter`
- LangGraph only used in disconnected `src/workflows/graphs.py`
- Native `google.genai` SDK handles all LLM calls
**Decision needed:** Keep if planning to activate LangGraph workflows, remove if staying procedural

### [ ] CR-27: Replace `print()` Statements With Structured Logging

- [ ] Replace `print()` calls in `src/main.py` with `structlog` logger
- [ ] Replace `print()` in `src/app.py` line 341 with logger
- [ ] Replace `print()` in `src/tools/firecrawl_client.py` line 280 with logger

### [ ] CR-28: Fix `sys.path` Manipulation in Streamlit UI

**File:** `src/ui/app.py` lines 14-15
**Fix:** Use proper package installation (`pip install -e .`) instead of `sys.path.insert`

### [ ] CR-29: Remove Docling Dependency Conflict

**Impact:** Docling pulls in PyTorch/transformers causing NumPy conflicts, all agent tests skipped
**Options:**
- Make docling an optional dependency
- Remove docling if Firecrawl handles PDF extraction sufficiently
- Pin compatible NumPy version

---

## 🔜 Previously Identified Items (Carried Forward)

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

---

## ✅ Phase 3: Intelligent Evolution (Complete)

**Approach:** Event-driven + User-centric (Option C hybrid)
**Status:** Built but not yet wired into production pipeline (see CR-01)

### [x] Phase 3.1: CivicEvent Unified Model + Adapters ✅
### [x] Phase 3.2: Event Persistence + Basic Queries ✅
### [x] Phase 3.3: Watchdog Rules Engine ✅
### [x] Phase 3.4: Health Metrics in Scrapers ✅

### [ ] Phase 3.5: User Watchlists (Deferred to v1.1)
### [ ] Phase 3.6: Entity Extraction Enhancement (Deferred to v1.1)
### [ ] Phase 3.7: Cross-Source Search (Deferred to v1.1)

### Future: Anomaly Detection

Detect unusual patterns (after sufficient historical data):

- Permit volume spikes in specific areas
- Rushed approvals (faster than typical)
- Repeat applicants with many active permits
- Missing required public notices
- Rezoning clusters in same area

### Future: Intelligent Scheduling

Optimize scrape timing based on learned patterns

---

## Notes

- **Current State:** P0 remediation complete - Intelligence layer bridged to orchestrator
- **LLM:** Using native `google.genai` SDK (not LangChain) to avoid PyTorch dependency issues
- **Testing:** 156 tests passing, 0 failures (11 agent + 39 scraper + 39 intelligence + 67 other)
- **Orchestrator:** Runs daily at 4 AM EST via Celery Beat, now with intelligence layer integration
- **Research Providers:** Dual providers (Tavily + Gemini Deep Research) for Layer 2
- **Architecture Decision:** Two-layer agent system (Scout + Analyst) with Orchestrator coordination
- **Intelligence Layer:** Now wired into orchestrator — adapters, EventStore, RulesEngine all active

---

## Quick Reference: File Status

### Core Application

| File | Status | Notes |
|:-----|:-------|:------|
| `src/tools.py` | ✅ Working | Firecrawl + Tavily tools |
| `src/models.py` | ✅ Working | Native google.genai SDK |
| `src/config.py` | ✅ Working | YAML config loader |
| `src/database.py` | ✅ Working | Meeting state tracking |
| `src/schemas.py` | ✅ Working | All report types |
| `src/exceptions.py` | ✅ Working | Custom exception classes |
| `src/orchestrator.py` | ✅ Working | Pipeline orchestrator with intelligence bridge |

### Agents

| File | Status | Notes |
|:-----|:-------|:------|
| `src/agents/base.py` | ✅ Working | BaseReport return type |
| `src/agents/scout.py` | ✅ Working | Tiered PDF/metadata analysis |
| `src/agents/analyst.py` | ✅ Working | Tested via Streamlit |

### Scrapers (with ResourceCache)

| File | Status | Notes |
|:-----|:-------|:------|
| `src/tools/civicclerk_scraper.py` | ✅ Updated | ResourceCache integration |
| `src/tools/florida_notices_scraper.py` | ✅ Updated | ResourceCache integration |
| `src/tools/srwmd_scraper.py` | ✅ Updated | ResourceCache integration |
| `src/tools/firecrawl_client.py` | ✅ Working | URL validation |
| `src/tools/resource_cache.py` | ✅ New | Discovered resources cache |

### Intelligence Layer (Phase 3)

| File | Status | Notes |
|:-----|:-------|:------|
| `src/intelligence/__init__.py` | ✅ New | Module exports |
| `src/intelligence/models.py` | ✅ New | CivicEvent, Entity, Document, Alert |
| `src/intelligence/event_store.py` | ✅ New | Event persistence + queries |
| `src/intelligence/rules_engine.py` | ✅ New | Watchdog alert generation |
| `src/intelligence/adapters/base_adapter.py` | ✅ New | Entity/tag extraction |
| `src/intelligence/adapters/civicclerk_adapter.py` | ✅ New | Meeting → CivicEvent |
| `src/intelligence/adapters/srwmd_adapter.py` | ✅ New | Permit → CivicEvent |
| `src/intelligence/adapters/florida_notices_adapter.py` | ✅ New | Notice → CivicEvent |

### Configuration

| File | Status | Notes |
|:-----|:-------|:------|
| `config/sources.yaml` | ✅ Working | All sources configured |
| `config/discovered_resources.yaml` | ✅ New | Resource ID cache |
| `config/watchdog_rules.yaml` | ✅ New | 14 civic alert rules |
| `config/source_playbooks/` | ✅ New | 5 source playbooks |

### UI & Scripts

| File | Status | Notes |
|:-----|:-------|:------|
| `src/ui/app.py` | ✅ Working | Orchestrator tab |
| `src/ui/pages/orchestrator_panel.py` | ✅ Working | Pipeline control |
| `scripts/discover_sitemaps.py` | ✅ New | Firecrawl map_site |
| `scripts/analyze_sources.py` | ✅ New | Playbook generator |
| `start-all.ps1` | ✅ Working | Starts FastAPI + Streamlit |

### Tests

| File | Status | Notes |
|:-----|:-------|:------|
| `test/test_scrapers.py` | ✅ Working | 39 tests passing |
| `test/test_intelligence.py` | ✅ Working | 39 tests passing |
| `test/test_agents.py` | ✅ Updated | 11 real tests (was 7 skipped stubs) |
| `test/test_schemas.py` | ✅ Fixed | 9 tests passing (Pydantic 2.x compat) |
