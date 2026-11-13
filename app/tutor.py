"""Tutor agent: fills what the chapter is missing (worked examples, memos, practice questions).
Nothing it writes reaches the student until the Reviewer has checked it in code."""
from . import llm
from .mathcheck import evaluate, fmt, parse_steps

FORMAT = (
    "Format for every solution: a list of lines, one calculation per line, written as "
    "'label = arithmetic = result', using only numbers, + - * / and brackets after the label, "
    "e.g. 'P(red) = 3/10' or 'x = 180/9 = 20'. Use exact fractions, never decimals. Every line must be correct. "
    "The last line gives the final numeric answer. Questions must have a single numeric answer. "
    "End each line with '(uses: <topic>)' naming the topic that step relies on, chosen from: {topics}.")


class Tutor:
    name = "Tutor"

    def __init__(self, log, counters):
        self.log, self.counters = log, counters

    def fill(self, chapter: dict, topics: list):
        """Decide what is missing, write it, and have it verified. Mutates chapter in place."""
        concepts = chapter["concepts"]
        need_ex = [c for c in concepts if not any(e["concept"] == c["id"] for e in chapter["examples"])]
        need_memo = [p for p in chapter["problems"] if not p["solution"]]
        need_prob = [c for c in concepts if not any(p["concept"] == c["id"] for p in chapter["problems"])]
        if not (need_ex or need_memo or need_prob):
            self.log("Planner", "plan", "The chapter has worked examples and solved exercises for every concept. "
                                        "Nothing for the Tutor to write.")
            return
        todo = []
        if need_ex:
            todo.append(f"worked examples for {', '.join(c['name'] for c in need_ex)}")
        if need_memo:
            todo.append(f"memos for {', '.join(p['id'] for p in need_memo)}")
        if need_prob:
            todo.append(f"practice questions for {', '.join(c['name'] for c in need_prob)}")
        self.log("Planner", "plan", "The chapter is missing " + "; ".join(todo) + ". Handing this to the Tutor.")

        fmt_rules = FORMAT.format(topics=topics)
        try:
            data = llm.complete_json(
                "You are the Tutor agent for a South African Grade 10 maths learner (CAPS curriculum).\n" + fmt_rules + "\n"
                f"1. One worked example each for: {[(c['id'], c['name'], c['summary']) for c in need_ex]}. "
                "Add 'explain': one or two sentences on the idea behind it.\n"
                f"2. A memo (solution) for each exercise: {[(p['id'], p['question']) for p in need_memo]}\n"
                f"3. Two new practice questions each, in everyday South African contexts and different from the "
                f"examples, with solutions, for: {[(c['id'], c['name']) for c in need_prob]}\n"
                'Return {"examples":[{"concept":"C1","question":"...","explain":"...","solution":["..."]}],'
                '"memos":{"P1":["..."]},"problems":[{"concept":"C1","question":"...","solution":["..."]}]}', timeout=180)
        except llm.LLMError as e:
            self.log(self.name, "warn", f"I could not write the missing material ({e}). Continuing with what the chapter has.")
            return

        ids = {c["id"] for c in concepts}
        new = []
        for e in data.get("examples", []):
            if e.get("concept") in ids:
                new.append({"kind": "example", "concept": e["concept"], "question": e.get("question", ""),
                            "explain": e.get("explain", ""), "solution": e.get("solution") or []})
        for pid, sol in (data.get("memos") or {}).items():
            p = next((p for p in need_memo if p["id"] == pid), None)
            if p:
                new.append({"kind": "memo", "target": p, "concept": p["concept"], "question": p["question"],
                            "solution": sol or []})
        for p in data.get("problems", []):
            if p.get("concept") in ids:
                new.append({"kind": "problem", "concept": p["concept"], "question": p.get("question", ""),
                            "solution": p.get("solution") or []})
        for i, it in enumerate(new):
            it["tmp"] = f"T{i + 1}"
        self.log(self.name, "info", f"Wrote {sum(i['kind'] == 'example' for i in new)} worked examples, "
                                    f"{sum(i['kind'] == 'memo' for i in new)} memos and "
                                    f"{sum(i['kind'] == 'problem' for i in new)} practice questions. "
                                    "Handing them to the Reviewer before the student sees anything.")

        passed, failed = verify(new, self.log)
        if failed:
            fixed = self._rewrite(failed, fmt_rules)
            ok2, still = verify(fixed, self.log, recheck=True)
            self.counters["reviewer_corrections"] += len(ok2)
            passed += ok2
            for it in still:
                self.log("Reviewer", "error", f"Dropped {it['tmp']} ('{it['question'][:60]}'): still wrong after a rewrite. "
                                              "The student will not see it.")
        self._place(chapter, passed)

    def _rewrite(self, failed, fmt_rules):
        self.log(self.name, "fix", f"Rewriting {len(failed)} item(s) the Reviewer sent back.")
        try:
            data = llm.complete_json(
                "You are the Tutor agent. The Reviewer found these solutions wrong. Rewrite each solution correctly "
                "(you may also fix the question if it is unclear). " + fmt_rules + "\n"
                f"{[(it['tmp'], it['question'], it['solution'], it['problem']) for it in failed]}\n"
                'Return {"T1":{"question":"...","solution":["..."]}, ...}', timeout=120)
        except llm.LLMError as e:
            self.log(self.name, "warn", f"Rewrite failed ({e}).")
            return []
        out = []
        for it in failed:
            fix = data.get(it["tmp"]) if isinstance(data, dict) else None
            if isinstance(fix, dict) and fix.get("solution"):
                if it["kind"] != "memo":  # a chapter exercise keeps its own wording
                    it["question"] = fix.get("question") or it["question"]
                it["solution"] = fix["solution"]
                out.append(it)
        return out

    @staticmethod
    def _place(chapter, items):
        def next_id(prefix, existing):
            n = max([int(x["id"][1:]) for x in existing if x["id"][1:].isdigit()] or [0])
            return f"{prefix}{n + 1}"

        for it in items:
            if it["kind"] == "memo":
                it["target"]["solution"] = it["solution"]
                it["target"]["memo_source"] = "tutor"
            elif it["kind"] == "example":
                chapter["examples"].append({"id": next_id("E", chapter["examples"]), "concept": it["concept"],
                                            "question": it["question"], "explain": it.get("explain", ""),
                                            "solution": it["solution"], "source": "tutor"})
            else:
                chapter["problems"].append({"id": next_id("P", chapter["problems"]), "concept": it["concept"],
                                            "question": it["question"], "solution": it["solution"], "source": "tutor"})
        chapter["examples"].sort(key=lambda e: (e["concept"], e["id"]))


