# 👁️ Open Sousveillance Studio

**AI-powered civic intelligence. Watching from below.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini_2.5-blue.svg)](https://ai.google.dev/)
[![Supabase](https://img.shields.io/badge/database-Supabase-green.svg)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Version:** 0.4.0-dev
**Status:** ✅ Two-Layer Agent Architecture Operational
**Origin:** 📍 Alachua County, Florida

> *"Sousveillance"* (French: sous "from below" + veillance "watching") — the recording of an activity by a participant, in contrast to surveillance. **From clear seeing, right action.**

---

## 🎯 What Is This?

Open Sousveillance Studio is an **open-source AI agent platform** that monitors local government activity and alerts citizens to important developments.

**The Problem:** Local government decisions happen fast. Agendas are posted days before meetings. Permit applications are buried in obscure portals. By the time citizens learn about a development threatening their water supply, it's often too late.

**The Solution:** AI agents that automatically watch government portals, extract actionable intelligence, and generate reports for community distribution.

### Key Features

- 🔍 **Two-Layer Agent System** — ScoutAgent (analysis) + AnalystAgent (deep research)
- 🧠 **Dual Research Providers** — Tavily (fast) + Gemini Deep Research (thorough)
- ⏰ **Scheduled Pipeline** — Daily runs at 4 AM EST via Celery Beat
- 🚨 **Watchdog Alerts** — 14 configurable rules for civic monitoring
- 🏷️ **Unified Events** — CivicEvent model normalizes data from all sources
- ⚠️ **Change Detection** — Content hashing detects new and updated items
- 📊 **Event Queries** — "What's new?", upcoming meetings, entity search
- 🔧 **Config-Driven** — Deploy to any municipality by editing YAML files
- 🖥️ **Orchestrator Panel** — Streamlit UI for manual runs and monitoring

---

## 🚀 Quick Start

### 📋 Prerequisites

- Python 3.10+
- API Keys: [Google AI](https://aistudio.google.com), [Firecrawl](https://firecrawl.dev), [Tavily](https://tavily.com)

### 💻 Installation

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

### ⚡ Quick Start (Windows)

The easiest way to start everything:

```powershell
# Run the startup script (starts both services)
.\start-all.ps1
```

This launches:
- **Streamlit Dev Console** at `http://localhost:8501`
- **FastAPI Backend** at `http://localhost:8000`

### 🔧 Manual Start

**Dev Console only:**
```bash
streamlit run src/ui/app.py
# Opens at http://localhost:8501
```

**API Server only:**
```bash
uvicorn src.app:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

---

## ⚙️ Configuration

Customize for your community by editing YAML files in `config/`:

| File | Purpose |
|:-----|:--------|
| `instance.yaml` | Your deployment identity, timezone, schedules |
| `sources.yaml` | Government portals to monitor |
| `entities.yaml` | Watchlist: entities, keywords, topics to FLAG (not filter) |
| `civic_categories.yaml` | Universal civic categories (shared across all instances) |

### Priority Tiers

Entities in your watchlist use priority tiers instead of urgency colors:

| Tier | Meaning |
|:-----|:--------|
| `critical` | Immediate attention, potential citizen action needed |
| `high` | Important to track closely, may escalate |
| `medium` | Worth monitoring, background awareness |
| `low` | Informational, allies, or general context |

### Example Watchlist Entry

```yaml
# config/entities.yaml
projects:
  - id: "tara-portfolio"
    name: "Tara Development Portfolio"
    priority: "critical"  # Flags items for priority review
    keywords: ["Mill Creek", "PSE22-0002"]
    aliases: ["Tara Forest", "Tara Baywood"]
```

**Key Principle:** The system documents ALL government activity. Watchlist items are *flagged* for priority attention, not used to *filter* what gets reported.

---

## 📁 Project Structure

```
open-sousveillance-studio/
├── config/                    # YAML configuration
│   ├── instance.yaml          # Deployment settings
│   ├── entities.yaml          # Watchlist (instance-specific)
│   ├── sources.yaml           # Data sources to monitor
│   ├── watchdog_rules.yaml    # Civic alert rules (14 rules)
│   └── discovered_resources.yaml  # Resource cache
├── src/
│   ├── agents/                # Scout & Analyst agents
│   ├── intelligence/          # 🆕 Event-driven intelligence layer
│   │   ├── models.py          # CivicEvent, Entity, Document, Alert
│   │   ├── event_store.py     # Persistence + queries
│   │   ├── rules_engine.py    # Watchdog alert generation
│   │   └── adapters/          # Source → CivicEvent converters
│   ├── tools/                 # Scrapers & utilities
│   │   ├── civicclerk_scraper.py
│   │   ├── srwmd_scraper.py
│   │   ├── florida_notices_scraper.py
│   │   ├── gemini_research.py # 🆕 Gemini Deep Research client
│   │   └── resource_cache.py
│   ├── ui/                    # Streamlit Dev Console
│   ├── api/                   # FastAPI routes
│   └── orchestrator.py        # Pipeline coordinator
├── scripts/                   # Utility scripts
│   ├── discover_sitemaps.py   # Source URL discovery
│   └── analyze_sources.py     # Playbook generator
├── prompt_library/            # Agent prompts & context
├── docs/                      # Documentation
└── test/                      # Test suite (78 tests)
```

---

## 📚 Documentation

| Document | Description |
|:---------|:------------|
| 📖 [USER_GUIDE.md](docs/USER_GUIDE.md) | Non-technical guide with visual diagrams |
| 📋 [LOGGING.md](docs/LOGGING.md) | **NEW** Logging system & debugging guide |
| 🏗️ [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, diagrams, technology stack |
| 🔄 [SYSTEM_OVERHAUL.md](docs/SYSTEM_OVERHAUL.md) | Comprehensive coverage architecture |
| 📏 [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Development standards, style guide |
| 👩‍💻 [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Setup, testing, contributing |
| 📅 [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | Roadmap, epics, features, user stories |
| 🔄 [SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) | Workflow design, data flow |
| 📋 [SPEC.md](docs/SPEC.md) | Technical specification |

---

## 🗺️ Roadmap

### Completed ✅
- [x] **Phase 1 - Foundation:** Config, schemas, logging, Streamlit Dev Console
- [x] **Phase 2 - Scout Layer:** Firecrawl integration, 3 scrapers, Orchestrator
- [x] **Phase 3 - Intelligence Layer:** CivicEvent model, EventStore, Watchdog Rules
- [x] **Phase 3b - Analyst Layer:** Dual research providers (Tavily + Gemini Deep Research)
- [x] **Scheduled Pipeline:** Daily 4 AM EST runs via Celery Beat
- [x] **Orchestrator Panel:** Manual runs, async execution, skip options

### In Progress 🚧
- [ ] **Health Metrics:** Self-healing scrapers with health tracking
- [ ] **User Watchlists:** Subscribe to topics, areas, keywords
- [ ] **Entity Extraction:** Cross-source linking for investigation

### Planned 📋
- [ ] **Human-in-the-Loop:** Approval workflow for high-impact reports
- [ ] **Synthesizer Layer:** Newsletters, social media content
- [ ] **Production:** Docker deployment, multi-municipality support

---

## 🏘️ Adopt for Your Community

This system is designed to be forked for **any US municipality**:

1. Fork this repository
2. Edit `config/instance.yaml` with your jurisdiction
3. Add your government portals to `config/sources.yaml`
4. Define your watchlist in `config/entities.yaml` (priority tiers: critical/high/medium/low)
5. `civic_categories.yaml` is universal — no changes needed
6. Deploy and start watching!

**Key Design Principle:** Generic framework (code) + Instance config (YAML) + LLM intelligence (dynamic reasoning)

---

## 🤝 Contributing

We welcome contributions! See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for setup and [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) for development standards.

**Priority Areas:**
- Government portal scrapers
- PDF extraction improvements
- Newsletter templates

---

## 📬 Contact

**Project Lead:** Hans
**Origin Coalition:** Our Alachua Water
**Repository:** [github.com/Hams-Ollo/open-sousveillance-studio](https://github.com/Hams-Ollo/open-sousveillance-studio)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**They watched us. Now we watch back. 👁️✊**
