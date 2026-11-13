"""The agents. Each has one role. The language model only reads text and writes explanations;
every mark and every number is decided in code (mathcheck)."""
import re

from . import llm
from .mathcheck import fmt, parse_steps, terms

GOAL = "Take me from a textbook chapter to proven understanding, then to a real career application."
LEVELS = ("gap", "partly", "understood")


def _numbers(text: str) -> set:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _faithful(lines, source: str) -> bool:
    """True if every number the model wrote appears in the source text (it did not invent or 'fix' numbers)."""
    src = _numbers(source)
    return all(n in src for line in lines for n in _numbers(line))


# ---------------------------------------------------------------- Planner

class Planner:
    name = "Planner"

    def __init__(self, log):
        self.log = log

    def read_chapter(self, text: str) -> dict:
        if not text.strip():
            raise ValueError("The chapter is empty. Upload a chapter with at least one worked example.")
        chapter, how = None, ""
        try:
            chapter = self._read_with_model(text)
            how = f"read by language model ({llm.provider()})"
        except (llm.LLMError, ValueError) as e:
            self.log(self.name, "warn", f"Model reading failed or was unfaithful ({e}). Falling back to the rule-based reader.")
        if chapter is None:
            chapter = self._read_with_rules(text)
            how = "read by rule-based parser"
        self._validate(chapter, text)
        self.log(self.name, "info",
                 f"Chapter {how}: {len(chapter['concepts'])} concepts, {len(chapter['problems'])} practice problems.",
                 {"concepts": chapter["concepts"]})
        return chapter

    def _read_with_model(self, text: str) -> dict:
        data = llm.complete_json(
            "Read this Grade 10 maths textbook chapter. Split it into concepts and practice problems.\n"
            'Return {"concepts":[{"id":"C1","name":"...","summary":"one sentence"}],'
            '"problems":[{"id":"P1","concept":"C1","question":"...","solution":["one calculation per line"]}]}.\n'
            "Copy each worked-solution line exactly as written, in the form 'P(...) = expression = value'. "
            "Do not change, add or correct any number.\n\nCHAPTER:\n" + text)
        if not isinstance(data, dict):
            raise ValueError("unexpected shape")
        self._validate(data, text)
        return data

    @staticmethod
    def _read_with_rules(text: str) -> dict:
        concepts, problems = [], []
        for m in re.finditer(r"^Concept\s+(C\d+):\s*(.+)\n((?:.+\n?)*)", text, flags=re.M):
            concepts.append({"id": m.group(1), "name": m.group(2).strip(), "summary": m.group(3).strip()})
        for m in re.finditer(r"^Problem\s+(P\d+)\s*\((C\d+)\):\s*(.+?)\nWorked solution:\s*\n((?:[^\n]+\n?)*)",
                             text, flags=re.M | re.S):
            problems.append({"id": m.group(1), "concept": m.group(2), "question": m.group(3).strip(),
                             "solution": [l.strip() for l in m.group(4).splitlines() if l.strip()]})
        return {"concepts": concepts, "problems": problems}

    @staticmethod
    def _validate(ch: dict, source: str):
        if not ch.get("concepts") or not ch.get("problems"):
            raise ValueError("No concepts or worked problems found. Label them 'Concept C1: ...' and "
                             "'Problem P1 (C1): ...' followed by 'Worked solution:'.")
        ids = {c["id"] for c in ch["concepts"]}
        for p in ch["problems"]:
            if p.get("concept") not in ids:
                raise ValueError(f"{p.get('id')} points to unknown concept {p.get('concept')}")
            if not parse_steps(p.get("solution", [])):
                raise ValueError(f"{p.get('id')} has no worked solution with calculations")
            if not _faithful(p["solution"], source):
                raise ValueError(f"{p['id']} worked solution has numbers not in the chapter")

    def plan(self, chapter: dict, attempted: dict) -> list:
        """Decide the order of work for this upload. Model proposes; code validates and repairs."""
        allowed = {p["id"] for p in chapter["problems"]}
        steps, reasoning = None, ""
        try:
            data = llm.complete_json(
                f"You are the Planner agent. The student's goal: {GOAL}\n"
                f"Concepts: {[(c['id'], c['name']) for c in chapter['concepts']]}\n"
                f"Problems (id, concept, attempted by student): "
                f"{[(p['id'], p['concept'], p['id'] in attempted) for p in chapter['problems']]}\n"
                "Decide the order in which the Checker should mark the attempted problems "
                "(foundations before concepts that build on them), and which unattempted problems to ask the student to do.\n"
                'Return {"reasoning":"two sentences","steps":[{"action":"check"|"ask_student","target":"P1","reason":"short"}]}')
            steps, reasoning = data.get("steps"), data.get("reasoning", "")
        except (llm.LLMError, AttributeError) as e:
            self.log(self.name, "warn", f"Model planning unavailable ({e}). Using rule-based plan.")

        clean, seen = [], set()
        for s in steps or []:
            t, a = s.get("target"), s.get("action")
            if t in allowed and t not in seen and a in ("check", "ask_student"):
                if a == "check" and t not in attempted:
                    a = "ask_student"
                clean.append({"action": a, "target": t, "reason": s.get("reason", "")})
                seen.add(t)
        for p in chapter["problems"]:  # repair: nothing gets skipped silently
            if p["id"] not in seen:
                a = "check" if p["id"] in attempted else "ask_student"
                why = "foundation-first order" if steps is None else "added by orchestrator: plan missed it"
                clean.append({"action": a, "target": p["id"], "reason": why})
        if reasoning:
            self.log(self.name, "reason", reasoning)
        self.log(self.name, "plan", "Plan: " + " → ".join(f"{s['action']} {s['target']}" for s in clean),
                 {"steps": clean})
        return clean


