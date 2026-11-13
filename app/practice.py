"""Practising the same idea in different forms. The Planner decides each new round (which concepts,
which forms, why); the Tutor writes the questions; the Reviewer checks them, including their visuals."""
from fractions import Fraction

from . import llm
from .mathcheck import parse_steps

# form -> (what the Tutor must write, which visual it must include)
FORMS = {
    "word": ("an everyday South African word problem", None),
    "table": ("the data is given in a small table; the question refers to the table",
              '{"headers":["..."],"rows":[["...", 3]]}'),
    "venn": ("the data is shown in a Venn diagram of two sets; the question refers to the diagram",
             '{"a":"set A label","b":"set B label","only_a":0,"only_b":0,"both":0,"neither":0}'),
    "sample_space": ("the student lists the sample space first; show every equally likely outcome",
                     '{"outcomes":["H1","H2"]}'),
    "spot_mistake": ("show a short worked solution by a learner that contains exactly ONE mistake; the student must "
                     "find it and write the correct working. 'solution' is the correct working",
                     '{"flawed":["one calculation per line, with one mistake"]}'),
    "reverse": ("work backwards: give a probability and ask for an unknown count", None),
    "career": ("set inside a real South African job (e.g. a nurse, insurance assessor, data analyst, farmer)", None),
}
LABELS = {"word": "Word problem", "table": "Read the table", "venn": "Venn diagram", "sample_space": "List the outcomes",
          "spot_mistake": "Spot the mistake", "reverse": "Work backwards", "career": "On the job"}
STRETCH = ["spot_mistake", "reverse", "career"]


def blind_text(it: dict) -> str:
    """The question plus its visual, as text, for the Reviewer's independent solve."""
    v, form = it.get("visual") or {}, it.get("form")
    if form == "table" and v:
        rows = "; ".join(", ".join(str(c) for c in r) for r in v.get("rows", []))
        return f"{it['question']} Table columns: {', '.join(map(str, v.get('headers', [])))}. Rows: {rows}."
    if form == "venn" and v:
        return (f"{it['question']} Venn diagram: only {v.get('a')} = {v.get('only_a')}, both = {v.get('both')}, "
                f"only {v.get('b')} = {v.get('only_b')}, neither = {v.get('neither', 0)}.")
    if form == "sample_space" and v:
        return f"{it['question']} Outcomes: {', '.join(map(str, v.get('outcomes', [])))}."
    if form == "spot_mistake" and v:
        return f"{it['question']} The learner's working: {' | '.join(v.get('flawed', []))}. Give the correct final answer."
    return it["question"]


def visual_problem(it: dict, answer: Fraction):
    """Code checks on a question's visual. Returns a reason it is wrong, or None."""
    form, v = it.get("form"), it.get("visual")
    if FORMS.get(form, (None, None))[1] is None:
        return None
    if not isinstance(v, dict):
        return f"the {LABELS.get(form, form)} question has no {form} to show"
    if form == "table":
        rows, heads = v.get("rows"), v.get("headers")
        if not (isinstance(rows, list) and rows and isinstance(heads, list)
                and all(isinstance(r, list) and len(r) == len(heads) for r in rows)):
            return "the table's rows do not match its columns"
    if form == "venn":
        parts = [v.get(k, 0) for k in ("only_a", "only_b", "both", "neither")]
        if not all(isinstance(x, int) and x >= 0 for x in parts):
            return "the Venn diagram needs whole, non-negative counts in every region"
    if form == "sample_space":
        out = v.get("outcomes")
        if not (isinstance(out, list) and 1 < len(out) <= 36 and len(set(map(str, out))) == len(out)):
            return "the sample space must list 2 to 36 different outcomes"
        if answer.denominator > 1 and len(out) % answer.denominator:
            return f"the answer {answer} cannot come from {len(out)} equally likely outcomes"
    if form == "spot_mistake":
        flawed = parse_steps(v.get("flawed") or [])
        if not flawed:
            return "the flawed working has no calculation to inspect"
        if flawed[-1].value == answer and all(s.consistent for s in flawed):
            return "the 'mistake' version reaches the right answer with no error, so there is nothing to spot"
    return None


