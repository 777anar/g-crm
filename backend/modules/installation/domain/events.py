"""Domain events published by the Installation module."""

CREW_CREATED = "CrewCreated"
JOB_CREATED = "InstallationJobCreated"
JOB_SCHEDULED = "InstallationJobScheduled"
JOB_STATUS_CHANGED = "InstallationJobStatusChanged"
JOB_COMPLETED = "InstallationJobCompleted"
JOB_CANCELLED = "InstallationJobCancelled"

# E-signature integration (Phase 22)
JOB_SIGNATURE_REQUESTED = "InstallationJobSignatureRequested"
JOB_SIGNATURE_COMPLETED = "InstallationJobSignatureCompleted"