# ---------------------------------------------------------------- Checker

class Checker:
    """Marks each problem by comparing the student's steps with the textbook's worked solution."""
    name = "Checker"

    def __init__(self, log):
        self.log = log

    def read_working(self, text: str, chapter: dict) -> dict:
        """Split the student's working into calculation lines per problem."""
        if not text.strip():
            return {}
        work = None
        try:
            data = llm.complete_json(
                "Read a Grade 10 student's handwritten maths working (already typed out). For each problem, "
                "rewrite every calculation the student did as one line 'label = expression = ... = value'.\n"
                "Copy the student's numbers EXACTLY, including mistakes. Never correct anything. "
                "Leave out problems the student did not attempt.\n"
                f"Problems: {[(p['id'], p['question']) for p in chapter['problems']]}\n"
                'Return {"P1":["line", ...], ...}\n\nSTUDENT WORKING:\n' + text)
            if not isinstance(data, dict) or not all(isinstance(v, list) for v in data.values()):
                raise ValueError("unexpected shape")
            if not all(_faithful(v, text) for v in data.values()):
                raise ValueError("model changed the student's numbers")
            work = {k: v for k, v in data.items() if parse_steps(v)}
        except (llm.LLMError, ValueError) as e:
            self.log(self.name, "warn", f"Model reading of working rejected ({e}). Using rule-based reader.")
        if work is None:
            work = {}
            for m in re.finditer(r"^\s*(P\d+)\s*[:.)]\s*(.*?)(?=^\s*P\d+\s*[:.)]|\Z)", text, flags=re.M | re.S):
                lines = [l.strip() for l in m.group(2).splitlines() if l.strip()]
                if parse_steps(lines):
                    work[m.group(1)] = lines
        self.log(self.name, "info", f"Read student working for {', '.join(sorted(work)) or 'no problems'}.")
        return work

    def check(self, problem: dict, student_lines: list, accept_alternative=False, align="index") -> dict:
        """Mark one problem. Default policy: the student must follow the textbook method step by step."""
        t, s = parse_steps(problem["solution"]), parse_steps(student_lines)
        if not s:
            return {"level": "gap", "step": None, "detail": "No calculation found for this problem."}
        t_final, s_final = t[-1].value, s[-1].value

        def match(i):
            ts = t[i]
            if align == "label":
                cand = [x for x in s if x.label and x.label == ts.label]
                ss = cand[0] if cand else (s[i] if i < len(s) else None)
            else:
                ss = s[i] if i < len(s) else None
            return ss is not None and ss.value == ts.value and terms(ss.first_expr) == terms(ts.first_expr)

        err = next((i for i in range(len(t)) if not match(i)), None)
        if s_final == t_final:
            if err is None or accept_alternative:
                how = "a valid method of their own" if err is not None else "the textbook method"
                return {"level": "understood", "step": None,
                        "detail": f"Final answer {fmt(s_final)} is correct using {how}."}
            return {"level": "partly", "step": err + 1,
                    "detail": f"Answer {fmt(s_final)} is correct, but step {err + 1} does not follow the textbook "
                              f"method ('{t[err].text}')."}
        step = err if err is not None else len(t) - 1
        level = "partly" if (step == len(t) - 1 and len(t) > 1) else "gap"
        wrote = s[step].text if step < len(s) else "(missing)"
        return {"level": level, "step": step + 1,
                "detail": f"Final answer {fmt(s_final)} should be {fmt(t_final)}. Went wrong at step {step + 1}: "
                          f"wrote '{wrote}', textbook has '{t[step].text}'."}


