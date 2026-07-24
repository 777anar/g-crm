class AIDomainError(Exception):
    pass


class UnknownAIProviderError(AIDomainError):
    """Raised when a caller asks for a provider name that isn't registered."""


class RecommendationAlreadyReviewedError(AIDomainError):
    """Raised when trying to accept/reject/edit a recommendation that has
    already left the `pending` state -- a review decision is final."""


class InvalidReviewDecisionError(AIDomainError):
    """Raised when a review decision isn't one of accept/reject/edit."""


class AIProviderNotConfiguredError(AIDomainError):
    """Raised when a real provider is selected (explicitly or via the
    company/deployment default) but lacks the configuration it needs to run
    (e.g. no API key set) -- deliberately not a boot-time guard like the JWT/
    encryption secrets in core.bootstrap.app_factory, since a real AI
    provider is genuinely optional per deployment (Phase 21)."""


class AIProviderUpstreamError(AIDomainError):
    """Raised when a real provider's call to its upstream API fails --
    network failure, authentication rejected by the upstream API itself,
    upstream rate limiting, or a response that couldn't be parsed as the
    expected structured JSON."""


class AIRateLimitedError(AIDomainError):
    """Raised when a company has made too many AI analysis calls within the
    current rate-limit window (Phase 21 cost control)."""


class AIBudgetExceededError(AIDomainError):
    """Raised when a company's configured daily AI spend cap
    (`Settings.ai_daily_budget_usd`) has already been reached for today
    (Phase 21 cost control)."""
