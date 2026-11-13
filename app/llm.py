"""Language-model adapter. Used only to read text and write explanations; never to decide marks.

VB_LLM=claude (default, uses the local `claude` CLI) | gemini (needs GEMINI_API_KEY) | mock (offline).
Every caller has a code fallback, so a failed or slow call never breaks a run.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # .env support is optional
    pass


class LLMError(Exception):
    pass


def _env(name: str):
    """Environment variable, matched case-insensitively (the .env may say Gemini_Api_Key)."""
    return next((v for k, v in os.environ.items() if k.upper() == name), None)


def provider() -> str:
    return os.environ.get("VB_LLM", "claude").lower()


def _claude(prompt: str, timeout: int) -> str:
    exe = shutil.which("claude")
    if not exe:
        raise LLMError("claude CLI not found on PATH")
    cmd = [
        exe, "-p", "--safe-mode", "--output-format", "json",
        "--model", os.environ.get("VB_CLAUDE_MODEL", "sonnet"),
        "--system-prompt", "You are one component of an education app. Follow the instructions in the message exactly",
        "--tools", "", "--no-session-persistence",
    ]
    try:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout, cwd=tempfile.gettempdir())
    except subprocess.TimeoutExpired:
        raise LLMError(f"claude CLI timed out after {timeout}s")
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise LLMError(f"claude CLI returned no JSON: {(r.stderr or r.stdout)[:200]}")
    if out.get("is_error"):
        raise LLMError(f"claude CLI error: {str(out.get('result'))[:200]}")
    return out.get("result", "")


def _gemini(prompt: str, timeout: int) -> str:
    key = _env("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    # gemini-2.5-flash is closed to new API users; the larger Flash models were timing out at the time of testing
    model = _env("VB_GEMINI_MODEL") or "gemini-3.1-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    for attempt in range(3):  # Google returns 503/429 during demand spikes; these usually clear in seconds
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
            return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
            except (ValueError, AttributeError):
                msg = ""
            if e.code in (429, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise LLMError(f"gemini {model} HTTP {e.code}: {msg[:200] or e.reason}")
        except Exception as e:  # network, timeout, unexpected reply shape
            raise LLMError(f"gemini {model} error: {e}")


# Timing of every model call, shown in the side panel so response times are visible.
_CALLS = []
_WHO = {"verify": "Reviewer", "explain": "Checker", "plan_round": "Planner", "write_variants": "Tutor",
        "_review_briefs": "Career guide", "read_answers": "Checker", "_read_with_model": "Planner", "_rewrite": "Tutor"}
_CLASS = {"Planner": "Planner", "Checker": "Checker", "Tutor": "Tutor", "CareerGuide": "Career guide"}


def _caller() -> str:
    """Which agent asked: the first frame outside this module, named by its class or function."""
    import inspect
    for f in inspect.stack()[2:8]:
        if f.filename.endswith("llm.py"):
            continue
        if f.function in _WHO:
            return _WHO[f.function]
        owner = f.frame.f_locals.get("self")
        if owner is not None and type(owner).__name__ in _CLASS:
            return _CLASS[type(owner).__name__]
        return f.function
    return "?"


def stats() -> dict:
    done = [c for c in _CALLS if c["ok"]]
    return {"provider": provider(), "calls": len(_CALLS), "errors": len(_CALLS) - len(done),
            "avg": round(sum(c["secs"] for c in done) / len(done), 1) if done else None,
            "recent": _CALLS[-6:][::-1]}


def complete(prompt: str, timeout: int = 90) -> str:
    p = provider()
    if p not in ("claude", "gemini"):
        raise LLMError("offline mode (VB_LLM=mock)")
    who, t0 = _caller(), time.time()
    try:
        out = _claude(prompt, timeout) if p == "claude" else _gemini(prompt, timeout)
        _CALLS.append({"who": who, "secs": round(time.time() - t0, 1), "ok": True, "at": time.strftime("%H:%M:%S")})
        return out
    except LLMError as e:
        _CALLS.append({"who": who, "secs": round(time.time() - t0, 1), "ok": False, "at": time.strftime("%H:%M:%S"),
                       "error": str(e)[:120]})
        raise
    finally:
        del _CALLS[:-200]  # keep the list small


def complete_json(prompt: str, timeout: int = 90):
    text = complete(prompt + "\n\nReply with JSON only, no prose and no code fences.", timeout)
    m = re.search(r"[\[{].*[\]}]", text, flags=re.S)
    if not m:
        raise LLMError("model reply contained no JSON")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise LLMError(f"model returned invalid JSON: {e}")
