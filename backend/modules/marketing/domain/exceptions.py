class InvalidCampaignTransitionError(ValueError):
    """Raised when a campaign status change doesn't follow the transition graph."""


class CampaignImmutableError(ValueError):
    """Raised when trying to edit a cancelled or completed campaign's core details."""
