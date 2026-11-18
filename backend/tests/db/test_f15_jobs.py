"""F15: every job writes its log to the database, and a restart mid-job loses nothing."""

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from vb.core.db import utcnow
from vb.core.jobs import repository
from vb.core.jobs.runner import Handler, Log, run_job, run_pending


def echo(payload: dict[str, Any], log: Log) -> None:
    log("Planner", "info", f"got {payload['word']}")


def broken(payload: dict[str, Any], log: Log) -> None:
    log("Tutor", "info", "starting")
    raise ValueError("model reply was not JSON")


HANDLERS: dict[str, Handler] = {"echo": echo, "broken": broken}


def test_f15_job_runs_and_its_log_is_stored(session: Session) -> None:
    job = repository.enqueue(session, "echo", {"word": "hello"})
    assert run_pending(session, HANDLERS) == 1
    done = repository.get_job(session, job.id)
    assert done is not None and done.status == "done" and done.attempts == 1 and done.finished_at is not None
    assert [(line.agent, line.message) for line in repository.logs_for(session, job.id)] == [("Planner", "got hello")]


def test_f15_a_failing_job_is_retried_then_marked_failed_with_its_error(session: Session) -> None:
    job = repository.enqueue(session, "broken", {})
    run_pending(session, HANDLERS)  # tries MAX_ATTEMPTS times, re-queued between tries
    failed = repository.get_job(session, job.id)
    assert failed is not None and failed.status == "failed"
    assert failed.attempts == repository.MAX_ATTEMPTS
    assert failed.error == "ValueError: model reply was not JSON"
    # The log written before the crash is kept, plus the error line.
    kinds = [line.kind for line in repository.logs_for(session, job.id)]
    assert kinds.count("error") == repository.MAX_ATTEMPTS and "info" in kinds


def test_f15_a_job_left_running_by_a_crash_is_recovered_and_finished(session: Session) -> None:
    job = repository.enqueue(session, "echo", {"word": "again"})
    assert repository.claim(session, job.id)  # a worker claimed it, then the process died
    session.commit()
    # Later, a new worker treats anything running since before "now + 1 minute" as crashed.
    assert repository.requeue_stale(session, started_before=utcnow() + timedelta(minutes=1)) == 1
    assert run_pending(session, HANDLERS) == 1
    recovered = repository.get_job(session, job.id)
    assert recovered is not None and recovered.status == "done" and recovered.attempts == 2


def test_only_one_runner_can_claim_a_job(session: Session) -> None:
    job = repository.enqueue(session, "echo", {"word": "x"})
    assert repository.claim(session, job.id) is True
    assert repository.claim(session, job.id) is False
    assert run_job(session, job.id, HANDLERS) is False  # already running: not claimed again


def test_unknown_job_kind_fails_with_a_clear_error(session: Session) -> None:
    job = repository.enqueue(session, "no_such_kind", {})
    run_pending(session, HANDLERS)
    result = repository.get_job(session, job.id)
    assert result is not None and result.status == "failed"
    assert result.error is not None and "no handler registered" in result.error
