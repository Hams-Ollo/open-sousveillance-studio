# 📋 Logging System

**Open Sousveillance Studio — Structured Logging & Debugging Guide**

---

## Overview

The application uses **structlog** for structured logging with dual output:
- **Console** — Colored output for development, JSON for production
- **File** — JSON format with daily rotation for analysis

---

## Quick Start

```python
from src.logging_config import get_logger, configure_logging

# Configure once at startup (usually done automatically)
configure_logging()

# Get a logger
logger = get_logger("my_module")

# Log with context
logger.info("Processing item", item_id=123, source="civicclerk")
logger.warning("Rate limit approaching", remaining=10)
logger.error("Failed to fetch", url="https://...", error="timeout")
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|:---------|:--------|:------------|
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | `console` | `console` (colored) or `json` (production) |
| `LOG_DIR` | `logs/` | Directory for log files |
| `LOG_FILE_ENABLED` | `true` | Enable/disable file logging |
| `LOG_RETENTION_DAYS` | `30` | Days to keep rotated logs |
| `LOG_MAX_BYTES` | `10485760` | Max bytes per file (10MB) |

### Example .env

```bash
# Development (colored console, file logging enabled)
LOG_LEVEL=DEBUG
LOG_FORMAT=console
LOG_FILE_ENABLED=true

# Production (JSON everywhere)
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_ENABLED=true
```

---

## Log Files

### Location

```
logs/
├── app.log              # Current log file
├── app.log.2026-02-01   # Yesterday's logs
├── app.log.2026-01-31   # Older logs...
└── ...
```

### Rotation Strategy

- **When:** Daily at midnight
- **Retention:** 30 days (configurable)
- **Format:** JSON (machine-readable)
- **Naming:** `app.log.YYYY-MM-DD`

### Log Entry Format (JSON)

```json
{
  "event": "Processing meeting",
  "level": "info",
  "timestamp": "2026-02-02T15:30:00.123456Z",
  "timestamp_unix": 1770065400.123456,
  "app": "alachua-civic-intel",
  "run_id": "abc-123",
  "source_id": "civicclerk",
  "meeting_id": "mtg-456",
  "duration_ms": 125.5
}
```

---

## Logging Patterns

### 1. Basic Logging

```python
from src.logging_config import get_logger

logger = get_logger("tools.scraper")

logger.debug("Fetching page", url=url)
logger.info("Found items", count=15)
logger.warning("Missing field", field="date")
logger.error("Request failed", status_code=500)
```

### 2. Module-Scoped Logger

```python
from src.logging_config import get_logger

# Create logger with initial context
logger = get_logger("agents.scout", agent_id="A1")

# All logs include agent_id automatically
logger.info("Starting run")  # includes agent_id="A1"
```

### 3. Run Correlation

Bind a `run_id` to trace all logs from a single pipeline run:

```python
from src.logging_config import bind_run_context, clear_context

def run_pipeline(source_id: str):
    run_id = str(uuid4())
    
    # Bind context for all subsequent logs
    bind_run_context(run_id=run_id, source_id=source_id)
    
    try:
        # All logs in this context include run_id and source_id
        scrape_data()
        process_events()
        generate_alerts()
    finally:
        clear_context()
```

### 4. Timing Decorator

Automatically log function duration:

```python
from src.logging_config import log_timing

@log_timing("scrape_meetings")
def scrape_meetings(self):
    # ... scraping logic ...
    pass

# Logs:
# DEBUG: Starting scrape_meetings
# INFO: Completed scrape_meetings (operation=scrape_meetings, duration_ms=1234.56, status=success)
```

### 5. Async Timing Decorator

```python
from src.logging_config import log_timing_async

@log_timing_async("fetch_data")
async def fetch_data(self):
    # ... async logic ...
    pass
```

### 6. Context Manager

Scoped logging with automatic timing:

```python
from src.logging_config import LogContext

with LogContext("process_batch", source_id="civicclerk", batch_size=50) as ctx:
    ctx.log.info("Processing item", item_id=1)
    ctx.log.info("Processing item", item_id=2)
    # ... more work ...

# Automatically logs:
# INFO: Starting process_batch
# INFO: Processing item (item_id=1)
# INFO: Processing item (item_id=2)
# INFO: Completed process_batch (duration_ms=567.89, status=success)
```

---

## Analyzing Logs

### View Recent Logs

```powershell
# Last 20 lines
Get-Content logs/app.log -Tail 20

# Follow live (like tail -f)
Get-Content logs/app.log -Wait -Tail 10
```

### Filter by Level

```powershell
# Errors only
Get-Content logs/app.log | Select-String '"level": "error"'

# Warnings and errors
Get-Content logs/app.log | Select-String '"level": "(warning|error)"'
```

### Filter by Run ID

```powershell
# Find all logs for a specific run
Get-Content logs/app.log | Select-String '"run_id": "abc-123"'
```

### Filter by Source

```powershell
# CivicClerk logs only
Get-Content logs/app.log | Select-String '"source_id": "civicclerk"'
```

### Parse with Python

```python
import json
from pathlib import Path

