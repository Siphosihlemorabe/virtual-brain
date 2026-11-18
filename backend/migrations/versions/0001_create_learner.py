"""Create the learner table.

Revision: 0001 (first migration)
Rules: one table change per migration; never drop or rename a column (docs/design/database.md §2).
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learner",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_learner"),
        sa.UniqueConstraint("email", name="uq_learner_email"),
    )


def downgrade() -> None:
    op.drop_table("learner")
