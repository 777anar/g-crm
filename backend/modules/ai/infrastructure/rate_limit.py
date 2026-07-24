"""Per-company AI analysis rate limit (Phase 21 cost control) -- reuses the
same in-process `FixedWindowRateLimiter` the login endpoint already uses
(`core/rbac/rate_limit.py`), keyed by company rather than by IP, so a
scripting error or an abusive loop against any of the four analysis
endpoints can't run away regardless of which provider (mock or real) is
configured."""
from core.rbac.rate_limit import FixedWindowRateLimiter

ai_analysis_rate_limiter = FixedWindowRateLimiter(max_requests=20, window_seconds=60)
