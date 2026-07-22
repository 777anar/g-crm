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


# Priority (Phase 1: Stone Fabrication Workflow) -- a simple, universally
# understood shop-floor triage vocabulary, not a numeric weight, so it reads
# the same on a Kanban card as it does in conversation with an operator.
PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_URGENT = "urgent"
VALID_PRIORITIES = {PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_URGENT}
DEFAULT_PRIORITY = PRIORITY_NORMAL

# Default configurable production stages, seeded per company the first time
# that company's stage list is requested and none exist yet. A company can
# rename, hide, add, or reorder these afterward -- this list is only ever a
# starting point, the same "starter vocabulary, not a hard enum" rule
# Catalog already uses for SUGGESTED_MATERIAL_TYPES/SUGGESTED_BRANDS.
DEFAULT_PRODUCTION_STAGES = [
    "Measuring",
    "Design",
    "CNC",
    "Waterjet",
    "Cutting",
    "Polishing",
    "Quality Control",
    "Ready for Installation",
]

# Work Order timeline/audit event types (Phase 1). One row per change,
# powering both the "complete production timeline" requirement and a
# production-specific audit trail richer than the generic core audit log
# (which every write in every module already records via `record_audit`).
WORK_ORDER_EVENT_CREATED = "created"
WORK_ORDER_EVENT_STATUS_CHANGED = "status_changed"
WORK_ORDER_EVENT_STAGE_CHANGED = "stage_changed"
WORK_ORDER_EVENT_PRIORITY_CHANGED = "priority_changed"
WORK_ORDER_EVENT_OPERATOR_ASSIGNED = "operator_assigned"
