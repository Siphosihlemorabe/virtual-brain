"""The only code that reads or writes the accounts tables (rule P2).

Functions take a Session from the caller and never commit: the caller decides when a transaction ends.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vb.accounts.models import LearnerRecord
from vb.accounts.schemas import Learner


def create_learner(session: Session, email: str | None = None, display_name: str | None = None) -> Learner:
    record = LearnerRecord(email=email, display_name=display_name)
    session.add(record)
    session.flush()  # sends the INSERT now, so id and created_at are filled in and errors surface here
    return Learner.model_validate(record)


def get_learner(session: Session, learner_id: uuid.UUID) -> Learner | None:
    record = session.get(LearnerRecord, learner_id)
    return Learner.model_validate(record) if record else None


def get_or_create_learner_by_email(session: Session, email: str, display_name: str | None = None) -> Learner:
    """The learner with this email, created on first use."""
    record = session.scalars(select(LearnerRecord).where(LearnerRecord.email == email)).first()
    if record is None:
        return create_learner(session, email=email, display_name=display_name)
    return Learner.model_validate(record)