def verify(items, log, recheck=False):
    """Reviewer check of Tutor material: every line must add up, and an independent solve must agree."""
    passed, failed, pending = [], [], []
    for it in items:
        steps = parse_steps(it["solution"])
        if not steps:
            it["problem"] = "no calculation I can check"
        else:
            bad = next((s for s in steps if not s.consistent), None)
            it["problem"] = (f"'{bad.text}' does not add up: {bad.first_expr} = {fmt(bad.values[0])}"
                             if bad else None)
        if it["problem"]:
            failed.append(it)
        else:
            it["answer"] = steps[-1].value
            pending.append(it)

    if pending:
        try:
            blind = llm.complete_json(
                "Solve each question yourself, independently. For each, reply with ONE arithmetic expression "
                "(numbers, + - * / and brackets only) whose value is the final answer. Use fractions, not decimals.\n"
                f"{[(it['tmp'], it['question']) for it in pending]}\n"
                'Return {"T1":"expression", ...}', timeout=120)
        except llm.LLMError as e:
            log("Reviewer", "warn", f"Independent solve unavailable ({e}); accepting items whose arithmetic adds up.")
            blind = None
        for it in pending:
            got = evaluate(str(blind.get(it["tmp"], ""))) if isinstance(blind, dict) else it["answer"]
            if got is None:
                it["problem"] = "my independent solve could not be read"
                failed.append(it)
            elif got != it["answer"]:
                it["problem"] = f"I solved it independently and got {fmt(got)}, but the Tutor's answer is {fmt(it['answer'])}"
                failed.append(it)
            else:
                passed.append(it)

    for it in failed:
        log("Reviewer", "flag", f"FLAG {it['tmp']} ({it['kind']}: '{it['question'][:70]}'): {it['problem']}. "
                                f"{'Still wrong after the rewrite.' if recheck else 'Sending back to the Tutor.'}")
    if passed:
        verb = "Re-check passed" if recheck else "Checked"
        log("Reviewer", "recheck" if recheck else "info",
            f"{verb}: {len(passed)} item(s) add up line by line and match my independent solve "
            f"({', '.join(fmt(i['answer']) for i in passed)}).")
    return passed, failed
