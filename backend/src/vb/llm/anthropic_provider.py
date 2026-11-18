"""The real provider: Claude through the Anthropic API, using structured outputs (messages.parse)."""

import anthropic

from vb.llm.provider import LLMError, ProviderResult, T


class AnthropicProvider:
    def __init__(self, api_key: str | None, timeout_seconds: float = 120.0) -> None:
        # api_key=None lets the SDK find a key itself (ANTHROPIC_API_KEY). The SDK retries rate limits and
        # server errors twice on its own.
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)

    def complete(self, system: str, user: str, schema: type[T], model: str, max_tokens: int) -> ProviderResult[T]:
        try:
            response = self._client.messages.parse(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,  # the reply must match this Pydantic model
            )
        except anthropic.APIStatusError as e:  # the API answered with an error (bad request, rate limit, outage)
            raise LLMError(f"Anthropic API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:  # network failure or timeout
            raise LLMError(f"could not reach the Anthropic API: {e}") from e

        if response.stop_reason in ("refusal", "max_tokens"):
            raise LLMError(f"no usable answer: stop_reason={response.stop_reason}")
        if response.parsed_output is None:
            raise LLMError("the reply could not be read as the expected schema")
        return ProviderResult(
            parsed=response.parsed_output,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
