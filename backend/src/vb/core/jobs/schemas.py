"""What the jobs module hands out: plain Pydantic models (rule P2)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

JobStatus = Literal["queued", "running", "done", "failed"]


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    created_at: datetime
    kind: str
    status: JobStatus
    payload: dict[str, Any]
    attempts: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class JobLogLine(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    created_at: datetime
    agent: str
    kind: str
    message: str
