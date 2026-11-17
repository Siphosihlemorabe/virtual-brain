"""The learner model inside the brain: how this student thinks, where they slip, and what works for them.
Every entry is detected in code from marked work, keeps its evidence, and changes what the agents do.
An entry only drives behaviour once it has been seen at least CONFIRM times."""
import re
import time

from .mathcheck import parse_steps

CONFIRM = 2

TRAITS = {
    "own_methods": ("Solves problems their own valid way",
                    "Feedback and the Planner treat your method as valid, and show the book's method as a second route."),
    "concise": ("Works steps out in their head and writes fewer lines",
                "Marking never takes marks off for missing steps when the answer is proven right."),
    "visual": ("Thinks visually: draws diagrams, tables or lists",
               "The Planner rebuilds weak concepts with Venn diagrams, tables, outcome lists and 3D simulations."),
}
MISTAKES = {
    "multiplies_instead_of_adds": "Multiplies where they should add (e.g. like terms: 3x + 2x is 5x, not 6x)",
    "adds_instead_of_multiplies": "Adds where they should multiply",
    "miscounts_outcomes": "Miscounts the outcomes they want (the top of the fraction)",
    "wrong_total": "Uses the wrong total (the bottom of the fraction)",
    "arithmetic_slip": "Arithmetic slips: a calculation that does not add up",
    "wrong_value": "Uses a wrong rule or value (e.g. 360 instead of 180)",
}
MISTAKE_EFFECT = "The Planner plants this exact mistake in spot-the-mistake questions so you learn to catch it."
VISUAL_FORMS = {"venn", "table", "sample_space", "simulate"}


def _profile(brain: dict) -> dict:
    prof = brain.setdefault("learner", {})
    for part in ("traits", "mistakes", "forms"):  # other modules (e.g. careers) may create the section first
        prof.setdefault(part, {})
    return prof


def _ops(expr: str):
    return set(re.findall(r"[+*]", expr)), sorted(re.findall(r"\d+(?:\.\d+)?", expr))


def classify_mistake(solution: list, student_lines: list):
    """Code classification of the first place the student's working departs from the correct working."""
    t, s = parse_steps(solution), parse_steps(student_lines)
    if not s:
        return None
    slip = next((x for x in s if not x.consistent), None)
    if slip:
        return "arithmetic_slip", slip.text
    for i, ts in enumerate(t):
        ss = next((x for x in s if x.label and x.label == ts.label), s[i] if i < len(s) else None)
        if ss is None or ss.value == ts.value:
            continue
        (s_ops, s_nums), (t_ops, t_nums) = _ops(ss.first_expr), _ops(ts.first_expr)
        if s_nums == t_nums and s_ops == {"*"} and "+" in t_ops:
            return "multiplies_instead_of_adds", ss.text
        if s_nums == t_nums and s_ops == {"+"} and "*" in t_ops:
            return "adds_instead_of_multiplies", ss.text
        sv, tv = ss.value, ts.value
        if 0 < tv < 1 and 0 < sv <= 1:
            sn, sd = ss.first_expr.split("/")[:2] if ss.first_expr.count("/") == 1 else (None, None)
            tn, td = ts.first_expr.split("/")[:2] if ts.first_expr.count("/") == 1 else (None, None)
            if sd and td and sd.strip() == td.strip():
                return "miscounts_outcomes", ss.text
            if sn and tn and sn.strip() == tn.strip():
                return "wrong_total", ss.text
        return "wrong_value", ss.text
    return None


