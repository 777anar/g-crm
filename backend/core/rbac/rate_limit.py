"""Minimal in-process fixed-window rate limiter.

Phase-appropriate implementation: no new dependency, scoped to a single
process. Sufficient for the current single-instance deployment; a
multi-instance deployment would need to move the counter store to Redis
(already part of the stack) instead of the in-memory dict below -- the
public interface (`check`) would not need to change.
"""
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

from core.api.errors import RateLimitedError


class FixedWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counts: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._lock = Lock()

    def check(self, key: str) -> None:
        """Raises RateLimitedError if `key` has exceeded the limit for the
        current window; otherwise records the attempt."""
        now = time.monotonic()
        with self._lock:
            count, window_start = self._counts[key]
            if now - window_start >= self.window_seconds:
                count, window_start = 0, now
            count += 1
            self._counts[key] = (count, window_start)
            if count > self.max_requests:
                raise RateLimitedError(
                    f"Too many requests. Try again in {int(self.window_seconds - (now - window_start))} seconds."
                )

    def reset(self) -> None:
        """Clears all tracked counters. Used by tests to isolate cases that
        exercise the limited endpoint from each other within one process."""
        with self._lock:
            self._counts.clear()


login_rate_limiter = FixedWindowRateLimiter(max_requests=10, window_seconds=60)
