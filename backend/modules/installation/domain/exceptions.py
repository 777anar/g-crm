class InvalidJobTransitionError(ValueError):
    """Raised when an installation job status change doesn't follow the transition graph."""


class JobAlreadyExistsError(ValueError):
    """Raised when creating an installation job for an Order that already has one."""


class OrderNotReadyForInstallationError(ValueError):
    """Raised when creating an installation job for an Order that hasn't reached ready/delivered."""


class CrewInactiveError(ValueError):
    """Raised when assigning an inactive crew to a job."""
