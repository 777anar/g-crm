"""Guards against SQLAlchemy metadata-level schema warnings that don't show
up as pytest failures on their own -- specifically the "unresolvable cycles
between tables" SAWarning that `crm_customers.primary_contact_id` <->
`crm_contacts.customer_id` used to trigger (PROJECT_AUDIT.md B5) before
`primary_contact_id`'s ForeignKey was marked `use_alter=True`. Import every
installed module's models package (same set tests/conftest.py imports for
`Base.metadata.create_all()`) so this test fails loudly if a future model
change reintroduces an unresolvable FK cycle anywhere in the schema.
"""
import warnings

from core.db.base import Base

# Importing these registers every table on Base.metadata -- mirrors
# tests/conftest.py's import list exactly.
from core.companies import models as _companies_models  # noqa: F401
from core.auth import models as _auth_models  # noqa: F401
from core.audit import models as _audit_models  # noqa: F401
from core.events import models as _events_models  # noqa: F401
from core.storage import models as _storage_models  # noqa: F401
from modules.crm.infrastructure import models as _crm_models  # noqa: F401
from modules.catalog.infrastructure import models as _catalog_models  # noqa: F401
from modules.sales.infrastructure import models as _sales_models  # noqa: F401
from modules.orders.infrastructure import models as _orders_models  # noqa: F401
from modules.production.infrastructure import models as _production_models  # noqa: F401
from modules.installation.infrastructure import models as _installation_models  # noqa: F401
from modules.finance.infrastructure import models as _finance_models  # noqa: F401
from modules.communication.infrastructure import models as _communication_models  # noqa: F401
from modules.ai.infrastructure import models as _ai_models  # noqa: F401
from modules.purchasing.infrastructure import models as _purchasing_models  # noqa: F401
from modules.marketing.infrastructure import models as _marketing_models  # noqa: F401
from modules.customer_portal.infrastructure import models as _customer_portal_models  # noqa: F401
from modules.cut_optimization.infrastructure import models as _cut_optimization_models  # noqa: F401


def test_metadata_table_sort_raises_no_circular_fk_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Base.metadata.sorted_tables
    cycle_warnings = [w for w in caught if "unresolvable cycles" in str(w.message)]
    assert cycle_warnings == [], (
        "Base.metadata.sorted_tables raised a circular-FK warning -- "
        f"{[str(w.message) for w in cycle_warnings]}"
    )


def test_crm_customers_primary_contact_fk_is_use_alter():
    """Pins down *how* the cycle is broken, not just that it is -- if a
    future change removes use_alter without an equivalent fix elsewhere,
    this fails with a clearer message than the generic warning check above.
    """
    from modules.crm.infrastructure.models.customer import Customer

    fk = next(iter(Customer.__table__.c.primary_contact_id.foreign_keys))
    assert fk.constraint.use_alter is True
    assert fk.constraint.name == "fk_crm_customers_primary_contact_id"
