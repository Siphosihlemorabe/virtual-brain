"""The language-model provider interface. Every provider (fake, Anthropic, any future one) must fit this."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Any failure to get a valid answer: network, refusal, cut-off reply, or output that doesn't match the schema."""


@dataclass(frozen=True)
class ProviderResult(Generic[T]):
    parsed: T  # the answer, already validated against the schema
    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    def complete(self, system: str, user: str, schema: type[T], model: str, max_tokens: int) -> ProviderResult[T]:
        """Ask the model and return an answer that matches `schema`, or raise LLMError."""
        ...
