"""Pure value objects for the Installation module. No framework or DB imports."""

# ── Installation Job lifecycle ────────────────────────────────────────────────

JOB_STATUS_SCHEDULED = "scheduled"
JOB_STATUS_EN_ROUTE = "en_route"
JOB_STATUS_IN_PROGRESS = "in_progress"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_CANCELLED = "cancelled"

VALID_JOB_STATUSES = {
    JOB_STATUS_SCHEDULED,
    JOB_STATUS_EN_ROUTE,
    JOB_STATUS_IN_PROGRESS,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_CANCELLED,
}

TERMINAL_JOB_STATUSES = {JOB_STATUS_COMPLETED, JOB_STATUS_CANCELLED}

# A crew's day: scheduled -> en_route -> in_progress -> completed, with
# cancellation reachable from any non-terminal stage (a job can fall through
# right up until it's marked done).
_VALID_JOB_TRANSITIONS = {
    JOB_STATUS_SCHEDULED: {JOB_STATUS_EN_ROUTE, JOB_STATUS_CANCELLED},
    JOB_STATUS_EN_ROUTE: {JOB_STATUS_IN_PROGRESS, JOB_STATUS_CANCELLED},
    JOB_STATUS_IN_PROGRESS: {JOB_STATUS_COMPLETED, JOB_STATUS_CANCELLED},
    JOB_STATUS_COMPLETED: set(),
    JOB_STATUS_CANCELLED: set(),
}


def is_valid_job_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_JOB_TRANSITIONS.get(current, set())


# ── Crew ───────────────────────────────────────────────────────────────────────

CREW_STATUS_ACTIVE = "active"
CREW_STATUS_INACTIVE = "inactive"
VALID_CREW_STATUSES = {CREW_STATUS_ACTIVE, CREW_STATUS_INACTIVE}
DEFAULT_CREW_STATUS = CREW_STATUS_ACTIVE

# ── Photo / signature attachments ──────────────────────────────────────────────

PHOTO_TYPE_BEFORE = "before"
PHOTO_TYPE_AFTER = "after"
PHOTO_TYPE_DAMAGE = "damage"
PHOTO_TYPE_SIGNATURE = "signature"
PHOTO_TYPE_OTHER = "other"
VALID_PHOTO_TYPES = {
    PHOTO_TYPE_BEFORE,
    PHOTO_TYPE_AFTER,
    PHOTO_TYPE_DAMAGE,
    PHOTO_TYPE_SIGNATURE,
    PHOTO_TYPE_OTHER,
}

# ── Notifications ──────────────────────────────────────────────────────────────

NOTIFICATION_TYPE_JOB_ASSIGNED = "job_assigned"
NOTIFICATION_TYPE_JOB_RESCHEDULED = "job_rescheduled"
NOTIFICATION_TYPE_JOB_STATUS_CHANGED = "job_status_changed"
VALID_NOTIFICATION_TYPES = {
    NOTIFICATION_TYPE_JOB_ASSIGNED,
    NOTIFICATION_TYPE_JOB_RESCHEDULED,
    NOTIFICATION_TYPE_JOB_STATUS_CHANGED,
}