def plan_round(chapter: dict, results: dict, tried: dict, log) -> list:
    """Planner: choose concepts and forms for the next round. Model proposes, code validates and repairs."""
    levels = {}
    for pid, r in results.items():
        if r["level"] in ("gap", "partly", "understood"):
            order = {"gap": 0, "partly": 1, "understood": 2}
            levels[r["concept"]] = min(levels.get(r["concept"], "understood"), r["level"], key=order.get)
    concepts = {c["id"]: c for c in chapter["concepts"]}
    summary = [(cid, concepts[cid]["name"], levels.get(cid, "not practised"), sorted(tried.get(cid, [])))
               for cid in concepts]
    proposal, reasoning = None, ""
    try:
        data = llm.complete_json(
            "You are the Planner agent for a Grade 10 learner. Plan the next practice round so the learner meets the "
            "same ideas in NEW forms. Concepts not yet understood need two new forms; understood ones get one stretch "
            "form (spot_mistake, reverse or career) to challenge their reasoning. Prefer forms not tried yet, and only "
            "forms that suit the concept (e.g. venn suits overlapping events).\n"
            f"Forms: {list(FORMS)}\nConcepts (id, name, level, forms tried): {summary}\n"
            'Return {"reasoning":"two sentences","round":[{"concept":"C1","forms":["venn"],"why":"short"}]}')
        proposal, reasoning = data.get("round"), data.get("reasoning", "")
    except (llm.LLMError, AttributeError) as e:
        log("Planner", "warn", f"Model planning unavailable ({e}). Using rule-based round.")

    plan = []
    for p in proposal or []:
        cid = p.get("concept")
        forms = [f for f in p.get("forms", []) if f in FORMS][:2]
        if cid in concepts and forms and cid not in {x["concept"] for x in plan}:
            plan.append({"concept": cid, "forms": forms, "why": p.get("why", "")})
    for cid in concepts:  # repair: every weak concept must be practised again
        if levels.get(cid) in ("gap", "partly") and cid not in {x["concept"] for x in plan}:
            fresh = [f for f in FORMS if f not in tried.get(cid, set())] or list(FORMS)
            plan.append({"concept": cid, "forms": fresh[:2],
                         "why": "added by orchestrator: weak concepts always get another round"})
    if proposal is None:  # rule-based stretch for understood concepts
        for cid in concepts:
            if levels.get(cid) == "understood":
                fresh = [f for f in STRETCH if f not in tried.get(cid, set())] or STRETCH
                plan.append({"concept": cid, "forms": fresh[:1], "why": "understood, so a stretch question"})
    if reasoning:
        log("Planner", "reason", reasoning)
    log("Planner", "plan", "Next round: " + "; ".join(
        f"{concepts[p['concept']]['name']} as {' + '.join(LABELS[f] for f in p['forms'])} ({p['why']})" for p in plan),
        {"round": plan})
    return plan


def write_variants(chapter: dict, plan: list, topics: list, fmt_rules: str, log) -> list:
    """Tutor: one question per (concept, form) in the plan. Returns raw items for the Reviewer."""
    concepts = {c["id"]: c for c in chapter["concepts"]}
    asks = [(p["concept"], concepts[p["concept"]]["name"], f, FORMS[f][0], FORMS[f][1]) for p in plan for f in p["forms"]]
    seen = [p["question"] for p in chapter["problems"]]
    try:
        data = llm.complete_json(
            "You are the Tutor agent for a South African Grade 10 maths learner (CAPS). Write one new practice "
            "question for each request below: same concept, presented in the requested form. Do not repeat these "
            f"earlier questions: {seen}\n" + fmt_rules + "\n"
            "Requests (concept id, concept, form, what the form means, visual to include or None):\n"
            f"{asks}\n"
            'Return {"problems":[{"concept":"C1","form":"venn","question":"...","visual":{...} or null,'
            '"solution":["..."]}]}', timeout=180)
    except llm.LLMError as e:
        log("Tutor", "warn", f"I could not write the new round ({e}).")
        return []
    wanted = {(c, f) for c, _, f, _, _ in asks}
    out = []
    for p in data.get("problems", []) if isinstance(data, dict) else []:
        if (p.get("concept"), p.get("form")) in wanted:
            out.append({"kind": "problem", "concept": p["concept"], "form": p["form"], "question": p.get("question", ""),
                        "visual": p.get("visual"), "solution": p.get("solution") or []})
    log("Tutor", "info", f"Wrote {len(out)} new questions: "
                         + ", ".join(LABELS[i["form"]] for i in out) + ". Handing them to the Reviewer.")
    return out
