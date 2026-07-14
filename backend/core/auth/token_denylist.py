"""Refresh-token revocation ("logout everywhere") via a per-user generation
counter.

Every refresh token is stamped with the `gen` claim its user was on at
issue time (see `create_refresh_token`). Logging out bumps that user's
generation; `refresh_access_token` rejects any refresh token stamped with
an older generation. A monotonic integer counter -- rather than a
wall-clock revocation timestamp compared against the token's issue time --
sidesteps a same-second race: JWT `iat`/timestamps only have second
granularity, so a token issued immediately after a logout (e.g. by a fresh
re-login) could land in the same wall-clock second as the logout and be
misclassified as revoked under a timestamp-cutoff scheme. A generation
counter has no such ambiguity: a token is either stamped with the current
generation (valid) or a stale one (rejected), full stop.

Backed by Redis when reachable -- required for the counter to survive a
process restart or apply across multiple app instances, which is the
actual "logout everywhere" guarantee. Falls back to a single-process
in-memory store (same tradeoff core/rbac/rate_limit.py already makes) if
Redis is unreachable, e.g. local development without a Redis server
running, so the login/refresh flow is never blocked by Redis being down
-- revocation degrades to "this process, until restart" rather than
silently doing nothing.
"""
import logging
from threading import Lock
from typing import Dict, Protocol

import redis

from core.config import settings

logger = logging.getLogger(__name__)


class TokenDenylist(Protocol):
    def current_generation(self, user_id: str) -> int: ...
    def revoke_all(self, user_id: str) -> None: ...
    def is_revoked(self, user_id: str, token_generation: int) -> bool: ...


class InMemoryTokenDenylist:
    def __init__(self) -> None:
        self._generation: Dict[str, int] = {}
        self._lock = Lock()

    def current_generation(self, user_id: str) -> int:
        with self._lock:
            return self._generation.get(user_id, 0)

    def revoke_all(self, user_id: str) -> None:
        with self._lock:
            self._generation[user_id] = self._generation.get(user_id, 0) + 1

    def is_revoked(self, user_id: str, token_generation: int) -> bool:
        with self._lock:
            current = self._generation.get(user_id, 0)
        return token_generation < current

    def reset(self) -> None:
        """Clears all tracked generations. Used by tests to isolate cases
        that exercise logout/refresh revocation from each other within one
        process, mirroring rate_limit.py's FixedWindowRateLimiter.reset()."""
        with self._lock:
            self._generation.clear()


class RedisTokenDenylist:
    """One key per user (`auth:token_generation:{user_id}`), TTL'd to the
    refresh-token lifetime on every bump so a stale counter never needs
    manual cleanup -- once that much time has passed, no refresh token
    issued against an older generation could still be unexpired anyway."""

    def __init__(self, client: "redis.Redis") -> None:
        self._client = client

    def _key(self, user_id: str) -> str:
        return f"auth:token_generation:{user_id}"

    def current_generation(self, user_id: str) -> int:
        value = self._client.get(self._key(user_id))
        return int(value) if value is not None else 0

    def revoke_all(self, user_id: str) -> None:
        key = self._key(user_id)
        self._client.incr(key)
        self._client.expire(key, settings.refresh_token_expire_days * 24 * 60 * 60)

    def is_revoked(self, user_id: str, token_generation: int) -> bool:
        return token_generation < self.current_generation(user_id)


def _create_token_denylist() -> TokenDenylist:
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        logger.info("Refresh-token denylist backed by Redis at %s", settings.redis_url)
        return RedisTokenDenylist(client)
    except Exception:
        logger.warning(
            "Redis unreachable at %s -- refresh-token revocation falling back to a "
            "single-process in-memory store (won't survive a restart or span multiple "
            "app instances until Redis is reachable).",
            settings.redis_url,
        )
        return InMemoryTokenDenylist()


token_denylist: TokenDenylist = _create_token_denylist()
