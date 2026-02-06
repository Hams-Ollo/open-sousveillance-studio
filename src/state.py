"""
Redis-backed state store for run tracking and approval management.

Replaces in-memory dicts with Redis for persistence across restarts
and compatibility with multiple Celery workers.

Falls back to in-memory storage if Redis is unavailable.
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional

import redis

logger = logging.getLogger(__name__)

# TTL for completed/failed runs (24 hours)
RUN_TTL_SECONDS = 86400
# TTL for pending approvals (7 days)
APPROVAL_TTL_SECONDS = 604800

# Redis key prefixes
_RUN_PREFIX = "oss:run:"
_APPROVAL_PREFIX = "oss:approval:"


def _serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _deserialize_datetimes(d: dict) -> dict:
    """Convert ISO datetime strings back to datetime objects."""
    for key in ("started_at", "completed_at", "created_at", "expires_at", "decision_at"):
        if key in d and d[key] is not None:
            try:
                d[key] = datetime.fromisoformat(d[key])
            except (ValueError, TypeError):
                pass
    return d


class RedisStateStore:
    """Redis-backed state store with in-memory fallback."""

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        self._client: Optional[redis.Redis] = None
        self._connected = False

        # In-memory fallback
        self._mem_runs: dict[str, dict] = {}
        self._mem_approvals: dict[str, dict] = {}

        self._connect()

    def _connect(self):
        """Attempt to connect to Redis."""
        try:
            self._client = redis.from_url(self._redis_url, decode_responses=True)
            self._client.ping()
            self._connected = True
            logger.info("Redis state store connected: %s", self._redis_url)
        except (redis.ConnectionError, redis.RedisError) as e:
            logger.warning("Redis unavailable, using in-memory fallback: %s", e)
            self._connected = False
            self._client = None

    @property
    def is_redis(self) -> bool:
        """Whether we're using Redis or in-memory fallback."""
        return self._connected

    # =========================================================================
    # Run State
    # =========================================================================

    def save_run(self, run_id: str, data: dict, ttl: Optional[int] = None):
        """Save or update a run status."""
        if self._connected and self._client:
            key = f"{_RUN_PREFIX}{run_id}"
            payload = json.dumps(data, default=_serialize_datetime)
            if ttl:
                self._client.setex(key, ttl, payload)
            else:
                self._client.set(key, payload)
        else:
            self._mem_runs[run_id] = data

    def get_run(self, run_id: str) -> Optional[dict]:
        """Get a run status by ID."""
        if self._connected and self._client:
            key = f"{_RUN_PREFIX}{run_id}"
            raw = self._client.get(key)
            if raw:
                return _deserialize_datetimes(json.loads(raw))
            return None
        else:
            return self._mem_runs.get(run_id)

    def update_run(self, run_id: str, **fields):
        """Update specific fields on an existing run."""
        data = self.get_run(run_id)
        if data is None:
            return
        data.update(fields)
        # Set TTL when run is terminal
        ttl = RUN_TTL_SECONDS if data.get("status") in ("completed", "failed") else None
        self.save_run(run_id, data, ttl=ttl)

    def list_runs(self, limit: int = 10) -> list[dict]:
        """List recent runs, sorted by started_at descending."""
        if self._connected and self._client:
            keys = self._client.keys(f"{_RUN_PREFIX}*")
            runs = []
            for key in keys:
                raw = self._client.get(key)
                if raw:
                    runs.append(_deserialize_datetimes(json.loads(raw)))
            runs.sort(key=lambda r: r.get("started_at") or "", reverse=True)
            return runs[:limit]
        else:
            runs = sorted(
                self._mem_runs.values(),
                key=lambda r: r.get("started_at") or "",
                reverse=True,
            )
            return runs[:limit]

    # =========================================================================
    # Approval State
    # =========================================================================

    def save_approval(self, approval_id: str, data: dict):
        """Save a pending approval item."""
        if self._connected and self._client:
            key = f"{_APPROVAL_PREFIX}{approval_id}"
            payload = json.dumps(data, default=_serialize_datetime)
            self._client.setex(key, APPROVAL_TTL_SECONDS, payload)
        else:
            self._mem_approvals[approval_id] = data

    def get_approval(self, approval_id: str) -> Optional[dict]:
        """Get an approval item by ID."""
        if self._connected and self._client:
            key = f"{_APPROVAL_PREFIX}{approval_id}"
            raw = self._client.get(key)
            if raw:
                return _deserialize_datetimes(json.loads(raw))
            return None
        else:
            return self._mem_approvals.get(approval_id)

    def remove_approval(self, approval_id: str) -> Optional[dict]:
        """Remove and return an approval item (pop)."""
        data = self.get_approval(approval_id)
        if data is None:
            return None
        if self._connected and self._client:
            self._client.delete(f"{_APPROVAL_PREFIX}{approval_id}")
        else:
            self._mem_approvals.pop(approval_id, None)
        return data

    def list_approvals(self) -> list[dict]:
        """List all pending approval items."""
        if self._connected and self._client:
            keys = self._client.keys(f"{_APPROVAL_PREFIX}*")
            approvals = []
            for key in keys:
                raw = self._client.get(key)
                if raw:
                    approvals.append(_deserialize_datetimes(json.loads(raw)))
            return approvals
        else:
            return list(self._mem_approvals.values())


# Module-level singleton
import threading

_state_store: Optional[RedisStateStore] = None
_state_lock = threading.Lock()


def get_state_store() -> RedisStateStore:
    """Get or create the global state store singleton."""
    global _state_store
    if _state_store is None:
        with _state_lock:
            if _state_store is None:
                _state_store = RedisStateStore()
    return _state_store
