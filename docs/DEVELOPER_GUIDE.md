# Developer Guide

**Open Sousveillance Studio — Development Setup & Contributing**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Environment Variables](#environment-variables)
4. [Project Structure](#project-structure)
5. [Running the Application](#running-the-application)
6. [Running Tests](#running-tests)
7. [Code Style & Standards](#code-style--standards)
8. [Architecture Overview](#architecture-overview)
9. [Contributing](#contributing)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|:---------|:--------|:--------|
| **Python** | 3.10+ | Runtime |
| **Redis** | 6.0+ | Celery message broker |
| **Git** | 2.30+ | Version control |

### Optional (Recommended)

| Software | Purpose |
|:---------|:--------|
| **Docker** | Run Redis, local Supabase |
| **VS Code / Windsurf** | IDE with Python support |

### Required API Keys

| Service | Purpose | Get Key |
|:--------|:--------|:--------|
| **Google AI (Gemini)** | LLM analysis | [aistudio.google.com](https://aistudio.google.com) |
| **Firecrawl** | Web scraping | [firecrawl.dev](https://firecrawl.dev) |
| **Tavily** | Deep research | [tavily.com](https://tavily.com) |
| **Supabase** | Database & storage | [supabase.com](https://supabase.com) |

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Hams-Ollo/open-sousveillance-studio.git
cd open-sousveillance-studio
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys (see Environment Variables section)
```

### 5. Start Redis

```bash
# Option A: Using Docker (recommended)
docker run -d --name redis -p 6379:6379 redis:alpine

# Option B: Native installation
redis-server
```

### 6. Verify Setup

```bash
# Check Python imports work
python -c "from src.config import build_app_config; print('✅ Config OK')"

# Check Redis connection
python -c "import redis; r = redis.Redis(); r.ping(); print('✅ Redis OK')"
```

---

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# =============================================================================
# REQUIRED: LLM & AI Services
# =============================================================================
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# =============================================================================
# REQUIRED: Web Scraping
# =============================================================================
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# =============================================================================
# REQUIRED: Database
# =============================================================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here

# Optional: Direct database connection (for migrations)
SUPABASE_DB_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# =============================================================================
# REQUIRED: Task Queue
# =============================================================================
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# =============================================================================
# OPTIONAL: Logging
# =============================================================================
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=console          # console (colored) or json (production)
```

### Getting API Keys

1. **Google AI (Gemini)**
   - Go to [aistudio.google.com](https://aistudio.google.com)
   - Create a new API key
   - Free tier includes generous limits for development

2. **Firecrawl**
   - Sign up at [firecrawl.dev](https://firecrawl.dev)
   - Free tier: 500 credits/month (sufficient for testing)

3. **Tavily**
   - Sign up at [tavily.com](https://tavily.com)
   - Free tier available for development

4. **Supabase**
   - Create project at [supabase.com](https://supabase.com)
   - Find keys in Project Settings → API

---

## Project Structure

```
open-sousveillance-studio/
├── config/                     # YAML configuration files
│   ├── instance.yaml           # Instance identity & scheduling
│   ├── sources.yaml            # Government data sources
│   └── entities.yaml           # Watchlist (projects, orgs, keywords)
│
├── src/                        # Application source code
│   ├── agents/                 # AI agent implementations
│   │   ├── base.py             # BaseAgent abstract class
│   │   ├── scout.py            # Layer 1: Scout agents (A1-A4)
│   │   └── analyst.py          # Layer 2: Analyst agents (B1-B2)
│   │
│   ├── api/                    # FastAPI routes
│   │   └── routes/
│   │       ├── workflows.py    # POST /run, GET /status
│   │       ├── approvals.py    # Human-in-the-loop endpoints
│   │       └── streaming.py    # SSE real-time updates
│   │
│   ├── tasks/                  # Celery background tasks
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── beat_schedule.py    # Cron schedules
│   │   └── scout_tasks.py      # Scout task definitions
│   │
│   ├── tools/                  # External service wrappers
│   │   ├── firecrawl_client.py # Web scraping
│   │   └── docling_processor.py# PDF parsing
│   │
│   ├── workflows/              # LangGraph workflows
│   │   ├── graphs.py           # Workflow definitions
│   │   ├── checkpointer.py     # State persistence
│   │   └── nodes.py            # Reusable nodes
│   │
│   ├── app.py                  # FastAPI application
│   ├── main.py                 # CLI entry point
│   ├── config.py               # Configuration loader
│   ├── database.py             # Supabase client
│   ├── schemas.py              # Pydantic models
│   └── tools.py                # LangChain tool definitions
│
├── prompt_library/             # Agent prompt templates
│   ├── layer-1-scouts/         # A1-A4 prompts
│   ├── layer-2-analysts/       # B1-B2 prompts
│   └── layer-3-synthesizers/   # C1-C4 prompts
│
├── test/                       # Test files
├── docs/                       # Documentation
├── data/                       # Generated reports
│
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # Project overview
```

---

## Running the Application

### Docker Compose (Recommended)

The easiest way to run all services:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

This starts:
- **api** - FastAPI server on port 8000
- **celery-worker** - Background task processor
- **celery-beat** - Scheduled task runner
- **redis** - Message broker on port 6379

### Development Mode (Manual)

You need **4 terminal windows** for full development:

#### Terminal 1: Redis
```bash
# If using Docker
docker run -d --name redis -p 6379:6379 redis:alpine

# Or native
redis-server
```

#### Terminal 2: Celery Worker
```bash
celery -A src.tasks.celery_app worker --loglevel=info
```

#### Terminal 3: Celery Beat (Scheduler)
```bash
celery -A src.tasks.celery_app beat --loglevel=info
```

#### Terminal 4: FastAPI Server
```bash
uvicorn src.app:app --reload --port 8000
```

### Quick Start (API Only)

For quick testing without background tasks:

```bash
uvicorn src.app:app --reload --port 8000
```

### CLI Mode

Run agents directly without the API:

```bash
# Run Scout on a specific URL
python -m src.main --agent A1 --url "https://alachuafl.portal.civicclerk.com/"

# Run Scout on all critical sources
python -m src.main --agent A1 --critical

# Run Analyst on a topic
python -m src.main --agent B1 --topic "Tara Forest Development"

# Save results to database
python -m src.main --agent A1 --url "https://..." --save
```

### API Endpoints

Once running, access:

| URL | Description |
|:----|:------------|
| http://localhost:8000 | Health check |
| http://localhost:8000/docs | Swagger UI (interactive API docs) |
| http://localhost:8000/redoc | ReDoc (alternative docs) |

#### Key Endpoints

```bash
# Start an agent run
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"agent": "A1", "url": "https://example.com"}'

# Check run status
curl "http://localhost:8000/status/{run_id}"

# List pending approvals
curl "http://localhost:8000/approvals/pending"

# Approve a report
curl -X POST "http://localhost:8000/approvals/{id}/decide" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "comments": "LGTM"}'
```

---

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Tests

```bash
# Run a specific test file
pytest test/test_config.py

# Run tests matching a pattern
pytest -k "test_scout"

# Run with verbose output
pytest -v
```

### Test Structure

```
test/
├── test_config.py          # Configuration loading tests
├── test_schemas.py         # Pydantic model validation
├── test_agents/
│   ├── test_scout.py       # Scout agent tests
│   └── test_analyst.py     # Analyst agent tests
└── test_tools/
    └── test_firecrawl.py   # Firecrawl client tests
```

---

## Code Style & Standards

### Python Style

- **PEP 8** compliance
- **Type hints** for all function signatures
- **Docstrings** for public functions and classes
- **Max line length:** 100 characters

### Formatting Tools

```bash
# Format code with Black
black src/

# Sort imports with isort
isort src/

# Lint with flake8
flake8 src/
```

### Commit Messages

Follow **Conventional Commits** format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(agents): add A3 legislative monitor scout
fix(database): handle missing credentials gracefully
docs(readme): update Firecrawl integration section
```

### Pydantic Models

All data structures use Pydantic v2:

```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    """Docstring describing the model."""
    field_name: str = Field(..., description="What this field contains")
    optional_field: str | None = Field(None, description="Optional field")
```

---

## Architecture Overview

### Three-Layer Agent Framework

```
Layer 1: Scouts (Daily)     → Data collection, fact extraction
Layer 2: Analysts (Weekly)  → Pattern recognition, deep research
Layer 3: Synthesizers       → Public-facing content (requires approval)
```

### Data Flow

```
Government Portal → Firecrawl → Scout Agent → ScoutReport → Database
                                                    ↓
                                            Analyst Agent → AnalystReport
                                                    ↓
                                            [Human Approval]
                                                    ↓
                                            Synthesizer → Newsletter
```

### Key Components

| Component | Technology | File |
|:----------|:-----------|:-----|
| Web Server | FastAPI | `src/app.py` |
| Orchestration | LangGraph | `src/workflows/graphs.py` |
| Task Queue | Celery | `src/tasks/celery_app.py` |
| LLM | Gemini 2.5 | `src/models.py` |
| Database | Supabase | `src/database.py` |
| Scraping | Firecrawl | `src/tools/firecrawl_client.py` |

---

## Contributing

### Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your feature: `git checkout -b feat/my-feature`
4. **Make changes** following code standards
5. **Test** your changes: `pytest`
6. **Commit** with conventional commit message
7. **Push** to your fork
8. **Open a Pull Request**

### Priority Areas

We especially welcome contributions in:

- **New government portal scrapers** (CivicClerk, eScribe, Granicus variants)
- **PDF extraction improvements** (table handling, OCR)
- **Test coverage** (unit tests, integration tests)
- **Documentation** (examples, tutorials)
- **City configurations** (share your `config/` for other jurisdictions)

### Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Include tests for new functionality
- Update documentation if needed
- Ensure all tests pass
- Request review from maintainers

---

## Troubleshooting

### Common Issues

#### "GOOGLE_API_KEY not set"

```bash
# Ensure .env file exists and contains the key
cat .env | grep GOOGLE_API_KEY

# Verify python-dotenv is loading it
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GOOGLE_API_KEY'))"
```

#### Redis Connection Refused

```bash
# Check if Redis is running
redis-cli ping

# Start Redis if needed
docker start redis
# or
redis-server
```

#### Celery Worker Not Processing Tasks

```bash
# Ensure broker URL is correct
echo $CELERY_BROKER_URL

# Check worker is connected
celery -A src.tasks.celery_app inspect active
```

#### Import Errors

```bash
# Ensure you're in the project root
pwd

# Ensure virtual environment is activated
which python  # Should show .venv path

# Reinstall dependencies
pip install -r requirements.txt
```

### Getting Help

- **GitHub Issues:** Report bugs or request features
- **Discussions:** Ask questions, share ideas
- **README:** Check the main documentation

---

## License

MIT License — See [LICENSE](../LICENSE) for details.

---

**Happy hacking! 👁️✊**