def observe(brain: dict, chapter: dict, results: dict, work: dict, keymap: dict, log) -> list:
    """Update the learner model from one checked round. Returns what was newly noticed, for the student."""
    prof, today, noticed = _profile(brain), time.strftime("%Y-%m-%d %H:%M"), []
    subject = chapter.get("subject") or "this chapter"
    names = {c["id"]: c["name"] for c in chapter["concepts"]}
    by_id = {p["id"]: p for p in chapter["problems"]}

    def add(kind, key, label, where, detail):
        bucket = prof[kind].setdefault(key, {"label": label, "evidence": []})
        if any(e["where"] == where for e in bucket["evidence"]):
            return  # the same question handed in again is not new evidence
        bucket["evidence"].append({"when": today, "where": where, "detail": detail})
        n = len(bucket["evidence"])
        status = "now confirmed, so your colleague will act on it" if n == CONFIRM else (
            "seen once, watching for it" if n < CONFIRM else f"seen {n} times")
        log("Brain", "learn", f"Noticed: {label.lower()} ({where}). {status[0].upper() + status[1:]}.")
        noticed.append({"kind": kind, "key": key, "label": label, "where": where, "count": n,
                        "confirmed": n >= CONFIRM})

    for pid, r in results.items():
        p, lines = by_id.get(pid), work.get(pid, [])
        if not p or r["level"] not in ("gap", "partly", "understood"):
            continue
        where = f"{subject} {pid}, {names.get(p['concept'], '')}"
        form = p.get("form", "word")
        stats = prof["forms"].setdefault(form, {"tried": 0, "understood": 0, "seen": []})
        if where not in stats.setdefault("seen", []):
            stats["seen"].append(where)
            stats["tried"] += 1
            stats["understood"] += r["level"] == "understood"

        overturned = r.get("checker", {}).get("level") not in (None, "understood") and r["level"] == "understood"
        other_method = r["level"] == "understood" and (r.get("method") or {}).get("uses_book") is False
        if overturned or other_method:
            fewer = len(parse_steps(lines)) < len(parse_steps(p["solution"]))
            key = "concise" if fewer else "own_methods"
            add("traits", key, TRAITS[key][0], where, "a correct answer that did not follow the book's method")
        if re.search(r"\b(venn|diagram|table|tree|draw|drew|list(ed)?)\b", " ".join(lines), re.I):
            add("traits", "visual", TRAITS["visual"][0], where, "used a diagram, table or list in their working")
        if r["level"] in ("gap", "partly"):
            m = classify_mistake(p["solution"], lines)
            if m:
                add("mistakes", m[0], MISTAKES[m[0]], where, m[1])
    return noticed


# ---------------------------------------------------------------- what the agents read

def recurring_mistakes(brain: dict) -> list:
    return [(k, v["label"], len(v["evidence"])) for k, v in _profile(brain)["mistakes"].items()
            if len(v["evidence"]) >= CONFIRM]


def form_record(brain: dict) -> dict:
    return {f: (s["understood"], s["tried"]) for f, s in _profile(brain)["forms"].items()}


def is_visual(brain: dict) -> bool:
    return len(_profile(brain)["traits"].get("visual", {}).get("evidence", [])) >= CONFIRM


def summary(brain: dict) -> str:
    """One paragraph the language model can use to tailor plans and feedback."""
    prof = _profile(brain)
    traits = [f"{v['label']} (seen {len(v['evidence'])}x)" for v in prof["traits"].values() if len(v["evidence"]) >= CONFIRM]
    mistakes = [f"{lbl} (seen {n}x)" for _, lbl, n in recurring_mistakes(brain)]
    forms = [f"{f}: {u}/{t} understood" for f, (u, t) in form_record(brain).items()]
    return (f"Confirmed traits: {traits or 'none yet'}. Recurring mistakes: {mistakes or 'none yet'}. "
            f"Results by practice form: {forms or 'none yet'}.")


def view(brain: dict) -> dict:
    """The learner model for the UI, each entry paired with what the colleague does with it."""
    prof = _profile(brain)
    traits = [{"key": k, "label": v["label"], "count": len(v["evidence"]), "confirmed": len(v["evidence"]) >= CONFIRM,
               "effect": TRAITS[k][1], "evidence": v["evidence"][-3:]} for k, v in prof["traits"].items()]
    mistakes = [{"key": k, "label": v["label"], "count": len(v["evidence"]), "confirmed": len(v["evidence"]) >= CONFIRM,
                 "effect": MISTAKE_EFFECT, "evidence": v["evidence"][-3:]} for k, v in prof["mistakes"].items()]
    forms = [{"form": f, "understood": s["understood"], "tried": s["tried"]} for f, s in prof["forms"].items()]
    return {"traits": traits, "mistakes": mistakes, "forms": forms, "confirm": CONFIRM}
