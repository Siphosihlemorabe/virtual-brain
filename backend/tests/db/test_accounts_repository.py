"""The accounts tables and repository, against a real PostgreSQL test database."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vb.accounts.repository import create_learner, get_learner


def test_migrations_create_the_learner_table(engine: Engine) -> None:
    columns = {c["name"]: c for c in inspect(engine).get_columns("learner")}
    assert set(columns) == {"id", "created_at", "email", "display_name"}
    # Rules P4 and P5: no database-side defaults; values come from Python.
    assert all(c["default"] is None for c in columns.values())


def test_create_then_get_learner(session: Session) -> None:
    created = create_learner(session, email="learner@example.com", display_name="Learner")
    assert get_learner(session, created.id) == created


def test_id_and_created_at_are_set_in_python(session: Session) -> None:
    first, second = create_learner(session), create_learner(session)
    assert isinstance(first.id, uuid.UUID) and first.id != second.id
    assert first.created_at.tzinfo is not None
    assert abs(datetime.now(UTC) - first.created_at) < timedelta(minutes=1)


def test_get_unknown_learner_returns_none(session: Session) -> None:
    assert get_learner(session, uuid.uuid4()) is None


def test_email_must_be_unique(session: Session) -> None:
    create_learner(session, email="same@example.com")
    with pytest.raises(IntegrityError):
        create_learner(session, email="same@example.com")
