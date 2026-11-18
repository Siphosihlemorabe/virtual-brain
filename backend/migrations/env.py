"""How Alembic connects and runs migrations. Each migration runs in its own transaction (rule P7)."""

from alembic import context
from sqlalchemy import create_engine

import vb.accounts.models  # noqa: F401  (registers the tables on Base.metadata)
import vb.core.jobs.models  # noqa: F401
import vb.llm.models  # noqa: F401
from vb.core.config import get_settings
from vb.core.db import Base

config = context.config
# Tests pass their own URL in the Alembic config; otherwise use the app settings.
url = config.get_main_option("sqlalchemy.url") or get_settings().database_url

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, transaction_per_migration=True)
    context.run_migrations()
engine.dispose()
