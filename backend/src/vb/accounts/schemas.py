"""What the accounts module hands to the rest of the app: plain Pydantic models, never database rows (rule P2)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Learner(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    created_at: datetime
    email: str | None
    display_name: str | None
