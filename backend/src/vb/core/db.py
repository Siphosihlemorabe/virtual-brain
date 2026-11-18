"""Database connection and the base class every table inherits (docs/design/database.md).

Only repository.py files use this module directly (portability rule P2).
"""

import uuid
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import DateTime, Engine, MetaData, Uuid, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from vb.core.config import get_settings

# Predictable constraint names, identical on every database (needed to change constraints in migrations later).
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class Entity(Base):
    """Columns every table has. Both values are set in Python, not by the database (rules P4, P5)."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping checks a pooled connection still works before using it.
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def session_maker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine())
