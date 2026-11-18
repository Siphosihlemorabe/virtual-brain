"""The llm service with the fake provider: schema-checked answers, and every call recorded (AI rule 6)."""

import pytest
from sqlalchemy.orm import Session

from vb.core.jobs import repository as jobs
from vb.llm import repository
from vb.llm.fake import FakeProvider
from vb.llm.provider import LLMError
from vb.llm.schemas import HealthCheckReply
from vb.llm.service import complete


def test_a_valid_answer_is_returned_and_the_call_recorded(session: Session) -> None:
    job = jobs.enqueue(session, "demo", {})
    provider = FakeProvider({HealthCheckReply: '{"status": "ok", "echo": "S3 stores objects"}'})

    answer = complete(session, provider, "health_check", {"text": "S3 stores objects"}, HealthCheckReply, job_id=job.id)

    assert answer == HealthCheckReply(status="ok", echo="S3 stores objects")
    assert "S3 stores objects" in provider.calls[0][1]  # the input reached the prompt
    [call] = repository.calls_for_job(session, job.id)
    assert call.ok and call.error is None
    assert (call.prompt_id, call.prompt_version, call.model) == ("health_check", 1, "claude-haiku-4-5")
    assert call.input_tokens > 0 and call.output_tokens > 0 and call.cost_usd is not None and call.cost_usd > 0


def test_an_answer_that_breaks_the_schema_is_rejected_and_recorded_as_failed(session: Session) -> None:
    provider = FakeProvider({HealthCheckReply: '{"status": "maybe", "echo": "x"}'})  # "maybe" is not allowed

    with pytest.raises(LLMError, match="does not match HealthCheckReply"):
        complete(session, provider, "health_check", {"text": "x"}, HealthCheckReply)

    [call] = repository.calls_for_prompt(session, "health_check")
    assert not call.ok and call.error is not None and "does not match" in call.error


def test_a_missing_input_fails_before_the_model_is_called(session: Session) -> None:
    provider = FakeProvider({HealthCheckReply: '{"status": "ok", "echo": ""}'})
    with pytest.raises(ValueError, match="needs input 'text'"):
        complete(session, provider, "health_check", {}, HealthCheckReply)
    assert provider.calls == []  # no call made, nothing spent
    assert repository.calls_for_prompt(session, "health_check") == []
