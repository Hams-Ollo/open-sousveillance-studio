# 👁️ Open Sousveillance Studio

**AI-powered civic intelligence. Watching from below.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Supabase](https://img.shields.io/badge/database-Supabase-green.svg)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Firecrawl](https://img.shields.io/badge/scraping-Firecrawl-red.svg)](https://firecrawl.dev/)

**Version:** 2.0  
**Status:** 🚧 Active Development  
**Origin:** 📍 Alachua County, Florida — Built to protect the Floridan Aquifer

> *"Sousveillance"* (French: sous "from below" + veillance "watching") — the recording of an activity by a participant, in contrast to surveillance, which is done by an authority. **They watched us. Now we watch back.**

---

## 🎯 The Problem

Local government decisions happen fast. Agendas are posted days before meetings. Permit applications are buried in obscure portals. Public notices appear in newspapers most people don't read. By the time citizens learn about a development project threatening their water supply, it's often too late to respond.

**The Tara Development Case Study:**  
The "Tara" development portfolio (~580 acres, 1,000+ homes) sits directly above **Mill Creek Sink**—a karst feature with a proven 12-day hydrologic connection to Hornsby Spring via the Floridan Aquifer. Despite documented environmental concerns, the project has advanced through fragmented municipal processes across City, County, and State agencies.

This system exists to ensure **no civic action goes unnoticed**.

---

## 💡 The Solution

**Open Sousveillance Studio** is an open-source AI agent platform that flips the surveillance paradigm. While governments have long monitored citizens, this system empowers citizens to monitor government — automatically, continuously, and intelligently.

The platform deploys AI agents that watch 15+ government data sources, detect new documents within hours of publication, extract actionable intelligence, and generate weekly reports for community distribution.

```mermaid
flowchart TB
    subgraph Sources["🌐 Government Data Sources"]
        S1[City of Alachua<br/>CivicClerk Portal]
        S2[Alachua County<br/>eScribe Meetings]
        S3[SRWMD<br/>Water Permits]
        S4[Florida Public Notices<br/>Legal Notices]
        S5[County GIS<br/>Map Genius]
    end

    subgraph Monitor["👁️ Change Detection"]
        FC[Firecrawl API<br/>LLM-ready Markdown]
        PDF[PDF Processor<br/>Firecrawl + Gemini]
    end

    subgraph Agents["🤖 LangGraph Agent Orchestration"]
        subgraph L1["Layer 1: Scouts (Daily)"]
            A1[A1: Meeting Scout]
            A2[A2: Permit Scout]
            A3[A3: Legislative Monitor]
        end
        
        subgraph L2["Layer 2: Analysts (Weekly)"]
            B1[B1: Impact Analyst]
            B2[B2: Procedural Analyst]
        end
        
        subgraph L3["Layer 3: Synthesizers (Monthly)"]
            C1[C1: Newsletter Generator]
            C2[C2: Social Media Planner]
        end
    end

    subgraph Storage["💾 Knowledge Base"]
        DB[(Supabase PostgreSQL<br/>Structured Reports)]
        VEC[(pgvector<br/>Semantic Search)]
        DOCS[(Document Archive<br/>Original PDFs)]
    end

    subgraph Output["📤 Community Distribution"]
        NEWS[Weekly Newsletter]
        DASH[Alert Dashboard]
        API[REST API]
    end

    Sources --> Monitor
    Monitor --> L1
    L1 --> DB
    DB --> L2
    L2 -->|Human Approval| L3
    L3 --> NEWS & DASH
    DB --> VEC
    DOCS --> VEC
```

---

## 🏗️ System Architecture

### Three-Layer Agent Framework

| Layer | Agents | Frequency | Purpose |
|:------|:-------|:----------|:--------|
| **Layer 1: Scouts** | A1-A4 | Daily | Data collection from government portals. Deterministic, fact-based extraction. |
| **Layer 2: Analysts** | B1-B2 | Weekly | Pattern recognition across Scout data. Deep research via Tavily. |
| **Layer 3: Synthesizers** | C1-C4 | Monthly | Public-facing content generation. Requires human approval before publishing. |

### Technology Stack

```mermaid
graph LR
    subgraph Frontend["🖥️ API Layer"]
        FAST[FastAPI + Uvicorn]
        SSE[Server-Sent Events]
    end

    subgraph Orchestration["🔀 Orchestration"]
        LG[LangGraph<br/>Multi-Agent Workflows]
        APS[APScheduler<br/>Cron Jobs]
    end

    subgraph AI["🧠 AI/ML"]
        GEM[Gemini 2.5 Pro/Flash]
        TAV[Tavily Search]
        EMB[Embeddings + RAG]
    end

    subgraph Data["💾 Data Layer"]
        SUP[(Supabase<br/>PostgreSQL + pgvector)]
        STORE[(Supabase Storage<br/>PDF Archive)]
    end

    subgraph Scraping["🕷️ Web Scraping (Firecrawl)"]
        SCRAPE[Scrape<br/>Single URL → Markdown]
        MAP[Map<br/>Discover All URLs]
        BATCH[Batch Scrape<br/>Multiple URLs]
        ACTIONS[Actions<br/>Click/Scroll/Wait]
    end

    FAST --> LG
    LG --> GEM & TAV
    LG --> SUP
    APS --> LG
    Scraping --> LG
    GEM --> EMB --> SUP
```

| Component | Technology | Purpose |
|:----------|:-----------|:--------|
| **Web Server** | FastAPI + Uvicorn | REST API, SSE streaming, approval endpoints |
| **Orchestration** | LangGraph | Multi-agent workflows with human-in-the-loop |
| **Scheduling** | APScheduler | Daily/weekly/monthly cron triggers |
| **LLM** | Gemini 2.5 Pro & Flash | Pro for reasoning, Flash for extraction |
| **Search** | Tavily | AI-optimized web research |
| **Database** | Supabase (PostgreSQL) | Structured data, JSONB, pgvector |
| **Document Storage** | Supabase Storage | PDF archive with full traceability |
| **Validation** | Pydantic v2 | Strict schemas for all data |
| **Scraping** | Firecrawl | LLM-ready markdown, JS rendering, PDF parsing, batch operations |

---

## 📊 Data Flow: From Source to Newsletter

```mermaid
sequenceDiagram
    participant CRON as ⏰ Scheduler
    participant SCOUT as 🔍 Scout Agent
    participant SRC as 🌐 CivicClerk
    participant PDF as 📄 PDF Processor
    participant DB as 💾 Supabase
    participant ANALYST as 🧠 Analyst Agent
    participant HUMAN as 👤 Human Reviewer
    participant SYNTH as 📝 Synthesizer
    participant EMAIL as 📧 Newsletter

    CRON->>SCOUT: Daily trigger (6 AM)
    SCOUT->>SRC: Fetch meeting list (Firecrawl)
    SRC-->>SCOUT: Markdown + PDF links
    SCOUT->>PDF: Download agenda packets
    PDF-->>SCOUT: Extracted text + tables
    SCOUT->>DB: Store ScoutReport + embeddings
    
    Note over DB: Deduplicate via content hash
    
    CRON->>ANALYST: Weekly trigger (Monday 9 AM)
    ANALYST->>DB: Query RED/YELLOW alerts
    ANALYST->>ANALYST: Tavily deep research
    ANALYST->>DB: Store AnalystReport
    ANALYST->>HUMAN: interrupt() - Approval required
    
    HUMAN-->>ANALYST: Approved ✓
    
    ANALYST->>SYNTH: Resume workflow
    SYNTH->>SYNTH: Generate newsletter content
    SYNTH->>EMAIL: Send via Resend API
```

---

## � Firecrawl Integration

Open Sousveillance Studio uses **[Firecrawl](https://firecrawl.dev)** as its primary web scraping engine. Firecrawl handles the complexity of modern government portals (JavaScript SPAs, anti-bot measures, dynamic content) and returns clean, LLM-ready data.

### Why Firecrawl?

| Challenge | Firecrawl Solution |
|:----------|:-------------------|
| **React/Angular SPAs** | Full JavaScript rendering with configurable wait times |
| **Dynamic content** | Actions API: click, scroll, wait before scraping |
| **PDF documents** | Native PDF text extraction (staff reports, agendas) |
| **Rate limiting** | Built-in caching (2-day default), batch operations |
| **Anti-bot measures** | Managed proxies and stealth mode |
| **LLM integration** | Returns markdown optimized for AI processing |

### Key Features We Use

```python
from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key="fc-YOUR-API-KEY")

# 1. SCRAPE: Get a single meeting page as markdown
doc = firecrawl.scrape(
    "https://alachuafl.portal.civicclerk.com/event/849/overview",
    formats=["markdown", "links"],
    actions=[
        {"type": "wait", "milliseconds": 2000},  # Wait for React to render
        {"type": "scroll", "direction": "down"}   # Load lazy content
    ]
)

# 2. MAP: Discover all meeting URLs on the portal
urls = firecrawl.map(
    url="https://alachuafl.portal.civicclerk.com",
    search="meeting",  # Filter to meeting-related pages
    limit=100
)

# 3. BATCH SCRAPE: Fetch multiple meetings efficiently
results = firecrawl.batch_scrape(
    urls=["https://...meeting1", "https://...meeting2"],
    formats=["markdown"]
)

# 4. STRUCTURED EXTRACTION: Get typed data with Pydantic schemas
from pydantic import BaseModel

class AgendaItem(BaseModel):
    item_number: str
    title: str
    applicant: str | None
    parcel_number: str | None

result = firecrawl.scrape(
    "https://alachuafl.portal.civicclerk.com/event/849/overview",
    formats=[{"type": "json", "schema": AgendaItem.model_json_schema()}]
)
```

### Scraping Strategy by Source

| Source | Method | Actions Required | Output |
|:-------|:-------|:-----------------|:-------|
| **CivicClerk** (City of Alachua) | `scrape` + actions | `wait` 2s, `scroll` down | Markdown + links |
| **Florida Public Notices** | `scrape` | None (static) | Markdown |
| **eScribe** (County) | `scrape` + actions | `wait` for selector | Markdown + PDF links |
| **PDF Agendas** | `scrape` with `parsers=["pdf"]` | None | Extracted text |

### Cost Estimation

| Plan | Credits/Month | Cost | Sufficient For |
|:-----|:--------------|:-----|:---------------|
| **Free** | 500 | $0 | Testing, ~16 scrapes/day |
| **Hobby** | 3,000 | $16/mo | Production monitoring (~100/day) |
| **Standard** | 100,000 | $99/mo | Multi-jurisdiction deployment |

**Estimated usage for single-jurisdiction monitoring:** ~1,500 scrapes/month (Hobby plan)

> **Note:** We use `scrape` with `formats=["json"]` instead of the `/extract` endpoint to avoid the separate token-based billing ($89+/mo). Our own LLM handles analysis.

---

## �📁 Project Structure

```
alachua-civic-intelligence-reporting-studio/
├── config/                         # ⭐ YAML CONFIGURATION (customize for your community)
│   ├── instance.yaml               # Instance identity, jurisdiction, scheduling
│   ├── sources.yaml                # Government data sources to monitor
│   └── entities.yaml               # Watchlist: projects, orgs, keywords
│
├── src/
│   ├── main.py                     # FastAPI application entry point
│   ├── config.py                   # Configuration loader (YAML + Pydantic)
│   ├── database.py                 # Supabase client
│   ├── schemas.py                  # Pydantic models
│   ├── registry.py                 # Source URL registry
│   │
│   ├── agents/
│   │   ├── base.py                 # Base agent class
│   │   ├── scout.py                # A1-A4 Scout implementations
│   │   └── analyst.py              # B1-B2 Analyst implementations
│   │
│   ├── workflows/
│   │   ├── graphs.py               # LangGraph workflow definitions
│   │   ├── checkpointer.py         # Supabase state persistence
│   │   └── nodes.py                # Reusable node functions
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── workflows.py        # POST /run, GET /status
│   │       ├── approvals.py        # Human-in-the-loop endpoints
│   │       └── streaming.py        # SSE for real-time updates
│   │
│   ├── tools/
│   │   ├── firecrawl_client.py     # Firecrawl wrapper with retry logic
│   │   ├── civicclerk_scraper.py   # CivicClerk-specific scraping patterns
│   │   ├── pdf_processor.py        # Firecrawl PDF + Gemini hybrid
│   │   └── document_storage.py     # Supabase file management
│   │
│   └── scheduler/
│       ├── manager.py              # APScheduler setup
│       └── jobs.py                 # Scheduled task definitions
│
├── prompt_library/                 # Agent prompt templates
│   ├── config/                     # Legacy source registry docs
│   ├── layer-1-scouts/             # A1-A4 prompts
│   ├── layer-2-analysts/           # B1-B2 prompts
│   └── layer-3-synthesizers/       # C1-C4 prompts
│
├── docs/
│   ├── PLAN.md                     # Technical architecture plan
│   └── DEVELOPER_GUIDE.md          # Setup and contribution guide
│
├── data/                           # Generated reports by frequency
│   ├── daily/
│   ├── weekly/
│   └── monthly/
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Configuration System

Open Sousveillance Studio uses a **modular YAML configuration system** that makes it easy to deploy for any US municipality without code changes.

### Configuration Files

| File | Purpose | Key Settings |
|:-----|:--------|:-------------|
| `config/instance.yaml` | Your deployment identity | Instance name, jurisdiction hierarchy, timezone, schedules |
| `config/sources.yaml` | Government data sources | URLs, scraping methods, document types, board filters |
| `config/entities.yaml` | Watchlist items | Projects, organizations, people, keywords to monitor |

### Instance Configuration (`instance.yaml`)

Define your community and scheduling:

```yaml
instance:
  id: "alachua-fl"
  name: "Alachua County Civic Watch"
  timezone: "America/New_York"
  operator:
    name: "Our Alachua Water Coalition"
    email: "contact@ouralachuawater.org"

jurisdiction:
  country: "US"
  state: "FL"
  county: "Alachua"
  municipalities:
    - name: "City of Alachua"
      primary: true
    - name: "City of High Springs"
      primary: false

schedule:
  scouts:
    enabled: true
    cron: "0 6 * * *"  # Daily at 6 AM
  analysts:
    enabled: true
    cron: "0 9 * * 1"  # Weekly on Monday
    requires_approval: true
```

### Sources Configuration (`sources.yaml`)

Define government portals organized by tier:

```yaml
tier_1_municipal:
  - id: "alachua-civicclerk"
    name: "City of Alachua - Meeting Portal"
    url: "https://alachuafl.portal.civicclerk.com/"
    platform: "civicclerk"
    priority: "critical"
    scraping:
      method: "playwright"
      requires_javascript: true
      wait_for_selector: ".meeting-list"
    document_types:
      - "agenda"
      - "minutes"
    boards:
      - name: "City Commission"
        keywords: ["commission"]
        priority: "critical"

tier_2_county:
  - id: "alachua-county-escribe"
    name: "Alachua County - Meeting Portal"
    url: "https://pub-alachuacounty.escribemeetings.com/"
    # ...
```

### Entities Configuration (`entities.yaml`)

Define what to watch for:

```yaml
projects:
  - id: "tara-portfolio"
    name: "Tara Development Portfolio"
    urgency: "red"
    aliases:
      - "Tara Forest"
      - "Tara Baywood"
    keywords:
      - "Mill Creek"
      - "PSE22-0002"

organizations:
  - id: "tara-forest-llc"
    name: "Tara Forest, LLC"
    type: "developer"
    urgency: "red"

keywords:
  environmental:
    - "aquifer"
    - "karst"
    - "sinkhole"
    - "stormwater"
  procedural:
    - "variance"
    - "waiver"
    - "public hearing"
```

### Using Configuration in Code

```python
from src.config import (
    build_app_config,
    get_all_sources,
    get_sources_by_priority,
    get_projects,
    get_all_keywords,
)

# Load complete configuration
config = build_app_config()
print(config.instance.name)  # "Alachua County Civic Watch"
print(config.jurisdiction.state)  # "FL"

# Get all sources across all tiers
sources = get_all_sources()
for source in sources:
    print(f"{source.name}: {source.url}")

# Filter by priority
critical_sources = get_sources_by_priority("critical")

# Get watchlist items
projects = get_projects()
keywords = get_all_keywords()  # Deduplicated set for text matching
```

---

## 🌐 Monitored Data Sources (Example: Alachua County, FL)

Open Sousveillance Studio is designed to be **location-agnostic**. The source registry can be configured for any municipality. Below is the default configuration for Alachua County, Florida:

| Tier | Source | Platform | Priority | Scraping Method |
|:-----|:-------|:---------|:---------|:----------------|
| **1** | City of Alachua Meetings | CivicClerk (SPA) | 🔴 Critical | Playwright + XHR interception |
| **1** | Development Projects Map | Granicus CMS | 🔴 Critical | BeautifulSoup |
| **2** | Alachua County Meetings | eScribe | 🔴 Critical | Playwright + PDF download |
| **2** | Map Genius (Projects) | County GIS | 🔴 Critical | JSON API |
| **3** | SRWMD Water Permits | E-Permitting Portal | 🔴 Critical | Form submission + scrape |
| **4** | Florida Public Notices | Statewide Repository | 🔴 Critical | Filter by county + parse |
| **5** | WUFT Environment News | WordPress | 🟡 High | RSS feed |

Full registry: [`prompt_library/config/source-registry.md`](prompt_library/config/source-registry.md)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker (optional, for local Supabase)
- API keys:
  - **Firecrawl** - Web scraping ([get key](https://firecrawl.dev)) - Free tier: 500 credits
  - **Google AI (Gemini)** - LLM analysis ([get key](https://aistudio.google.com))
  - **Tavily** - Deep research ([get key](https://tavily.com))
  - **Supabase** - Database ([get project](https://supabase.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/Hams-Ollo/open-sousveillance-studio.git
cd open-sousveillance-studio

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# .env
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_key
FIRECRAWL_API_KEY=your_firecrawl_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_DB_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

### Running the Server

```bash
# Start the FastAPI server
uvicorn src.main:app --reload --port 8000

# The API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Running Agents Manually

```bash
# Run a specific Scout agent
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"agent": "A1", "url": "https://alachuafl.portal.civicclerk.com/"}'

# Check pending approvals
curl "http://localhost:8000/approvals/pending"

# Approve an analyst report
curl -X POST "http://localhost:8000/approvals/{thread_id}/decide" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "comments": "Looks good!"}'
```

---

## 📅 Roadmap

### Phase 1: Foundation ✅
- [x] Project structure and configuration
- [x] Pydantic schemas for all data models
- [x] Supabase database connection
- [x] Source registry documentation

### Phase 2: Scout Layer (Current) 🚧
- [ ] Firecrawl client wrapper with retry logic
- [ ] CivicClerk scraper (Firecrawl + actions)
- [ ] Florida Public Notices scraper
- [ ] PDF processing pipeline (Firecrawl + Gemini)
- [ ] Document storage with Supabase
- [ ] Change detection and deduplication

### Phase 3: Analyst Layer
- [ ] LangGraph workflow implementation
- [ ] Tavily integration for deep research
- [ ] Human approval checkpoint (interrupt/resume)
- [ ] FastAPI approval endpoints

### Phase 4: Synthesizer Layer
- [ ] Newsletter generation with MJML
- [ ] Resend email integration
- [ ] Social media content templates
- [ ] Quarterly health scorecard

### Phase 5: Production Hardening
- [ ] APScheduler cron integration
- [ ] Error handling and retry logic
- [ ] Monitoring and alerting
- [ ] Docker deployment

---

## 🤝 Contributing

We welcome contributions! Please see [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) for setup instructions and coding standards.

**Priority Areas:**
- Government portal scrapers (new sources)
- PDF extraction improvements
- Newsletter template design
- Documentation and testing

---

## 🌍 Adopt for Your Community

Open Sousveillance Studio is designed to be forked and adapted for **any US municipality** with zero code changes. The YAML configuration system makes this simple:

### Quick Start for Your City

1. **Fork this repository**

2. **Configure your instance** (`config/instance.yaml`):
   ```yaml
   instance:
     id: "yourtown-tx"
     name: "Your Town Civic Watch"
     timezone: "America/Chicago"
   
   jurisdiction:
     state: "TX"
     county: "Your County"
     municipalities:
       - name: "City of Your Town"
         primary: true
   ```

3. **Add your government sources** (`config/sources.yaml`):
   - Find your city's meeting portal (CivicClerk, eScribe, Granicus, etc.)
   - Add county commission URLs
   - Include relevant state agencies

4. **Define your watchlist** (`config/entities.yaml`):
   - Add local development projects of concern
   - List developers and organizations to track
   - Define keywords relevant to your issues

5. **Deploy and start watching!**

### Common Government Portal Platforms

| Platform | Common In | Scraping Method |
|:---------|:----------|:----------------|
| **CivicClerk** | Small/mid cities | Firecrawl (React SPA) |
| **eScribe** | Counties, larger cities | Firecrawl + PDF download |
| **Granicus** | Large cities | BeautifulSoup or API |
| **Legistar** | Major metros | REST API |
| **BoardDocs** | School boards | Firecrawl |

### Example Configurations

We welcome community contributions of configurations for other jurisdictions:
- `config/examples/gainesville-fl/` - Gainesville, FL
- `config/examples/austin-tx/` - Austin, TX  
- `config/examples/seattle-wa/` - Seattle, WA

**Share your config!** Open a PR to add your city's configuration to help others get started.

We'd love to hear how you're using this tool. Open an issue or PR to share your experience!

---

## 📧 Contact

**Project Lead:** Hans  
**Origin Coalition:** Our Alachua Water  
**Repository:** [github.com/Hams-Ollo/open-sousveillance-studio](https://github.com/Hams-Ollo/open-sousveillance-studio)

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**They watched us. Now we watch back. 👁️✊**
