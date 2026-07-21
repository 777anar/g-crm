from core.module_registry.contracts import ModuleManifest
from modules.customer_portal.navigation import CUSTOMER_PORTAL_NAVIGATION
from modules.customer_portal.permissions import CUSTOMER_PORTAL_PERMISSIONS
from modules.customer_portal.presentation.api.router import customer_portal_router_main  # noqa: F401
from modules.customer_portal.settings_schema import CUSTOMER_PORTAL_SETTINGS_SCHEMA

MODULE_MANIFEST = ModuleManifest(
    name="customer_portal",
    version="1.0.0",
    router=customer_portal_router_main,
    permissions=CUSTOMER_PORTAL_PERMISSIONS,
    # crm: CustomerLogin FK's to crm_customers.id, and /me looks up the
    # Customer row for a profile. sales/orders/finance/installation: the
    # customer-facing read endpoints query Order/Quote/Invoice/
    # InstallationJob directly (PortalQueryRepository), the same
    # "depends_on for read access" pattern Reports and Marketing use.
    depends_on=["crm", "sales", "orders", "finance", "installation"],
    navigation=CUSTOMER_PORTAL_NAVIGATION,
    settings_schema=CUSTOMER_PORTAL_SETTINGS_SCHEMA,
    jobs=[],
    event_subscriptions={},
    models_package="modules.customer_portal.infrastructure.models",
    migrations_path="modules/customer_portal/infrastructure/migrations",
)
