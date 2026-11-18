"""One unit of work per request: everything is saved together, or nothing is."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

from vb.accounts.repository import create_learner, get_learner
from vb.core.db import unit_of_work


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    """An outer transaction that is rolled back at the end, so these tests leave no data behind."""
    with engine.connect() as conn:
        transaction = conn.begin()
        yield conn
        transaction.rollback()


def make_session_on(conn: Connection) -> Session:
    # Each unit of work runs in a savepoint inside the outer transaction: commit and rollback behave as normal.
    return Session(bind=conn, join_transaction_mode="create_savepoint")


def test_changes_are_saved_when_the_block_finishes(connection: Connection) -> None:
    with unit_of_work(lambda: make_session_on(connection)) as session:
        learner = create_learner(session, email="saved@example.com")
    with unit_of_work(lambda: make_session_on(connection)) as session:
        assert get_learner(session, learner.id) is not None


def test_nothing_is_saved_when_the_block_fails(connection: Connection) -> None:
    with pytest.raises(ValueError), unit_of_work(lambda: make_session_on(connection)) as session:
        learner = create_learner(session, email="undone@example.com")
        raise ValueError("something went wrong later in the request")
    with unit_of_work(lambda: make_session_on(connection)) as session:
        assert get_learner(session, learner.id) is None
