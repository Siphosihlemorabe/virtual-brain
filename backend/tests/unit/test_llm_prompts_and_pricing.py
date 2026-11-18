"""Prompt files and cost maths: pure code, no database, no model."""

from pathlib import Path

import pytest

from vb.llm.pricing import cost_usd
from vb.llm.prompts import load_prompt, render


def write(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(text, encoding="utf-8")


def test_newest_version_is_loaded_unless_one_is_pinned(tmp_path: Path) -> None:
    write(tmp_path, "greet.v1.md", "old system\n---\nold user")
    write(tmp_path, "greet.v2.md", "new system\n---\nHello $name")
    newest = load_prompt("greet", directory=tmp_path)
    assert (newest.version, newest.system, newest.user_template) == (2, "new system", "Hello $name")
    assert load_prompt("greet", version=1, directory=tmp_path).system == "old system"


def test_render_fills_inputs_and_rejects_missing_ones(tmp_path: Path) -> None:
    write(tmp_path, "greet.v1.md", 'system\n---\nHello $name, reply as {"ok": true}')
    prompt = load_prompt("greet", directory=tmp_path)
    assert render(prompt, {"name": "Sipho"}) == 'Hello Sipho, reply as {"ok": true}'  # JSON braces untouched
    with pytest.raises(ValueError, match="needs input 'name'"):
        render(prompt, {})


def test_prompt_without_separator_or_missing_is_an_error(tmp_path: Path) -> None:
    write(tmp_path, "bad.v1.md", "no separator here")
    with pytest.raises(ValueError, match="---"):
        load_prompt("bad", directory=tmp_path)
    with pytest.raises(FileNotFoundError):
        load_prompt("nothing", directory=tmp_path)


def test_the_real_health_check_prompt_loads() -> None:
    prompt = load_prompt("health_check")
    assert prompt.version >= 1 and "$text" in prompt.user_template


def test_cost_uses_list_prices_per_million_tokens() -> None:
    # Haiku 4.5: $1 in, $5 out per million tokens -> 1,000 in + 500 out = $0.001 + $0.0025
    assert cost_usd("claude-haiku-4-5", 1_000, 500) == pytest.approx(0.0035)
    assert cost_usd("claude-sonnet-5", 1_000_000, 0) == pytest.approx(2.00)
    assert cost_usd("unknown-model", 10, 10) is None
