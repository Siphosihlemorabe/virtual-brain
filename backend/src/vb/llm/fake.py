"""A provider that returns recorded replies: no API key, no cost, same answer every time. The default."""

from pydantic import BaseModel, ValidationError

from vb.llm.provider import LLMError, ProviderResult, T


class FakeProvider:
    def __init__(self, replies: dict[type[BaseModel], str]) -> None:
        # Recorded replies, keyed by the output schema: "when asked for a HealthCheckReply, answer this JSON".
        self.replies = replies
        self.calls: list[tuple[str, str]] = []  # (system, user) of every call, so tests can check what was sent

    def complete(self, system: str, user: str, schema: type[T], model: str, max_tokens: int) -> ProviderResult[T]:
        self.calls.append((system, user))
        reply = self.replies.get(schema)
        if reply is None:
            raise LLMError(f"no recorded reply for {schema.__name__}")
        try:
            parsed = schema.model_validate_json(reply)
        except ValidationError as e:
            raise LLMError(f"reply does not match {schema.__name__}: {e.error_count()} error(s)") from e
        return ProviderResult(parsed=parsed, input_tokens=_estimate(system + user), output_tokens=_estimate(reply))


def _estimate(text: str) -> int:
    return max(1, len(text) // 4)  # rough: about 4 characters per token
