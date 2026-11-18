"""Index job by (status, created_at): finding the oldest queued job.

Revision: 0004 (after 0003)
Rules: one table change per migration; never drop or rename a column (docs/design/database.md §2).
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_job_status_created_at", "job", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_job_status_created_at", table_name="job")
