"""Development-only provider: Claude through the local `claude` CLI (Claude Code), using your Claude Code login.

No API key and no API bill, but it only works on a machine where you are logged in to Claude Code, so it can
never be deployed. Production uses AnthropicProvider. Structured output comes from the CLI's --json-schema option.
"""

import json
import shutil
import subprocess
import tempfile

from pydantic import ValidationError

from vb.llm.provider import LLMError, ProviderResult, T


class ClaudeCLIProvider:
    def __init__(self, executable: str = "claude", timeout_seconds: float = 180.0) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def complete(self, system: str, user: str, schema: type[T], model: str, max_tokens: int) -> ProviderResult[T]:
        # max_tokens has no CLI option; the CLI manages output length itself.
        path = shutil.which(self.executable)
        if path is None:
            raise LLMError(f"{self.executable!r} CLI not found on PATH")
        command = [
            path,
            "-p",  # print the answer and exit (non-interactive)
            "--safe-mode",  # ignore local customisations, so answers don't depend on this machine's setup
            "--no-session-persistence",  # don't save a chat session for every call
            "--tools",
            "",  # no tools: the model only answers, it can't read files or run commands
            "--output-format",
            "json",
            "--model",
            model,
            "--system-prompt",
            system,
            "--json-schema",
            json.dumps(schema.model_json_schema()),  # the reply must match the Pydantic schema
        ]
        try:
            completed = subprocess.run(
                command,
                input=user,  # the user message goes in on stdin, not on the command line
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                cwd=tempfile.gettempdir(),  # run outside the repo so no project files are picked up
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"claude CLI timed out after {self.timeout_seconds:.0f}s") from e

        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError as e:
            raise LLMError(f"claude CLI gave no JSON: {(completed.stderr or completed.stdout)[:200]}") from e
        if data.get("is_error"):
            raise LLMError(f"claude CLI error: {str(data.get('result'))[:200]}")
        structured = data.get("structured_output")
        if structured is None:
            raise LLMError("claude CLI returned no structured output")
        try:
            parsed = schema.model_validate(structured)
        except ValidationError as e:
            raise LLMError(f"reply does not match {schema.__name__}: {e.error_count()} error(s)") from e

        usage = data.get("usage") or {}
        return ProviderResult(
            parsed=parsed,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
