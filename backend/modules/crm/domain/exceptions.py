class CRMDomainError(Exception):
    pass


class CustomerAlreadyArchivedError(CRMDomainError):
    pass


class LeadAlreadyConvertedError(CRMDomainError):
    pass


class InvalidLeadSourceChannelError(CRMDomainError):
    pass


class InvalidTaskTransitionError(CRMDomainError):
    """Raised when a task status change doesn't follow the transition graph."""


class TaskImmutableError(CRMDomainError):
    """Raised when trying to edit a task that is done or cancelled."""


class InvalidRecurrenceError(CRMDomainError):
    """Raised when a recurring task is missing the fields needed to compute
    its next occurrence (a due date and a recurrence rule)."""
