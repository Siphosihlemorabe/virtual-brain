"""The only code that reads or writes the job tables (rule P2). Functions never commit; the runner does."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from vb.core.db import utcnow
from vb.core.jobs.models import JobLogRecord, JobRecord
from vb.core.jobs.schemas import Job, JobLogLine

MAX_ATTEMPTS = 3


def enqueue(session: Session, kind: str, payload: dict[str, Any]) -> Job:
    record = JobRecord(kind=kind, status="queued", payload=payload, attempts=0)
    session.add(record)
    session.flush()
    return Job.model_validate(record)


def get_job(session: Session, job_id: uuid.UUID) -> Job | None:
    record = session.get(JobRecord, job_id)
    return Job.model_validate(record) if record else None


def next_queued_id(session: Session) -> uuid.UUID | None:
    """The oldest queued job, or None."""
    stmt = select(JobRecord.id).where(JobRecord.status == "queued").order_by(JobRecord.created_at).limit(1)
    return session.scalars(stmt).first()


def claim(session: Session, job_id: uuid.UUID) -> bool:
    """Mark a queued job as running. Returns False if someone else claimed it first.

    The WHERE status = 'queued' makes this safe without database-specific locking (rule P6):
    if two runners race, only one UPDATE changes a row.
    """
    stmt = (
        update(JobRecord)
        .where(JobRecord.id == job_id, JobRecord.status == "queued")
        .values(status="running", started_at=utcnow(), attempts=JobRecord.attempts + 1)
    )
    result: CursorResult[Any] = session.execute(stmt)  # type: ignore[assignment]
    session.expire_all()  # make later reads see the new values
    return result.rowcount == 1


def finish(session: Session, job_id: uuid.UUID) -> None:
    session.execute(
        update(JobRecord).where(JobRecord.id == job_id).values(status="done", finished_at=utcnow(), error=None)
    )
    session.expire_all()


def fail(session: Session, job_id: uuid.UUID, error: str) -> None:
    """Back to the queue for another try, or failed for good after MAX_ATTEMPTS."""
    job = session.get(JobRecord, job_id)
    if job is None:
        return
    job.error = error
    if job.attempts >= MAX_ATTEMPTS:
        job.status, job.finished_at = "failed", utcnow()
    else:
        job.status = "queued"
    session.flush()


def requeue_stale(session: Session, started_before: datetime) -> int:
    """After a crash: jobs still 'running' that started before the cut-off go back to the queue."""
    stmt = (
        update(JobRecord)
        .where(JobRecord.status == "running", JobRecord.started_at < started_before)
        .values(status="queued")
    )
    result: CursorResult[Any] = session.execute(stmt)  # type: ignore[assignment]
    session.expire_all()
    return result.rowcount


def add_log(session: Session, job_id: uuid.UUID, agent: str, kind: str, message: str) -> None:
    session.add(JobLogRecord(job_id=job_id, agent=agent, kind=kind, message=message))
    session.flush()


def logs_for(session: Session, job_id: uuid.UUID) -> list[JobLogLine]:
    stmt = select(JobLogRecord).where(JobLogRecord.job_id == job_id).order_by(JobLogRecord.created_at)
    return [JobLogLine.model_validate(r) for r in session.scalars(stmt)]
