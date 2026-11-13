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

    def read_chapter(self, text: str, known=()) -> dict:
        """Split a chapter into concepts, worked examples (E) and practice problems (P).
        Solutions may be missing: the Tutor fills those gaps later."""
        if not text.strip():
            raise ValueError("The chapter is empty. Paste or upload the chapter you are studying.")
        chapter, how = None, ""
        try:
            chapter = self._read_with_model(text, known)
            how = f"read by language model ({llm.provider()})"
        except (llm.LLMError, ValueError) as e:
            self.log(self.name, "warn", f"Model reading failed or was unfaithful ({e}). Falling back to the rule-based reader.")
        if chapter is None:
            chapter = self._read_with_rules(text)
            how = "read by rule-based parser"
            if not chapter["concepts"]:
                raise ValueError("I could not find the concepts in this chapter without the language model. "
                                 "Check the model is available, or label concepts 'Concept C1: name'.")
        self._validate(chapter, text)
        for item in chapter["examples"] + chapter["problems"]:
            item["source"] = "chapter"
        solved = sum(1 for p in chapter["problems"] if p["solution"])
        self.log(self.name, "info",
                 f"Chapter {how}: {len(chapter['concepts'])} concepts, {len(chapter['examples'])} worked examples, "
                 f"{len(chapter['problems'])} exercises ({solved} with solutions).", {"concepts": chapter["concepts"]})
        return chapter

    def _read_with_model(self, text: str, known) -> dict:
        data = llm.complete_json(
            "Read this Grade 10 maths textbook chapter. Split it into concepts, worked examples and exercises.\n"
            f"The learner's brain already has these concepts (key, name): {[(k, n) for k, n, _ in known]}\n"
            "Keep concept names as written in the chapter. If a chapter concept is the same as a known one, set "
            "brain_key to its key. List in builds_on the known keys it directly depends on.\n"
            "A worked example is a question the chapter solves for the reader. An exercise is a question for the "
            "student; if the chapter gives its solution or memo, include it, otherwise use an empty list. "
            "If the chapter only explains and has no questions, return empty lists. Never invent questions or solutions.\n"
            'Return {"subject":"...","concepts":[{"id":"C1","name":"...","summary":"one sentence",'
            '"brain_key":"key or null","builds_on":["key"]}],'
            '"examples":[{"id":"E1","concept":"C1","question":"...","solution":["one calculation per line"]}],'
            '"problems":[{"id":"P1","concept":"C1","question":"...","solution":[]}]}.\n'
            "Copy each solution line exactly as written, including any '(uses: ...)' tag. "
            "Do not change, add or correct any number.\n\nCHAPTER:\n" + text)
        if not isinstance(data, dict):
            raise ValueError("unexpected shape")
        data.setdefault("examples", [])
        data.setdefault("problems", [])
        self._validate(data, text)
        lines = [l for it in data["examples"] + data["problems"] for l in it.get("solution", [])]
        if sum(l.count("(uses:") for l in lines) < text.count("(uses:"):
            raise ValueError("model dropped the (uses: ...) skill tags from solutions")
        return data

    @staticmethod
    def _read_with_rules(text: str) -> dict:
        """Reader for labelled chapters: 'Concept C1: name', 'Example E1 (C1): ...', 'Problem P1 (C1): ...'
        with an optional 'Worked solution:' / 'Memo:' / 'Solution:' section."""
        concepts, examples, problems = [], [], []
        head = re.compile(r"^(Concept|Example|Worked example|Problem|Exercise)\s+([CEP]\d+)\s*(?:\((C\d+)\))?\s*:\s*(.*)$", re.I)
        for block in re.split(r"\n\s*\n", text):
            lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
            m = head.match(lines[0]) if lines else None
            if not m:
                continue
            kind, iid, concept, first = m.group(1).lower(), m.group(2).upper(), m.group(3), m.group(4).strip()
            if kind == "concept":
                concepts.append({"id": iid, "name": first, "summary": " ".join(lines[1:])})
                continue
            question, solution, in_sol = [first], [], False
            for l in lines[1:]:
                if re.match(r"^(worked solution|memo|solution)\s*:\s*$", l, re.I):
                    in_sol = True
                elif in_sol:
                    solution.append(l)
                else:
                    question.append(l)
            item = {"id": iid, "concept": concept, "question": " ".join(question).strip(), "solution": solution}
            (examples if kind in ("example", "worked example") else problems).append(item)
        subject = re.search(r"Chapter\s+\d+\s*:\s*([^(\n]+)", text)
        return {"subject": subject.group(1).strip() if subject else "", "concepts": concepts,
                "examples": examples, "problems": problems}

    @staticmethod
    def _validate(ch: dict, source: str):
        if not ch.get("concepts"):
            raise ValueError("No concepts found in this chapter.")
        ids = {c["id"] for c in ch["concepts"]}
        for item in ch.get("examples", []) + ch.get("problems", []):
            if item.get("concept") not in ids:
                raise ValueError(f"{item.get('id')} points to unknown concept {item.get('concept')}")
            item["solution"] = [l for l in item.get("solution") or [] if str(l).strip()]
            if item["solution"]:
                if not parse_steps(item["solution"]):
                    raise ValueError(f"{item['id']} has a solution with no calculations I can check")
                if not _faithful(item["solution"], source):
                    raise ValueError(f"{item['id']} solution has numbers not in the chapter")

    def plan(self, chapter: dict, attempted: dict, known=()) -> list:
        """Decide the order of work for this upload. Model proposes; code validates and repairs."""
        allowed = {p["id"] for p in chapter["problems"]}
        steps, reasoning = None, ""
        try:
            data = llm.complete_json(
                f"You are the Planner agent. The student's goal: {GOAL}\n"
                f"Concepts: {[(c['id'], c['name']) for c in chapter['concepts']]}\n"
                f"What the learner's brain already knows (key, name, level): {list(known)}\n"
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

    def read_answers(self, answers: dict, chapter: dict) -> dict:
        """Turn the student's answer box for each problem into calculation lines.
        Plain 'a = b = c' working is read in code; anything else is rewritten by the model,
        and rejected if the model changed any of the student's numbers."""
        questions = {p["id"]: p["question"] for p in chapter["problems"]}
        work, messy = {}, {}
        for pid, text in answers.items():
            if pid not in questions or not str(text).strip():
                continue
            lines = [l.strip() for l in str(text).splitlines() if l.strip()]
            if parse_steps(lines):
                work[pid] = lines
            else:
                messy[pid] = str(text)
        if messy:
            try:
                data = llm.complete_json(
                    "Read a Grade 10 student's maths working. For each problem, rewrite every calculation the student "
                    "did as one line 'label = expression = ... = value'. Copy the student's numbers EXACTLY, including "
                    "mistakes. Never correct anything.\n"
                    f"{[(pid, questions[pid], txt) for pid, txt in messy.items()]}\n"
                    'Return {"P1":["line", ...], ...}')
                for pid, lines in (data.items() if isinstance(data, dict) else []):
                    if pid in messy and isinstance(lines, list) and _faithful(lines, messy[pid]) and parse_steps(lines):
                        work[pid] = lines
                    elif pid in messy:
                        self.log(self.name, "warn", f"{pid}: the model's reading changed the student's numbers, so I ignored it.")
            except llm.LLMError as e:
                self.log(self.name, "warn", f"Could not read the free-text working ({e}).")
            for pid in messy:
                if pid not in work:
                    self.log(self.name, "warn", f"{pid}: I could not find a calculation in the answer.")
        self.log(self.name, "info", f"Read the student's working for {', '.join(sorted(work)) or 'no problems'}.")
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
