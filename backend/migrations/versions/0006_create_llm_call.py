"""Create the llm_call table.

Revision: 0006 (after 0005)
Rules: one table change per migration; never drop or rename a column (docs/design/database.md §2).
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_call",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_id", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_llm_call"),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], name="fk_llm_call_job_id_job"),
    )


def downgrade() -> None:
    op.drop_table("llm_call")