logs = []
for line in Path("logs/app.log").read_text().splitlines():
    try:
        logs.append(json.loads(line))
    except json.JSONDecodeError:
        continue

# Find slow operations
slow_ops = [l for l in logs if l.get("duration_ms", 0) > 1000]

# Find errors
errors = [l for l in logs if l.get("level") == "error"]

# Group by source
from collections import Counter
sources = Counter(l.get("source_id") for l in logs if l.get("source_id"))
```

### Parse with jq (if installed)

```bash
# Pretty print
cat logs/app.log | jq .

# Filter errors
cat logs/app.log | jq 'select(.level == "error")'

# Get timing stats
cat logs/app.log | jq 'select(.duration_ms) | {operation, duration_ms}'
```

---

## Performance Analysis

### Find Slow Operations

```python
import json
from pathlib import Path

logs = [json.loads(l) for l in Path("logs/app.log").read_text().splitlines() if l.strip()]

# Operations over 1 second
slow = [l for l in logs if l.get("duration_ms", 0) > 1000]
for op in slow:
    print(f"{op.get('operation')}: {op.get('duration_ms')}ms")
```

### Timing Summary by Operation

```python
from collections import defaultdict
import statistics

timings = defaultdict(list)
for log in logs:
    if "duration_ms" in log and "operation" in log:
        timings[log["operation"]].append(log["duration_ms"])

for op, times in sorted(timings.items()):
    print(f"{op}:")
    print(f"  count: {len(times)}")
    print(f"  avg: {statistics.mean(times):.2f}ms")
    print(f"  max: {max(times):.2f}ms")
```

---

## Debugging Tips

### 1. Enable Debug Logging

```bash
# In .env or environment
LOG_LEVEL=DEBUG
```

### 2. Check Log Stats

```python
from src.logging_config import get_log_stats

print(get_log_stats())
# {'log_level': 'INFO', 'log_format': 'console', 'log_dir': 'logs', ...}
```

### 3. Trace a Single Run

```python
# At the start of your run
from src.logging_config import bind_run_context
import uuid

run_id = str(uuid.uuid4())[:8]
print(f"Run ID: {run_id}")  # Save this!
bind_run_context(run_id=run_id)

# Later, filter logs:
# Get-Content logs/app.log | Select-String "run_id.*{run_id}"
```

### 4. Add Custom Context

```python
logger = get_logger("my_module")

# Bind context that persists for this logger
logger = logger.bind(user_id="user-123", session="sess-456")

# All subsequent logs include this context
logger.info("Action performed")  # includes user_id and session
```

---

## Integration with Scrapers

The scrapers use logging extensively. Example from `civicclerk_scraper.py`:

```python
from src.logging_config import get_logger, log_timing

logger = get_logger("tools.civicclerk_scraper")

class CivicClerkScraper:
    def __init__(self):
        self.logger = logger.bind(scraper="civicclerk")
    
    @log_timing("scrape_meetings")
    def scrape_meetings(self, board_id: str):
        self.logger.info("Scraping board", board_id=board_id)
        # ... scraping logic ...
        self.logger.info("Found meetings", count=len(meetings))
        return meetings
```

---

## Best Practices

1. **Use structured data** — Pass key-value pairs, not formatted strings
   ```python
   # Good
   logger.info("Found items", count=15, source="civicclerk")
   
   # Avoid
   logger.info(f"Found 15 items from civicclerk")
   ```

2. **Include context** — Add relevant IDs and metadata
   ```python
   logger.info("Processing", event_id=event.event_id, event_type=event.event_type.value)
   ```

3. **Use appropriate levels**
   - `DEBUG` — Detailed diagnostic info
   - `INFO` — Normal operations, milestones
   - `WARNING` — Unexpected but handled situations
   - `ERROR` — Failures that need attention

4. **Time expensive operations**
   ```python
   @log_timing("expensive_operation")
   def expensive_operation():
       ...
   ```

5. **Correlate with run_id** — Bind at pipeline start
   ```python
   bind_run_context(run_id=run_id, source_id=source_id)
   ```

---

## Troubleshooting

### Logs Not Appearing in File

1. Check `LOG_FILE_ENABLED` is `true`
2. Check `logs/` directory exists and is writable
3. Verify `configure_logging()` was called

### Console Colors Not Working

- Windows: Use Windows Terminal or set `TERM=xterm-256color`
- Set `LOG_FORMAT=json` if colors cause issues

### Log File Too Large

- Reduce `LOG_RETENTION_DAYS`
- Reduce `LOG_MAX_BYTES`
- Increase `LOG_LEVEL` to reduce volume

---

*Last updated: February 2, 2026*
