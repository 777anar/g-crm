from core.rbac.permissions import role_has_permission


def test_viewer_can_read_but_not_write():
    assert role_has_permission(role="viewer", permission="crm:deals:read") is True
    assert role_has_permission(role="viewer", permission="crm:deals:write") is False


def test_rep_can_write_but_not_approve():
    assert role_has_permission(role="rep", permission="sales:orders:write") is True
    assert role_has_permission(role="rep", permission="sales:orders:approve") is False


def test_manager_can_approve_but_not_change_settings():
    assert role_has_permission(role="manager", permission="sales:orders:approve") is True
    assert role_has_permission(role="manager", permission="crm:settings:write") is False


def test_owner_can_do_everything():
    assert role_has_permission(role="owner", permission="crm:settings:write") is True


def test_module_permission_override_grants_extra_access():
    assert role_has_permission(role="viewer", permission="finance:invoices:write") is False
    assert (
        role_has_permission(
            role="viewer",
            permission="finance:invoices:write",
            module_permission_overrides={"finance": ["finance:invoices:write"]},
        )
        is True
    )


def test_no_role_has_no_permission():
    assert role_has_permission(role=None, permission="crm:deals:read") is False
