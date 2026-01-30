# 🔄 System Overview & Design Discussion

**Open Sousveillance Studio — Architecture Deep Dive**

*Document for brainstorming and refinement*

---

## 🎯 Core Concept

**Goal:** Automatically monitor local government activity and alert citizens before important decisions are made, not after.

**The Gap It Fills:** Government information is public but not accessible. Meeting agendas are posted 3-5 days before votes. Permit applications are buried in portals. By the time citizens find out, public comment periods have closed.

---

## 🏗️ Three-Layer Agent Architecture

```mermaid
flowchart TB
    subgraph Layer1["Layer 1: SCOUTS (Daily)"]
        direction LR
        A1[A1: Meeting Scout<br/>Agendas & Minutes]
        A2[A2: Permit Scout<br/>Applications]
        A3[A3: Legislative Monitor<br/>Code Changes]
        A4[A4: Public Notice Scout<br/>Legal Notices]
    end

    subgraph Layer2["Layer 2: ANALYSTS (Weekly)"]
        direction LR
        B1[B1: Impact Analyst<br/>Environmental/Community]
        B2[B2: Procedural Analyst<br/>Process Violations]
    end

    subgraph Layer3["Layer 3: SYNTHESIZERS (Monthly)"]
        direction LR
        C1[C1: Newsletter Generator]
        C2[C2: Social Media Planner]
        C3[C3: Alert Broadcaster]
        C4[C4: Quarterly Scorecard]
    end

    Layer1 -->|ScoutReports| DB[(Supabase)]
    DB -->|Query| Layer2
    Layer2 -->|AnalystReports| DB
    DB -->|Human Approval| Layer3
    Layer3 -->|Publish| Output[Citizens]
```

---

## 🔍 Layer 1: Scouts — Data Collection

### Purpose

Fetch raw data from government sources, extract structured information, flag items matching the watchlist.

### Current Implementation

- `ScoutAgent` in `src/agents/scout.py`
- Uses Firecrawl to scrape web pages
- Gemini 2.5 Pro extracts structured `ScoutReport`
- Matches against keywords from `config/entities.yaml`

### Data Flow

```
URL → Firecrawl (scrape) → Raw Markdown → Gemini (analyze) → ScoutReport → Supabase
```

### ScoutReport Schema

```python
class ScoutReport(BaseReport):
    report_id: str           # "A1-2026-01-30"
    executive_summary: str   # Key findings
    alerts: List[UrgencyAlert]  # RED/YELLOW/GREEN items
    items: List[MeetingItem]    # Extracted agenda items
```

### Open Questions

1. Scouts run on a fixed daily schedule (4 AM), with support for manual triggering via API or Dev Console.
2. Do you want Scouts to store the raw scraped content, or just the extracted report?
3. Should each source have its own Scout instance, or one Scout handles multiple sources?

---

## 🧠 Layer 2: Analysts — Pattern Recognition

### Purpose

Take Scout data, perform deep research, identify patterns across multiple reports.

### Current Implementation

- `AnalystAgent` in `src/agents/analyst.py`
- Queries Supabase for recent ScoutReports
- Uses Tavily for web research on flagged items
- Produces `AnalystReport` with sections and recommendations

### Data Flow

```
ScoutReports (from DB) → Filter RED/YELLOW → Tavily Research → Gemini Analysis → AnalystReport
```

### AnalystReport Schema

```python
class AnalystReport(BaseReport):
    topic: str                    # "Tara Development Update"
    scout_report_ids: List[str]   # Source reports
    sections: List[AnalysisSection]  # Analysis with confidence scores
    recommendations: List[str]    # Actionable items
```

### Open Questions

1. What triggers an Analyst run? Weekly schedule, or when X number of RED alerts accumulate?
2. Should Analysts have access to historical data (RAG over past reports)?
3. How deep should Tavily research go? (cost vs. thoroughness)

---

## 📣 Layer 3: Synthesizers — Public Output

### Purpose

Generate citizen-facing content. This is where human approval is required.

### Current Implementation

Mostly scaffolded, not fully built.

### Planned Flow

```
AnalystReports → Human Approval → Synthesizer → Newsletter/Social/Alert
```

### Open Questions

1. What's the primary output format? Email newsletter? Dashboard? Both?
2. Who approves content before publishing? Single person or committee?
3. Should there be different approval levels (alerts = auto, newsletter = manual)?

---

## 👤 Human-in-the-Loop Approval

### Current Design

- LangGraph `interrupt()` pauses workflow before Layer 3
- Human reviews via API endpoint or Streamlit UI
- Approved content continues to publishing

### Open Questions

1. Is approval per-report or per-batch?
2. What's the timeout? (e.g., auto-reject after 48 hours?)
3. Should rejected content go back to Analyst for revision?

---

## 🗄️ Data Storage Architecture

