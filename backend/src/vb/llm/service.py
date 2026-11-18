"""The one way the app talks to a language model: llm.service.complete(...).

Loads a versioned prompt, fills it, picks the model, asks the provider for schema-checked output (AI rule 6), and
records every call, successful or not, in llm_call.
"""

import time
import uuid

from sqlalchemy.orm import Session

from vb.core.config import Settings, get_settings
from vb.llm import repository
from vb.llm.anthropic_provider import AnthropicProvider
from vb.llm.claude_cli_provider import ClaudeCLIProvider
from vb.llm.fake import FakeProvider
from vb.llm.pricing import cost_usd
from vb.llm.prompts import load_prompt, render
from vb.llm.provider import LLMError, LLMProvider, T

DEFAULT_MAX_TOKENS = 4000


def model_for(prompt_id: str, settings: Settings) -> str:
    return settings.llm_prompt_models.get(prompt_id, settings.llm_default_model)


def provider_from_settings(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "anthropic":
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        return AnthropicProvider(api_key=key)
    if settings.llm_provider == "claude_cli":
        return ClaudeCLIProvider()
    return FakeProvider(replies={})  # replies are registered by tests and by local seed data


def complete(
    session: Session,
    provider: LLMProvider,
    prompt_id: str,
    inputs: dict[str, str],
    schema: type[T],
    *,
    job_id: uuid.UUID | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> T:
    """Ask the model; return output matching `schema`, or raise LLMError. Every attempt is recorded."""
    prompt = load_prompt(prompt_id)
    user = render(prompt, inputs)  # a missing input fails here, before any money is spent
    model = model_for(prompt_id, get_settings())

    started = time.monotonic()
    try:
        result = provider.complete(prompt.system, user, schema, model, max_tokens)
    except LLMError as e:
        _record(session, job_id, prompt_id, prompt.version, model, 0, 0, started, ok=False, error=str(e))
        raise
    _record(session, job_id, prompt_id, prompt.version, model, result.input_tokens, result.output_tokens, started)
    return result.parsed


def _record(
    session: Session,
    job_id: uuid.UUID | None,
    prompt_id: str,
    prompt_version: int,
    model: str,
    input_tokens: int,
    output_tokens: int,
    started: float,
    ok: bool = True,
    error: str | None = None,
) -> None:
    repository.record_call(
        session,
        job_id=job_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=int((time.monotonic() - started) * 1000),
        cost_usd=cost_usd(model, input_tokens, output_tokens),
        ok=ok,
        error=error,
    )
