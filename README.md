# 👁️ Open Sousveillance Studio

**AI-powered civic intelligence. Watching from below.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini_2.5-blue.svg)](https://ai.google.dev/)
[![Supabase](https://img.shields.io/badge/database-Supabase-green.svg)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Version:** 0.2.0-dev
**Status:** ✅ Comprehensive Civic Intelligence
**Origin:** 📍 Alachua County, Florida

> *"Sousveillance"* (French: sous "from below" + veillance "watching") — the recording of an activity by a participant, in contrast to surveillance. **From clear seeing, right action.**

---

## 🎯 What Is This?

Open Sousveillance Studio is an **open-source AI agent platform** that monitors local government activity and alerts citizens to important developments.

**The Problem:** Local government decisions happen fast. Agendas are posted days before meetings. Permit applications are buried in obscure portals. By the time citizens learn about a development threatening their water supply, it's often too late.

**The Solution:** AI agents that automatically watch government portals, extract actionable intelligence, and generate reports for community distribution.

### Key Features

- 🔍 **Comprehensive Coverage** — Scouts analyze ALL government activity, not just keyword matches
- 🧠 **AI Analysis** — Gemini 2.5 Pro extracts insights from meeting agendas and permits
- 🚨 **Smart Alerts** — RED/YELLOW/GREEN urgency levels for time-sensitive items
- 🏷️ **Civic Categories** — 12 universal categories (Budget, Land Use, Environment, etc.)
- ⚠️ **Priority Flagging** — Watchlist items highlighted without filtering other content
- 📊 **Structured Reports** — JSON output ready for dashboards or newsletters
- 🔧 **Config-Driven** — Deploy to any municipality by editing YAML files
- 🖥️ **Dev Console** — Streamlit UI for testing and debugging

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
│   └── civic_categories.yaml  # Universal categories
├── src/
│   ├── agents/                # Scout & Analyst agents
│   ├── prompts/               # Context & prompt loading
│   ├── schemas.py             # Pydantic models (CivicCategory, Significance, etc.)
│   ├── ui/                    # Streamlit Dev Console
│   ├── api/                   # FastAPI routes
│   └── app.py                 # Main application
├── prompt_library/            # Agent prompts & context
├── docs/                      # Documentation
└── test/                      # Test suite
```

---

## 📚 Documentation

| Document | Description |
|:---------|:------------|
| 🏗️ [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, diagrams, technology stack |
| � [SYSTEM_OVERHAUL.md](docs/SYSTEM_OVERHAUL.md) | **NEW** Comprehensive coverage architecture |
| �📏 [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Development standards, style guide |
| 👩‍💻 [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Setup, testing, contributing |
| 📅 [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | Roadmap, epics, features, user stories |
| 🔄 [SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) | Workflow design, data flow |
| 📋 [SPEC.md](docs/SPEC.md) | Technical specification |

---

## 🗺️ Roadmap

### Completed
- [x] **Foundation:** Config, schemas, logging, Streamlit Dev Console
- [x] **Scout Layer:** Firecrawl integration, Gemini analysis
- [x] **Comprehensive Coverage:** Analyze ALL items, not just keyword matches
- [x] **Config-Driven Architecture:** YAML-based watchlists and categories

### In Progress
- [ ] **Analyst Layer:** Deep research, pattern recognition, approvals
- [ ] **Vector Search:** Query past reports for context

### Planned
- [ ] **Synthesizer Layer:** Newsletters, social media content
- [ ] **Feedback System:** User ratings to improve relevance
- [ ] **Production:** Monitoring, Docker deployment, multi-municipality

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
