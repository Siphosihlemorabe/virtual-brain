"""Practising the same idea in different forms. The Planner decides each new round (which concepts,
which forms, why); the Tutor writes the questions; the Reviewer checks them, including their visuals."""
from fractions import Fraction

from . import learner, llm, simulate
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
    "simulate": ("a dice or coin experiment the student will predict and then run in a 3D simulator. Choose ONE "
                 "experiment id from the list given with the request, set visual.event to it, and ask for exactly "
                 "that experiment's probability (the question and the id must describe the same event)",
                 '{"event":"<experiment id from the list>"}'),
}
LABELS = {"word": "Word problem", "table": "Read the table", "venn": "Venn diagram", "sample_space": "List the outcomes",
          "spot_mistake": "Spot the mistake", "reverse": "Work backwards", "career": "On the job",
          "simulate": "Predict, then simulate"}
STRETCH = ["spot_mistake", "reverse", "career"]
VISUAL_FORMS = learner.VISUAL_FORMS


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


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
    if form == "simulate" and v and v.get("event") in simulate.EVENTS:
        return f"{it['question']} (Experiment: {simulate.EVENTS[v['event']][2]}, fair dice/coins.)"
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
    if form == "simulate":
        if v.get("event") not in simulate.EVENTS:
            return f"the experiment '{v.get('event')}' is not one the simulator can run"
        truth = simulate.exact(v["event"])
        if answer != truth:
            return (f"I listed every outcome of '{simulate.EVENTS[v['event']][2]}': the exact probability is "
                    f"{truth}, but the memo says {answer}. The question and the experiment do not match: either "
                    f"pick the experiment id that matches the question, or ask exactly '{simulate.EVENTS[v['event']][2]}'")
    if form == "spot_mistake":
        flawed = parse_steps(v.get("flawed") or [])
        if not flawed:
            return "the flawed working has no calculation to inspect"
        if flawed[-1].value == answer and all(s.consistent for s in flawed):
            return "the 'mistake' version reaches the right answer with no error, so there is nothing to spot"
        if it.get("plant"):
            got = learner.classify_mistake(it["solution"], v.get("flawed") or [])
            if not got or got[0] != it["plant"]:
                return (f"the flawed working was meant to show '{learner.MISTAKES[it['plant']]}', but it shows "
                        f"{'no recognisable mistake' if not got else repr(learner.MISTAKES[got[0]])}")
    return None


