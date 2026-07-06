class AIDomainError(Exception):
    pass


class UnknownAIProviderError(AIDomainError):
    """Raised when a caller asks for a provider name that isn't registered."""


class RecommendationAlreadyReviewedError(AIDomainError):
    """Raised when trying to accept/reject/edit a recommendation that has
    already left the `pending` state -- a review decision is final."""


class InvalidReviewDecisionError(AIDomainError):
    """Raised when a review decision isn't one of accept/reject/edit."""
