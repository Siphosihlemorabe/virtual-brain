"""Tables owned by the accounts module (docs/design/database.md §3.1)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from vb.core.db import Entity


class LearnerRecord(Entity):
    __tablename__ = "learner"

    email: Mapped[str | None] = mapped_column(String(320), unique=True)  # null until login exists (stage 3)
    display_name: Mapped[str | None] = mapped_column(String(200))
