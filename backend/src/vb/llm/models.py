"""The llm_call table: one row per language-model call (docs/design/database.md §3.5)."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vb.core.db import Entity


class LLMCallRecord(Entity):
    __tablename__ = "llm_call"

    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job.id"))  # the job it ran in, if any
    prompt_id: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)  # null when the model's price is unknown
    ok: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
