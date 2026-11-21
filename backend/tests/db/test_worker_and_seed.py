"""The worker loop runs queued jobs; seeding is safe to repeat."""

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

from vb.core.config import Settings
from vb.core.jobs import repository
from vb.core.jobs.runner import Handler, Log
from vb.core.jobs.worker import serve
from vb.seed import seed


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as conn:
        transaction = conn.begin()
        yield conn
        transaction.rollback()


def test_one_worker_cycle_runs_a_queued_job(connection: Connection) -> None:
    def greet(payload: dict[str, Any], log: Log) -> None:
        log("Planner", "info", f"hello {payload['name']}")

    handlers: dict[str, Handler] = {"greet": greet}

    def make_session() -> Session:
        return Session(bind=connection, join_transaction_mode="create_savepoint")

    with make_session() as session:
        job = repository.enqueue(session, "greet", {"name": "Sipho"})
        session.commit()

    serve(make_session, handlers, max_cycles=1, sleep=lambda seconds: None)

    with make_session() as session:
        done = repository.get_job(session, job.id)
        assert done is not None and done.status == "done"
        assert [line.message for line in repository.logs_for(session, job.id)] == ["hello Sipho"]


def test_seeding_twice_gives_exactly_one_dev_learner(session: Session) -> None:
    settings = Settings(dev_learner_email="seed-test@localhost")
    first, second = seed(session, settings), seed(session, settings)
    assert first == second  # same learner, same id: nothing duplicated
