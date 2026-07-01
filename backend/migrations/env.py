from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from core.config import settings
from core.db.base import Base

# Import every core model module so Base.metadata is fully populated before
# autogenerate/upgrade runs. Module-owned tables are imported the same way
# from each module's own migrations/env hook once modules are installed.
from core.companies import models as companies_models  # noqa: F401
from core.auth import models as auth_models  # noqa: F401
from core.audit import models as audit_models  # noqa: F401
from core.events import models as events_models  # noqa: F401
from core.storage import models as storage_models  # noqa: F401

# Module-owned tables. Each installed module's infrastructure models are
# imported here so `alembic revision --autogenerate` sees them; per the
# frozen architecture each module conceptually owns its own migration
# history even though they run through this one unified Alembic chain.
from modules.crm.infrastructure import models as crm_models  # noqa: F401
from modules.catalog.infrastructure import models as catalog_models  # noqa: F401
from modules.sales.infrastructure import models as sales_models  # noqa: F401
from modules.orders.infrastructure import models as orders_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
