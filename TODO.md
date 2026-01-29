# TODO: Alachua Civic Intelligence Reporting Studio

**Last Updated:** 2026-01-29  
**Status:** Active Development

---

## Priority Legend
- 🔴 **P0 - Critical:** Blocking issues, application won't run
- 🟠 **P1 - High:** Core functionality gaps, should fix before new features
- 🟡 **P2 - Medium:** Important improvements, can work around temporarily
- 🟢 **P3 - Low:** Nice to have, polish items

---

## 🔴 P0 - Critical (Fix Immediately)

### [ ] 1. Fix `src/tools.py` - Uses Removed Dependencies
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

### [ ] 2. Fix `src/models.py` - Invalid Gemini Model Names
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

### [ ] 3. Fix `src/config.py` - Module-Level Crash
**File:** `src/config.py` (lines 392-401)  
**Issue:** Raises `ValueError` on import if `GOOGLE_API_KEY` not set  
**Impact:** Cannot import any module that imports config without API key  
**Solution:** Remove legacy exports or make validation lazy

---

## 🟠 P1 - High Priority (Core Functionality)

### [ ] 4. Delete `src/registry.py` - Redundant Source Registry
**File:** `src/registry.py`  
**Issue:** Hardcoded registry duplicates `config/sources.yaml`  
**Impact:** Configuration drift, maintenance burden  
**Solution:** Remove file, update `main.py` to use `config.get_all_sources()`

---

### [ ] 5. Create `src/tools/firecrawl_client.py`
**Status:** File does not exist  
**Required by:** README architecture, Scout agents  
**Implementation:**
- Firecrawl wrapper with retry logic
- Actions support for React SPAs (wait, scroll, click)
- Batch scraping support
- Error handling and rate limiting

---

### [ ] 6. Create `src/tools/docling_processor.py`
**Status:** File does not exist  
**Required by:** README architecture, PDF processing  
**Implementation:**
- Docling DocumentConverter wrapper
- Markdown export
- LangChain text splitting integration
- Table extraction handling

---

### [ ] 7. Refactor `src/main.py` - Convert to FastAPI
**File:** `src/main.py`  
**Issue:** Currently CLI-only with `argparse`, README documents FastAPI server  
**Solution:** Create proper FastAPI application with:
- `POST /run` - Trigger agent runs
- `GET /status` - Check run status
- `GET /approvals/pending` - List pending approvals
- `POST /approvals/{id}/decide` - Approve/reject

---

### [ ] 8. Create `src/tasks/` Directory - Celery Integration
**Status:** Directory does not exist  
**Required files:**
- `src/tasks/__init__.py`
- `src/tasks/celery_app.py` - Celery application configuration
- `src/tasks/beat_schedule.py` - Periodic task schedule
- `src/tasks/scout_tasks.py` - Scout agent task definitions

---

### [ ] 9. Create `src/api/routes/` Directory - FastAPI Routes
**Status:** Directory does not exist  
**Required files:**
- `src/api/__init__.py`
- `src/api/routes/__init__.py`
- `src/api/routes/workflows.py` - POST /run, GET /status
- `src/api/routes/approvals.py` - Human-in-the-loop endpoints
- `src/api/routes/streaming.py` - SSE for real-time updates

---

### [ ] 10. Create `src/workflows/` Directory - LangGraph
**Status:** Directory does not exist  
**Required files:**
- `src/workflows/__init__.py`
- `src/workflows/graphs.py` - LangGraph workflow definitions
- `src/workflows/checkpointer.py` - Supabase state persistence
- `src/workflows/nodes.py` - Reusable node functions

---

## 🟡 P2 - Medium Priority (Improvements)

### [ ] 11. Fix `src/database.py` - Fragile Initialization
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

### [ ] 12. Create Additional Schemas
**File:** `src/schemas.py`  
**Issue:** Only `ScoutReport` exists, Analyst reuses it  
**Add:**
- `AnalystReport` - For B1/B2 agents
- `SynthesizerReport` - For C1-C4 agents
- `ApprovalRequest` - For human-in-the-loop

---

### [ ] 13. Fix `src/agents/base.py` - Return Type
**File:** `src/agents/base.py`  
**Issue:** Forces all agents to return `ScoutReport`  
**Solution:** Use `Union[ScoutReport, AnalystReport, ...]` or generic

---

### [ ] 14. Create `docs/DEVELOPER_GUIDE.md`
**Status:** Referenced in PROJECT-KNOWLEDGE-BASE.md but doesn't exist  
**Content needed:**
- Local development setup
- Environment variables
- Running tests
- Contributing guidelines

---

### [ ] 15. Add Embedding/Vector Support
**Status:** Not implemented  
**Required for:** RAG, semantic search  
**Implementation:**
- Gemini embeddings integration
- pgvector storage in Supabase
- Chunking pipeline with Docling + LangChain

---

## 🟢 P3 - Low Priority (Polish)

### [ ] 16. Add Unit Tests
**Directory:** `test/` (empty)  
**Needed:**
- Config loading tests
- Schema validation tests
- Agent mock tests

---

### [ ] 17. Create Docker Compose
**Status:** Referenced in README but doesn't exist  
**Services:**
- Redis
- Celery worker
- Celery Beat
- FastAPI app

---

### [ ] 18. Add Logging Configuration
**Status:** Using print statements  
**Solution:** Proper Python logging with structured output

---

### [ ] 19. Update PROJECT-KNOWLEDGE-BASE.md
**File:** `docs/PROJECT-KNOWLEDGE-BASE.md`  
**Issues:**
- References outdated tech (BeautifulSoup as fallback)
- References non-existent DEVELOPER_GUIDE.md
- Tech stack section outdated

---

### [ ] 20. Clean Up Prompt Library
**Directory:** `prompt_library/`  
**Task:** Ensure prompts align with current architecture and agent implementations

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

---

## Notes

- **Current State:** The codebase has excellent documentation (README, YAML configs, prompt library) but implementation lags behind
- **Recommended Approach:** Fix P0 issues first to get a runnable baseline, then build out P1 features incrementally
- **Testing Strategy:** Add tests as features are implemented, not retroactively

---

## Quick Reference: File Status

| File | Status | Priority |
|:-----|:-------|:---------|
| `src/tools.py` | 🔴 Broken | P0 |
| `src/models.py` | 🔴 Broken | P0 |
| `src/config.py` | 🟡 Fragile | P0/P2 |
| `src/registry.py` | 🟠 Redundant | P1 |
| `src/main.py` | 🟠 Incomplete | P1 |
| `src/database.py` | 🟡 Fragile | P2 |
| `src/schemas.py` | 🟢 Good | P2 |
| `src/agents/base.py` | 🟡 Needs refactor | P2 |
| `src/agents/scout.py` | 🟢 Good | - |
| `src/agents/analyst.py` | 🟢 Good | - |
