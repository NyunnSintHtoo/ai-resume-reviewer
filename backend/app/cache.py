"""Response cache.

Backed by Redis when REDIS_URL is set (see docker-compose.yml); otherwise an
in-process TTL cache so the app runs with zero infrastructure. The cache key
is a SHA-256 over (resume text, job description, provider) so identical
submissions return instantly without re-running the review pipeline.
"""

from __future__ import annotations

import hashlib
import json
import time
from threading import Lock
from typing import Any, Protocol

from .config import get_settings


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl: int) -> None: ...


class InMemoryCache:
    """Thread-safe in-process TTL cache (fallback when Redis is absent)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class RedisCache:
    def __init__(self, url: str) -> None:
        import redis  # imported lazily so the package is optional at runtime

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Any | None:
        raw = self._client.get(key)
        return json.loads(raw) if raw else None

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._client.setex(key, ttl, json.dumps(value))


_cache: CacheBackend | None = None


def get_cache() -> CacheBackend:
    global _cache
    if _cache is None:
        settings = get_settings()
        if settings.redis_url:
            try:
                _cache = RedisCache(settings.redis_url)
            except Exception:
                _cache = InMemoryCache()
        else:
            _cache = InMemoryCache()
    return _cache


def review_cache_key(resume_text: str, job_description: str | None, provider: str) -> str:
    payload = json.dumps(
        {"resume": resume_text.strip(), "jd": (job_description or "").strip(), "provider": provider},
        sort_keys=True,
    )
    return "review:" + hashlib.sha256(payload.encode()).hexdigest()