def plan_round(chapter: dict, results: dict, tried: dict, log, brain=None) -> list:
    """Planner: choose concepts and forms for the next round. Model proposes, code validates and repairs."""
    levels = {}
    for pid, r in results.items():
        if r["level"] in ("gap", "partly", "understood"):
            order = {"gap": 0, "partly": 1, "understood": 2}
            levels[r["concept"]] = min(levels.get(r["concept"], "understood"), r["level"], key=order.get)
    concepts = {c["id"]: c for c in chapter["concepts"]}
    summary = [(cid, concepts[cid]["name"], levels.get(cid, "not practised"), sorted(tried.get(cid, [])))
               for cid in concepts]
    brain = brain or {}
    recurring = learner.recurring_mistakes(brain)
    record = learner.form_record(brain)
    proposal, reasoning = None, ""
    try:
        data = llm.complete_json(
            "You are the Planner agent for a Grade 10 learner. Plan the next practice round so the learner meets the "
            "same ideas in NEW forms. Concepts not yet understood need two new forms; understood ones get one stretch "
            "form (spot_mistake, reverse or career) to challenge their reasoning. Prefer forms not tried yet, and only "
            "forms that suit the concept (e.g. venn suits overlapping events).\n"
            f"Forms: {list(FORMS)}\nConcepts (id, name, level, forms tried): {summary}\n"
            f"What the brain knows about how this learner learns: {learner.summary(brain)}\n"
            "Use it: rebuild weak concepts with forms that have worked for this learner. If a recurring mistake "
            "fits a concept, add a spot_mistake for it and set plant to that mistake's key "
            f"(recurring mistake keys: {[k for k, _, _ in recurring]}).\n"
            'Return {"reasoning":"two sentences","round":[{"concept":"C1","forms":["venn"],"plant":"key or null",'
            '"why":"short"}]}')
        proposal, reasoning = data.get("round"), data.get("reasoning", "")
    except (llm.LLMError, AttributeError) as e:
        log("Planner", "warn", f"Model planning unavailable ({e}). Using rule-based round.")

    plan = []
    for p in proposal or []:
        cid = p.get("concept")
        forms = [f for f in p.get("forms", []) if f in FORMS][:2]
        if cid in concepts and forms and cid not in {x["concept"] for x in plan}:
            plant = p.get("plant") if p.get("plant") in {k for k, _, _ in recurring} and "spot_mistake" in forms else None
            plan.append({"concept": cid, "forms": forms, "why": p.get("why", ""), "plant": plant})
    for cid in concepts:  # repair: every weak concept must be practised again
        if levels.get(cid) in ("gap", "partly") and cid not in {x["concept"] for x in plan}:
            fresh = [f for f in FORMS if f not in tried.get(cid, set())] or list(FORMS)
            # forms that have worked for this learner first (visual ones for a visual thinker)
            fresh.sort(key=lambda f: (-(record.get(f, (0, 1))[0] / max(record.get(f, (0, 1))[1], 1)),
                                      0 if learner.is_visual(brain) and f in VISUAL_FORMS else 1))
            plan.append({"concept": cid, "forms": fresh[:2], "plant": None,
                         "why": "added by orchestrator: weak concepts always get another round"})
    if proposal is None:  # rule-based stretch for understood concepts
        for cid in concepts:
            if levels.get(cid) == "understood":
                fresh = [f for f in STRETCH if f not in tried.get(cid, set())] or STRETCH
                plan.append({"concept": cid, "forms": fresh[:1], "plant": None, "why": "understood, so a stretch question"})
    if reasoning:
        log("Planner", "reason", reasoning)
    log("Planner", "plan", "Next round: " + "; ".join(
        f"{concepts[p['concept']]['name']} as {' + '.join(LABELS[f] for f in p['forms'])} ({p['why']})"
        + (f" [planting your recurring mistake: {learner.MISTAKES[p['plant']]}]" if p.get("plant") else "")
        for p in plan), {"round": plan})
    return plan


def write_variants(chapter: dict, plan: list, topics: list, fmt_rules: str, log) -> list:
    """Tutor: one question per (concept, form) in the plan. Returns raw items for the Reviewer."""
    concepts = {c["id"]: c for c in chapter["concepts"]}
    def meaning(f, p):
        if f == "simulate":
            c = concepts[p["concept"]]
            fits = [(e, simulate.EVENTS[e][2]) for e in simulate.EVENTS
                    if (c.get("brain_key") or _slug(c["name"])) in simulate.EVENTS[e][3]] or simulate.menu()
            return FORMS[f][0] + f". Experiments for this concept (id, event): {fits}"
        if f == "spot_mistake" and p.get("plant"):
            return FORMS[f][0] + f". The ONE mistake must be this kind: {learner.MISTAKES[p['plant']]}"
        return FORMS[f][0]

    asks = [(p["concept"], concepts[p["concept"]]["name"], f, meaning(f, p), FORMS[f][1]) for p in plan for f in p["forms"]]
    plants = {(p["concept"], "spot_mistake"): p["plant"] for p in plan if p.get("plant")}
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
                        "visual": p.get("visual"), "solution": p.get("solution") or [],
                        "plant": plants.get((p["concept"], p["form"]))})
    log("Tutor", "info", f"Wrote {len(out)} new questions: "
                         + ", ".join(LABELS[i["form"]] for i in out) + ". Handing them to the Reviewer.")
    return out
