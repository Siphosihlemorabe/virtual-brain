"""Career guide agent: links understood concepts to a real career application, runs the code,
and sets a tiny by-hand task. The Reviewer then checks the hand maths against the code's output."""
import contextlib
import io
import json
import runpy
import time
from fractions import Fraction
from pathlib import Path

from . import llm
from .mathcheck import fmt, parse_steps

ROOT = Path(__file__).resolve().parent.parent
CAREERS = ROOT / "samples" / "careers.json"
CODE_DIR = ROOT / "samples" / "career_code"


def _careers() -> dict:
    return {k: v for k, v in json.loads(CAREERS.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def run_code(filename: str):
    """Run the career code exactly as shown to the student; return its source, printed output and variables."""
    path = CODE_DIR / filename
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        env = runpy.run_path(str(path))
    return path.read_text(encoding="utf-8"), out.getvalue().strip(), env


class CareerGuide:
    name = "Career guide"

    def __init__(self, log):
        self.log = log

    def offer(self, brain: dict) -> list:
        """One career card per understood concept that has a career link."""
        careers, cards = _careers(), []
        ready = [k for k, c in brain["concepts"].items() if c["level"] == "understood"]
        for key in ready:
            info = careers.get(key)
            if not info:
                continue
            name = brain["concepts"][key]["name"]
            source, printed, env = run_code(info["code"])
            answers = {v: fmt(env[v]) for v in info["check"]}
            explain = info["explain"]
            try:
                explain = llm.complete(
                    "In at most three short sentences for a Grade 10 learner, explain how the maths concept "
                    f"'{name}' is used in a {info['application']} for {info['use']}, and what a "
                    f"{info['career']} does with it. No formulas beyond fractions.", timeout=60).strip() or explain
            except llm.LLMError:
                pass
            chain = [name, info["application"], info["use"], info["career"]]
            self.log(self.name, "career", f"{name} is understood, so unlocking: {' → '.join(chain)}.")
            self.log(self.name, "info", f"Ran {info['code']}: {printed}. Asking the student to prove it by hand.")
            cards.append({"concept": key, "name": name, "chain": chain, "explain": explain, "code": source,
                          "output": printed, "task": info["task"], "answers": answers, "check": info["check"]})
        if not cards:
            self.log(self.name, "info", "No understood concept has a career link yet. Nothing to unlock this time.")
        return cards


def check_hand_maths(card: dict, text: str) -> dict:
    """Reviewer's check: every hand step must add up and match the value the code computed."""
    expected = {k: Fraction(v) for k, v in card["answers"].items()}
    steps = parse_steps([l for l in text.splitlines() if l.strip()])
    if not steps:
        return {"ok": False, "msg": "I could not find any calculations. Write one line per value, e.g. "
                                    "'score_spam = 4/8 * 3/4 * 2/4 = 3/16'."}
    problems = []
    for i, name in enumerate(card["check"]):
        st = next((s for s in steps if s.label == name.lower()), steps[i] if i < len(steps) else None)
        if st is None:
            problems.append(f"{name}: missing")
        elif not st.consistent:
            problems.append(f"{name}: '{st.text}' does not add up. {st.first_expr} = {fmt(st.values[0])}, "
                            f"not {fmt(st.value)}")
        elif st.value != expected[name]:
            problems.append(f"{name}: you got {fmt(st.value)}, the code got {fmt(expected[name])}")
    if problems:
        return {"ok": False, "msg": "Does not match the code yet. " + " | ".join(problems)}
    return {"ok": True, "msg": "Every hand step adds up and matches the code: "
                               + ", ".join(f"{k} = {v}" for k, v in card["answers"].items()) + "."}


def record_proof(brain: dict, card: dict):
    node = brain["concepts"][card["concept"]]
    node["careers"] = [c for c in node.get("careers", []) if c["career"] != card["chain"][-1]]
    node["careers"].append({"career": card["chain"][-1], "application": card["chain"][1], "use": card["chain"][2],
                            "proven": time.strftime("%Y-%m-%d %H:%M")})
