# System Overhaul: Comprehensive Civic Intelligence

**Version:** 1.0.0
**Created:** 2026-01-30
**Status:** Planning → Implementation
**Author:** Development Team

---

## Executive Summary

This document outlines the architectural evolution of Open Sousveillance Studio from a **narrow, keyword-focused monitoring system** to a **comprehensive civic intelligence platform** that can:

1. Provide complete coverage of all government activity
2. Intelligently flag priority items based on watchlists
3. Evolve and learn from accumulated data
4. Be deployed to any municipality with minimal configuration

**Core Principle:** Config-driven *structure* with LLM-driven *intelligence*.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Vision & Goals](#vision--goals)
3. [Architectural Principles](#architectural-principles)
4. [Implementation Phases](#implementation-phases)
5. [Phase 1: Comprehensive Coverage](#phase-1-comprehensive-coverage)
6. [Phase 2: Enhanced Configuration](#phase-2-enhanced-configuration)
7. [Phase 3: Intelligent Evolution](#phase-3-intelligent-evolution)
8. [File Change Tracker](#file-change-tracker)
9. [Testing Checkpoints](#testing-checkpoints)

---

## Current State Analysis

### What Works
- ✅ Agent framework (Scout, Analyst, Synthesizer layers)
- ✅ Structured output schemas (Pydantic models)
- ✅ Prompt library organization
- ✅ Entity/keyword configuration in YAML
- ✅ Supabase integration for storage
- ✅ Streamlit dev console for testing

### What's Too Narrow
- ❌ Prompts hardcode Tara as primary focus
- ❌ Reports filter OUT non-matching items
- ❌ Keywords are 90% Tara-specific
- ❌ No comprehensive civic coverage
- ❌ Can't easily adapt to other municipalities

### The Problem
> "Show up knowing about Tara but blind to everything else"

### The Goal
> "Show up knowing EVERYTHING, with priority items highlighted"

---

## Vision & Goals

### Primary Goals

1. **Comprehensive Coverage**
   - Document ALL agenda items, not just keyword matches
   - Every meeting item gets summarized
   - Every permit gets logged
   - Every vote gets recorded

2. **Intelligent Priority Flagging**
   - Watchlist items trigger elevated urgency
   - LLM identifies connections humans might miss
   - Pattern recognition across reports

3. **Modular & Portable**
   - Plug-and-play for any municipality
   - Instance-specific config (sources, entities)
   - Universal framework (civic categories, agent patterns)

4. **Evolvable Intelligence**
   - System learns from accumulated reports
   - User feedback refines what matters
   - Entity relationships emerge over time

### Success Criteria

- [ ] Scout reports include ALL agenda items (not just keyword matches)
- [ ] Priority items are clearly highlighted within comprehensive reports
- [ ] New municipality can be onboarded with config changes only
- [ ] Reports reference relevant past findings when available

---

## Architectural Principles

### 1. Separation of Concerns

```
┌─────────────────────────────────────────────────────────┐
│                    INSTANCE CONFIG                       │
│  (Municipality-specific: sources, entities, watchlists) │
└─────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    AGENT FRAMEWORK                       │
│  (Generic: Scout, Analyst, Synthesizer patterns)        │
└─────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    LLM INTELLIGENCE                      │
│  (Dynamic: reasoning, pattern recognition, synthesis)   │
└─────────────────────────────────────────────────────────┘
```

### 2. What to Hardcode vs. Let LLM Handle

| Hardcode in Config | Let LLM Handle |
|--------------------|----------------|
| Source URLs | Meaning/implications |
| Entity watchlists | Connection discovery |
| Output schemas | Significance assessment |
| Escalation rules | Pattern recognition |
| Civic categories | Contextual analysis |

### 3. Memory Tiers

| Tier | Scope | Storage | Purpose |
|------|-------|---------|---------|
| Session | Current run | In-memory | Immediate context |
| Medium-term | 30-90 days | Vector DB | "Have we seen this before?" |
| Long-term | Persistent | Knowledge graph | Entity relationships, patterns |

---

## Implementation Phases

### Overview

| Phase | Focus | Timeline | Risk |
|-------|-------|----------|------|
| **Phase 1** | Comprehensive Coverage | Immediate | Low |
| **Phase 2** | Enhanced Configuration | This week | Low |
| **Phase 3** | Intelligent Evolution | Next 2 weeks | Medium |

---

## Phase 1: Comprehensive Coverage

**Goal:** Scouts analyze ALL content, not just keyword matches.

### 1.1 Schema Updates

**File:** `src/schemas.py`

Add fields to `MeetingItem`:

```python
class CivicCategory(str, Enum):
    BUDGET_FINANCE = "budget_finance"
    LAND_USE = "land_use"
    PUBLIC_SAFETY = "public_safety"
    INFRASTRUCTURE = "infrastructure"
    PERSONNEL = "personnel"
    CONTRACTS = "contracts"
    ENVIRONMENT = "environment"
    PUBLIC_HEARING = "public_hearing"
    CONSENT = "consent"
    OTHER = "other"

class Significance(str, Enum):
    ROUTINE = "routine"      # Standard business, no action needed
    NOTABLE = "notable"      # Worth knowing about
    CRITICAL = "critical"    # Requires attention or action

class MeetingItem(BaseModel):
    agenda_id: Optional[str] = None
    topic: str
    summary: str = Field(..., description="2-3 sentence summary of the item")
    category: CivicCategory = CivicCategory.OTHER
    significance: Significance = Significance.ROUTINE
    related_to: List[str] = Field(default_factory=list)
    outcome: Optional[str] = None

    # Priority flagging
    priority_flag: bool = False
    priority_reason: Optional[str] = None
    watchlist_matches: List[str] = Field(default_factory=list)
```

- [x] Add `CivicCategory` enum
- [x] Add `Significance` enum
- [x] Update `MeetingItem` with new fields
- [ ] Test schema validation

### 1.2 Prompt Updates

**File:** `prompt_library/layer-1-scouts/A1-meeting-intelligence-scout.md`

Change the core instruction from:

> "Focus on items related to: Tara development, Mill Creek Sink..."

To:

> "Analyze ALL agenda items comprehensively. For each item:
> 1. Summarize what it is (2-3 sentences)
> 2. Categorize it (budget, land use, personnel, etc.)
> 3. Assess civic significance (routine/notable/critical)
> 4. Check against the watchlist - flag if it relates to tracked entities
> 5. Note any connections to other items or past patterns"

- [x] Update A1 scout prompt (via ScoutAgent._build_prompt)
- [ ] Update A2 scout prompt (if applicable)
- [ ] Update A3 scout prompt (if applicable)
- [ ] Update A4 scout prompt (if applicable)

### 1.3 Agent Code Updates

**File:** `src/agents/scout.py`

Update `_build_prompt()` to:
- Include comprehensive analysis instructions
- Pass watchlist for flagging (not filtering)
- Request structured output matching new schema

- [x] Update `_build_prompt()` method
- [x] Ensure structured output matches new schema
- [ ] Test with sample URL

### 1.4 Context Module Updates

**File:** `src/prompts/context.py`

Split context into:
- `get_watchlist_context()` - entities/keywords for flagging
- `get_civic_context()` - general civic analysis guidance

- [x] Refactored `get_prompt_context()` for comprehensive + watchlist approach
- [x] Updated mission statement and behavioral standards
- [x] Separated local context from general civic guidance

### 1.5 UI Updates

**File:** `src/ui/pages/agent_runner.py`

Update `display_scout_result()` to:
- Show ALL items, organized by category
- Highlight priority-flagged items
- Show significance indicators

- [x] Update display function
- [x] Add category grouping
- [x] Add priority highlighting
- [x] Add executive summary display
- [x] Add `_display_meeting_item()` helper function

### Phase 1 Testing Checkpoint

- [ ] Run scout on a meeting agenda URL
- [ ] Verify ALL items are documented (not just keyword matches)
- [ ] Verify priority items are flagged correctly
- [ ] Verify categories are assigned appropriately

---

## Phase 2: Enhanced Configuration

**Goal:** Clean separation of instance-specific vs. universal config.

### 2.1 Create Civic Categories Config

**File:** `config/civic_categories.yaml` (NEW)

Universal categories that apply to any municipality:

```yaml
categories:
  - id: budget_finance
    name: "Budget & Finance"
    description: "Budgets, taxes, appropriations, audits, financial reports"
    keywords:
      - budget
      - millage
      - tax
      - appropriation
      - audit
      - revenue
      - expenditure

  - id: land_use
    name: "Land Use & Development"
    description: "Zoning, plats, subdivisions, comprehensive plan"
    keywords:
      - zoning
      - rezoning
      - plat
      - subdivision
      - comprehensive plan
      - land use
      - development order

  # ... additional categories
```

- [ ] Create `civic_categories.yaml`
- [ ] Define all universal categories
- [ ] Add loader function in `src/prompts/loader.py`

### 2.2 Refactor Instance Config

**File:** `config/instance.yaml`

Make municipality-specific settings explicit:

```yaml
instance:
  name: "Alachua Civic Intelligence"
  jurisdiction:
    primary: "City of Alachua"
    secondary: "Alachua County"
    state: "Florida"
  timezone: "America/New_York"

  # What makes this instance unique
  focus_areas:
    - "Environmental protection"
    - "Water quality"
    - "Development oversight"

  # Reference to other configs
  sources_config: "sources.yaml"
  entities_config: "entities.yaml"
```

- [ ] Update `instance.yaml` structure
- [ ] Add jurisdiction metadata
- [ ] Add focus areas (high-level, not keyword lists)

### 2.3 Refactor Entities Config

**File:** `config/entities.yaml`

Separate into:
- `watchlist` (HIGH priority - triggers alerts)
- `tracked` (standard tracking - logged but not alerted)
- `known` (context only - helps LLM understand relationships)

- [ ] Restructure entities.yaml
- [ ] Add priority tiers
- [ ] Update loader to handle new structure

### Phase 2 Testing Checkpoint

- [ ] Verify civic categories load correctly
- [ ] Verify instance config loads correctly
- [ ] Verify entity tiers work (watchlist vs tracked)
- [ ] Test with a new "mock municipality" config

---

## Phase 3: Intelligent Evolution

**Goal:** System learns and improves from accumulated data.

### 3.1 Vector Search for Past Reports

Enable scouts/analysts to query past reports for context.

**Files:**
- `src/database.py` - add vector search functions
- `src/agents/base.py` - add memory retrieval method

```python
async def get_related_reports(self, query: str, limit: int = 5) -> List[Report]:
    """Find past reports related to current analysis."""
    # Vector similarity search in Supabase
    pass
```

- [ ] Implement vector search function
- [ ] Add to base agent class
- [ ] Inject relevant past context into prompts

### 3.2 Feedback Mechanism

Allow users to rate report items.

**Schema addition:**
```python
class ItemFeedback(BaseModel):
    item_id: str
    report_id: str
    rating: Literal["useful", "noise", "critical"]
    notes: Optional[str] = None
```

- [ ] Add feedback schema
- [ ] Add feedback API endpoint
- [ ] Add feedback UI in agent runner
- [ ] Store feedback for future reference

### 3.3 Pattern Detection

Identify recurring patterns across reports.

**Example patterns:**
- "Entity X appears in consent agenda frequently"
- "Items mentioning Y often followed by Z within 2 weeks"
- "This type of item usually has significance level X"

- [ ] Design pattern detection approach
- [ ] Implement basic pattern logging
- [ ] Add pattern context to prompts

### Phase 3 Testing Checkpoint

- [ ] Verify vector search returns relevant past reports
- [ ] Verify feedback is stored correctly
- [ ] Verify patterns are detected and logged

---

## File Change Tracker

Track all files modified during this overhaul.

| File | Phase | Status | Notes |
|------|-------|--------|-------|
| `src/schemas.py` | 1 | ✅ Done | Added CivicCategory, Significance enums, updated MeetingItem |
| `prompt_library/layer-1-scouts/A1-meeting-intelligence-scout.md` | 1 | ⏭️ Skipped | Prompt built dynamically in ScoutAgent |
| `src/agents/scout.py` | 1 | ✅ Done | Updated _build_prompt for comprehensive analysis |
| `src/prompts/context.py` | 1 | ✅ Done | Refactored get_prompt_context for comprehensive + watchlist |
| `src/ui/pages/agent_runner.py` | 1 | ✅ Done | Added category grouping, priority highlighting, exec summary |
| `config/civic_categories.yaml` | 2 | ⬜ Pending | NEW - universal categories |
| `config/instance.yaml` | 2 | ⬜ Pending | Refactor structure |
| `config/entities.yaml` | 2 | ⬜ Pending | Add priority tiers |
| `src/prompts/loader.py` | 2 | ⬜ Pending | Load civic categories |
| `src/database.py` | 3 | ⬜ Pending | Vector search functions |
| `src/agents/base.py` | 3 | ⬜ Pending | Memory retrieval |

---

## Testing Checkpoints

### After Phase 1
```bash
# Run scout on a real meeting agenda
# Expected: ALL items documented, priority items flagged
python -c "
from src.agents.scout import ScoutAgent
agent = ScoutAgent('A1')
result = agent.run({'url': 'https://alachuafl.portal.civicclerk.com/event/791/files/agenda/1746'})
print(f'Items found: {len(result.items)}')
print(f'Priority flagged: {sum(1 for i in result.items if i.priority_flag)}')
"
```

### After Phase 2
```bash
# Verify config loading
python -c "
from src.prompts.loader import get_prompt_loader
loader = get_prompt_loader()
categories = loader.load_civic_categories()
print(f'Categories loaded: {len(categories)}')
"
```

### After Phase 3
```bash
# Verify vector search
python -c "
from src.database import get_related_reports
reports = get_related_reports('Tara development', limit=5)
print(f'Related reports found: {len(reports)}')
"
```

---

## Decision Log

Track key decisions made during implementation.

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-30 | Comprehensive first, priority second | User wants full civic awareness, not tunnel vision |
| 2026-01-30 | Three-phase approach | Minimize risk, deliver value incrementally |
| 2026-01-30 | Keep Alachua as reference implementation | Real-world testing ground for the platform |

---

## Next Steps

**Immediate:** Begin Phase 1 implementation
1. Update `src/schemas.py` with new enums and fields
2. Update scout prompts for comprehensive analysis
3. Test with real meeting agenda

**Ready to proceed?** Mark Phase 1 tasks as in-progress and begin implementation.
