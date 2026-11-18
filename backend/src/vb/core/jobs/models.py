"""The job and job_log tables (docs/design/database.md §3.5)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vb.core.db import Entity


class JobRecord(Entity):
    __tablename__ = "job"
    __table_args__ = (Index("ix_job_status_created_at", "status", "created_at"),)

    kind: Mapped[str] = mapped_column(String(100))  # which handler runs it, e.g. "process_segment"
    status: Mapped[str] = mapped_column(String(20))  # queued | running | done | failed
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)  # the handler's inputs
    attempts: Mapped[int] = mapped_column(Integer)  # how many times it has been started
    error: Mapped[str | None] = mapped_column(Text)  # the last error, if any
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobLogRecord(Entity):
    __tablename__ = "job_log"
    __table_args__ = (Index("ix_job_log_job_id_created_at", "job_id", "created_at"),)

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job.id"))
    agent: Mapped[str] = mapped_column(String(50))  # Planner, Tutor, Reviewer, …
    kind: Mapped[str] = mapped_column(String(20))  # info | flag | fix | recheck | error
    message: Mapped[str] = mapped_column(Text)