# ---------------------------------------------------------------- Reviewer

class Reviewer:
    """Double-checks the Checker by redoing the maths itself, independent of the textbook's method."""
    name = "Reviewer"

    def __init__(self, log):
        self.log = log

    def own_verdict(self, problem: dict, student_lines: list) -> dict:
        t, s = parse_steps(problem["solution"]), parse_steps(student_lines)
        for i, ts in enumerate(t):
            if not ts.consistent:
                self.log(self.name, "warn", f"{problem['id']}: textbook step {i + 1} '{ts.text}' does not add up. "
                                            "Using my own recomputation as the true answer.")
        truth = t[-1].values[0]  # recomputed from the expression, not copied from the stated answer
        if not s:
            return {"level": "gap", "step": None, "truth": truth}
        slips = [i for i, x in enumerate(s) if not x.consistent]
        if s[-1].value == truth:
            if slips:
                return {"level": "partly", "step": slips[0] + 1, "truth": truth,
                        "why": f"right answer but step {slips[0] + 1} '{s[slips[0]].text}' does not add up"}
            return {"level": "understood", "step": None, "truth": truth,
                    "why": f"every step is arithmetically valid and the answer {fmt(truth)} is correct"}
        # wrong answer: find where it first goes wrong, matching steps by what they compute (label)
        step = None
        if slips:
            step = slips[0]
        else:
            for ts in t:
                ss = next((x for x in s if x.label and x.label == ts.label), None)
                if ss is not None and ss.value != ts.value:
                    step = s.index(ss)
                    break
        if step is None:
            step = len(s) - 1
        level = "partly" if (step == len(s) - 1 and len(s) > 1) else "gap"  # only the final step slipped
        return {"level": level, "step": step + 1, "truth": truth,
                "why": f"answer {fmt(s[-1].value)} should be {fmt(truth)}; first wrong step is "
                       f"{step + 1} '{s[step].text}'"}

    def review(self, problem: dict, student_lines: list, mark: dict) -> dict:
        own = self.own_verdict(problem, student_lines)
        same_level = own["level"] == mark["level"]
        same_step = own["level"] == "understood" or own["step"] == mark["step"]
        if same_level and same_step:
            return {"agree": True, "own": own}
        if own["level"] == "understood":
            reason = "valid_alternative_method"
        elif same_level:
            reason = "wrong_step"
        else:
            reason = "wrong_level"
        return {"agree": False, "own": own, "reason": reason}


def explain(problem: dict, student_lines: list, mark: dict, log) -> str:
    """Student-friendly feedback. The model only words it; the mark and step are already decided."""
    try:
        text = llm.complete(
            "You are a kind Grade 10 maths tutor. In at most two short sentences, tell the student what went "
            "wrong and what to revise. Do not give a different answer or step than the one stated.\n"
            f"Question: {problem['question']}\nTextbook solution: {problem['solution']}\n"
            f"Student's working: {student_lines}\nVerified finding: {mark['detail']}", timeout=60).strip()
        if text:
            log("Checker", "info", f"Feedback for {problem['id']}: {text}")
            return f"{mark['detail']} {text}"
    except llm.LLMError:
        pass
    return mark["detail"]
