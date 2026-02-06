"""
LLM cost tracking and budget enforcement.

Tracks input/output tokens per model per call, applies model-specific pricing,
and enforces configurable daily budget caps with circuit breaker.
"""

import os
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# MODEL PRICING (per 1M tokens, USD)
# =============================================================================
# Source: https://ai.google.dev/pricing (as of 2026-02)

MODEL_PRICING = {
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.0-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "models/gemini-embedding-001": {"input": 0.00, "output": 0.00},
}

# Default pricing for unknown models
DEFAULT_PRICING = {"input": 2.00, "output": 10.00}

# Default daily budget in USD (0 = unlimited)
DEFAULT_DAILY_BUDGET = float(os.getenv("LLM_DAILY_BUDGET_USD", "0"))


@dataclass
class CallRecord:
    """Record of a single LLM call."""
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DailyStats:
    """Aggregated daily usage statistics."""
    date: date
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    calls_by_model: dict = field(default_factory=dict)


class CostTracker:
    """
    Tracks LLM token usage and costs with daily budget enforcement.

    Thread-safe for use with concurrent Celery workers.
    """

    def __init__(self, daily_budget_usd: float = DEFAULT_DAILY_BUDGET):
        self._daily_budget = daily_budget_usd
        self._lock = threading.Lock()
        self._today: Optional[DailyStats] = None
        self._history: list[CallRecord] = []

    def _get_today(self) -> DailyStats:
        """Get or create today's stats, resetting if day changed."""
        today = date.today()
        if self._today is None or self._today.date != today:
            self._today = DailyStats(date=today)
        return self._today

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a given token count."""
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def check_budget(self, model: str = "", estimated_tokens: int = 0) -> bool:
        """
        Check if we're within budget.

        Returns True if the call is allowed, False if budget exceeded.
        """
        if self._daily_budget <= 0:
            return True  # No budget limit

        with self._lock:
            stats = self._get_today()
            if stats.total_cost_usd >= self._daily_budget:
                logger.warning(
                    "Daily LLM budget exceeded: $%.4f / $%.2f",
                    stats.total_cost_usd, self._daily_budget
                )
                return False

            # Warn at 80% threshold
            if stats.total_cost_usd >= self._daily_budget * 0.8:
                logger.warning(
                    "LLM budget at %.0f%%: $%.4f / $%.2f",
                    (stats.total_cost_usd / self._daily_budget) * 100,
                    stats.total_cost_usd, self._daily_budget
                )

        return True

    def record_call(self, model: str, input_tokens: int, output_tokens: int) -> CallRecord:
        """Record a completed LLM call and update daily stats."""
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        record = CallRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost
        )

        with self._lock:
            stats = self._get_today()
            stats.total_calls += 1
            stats.total_input_tokens += input_tokens
            stats.total_output_tokens += output_tokens
            stats.total_cost_usd += cost

            # Track per-model stats
            if model not in stats.calls_by_model:
                stats.calls_by_model[model] = {
                    "calls": 0, "input_tokens": 0,
                    "output_tokens": 0, "cost_usd": 0.0
                }
            stats.calls_by_model[model]["calls"] += 1
            stats.calls_by_model[model]["input_tokens"] += input_tokens
            stats.calls_by_model[model]["output_tokens"] += output_tokens
            stats.calls_by_model[model]["cost_usd"] += cost

            self._history.append(record)

        logger.debug(
            "LLM call: %s | in=%d out=%d | $%.6f | daily=$%.4f",
            model, input_tokens, output_tokens, cost, stats.total_cost_usd
        )

        return record

    def get_daily_summary(self) -> dict:
        """Get today's usage summary."""
        with self._lock:
            stats = self._get_today()
            return {
                "date": stats.date.isoformat(),
                "total_calls": stats.total_calls,
                "total_input_tokens": stats.total_input_tokens,
                "total_output_tokens": stats.total_output_tokens,
                "total_cost_usd": round(stats.total_cost_usd, 6),
                "daily_budget_usd": self._daily_budget,
                "budget_remaining_usd": round(
                    max(0, self._daily_budget - stats.total_cost_usd), 6
                ) if self._daily_budget > 0 else None,
                "calls_by_model": dict(stats.calls_by_model),
            }

    @property
    def daily_budget(self) -> float:
        return self._daily_budget

    @daily_budget.setter
    def daily_budget(self, value: float):
        self._daily_budget = value


# =============================================================================
# SINGLETON
# =============================================================================

_cost_tracker: Optional[CostTracker] = None
_cost_lock = threading.Lock()


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker singleton."""
    global _cost_tracker
    if _cost_tracker is None:
        with _cost_lock:
            if _cost_tracker is None:
                _cost_tracker = CostTracker()
    return _cost_tracker


class BudgetExceededError(Exception):
    """Raised when the daily LLM budget has been exceeded."""
    pass
