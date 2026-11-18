"""Create the job_log table.

Revision: 0003 (after 0002)
Rules: one table change per migration; never drop or rename a column (docs/design/database.md §2).
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("agent", sa.String(50), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_job_log"),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], name="fk_job_log_job_id_job"),
    )


def downgrade() -> None:
    op.drop_table("job_log")
