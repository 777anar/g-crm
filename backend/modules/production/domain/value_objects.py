"""Pure value objects for the Production module. No framework or DB imports."""

WORK_ORDER_STATUS_QUEUED = "queued"
WORK_ORDER_STATUS_CUTTING = "cutting"
WORK_ORDER_STATUS_POLISHING = "polishing"
WORK_ORDER_STATUS_QUALITY_CHECK = "quality_check"
WORK_ORDER_STATUS_COMPLETED = "completed"
WORK_ORDER_STATUS_CANCELLED = "cancelled"

VALID_WORK_ORDER_STATUSES = {
    WORK_ORDER_STATUS_QUEUED,
    WORK_ORDER_STATUS_CUTTING,
    WORK_ORDER_STATUS_POLISHING,
    WORK_ORDER_STATUS_QUALITY_CHECK,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_CANCELLED,
}

TERMINAL_WORK_ORDER_STATUSES = {WORK_ORDER_STATUS_COMPLETED, WORK_ORDER_STATUS_CANCELLED}

# A cutting/polishing shop-floor job: queued -> cutting -> polishing ->
# quality_check -> completed, with cancellation reachable from any
# non-terminal stage (a job can be scrapped at any point before it ships).
_VALID_WORK_ORDER_TRANSITIONS = {
    WORK_ORDER_STATUS_QUEUED: {WORK_ORDER_STATUS_CUTTING, WORK_ORDER_STATUS_CANCELLED},
    WORK_ORDER_STATUS_CUTTING: {WORK_ORDER_STATUS_POLISHING, WORK_ORDER_STATUS_CANCELLED},
    WORK_ORDER_STATUS_POLISHING: {WORK_ORDER_STATUS_QUALITY_CHECK, WORK_ORDER_STATUS_CANCELLED},
    WORK_ORDER_STATUS_QUALITY_CHECK: {WORK_ORDER_STATUS_COMPLETED, WORK_ORDER_STATUS_CANCELLED},
    WORK_ORDER_STATUS_COMPLETED: set(),
    WORK_ORDER_STATUS_CANCELLED: set(),
}


def is_valid_work_order_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_WORK_ORDER_TRANSITIONS.get(current, set())
