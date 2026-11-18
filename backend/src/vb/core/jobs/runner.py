"""Runs jobs: claim, call the handler, record the result. Commits after every step so progress survives a crash."""

import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from vb.core.db import utcnow
from vb.core.jobs import repository

# A handler gets the job's payload and a log function: log(agent, kind, message).
Log = Callable[[str, str, str], None]
Handler = Callable[[dict[str, Any], Log], None]

STALE_AFTER = timedelta(minutes=30)  # a 'running' job older than this is assumed crashed


def run_job(session: Session, job_id: uuid.UUID, handlers: dict[str, Handler]) -> bool:
    """Run one job. Returns False if it could not be claimed (already taken or not queued)."""
    if not repository.claim(session, job_id):
        session.rollback()
        return False
    session.commit()

    job = repository.get_job(session, job_id)
    assert job is not None

    def log(agent: str, kind: str, message: str) -> None:
        repository.add_log(session, job_id, agent, kind, message)
        session.commit()  # visible straight away, and kept even if the handler crashes later

    handler = handlers.get(job.kind)
    try:
        if handler is None:
            raise LookupError(f"no handler registered for job kind {job.kind!r}")
        handler(job.payload, log)
    except Exception as e:  # any failure is recorded on the job, never lost
        session.rollback()
        log("Orchestrator", "error", f"{type(e).__name__}: {e}")
        repository.fail(session, job_id, f"{type(e).__name__}: {e}")
        session.commit()
        return True

    repository.finish(session, job_id)
    session.commit()
    return True


def run_pending(session: Session, handlers: dict[str, Handler], max_jobs: int = 100) -> int:
    """Local development loop: recover crashed jobs, then run queued jobs oldest first. Returns how many ran."""
    repository.requeue_stale(session, utcnow() - STALE_AFTER)
    session.commit()
    ran = 0
    while ran < max_jobs and (job_id := repository.next_queued_id(session)) is not None:
        if run_job(session, job_id, handlers):
            ran += 1
    return ran
