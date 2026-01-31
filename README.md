# 👁️ Open Sousveillance Studio

**AI-powered civic intelligence. Watching from below.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini_2.5-blue.svg)](https://ai.google.dev/)
[![Supabase](https://img.shields.io/badge/database-Supabase-green.svg)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Version:** 0.1.0-dev
**Status:** ✅ Core Agents Working
**Origin:** 📍 Alachua County, Florida

> *"Sousveillance"* (French: sous "from below" + veillance "watching") — the recording of an activity by a participant, in contrast to surveillance. **From clear seeing, right action.**

---

## 🎯 What Is This?

Open Sousveillance Studio is an **open-source AI agent platform** that monitors local government activity and alerts citizens to important developments.

**The Problem:** Local government decisions happen fast. Agendas are posted days before meetings. Permit applications are buried in obscure portals. By the time citizens learn about a development threatening their water supply, it's often too late.

**The Solution:** AI agents that automatically watch government portals, extract actionable intelligence, and generate reports for community distribution.

### Key Features

- 🔍 **Automated Monitoring** — Scouts watch 15+ government data sources daily
- 🧠 **AI Analysis** — Gemini 2.5 Pro extracts insights from meeting agendas and permits
- 🚨 **Smart Alerts** — RED/YELLOW/GREEN urgency levels for time-sensitive items
- 📊 **Structured Reports** — JSON output ready for dashboards or newsletters
- 🔧 **Dev Console** — Streamlit UI for testing and debugging

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
| `entities.yaml` | Projects, organizations, and keywords to watch |

Example watchlist entry:

```yaml
# config/entities.yaml
projects:
  - id: "tara-portfolio"
    name: "Tara Development Portfolio"
    urgency: "red"
    keywords: ["Mill Creek", "PSE22-0002"]
```

---

## 📁 Project Structure

```
open-sousveillance-studio/
├── config/              # YAML configuration
├── src/
│   ├── agents/          # Scout & Analyst agents
│   ├── ui/              # Streamlit Dev Console
│   ├── api/             # FastAPI routes
│   ├── tools/           # Firecrawl, embeddings, RAG
│   └── app.py           # Main application
├── prompt_library/      # Agent prompts
├── docs/                # Documentation
└── test/                # Test suite
```

---

## 📚 Documentation

| Document | Description |
|:---------|:------------|
| 🏗️ [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, diagrams, technology stack |
| 📏 [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Development standards, style guide, AI assistant guidelines |
| 👩‍💻 [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Setup, testing, contributing |
| 📅 [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | Roadmap, epics, features, user stories |
| 🔄 [SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) | Workflow design, data flow, open questions |
| 📋 [SPEC.md](docs/SPEC.md) | Technical specification |

---

## 🗺️ Roadmap

- [x] **Phase 1:** Foundation (config, schemas, logging)
- [x] **Phase 2:** Scout Layer (Firecrawl, Gemini, Dev Console)
- [ ] **Phase 3:** Analyst Layer (deep research, approvals)
- [ ] **Phase 4:** Synthesizer Layer (newsletters, social media)
- [ ] **Phase 5:** Production (monitoring, Docker deployment)

---

## 🏘️ Adopt for Your Community

This system is designed to be forked for **any US municipality**:

1. Fork this repository
2. Edit `config/instance.yaml` with your jurisdiction
3. Add your government portals to `config/sources.yaml`
4. Define your watchlist in `config/entities.yaml`
5. Deploy and start watching!

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
