class InvalidJobTransitionError(ValueError):
    """Raised when an installation job status change doesn't follow the transition graph."""


class JobAlreadyExistsError(ValueError):
    """Raised when creating an installation job for an Order that already has one."""


class OrderNotReadyForInstallationError(ValueError):
    """Raised when creating an installation job for an Order that hasn't reached ready/delivered."""


class CrewInactiveError(ValueError):
    """Raised when assigning an inactive crew to a job."""


class SignatureAttributionError(ValueError):
    """Raised when a webhook-originated signature completion can't be
    attributed to an audit actor because the job has no created_by --
    mirrors Communication's identical guard for channel webhooks with no
    configuring user."""
