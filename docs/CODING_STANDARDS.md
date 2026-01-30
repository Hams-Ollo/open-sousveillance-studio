# 📏 Coding Standards

**Open Sousveillance Studio — Development Standards & Best Practices**

*This document ensures consistency across all contributors, including AI coding assistants.*

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Python Style Guide](#python-style-guide)
3. [Project Structure](#project-structure)
4. [Agent Development Standards](#agent-development-standards)
5. [Testing Standards](#testing-standards)
6. [Documentation Standards](#documentation-standards)
7. [Git Workflow](#git-workflow)
8. [Security Standards](#security-standards)
9. [Performance Standards](#performance-standards)
10. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## 💡 Philosophy

### Core Principles

1. **Clarity over cleverness** — Code should be readable by humans first, optimized second
2. **Explicit over implicit** — No magic; dependencies and behavior should be obvious
3. **Fail fast, fail loud** — Errors should be caught early with clear messages
4. **Test what matters** — Focus on behavior, not implementation details
5. **Document the why** — Code shows what; comments explain why

### Design Principles

1. **Configuration-driven** — Behavior controlled by YAML, not hardcoded
2. **Graceful degradation** — System continues with reduced functionality if a component fails
3. **Audit everything** — All agent actions must be traceable
4. **Human-in-the-loop** — AI assists, humans decide on public-facing content

---

## 🐍 Python Style Guide

### Base Standard

We follow **[PEP 8](https://peps.python.org/pep-0008/)** with the following specifics:

### Formatting

```python
# Line length: 100 characters max (not 79)
# Use Black formatter with line-length=100

# Imports: grouped and sorted
# 1. Standard library
# 2. Third-party packages
# 3. Local imports

# Example:
import os
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
import structlog

from src.config import get_all_sources
from src.schemas import ScoutReport
```

### Naming Conventions

```python
# Modules: lowercase_with_underscores
firecrawl_client.py
scout_tasks.py

# Classes: PascalCase
class ScoutAgent:
class FirecrawlClient:

# Functions/Methods: lowercase_with_underscores
def run_scout_agent():
def extract_meeting_items():

# Constants: UPPERCASE_WITH_UNDERSCORES
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private: single leading underscore
def _internal_helper():
_cached_client = None

# Type hints: always use for public functions
def process_document(url: str, timeout: int = 30) -> ScoutReport:
```

### Type Hints

```python
# Always use type hints for:
# - Function parameters
# - Function return values
# - Class attributes

from typing import List, Optional, Dict, Any, Union

def analyze_content(
    content: str,
    keywords: List[str],
    max_items: Optional[int] = None
) -> Dict[str, Any]:
    """Analyze content for keyword matches."""
    ...

# Use Pydantic models for complex types
from src.schemas import ScoutReport, UrgencyAlert

def generate_report(data: dict) -> ScoutReport:
    ...
```

### Error Handling

```python
# Be specific with exceptions
# Bad:
try:
    result = api_call()
except Exception:
    pass

# Good:
try:
    result = api_call()
except requests.Timeout as e:
    logger.warning("API timeout", url=url, error=str(e))
    raise ScrapingError(f"Timeout fetching {url}") from e
except requests.HTTPError as e:
    logger.error("API error", status=e.response.status_code)
    raise

# Custom exceptions in src/exceptions.py
class ScrapingError(Exception):
    """Raised when web scraping fails."""
    pass

class AgentError(Exception):
    """Raised when an agent fails to execute."""
    pass
```

### Logging

```python
# Use structlog for structured logging
import structlog

logger = structlog.get_logger(__name__)

# Good: structured with context
logger.info(
    "Scout completed",
    agent_id="A1",
    url=url,
    items_found=len(items),
    duration_ms=elapsed
)

# Bad: string formatting
logger.info(f"Scout A1 found {len(items)} items in {elapsed}ms")

# Log levels:
# - DEBUG: Detailed diagnostic info
# - INFO: Normal operation milestones
# - WARNING: Unexpected but handled situations
# - ERROR: Failures that need attention
# - CRITICAL: System-wide failures
```

### Docstrings

```python
# Use Google-style docstrings

def extract_agenda_items(
    content: str,
    board_filter: Optional[str] = None
) -> List[MeetingItem]:
    """Extract agenda items from meeting content.

    Parses the provided content and extracts structured agenda items,
    optionally filtering by board name.

    Args:
        content: Raw markdown content from scraped page.
        board_filter: Optional board name to filter items (e.g., "Planning").

    Returns:
        List of MeetingItem objects with extracted data.

    Raises:
        ValueError: If content is empty or malformed.
        ExtractionError: If LLM fails to parse content.

    Example:
        >>> items = extract_agenda_items(content, board_filter="Commission")
        >>> print(items[0].topic)
        "Rezoning Application RZ-2026-001"
    """
```

---

## 📁 Project Structure

### Directory Layout

```
src/
├── agents/                 # Agent implementations
│   ├── __init__.py
│   ├── base.py            # BaseAgent abstract class
│   ├── scout.py           # Scout agents (A1-A4)
│   └── analyst.py         # Analyst agents (B1-B2)
│
├── api/                   # FastAPI routes
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── workflows.py   # /run, /status endpoints
│       └── approvals.py   # /approvals endpoints
│
├── tools/                 # External service wrappers
│   ├── __init__.py
│   ├── firecrawl_client.py
│   ├── embeddings.py
│   └── vector_store.py
│
├── workflows/             # LangGraph workflows
│   ├── __init__.py
│   └── graphs.py
│
├── ui/                    # Streamlit dev console
│   ├── __init__.py
│   ├── app.py
│   └── pages/
│
├── prompts/               # Prompt loading utilities
│   ├── __init__.py
│   ├── loader.py
│   └── context.py
│
├── app.py                 # FastAPI application
├── config.py              # Configuration loader
├── database.py            # Supabase client
├── schemas.py             # Pydantic models
├── models.py              # LLM configuration
├── exceptions.py          # Custom exceptions
└── logging_config.py      # Logging setup
```

### Module Guidelines

1. **One responsibility per module** — `firecrawl_client.py` only handles Firecrawl
2. **Lazy imports for heavy dependencies** — Avoid importing torch/docling at module level
3. **Export public API in `__init__.py`** — Users import from package, not submodules
4. **Keep modules under 500 lines** — Split if larger

---

## 🤖 Agent Development Standards

### Agent Structure

All agents must inherit from `BaseAgent`:

```python
from src.agents.base import BaseAgent
from src.schemas import ScoutReport

class MeetingScoutAgent(BaseAgent):
    """A1: Monitors city meeting portals for new agendas."""

    agent_id: str = "A1"
    agent_name: str = "Meeting Scout"
    layer: int = 1  # 1=Scout, 2=Analyst, 3=Synthesizer

    def __init__(self):
        super().__init__()
        # Initialize dependencies
        self.llm = get_gemini_pro()

    def _execute(self, input_data: dict) -> ScoutReport:
        """Execute the agent's primary task.

        Args:
            input_data: Must contain 'url' key.

        Returns:
            ScoutReport with extracted data.
        """
        url = input_data["url"]

        # 1. Fetch content
        content = self._fetch_content(url)

        # 2. Analyze with LLM
        report = self._analyze(content)

        # 3. Return structured output
        return report
```

### Agent Naming Convention

| Layer | Prefix | Example |
|:------|:-------|:--------|
| Scout | A | A1, A2, A3, A4 |
| Analyst | B | B1, B2, B3 |
| Synthesizer | C | C1, C2, C3, C4 |
| Reactive | R | R1, R2, R3 |

### Prompt Standards

```markdown
# Prompts stored in prompt_library/layer-X-agents/

## File naming
- agent-id-name.md (e.g., a1-meeting-scout.md)

## Required sections
1. Role definition
2. Context injection point ({{ALACHUA_CONTEXT}})
3. Input format
4. Output format (with JSON schema)
5. Examples (few-shot)
6. Constraints and guardrails
```

### Output Schema Requirements

All agent outputs must:

1. **Inherit from BaseReport** — Ensures common fields (report_id, date, alerts)
2. **Use Pydantic models** — Strict validation, JSON serialization
3. **Include source attribution** — Every claim links to source URL
4. **Include confidence scores** — Where applicable

```python
class ScoutReport(BaseReport):
    """Output from Scout agents."""

    items: List[MeetingItem] = Field(
        default_factory=list,
        description="Extracted agenda items"
    )
    source_url: str = Field(
        ...,
        description="URL that was analyzed"
    )
    scrape_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When content was fetched"
    )
```

---

## 🧪 Testing Standards

### Test Structure

```
test/
├── conftest.py           # Shared fixtures
├── test_config.py        # Configuration tests
├── test_schemas.py       # Schema validation tests
├── test_agents.py        # Agent unit tests
├── test_api.py           # API endpoint tests
├── test_tools.py         # Tool wrapper tests
└── integration/
    ├── test_scout_workflow.py
    └── test_analyst_workflow.py
```

### Test Naming

```python
# test_<module>.py

# Function naming: test_<function>_<scenario>_<expected>
def test_extract_items_with_valid_content_returns_list():
    ...

def test_extract_items_with_empty_content_raises_error():
    ...

def test_scout_agent_with_timeout_retries_three_times():
    ...
```

### Test Requirements

1. **Unit tests for all public functions** — Minimum 80% coverage
2. **Integration tests for workflows** — End-to-end happy path
3. **Mock external services** — Never call real APIs in tests
4. **Test edge cases** — Empty input, malformed data, timeouts

```python
# Example test with mocking
import pytest
from unittest.mock import Mock, patch

def test_scout_agent_extracts_meeting_items():
    """Scout should extract items from valid content."""
    # Arrange
    mock_content = "## Agenda\n1. Rezoning RZ-2026-001"

    with patch("src.tools.firecrawl_client.scrape_page") as mock_scrape:
        mock_scrape.return_value = mock_content

        agent = ScoutAgent()

        # Act
        result = agent.run({"url": "https://example.com"})

        # Assert
        assert isinstance(result, ScoutReport)
        assert len(result.items) > 0
        mock_scrape.assert_called_once()


def test_scout_agent_handles_scraping_failure():
    """Scout should raise AgentError on scraping failure."""
    with patch("src.tools.firecrawl_client.scrape_page") as mock_scrape:
        mock_scrape.side_effect = ScrapingError("Timeout")

        agent = ScoutAgent()

        with pytest.raises(AgentError):
            agent.run({"url": "https://example.com"})
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest test/test_agents.py

# Run tests matching pattern
pytest -k "scout"

# Run with verbose output
pytest -v
```

---

## 📝 Documentation Standards

### Code Documentation

1. **All public functions have docstrings** — Google style
2. **Complex logic has inline comments** — Explain why, not what
3. **Type hints on all public APIs** — Enables IDE support

### Project Documentation

| Document | Purpose | Update Frequency |
|:---------|:--------|:-----------------|
| `README.md` | Project overview, quick start | Each release |
| `docs/ARCHITECTURE.md` | System design, diagrams | Major changes |
| `docs/DEVELOPER_GUIDE.md` | Setup, contributing | As needed |
| `docs/CODING_STANDARDS.md` | This document | As standards evolve |
| `docs/PROJECT_PLAN.md` | Roadmap, epics, tasks | Sprint planning |
| `CHANGELOG.md` | Release notes | Each release |

### Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
# Changelog

## [Unreleased]

### Added
- New Budget Scout agent (A5)

### Changed
- Improved error messages in ScoutAgent

### Fixed
- Timeout handling in Firecrawl client

## [0.1.0] - 2026-01-30

### Added
- Initial Scout and Analyst agents
- Streamlit dev console
- FastAPI endpoints
```

---

## 🔀 Git Workflow

### Branch Naming

```
main              # Production-ready code
develop           # Integration branch
feature/xxx       # New features
bugfix/xxx        # Bug fixes
hotfix/xxx        # Urgent production fixes
docs/xxx          # Documentation updates
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

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
- `refactor`: Code change that neither fixes nor adds
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
feat(agents): add Budget Scout agent A5

fix(scraping): handle timeout in CivicClerk scraper

docs(readme): update quick start instructions

refactor(models): migrate to native google.genai SDK

Migrated from langchain_google_genai to native SDK
to avoid PyTorch dependency issues on Windows.

Closes #42
```

### Pull Request Process

1. **Create feature branch** from `develop`
2. **Write code** following standards
3. **Add/update tests** — PR must not decrease coverage
4. **Update documentation** if needed
5. **Run linters** — `black`, `ruff`, `mypy`
6. **Create PR** with description template
7. **Address review feedback**
8. **Squash and merge** to `develop`

### PR Description Template

```markdown
## Summary
Brief description of changes.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactor

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project standards
- [ ] Self-reviewed code
- [ ] Documentation updated
- [ ] No new warnings
```

---

## 🔒 Security Standards

### Secrets Management

```python
# NEVER hardcode secrets
# Bad:
api_key = "sk-1234567890"

# Good:
import os
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable required")
```

### Environment Variables

```bash
# All secrets in .env (never committed)
# Document in .env.example (committed)

# .env.example
GOOGLE_API_KEY=your_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
```

### Input Validation

```python
# Always validate external input
from pydantic import BaseModel, Field, validator

class RunAgentRequest(BaseModel):
    agent: str = Field(..., regex=r"^[ABC]\d$")
    url: str = Field(..., min_length=10)

    @validator("url")
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v
```

### Dependency Security

```bash
# Regular security audits
pip-audit
safety check

# Pin all dependencies
# requirements.txt
pydantic==2.10.6
fastapi==0.115.8
```

---

## ⚡ Performance Standards

### API Response Times

| Endpoint | Target | Max |
|:---------|:-------|:----|
| Health check | <50ms | 200ms |
| List reports | <200ms | 1s |
| Run agent | <30s | 60s |

### Resource Limits

```python
# Set timeouts on all external calls
response = requests.get(url, timeout=30)

# Limit LLM output tokens
llm = GeminiModel(max_output_tokens=8192)

# Batch operations where possible
results = firecrawl.batch_scrape(urls, batch_size=10)
```

### Caching

```python
# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=100)
def get_source_config(source_id: str) -> SourceConfig:
    ...

# Use content hashing to avoid reprocessing
def should_process(content: str, stored_hash: str) -> bool:
    current_hash = hashlib.sha256(content.encode()).hexdigest()
    return current_hash != stored_hash
```

---

## 🤖 AI Assistant Guidelines

### For AI Coding Assistants (Cascade, Copilot, etc.)

When working on this codebase, AI assistants should:

#### Code Generation

1. **Follow all standards in this document** — Style, naming, structure
2. **Use type hints** on all functions
3. **Add docstrings** to all public functions
4. **Prefer existing patterns** — Look at similar code in the project first
5. **Don't add comments unless explaining "why"** — Code should be self-documenting

#### Agent Development

1. **Inherit from BaseAgent** — Never create standalone agent classes
2. **Use Pydantic schemas** — All inputs/outputs must be validated
3. **Include source attribution** — Every claim must link to source
4. **Log with structlog** — Use structured logging, not print statements

#### Testing

1. **Write tests for new code** — Don't decrease coverage
2. **Mock external services** — Never call real APIs in tests
3. **Test edge cases** — Empty input, errors, timeouts

#### Dependencies

1. **Check requirements.txt first** — Don't add new dependencies without discussion
2. **Use lazy imports** for heavy libraries (torch, docling)
3. **Pin versions** when adding dependencies

#### Commits

1. **Use Conventional Commits** format
2. **One logical change per commit**
3. **Reference issues** where applicable

### Prompt for AI Assistants

When starting work on this project, AI assistants should be given:

```
You are working on Open Sousveillance Studio, an AI-powered civic monitoring platform.

Before making changes:
1. Read docs/CODING_STANDARDS.md for project conventions
2. Check existing code for patterns to follow
3. Run tests after changes: pytest

Key standards:
- Python 3.10+, PEP 8, Black formatter (line-length=100)
- Type hints required on all public functions
- Google-style docstrings
- structlog for logging
- Pydantic for all data models
- Conventional Commits for git messages

Agent development:
- All agents inherit from src.agents.base.BaseAgent
- Output schemas inherit from src.schemas.BaseReport
- Prompts stored in prompt_library/
```

---

## 🛠️ Tooling Configuration

### pyproject.toml

```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
exclude = '''
/(
    \.git
    | \.venv
    | __pycache__
    | build
    | dist
)/
'''

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line length handled by Black

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["test"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

### VS Code Settings

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "editor.formatOnSave": true,
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["test"]
}
```

---

## ✅ Checklist for Contributors

Before submitting a PR, verify:

- [ ] Code follows PEP 8 and project style guide
- [ ] All public functions have type hints
- [ ] All public functions have docstrings
- [ ] Tests added/updated for changes
- [ ] All tests pass (`pytest`)
- [ ] No new linter warnings (`ruff check src/`)
- [ ] Code formatted (`black src/ test/`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow Conventional Commits
- [ ] PR description filled out completely

---

*Last updated: 2026-01-30*
