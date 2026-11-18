"""What the llm module hands out, and the output schema of the health-check prompt."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LLMCall(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    created_at: datetime
    job_id: uuid.UUID | None
    prompt_id: str
    prompt_version: int
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float | None
    ok: bool
    error: str | None


class HealthCheckReply(BaseModel):
    """Output of prompts/health_check: proves a provider can return schema-checked JSON."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    echo: str