```mermaid
erDiagram
    SCOUT_REPORTS {
        uuid id PK
        string report_id
        timestamp created_at
        string source_url
        jsonb report_data
        string content_hash
    }

    ANALYST_REPORTS {
        uuid id PK
        string report_id
        timestamp created_at
        string topic
        jsonb report_data
        string[] scout_report_ids FK
    }

    APPROVALS {
        uuid id PK
        string report_id FK
        string status
        string reviewer
        timestamp decided_at
        text comments
    }

    DOCUMENTS {
        uuid id PK
        string url
        string content_hash
        bytea pdf_content
        text extracted_text
    }

    EMBEDDINGS {
        uuid id PK
        uuid document_id FK
        vector embedding
        text chunk_text
    }

    SCOUT_REPORTS ||--o{ ANALYST_REPORTS : "feeds"
    ANALYST_REPORTS ||--o| APPROVALS : "requires"
    DOCUMENTS ||--o{ EMBEDDINGS : "chunks"
```

### Open Questions

1. Should we deduplicate by content hash (same document = skip)?
2. How long to retain data? (compliance, storage costs)
3. Do you want full-text search, vector search, or both?

---

## ⚙️ Configuration-Driven Design

The system is designed to be **forkable** for any municipality:

```yaml
# config/instance.yaml - WHO you are
instance:
  id: "alachua-fl"
  name: "Alachua County Civic Watch"

# config/sources.yaml - WHAT to watch
tier_1_municipal:
  - id: "alachua-civicclerk"
    url: "https://alachuafl.portal.civicclerk.com/"
    priority: "critical"

# config/entities.yaml - WHY it matters
projects:
  - id: "tara-portfolio"
    urgency: "red"
    keywords: ["Mill Creek", "PSE22-0002"]
```

### Open Questions

1. Is the tier system (1-5) useful, or should it just be priority (critical/high/medium)?
2. Should keywords support regex or just exact/fuzzy matching?
3. Do you want entity relationships (e.g., "Tara Forest LLC" → "Tara Development")?

---

## 💡 Potential Gaps & Enhancements

### 1. Change Detection

**Current:** We scrape and analyze everything on schedule.

**Enhancement:** Detect "new content only" to avoid reprocessing unchanged pages.

**Options:**
- Content hash comparison
- Last-modified header checking
- RSS/Atom feed monitoring where available

### 2. Alert Routing

**Current:** All alerts wait for weekly Analyst run.

**Enhancement:** RED alerts should trigger immediate notification.

```mermaid
flowchart LR
    Scout -->|RED| Immediate[SMS/Email Alert]
    Scout -->|YELLOW| Queue[Weekly Analyst Queue]
    Scout -->|GREEN| Log[Archive Only]
```

### 3. Source Health Monitoring

**Problem:** Government portals change structure without notice.

**Enhancement:** Alert when scraping fails or returns unexpected format.

### 4. Feedback Loop

**Problem:** No way to improve from citizen feedback.

**Enhancement:** "This alert was wrong" button → feeds back to prompt tuning.

### 5. Multi-Jurisdiction Sharing

**Problem:** Each fork operates in isolation.

**Enhancement:** Optional anonymized sharing of:
- Effective prompts
- Source scraping patterns
- Keyword lists by topic

---

## 🔄 End-to-End Workflow Example

**Scenario:** City of Alachua posts a new Planning & Zoning meeting agenda.

```mermaid
sequenceDiagram
    participant Celery as ⏰ Scheduler
    participant Scout as 🔍 A1 Scout
    participant FC as 🌐 Firecrawl
    participant Gemini as 🧠 Gemini
    participant DB as 💾 Supabase
    participant Analyst as 📊 B1 Analyst
    participant Human as 👤 Reviewer
    participant Synth as 📝 Synthesizer
    participant Citizen as 👥 Citizens

    Note over Celery: Daily 6 AM trigger
    Celery->>Scout: Run A1 for CivicClerk
    Scout->>FC: Scrape meeting list
    FC-->>Scout: Markdown + PDF links

    Scout->>Gemini: Extract agenda items
    Note over Gemini: Matches "Mill Creek" keyword
    Gemini-->>Scout: ScoutReport with RED alert

    Scout->>DB: Store report

    alt RED Alert - Immediate Path
        Scout->>Citizen: SMS/Email: "Mill Creek on agenda!"
    end

    Note over Celery: Weekly Monday 9 AM
    Celery->>Analyst: Run B1 analysis
    Analyst->>DB: Query RED/YELLOW reports
    Analyst->>Analyst: Tavily research on Mill Creek
    Analyst->>DB: Store AnalystReport

    Analyst->>Human: Approval required
    Human-->>Analyst: Approved ✓

    Analyst->>Synth: Generate newsletter
    Synth->>Citizen: Weekly digest email
```

---

## 💬 Discussion Points

### Your Vision vs. Current Implementation

| Aspect | Current | Your Vision? |
|:-------|:--------|:-------------|
| Scout frequency | Daily scheduled | Daily at 4 AM + manual trigger |
| Analyst trigger | Weekly scheduled | ? |
| RED alert handling | Waits for Analyst | Immediate? |
| Approval flow | Single reviewer | Committee? |
| Primary output | JSON reports | Newsletter? Dashboard? |
| Data retention | Indefinite | ? |
| Deduplication | Not implemented | Content hash? |

### Priority Questions

1. **What's the MVP output?** What do citizens actually receive?
2. **Who operates this?** Technical person or community organizer?
3. **What's the failure mode?** If scraping breaks, who gets notified?

---

*Add your notes and decisions below:*

## 📝 Your Notes

<!-- Add your thoughts here -->
