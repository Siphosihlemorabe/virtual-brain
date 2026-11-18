"""Prompts are versioned files in llm/prompts/, named <prompt_id>.v<N>.md.

A file is the system prompt, a line containing only ---, then the user message. $name placeholders are filled from
the inputs ($ rather than {} so JSON examples in a prompt need no escaping).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

PROMPT_DIR = Path(__file__).parent / "prompts"
_FILE = re.compile(r"^(?P<id>[a-z0-9_]+)\.v(?P<version>\d+)\.md$")


@dataclass(frozen=True)
class Prompt:
    id: str
    version: int
    system: str
    user_template: str


def load_prompt(prompt_id: str, version: int | None = None, directory: Path = PROMPT_DIR) -> Prompt:
    """The given version of a prompt, or the newest one if no version is given."""
    versions = {
        int(m["version"]): path
        for path in directory.iterdir()
        if (m := _FILE.match(path.name)) and m["id"] == prompt_id
    }
    if not versions:
        raise FileNotFoundError(f"no prompt files for {prompt_id!r} in {directory}")
    chosen = version if version is not None else max(versions)
    if chosen not in versions:
        raise FileNotFoundError(f"{prompt_id!r} has no version {chosen}")
    system, separator, user = versions[chosen].read_text(encoding="utf-8").partition("\n---\n")
    if not separator:
        raise ValueError(f"{versions[chosen].name} needs a line with only --- between system and user parts")
    return Prompt(id=prompt_id, version=chosen, system=system.strip(), user_template=user.strip())


def render(prompt: Prompt, inputs: dict[str, str]) -> str:
    """Fill the user message. A missing input is an error, never a silent blank."""
    try:
        return Template(prompt.user_template).substitute(inputs)
    except KeyError as e:
        raise ValueError(f"prompt {prompt.id!r} needs input {e.args[0]!r}") from e
