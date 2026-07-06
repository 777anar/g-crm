COMMUNICATION_PERMISSIONS = [
    "communication:channels:read",
    "communication:channels:write",
    "communication:conversations:read",
    "communication:conversations:write",
    "communication:notes:read",
    "communication:notes:write",
    "communication:templates:read",
    "communication:templates:write",
    # Real integrations (Version 2.9). Credential configuration is
    # "settings:read"/"settings:write" specifically so the generic RBAC
    # action-suffix convention (core/rbac/permissions.py) maps it to
    # manager-tier read / owner-tier write automatically -- only an owner
    # can ever set or change a real provider's secrets. Queue/log
    # visibility and retry-triggering don't touch secrets, so they use the
    # normal read (viewer) / write (rep) tiers.
    "communication:channels:settings:read",
    "communication:channels:settings:write",
    "communication:integrations:read",
    "communication:integrations:write",
]
