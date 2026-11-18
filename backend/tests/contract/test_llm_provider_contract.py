"""Every LLMProvider must pass these. Real models run only when explicitly allowed:

VB_RUN_CLI_TESTS=1 uv run pytest tests/contract       # claude CLI: uses your Claude Code allowance
VB_RUN_PAID_TESTS=1 VB_ANTHROPIC_API_KEY=... uv run pytest tests/contract   # API: a fraction of a cent
"""

import os
import shutil
from collections.abc import Callable

import pytest

from vb.llm.anthropic_provider import AnthropicProvider
from vb.llm.claude_cli_provider import ClaudeCLIProvider
from vb.llm.fake import FakeProvider
from vb.llm.provider import LLMProvider
from vb.llm.schemas import HealthCheckReply

PAID = os.environ.get("VB_RUN_PAID_TESTS") == "1"
KEY = os.environ.get("VB_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
CLI = os.environ.get("VB_RUN_CLI_TESTS") == "1" and shutil.which("claude") is not None


def fake() -> LLMProvider:
    return FakeProvider({HealthCheckReply: '{"status": "ok", "echo": "IAM controls access"}'})


def claude_cli() -> LLMProvider:
    return ClaudeCLIProvider()


def anthropic_api() -> LLMProvider:
    return AnthropicProvider(api_key=KEY)


@pytest.mark.parametrize(
    "make_provider",
    [
        pytest.param(fake, id="fake"),
        pytest.param(
            claude_cli,
            id="claude_cli",
            marks=pytest.mark.skipif(not CLI, reason="set VB_RUN_CLI_TESTS=1 (needs the claude CLI, logged in)"),
        ),
        pytest.param(
            anthropic_api,
            id="anthropic",
            marks=pytest.mark.skipif(not (PAID and KEY), reason="paid test: set VB_RUN_PAID_TESTS=1 and a key"),
        ),
    ],
)
def test_provider_returns_schema_checked_output(make_provider: Callable[[], LLMProvider]) -> None:
    result = make_provider().complete(
        system="Reply only with the requested JSON.",
        user='Reply with status "ok", and copy this text exactly into the echo field: IAM controls access',
        schema=HealthCheckReply,
        model="claude-haiku-4-5",
        max_tokens=200,
    )
    assert result.parsed == HealthCheckReply(status="ok", echo="IAM controls access")
    assert result.input_tokens > 0 and result.output_tokens > 0
