"""The only code that reads or writes the llm_call table (rule P2). Functions never commit."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vb.llm.models import LLMCallRecord
from vb.llm.schemas import LLMCall


def record_call(session: Session, **fields: object) -> LLMCall:
    record = LLMCallRecord(**fields)
    session.add(record)
    session.flush()
    return LLMCall.model_validate(record)


def calls_for_prompt(session: Session, prompt_id: str) -> list[LLMCall]:
    stmt = select(LLMCallRecord).where(LLMCallRecord.prompt_id == prompt_id).order_by(LLMCallRecord.created_at)
    return [LLMCall.model_validate(r) for r in session.scalars(stmt)]


def calls_for_job(session: Session, job_id: uuid.UUID) -> list[LLMCall]:
    stmt = select(LLMCallRecord).where(LLMCallRecord.job_id == job_id).order_by(LLMCallRecord.created_at)
    return [LLMCall.model_validate(r) for r in session.scalars(stmt)]
