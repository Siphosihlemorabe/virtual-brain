"""${message}

Revision: ${up_revision} (after ${down_revision | comma,n})
Rules: one table change per migration; never drop or rename a column (docs/design/database.md §2).
"""

import sqlalchemy as sa
from alembic import op

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
