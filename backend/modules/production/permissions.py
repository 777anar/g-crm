PRODUCTION_PERMISSIONS = [
    "production:read",
    "production:write",
    # Phase 19 (Stone Fabrication Workflow, Phase 3): finer-grained than the
    # coarse "production:write" every Phase 1/2 endpoint originally shared.
    # Each still falls back to the same rep-tier default via
    # core/rbac/permissions.py's action-suffix convention (the last segment
    # is still "write"), so this is additive -- existing roles see no
    # behavior change until a company explicitly grants/restricts one of
    # these individually via a user's `module_permissions` override, e.g.
    # letting a rep reassign operators without also letting them re-prioritize.
    "production:priority:write",
    "production:operator:write",
    "production:stage:write",
]
