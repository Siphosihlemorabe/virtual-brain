"""Index job_log by (job_id, created_at): showing a job's progress in order.

Revision: 0005 (after 0004)
Rules: one table change per migration; never drop or rename a column (docs/design/database.md §2).
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_job_log_job_id_created_at", "job_log", ["job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_job_log_job_id_created_at", table_name="job_log")
