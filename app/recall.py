"""Recall: when a student struggles, the brain proposes the earlier topic that is the likely cause,
and the Reviewer confirms it from the evidence before the student is sent back. All plain code."""
from .brain import RANK, slug
from .mathcheck import parse_steps


def ancestors(brain: dict, key: str) -> list:
    """Earlier topics this one builds on, nearest first."""
    out, frontier = [], [key]
    while frontier:
        nxt = []
        for k in frontier:
            for b in brain["concepts"].get(k, {}).get("builds_on", []):
                if b not in out and b != key:
                    out.append(b)
                    nxt.append(b)
        frontier = nxt
    return out


def hypothesise(brain: dict, key: str):
    """Brain's guess: the weakest earlier topic (gap, then partly, then never tested), nearest first."""
    weak = [a for a in ancestors(brain, key) if brain["concepts"][a]["level"] != "understood"]
    order = lambda a: RANK.get(brain["concepts"][a]["level"], 3)  # never tested ranks after partly
    return min(weak, key=order) if weak else None


def skill_of_wrong_step(problem: dict, step_no):
    """The skill the textbook says the wrong step relies on, from its (uses: ...) tag."""
    steps = parse_steps(problem["solution"])
    if not step_no or not steps:
        return None
    return steps[min(step_no, len(steps)) - 1].uses or None


def confirm(brain: dict, key: str, problem: dict, step_no, guess, names=None):
    """Reviewer's check of the brain's guess. Returns (cause_key or None, verdict text).
    names maps a topic name's slug to its brain key (chapter wording can differ from the brain's)."""
    skill = skill_of_wrong_step(problem, step_no)
    if not skill:
        level = brain["concepts"][guess]["level"]
        if level in ("gap", "partly"):
            return guess, f"the textbook does not tag this step, but the brain has evidence {brain['concepts'][guess]['name']} is a {level}"
        return None, (f"there is no evidence: the textbook does not tag step {step_no} and "
                      f"{brain['concepts'][guess]['name']} has never been tested. Revise this chapter first")
    skill_key = (names or {}).get(slug(skill), slug(skill))
    if skill_key == key:
        return None, (f"step {step_no} uses {skill} itself, so this is not caused by an earlier topic. "
                      "Revise this chapter's rule")
    if skill_key == guess:
        return guess, f"step {step_no} uses {skill}, and the brain shows that topic is weak"
    if skill_key in ancestors(brain, key) and brain["concepts"][skill_key]["level"] != "understood":
        return skill_key, f"step {step_no} actually uses {skill}, not the brain's first guess"
    if skill_key in brain["concepts"] and brain["concepts"][skill_key]["level"] == "understood":
        return None, f"step {step_no} uses {skill}, which the brain shows is understood, so it is not the cause"
    return None, f"step {step_no} uses {skill}, which is not an earlier topic this one builds on. Revise this chapter's rule"


def run(brain: dict, keymap: dict, chapter: dict, results: dict, log) -> list:
    by_id = {p["id"]: p for p in chapter["problems"]}
    names = {slug(c["name"]): k for k, c in brain["concepts"].items()}
    names.update({slug(c["name"]): keymap[c["id"]] for c in chapter["concepts"]})
    out = []
    for pid, r in results.items():
        if r["level"] not in ("gap", "partly"):
            continue
        key = keymap[r["concept"]]
        name = brain["concepts"][key]["name"]
        guess = hypothesise(brain, key)
        if guess is None:
            log("Brain", "info", f"{pid}: no weak earlier topic under {name}. Revise this chapter.")
            continue
        gname = brain["concepts"][guess]["name"]
        log("Brain", "recall", f"{pid} ({name}) is a {r['level']}. Likely cause: an earlier topic, "
                               f"{gname} (level: {brain['concepts'][guess]['level'] or 'never tested'}). "
                               "Asking the Reviewer to confirm.")
        cause, why = confirm(brain, key, by_id[pid], r.get("step"), guess, names)
        if cause == guess:
            log("Reviewer", "recheck", f"Confirmed for {pid}: {why}.")
        elif cause is None:
            log("Reviewer", "flag", f"Rejected the brain's guess for {pid}: {why}.")
        else:
            log("Reviewer", "flag", f"Corrected the brain's guess for {pid}: {why}.")
        if cause:
            node = brain["concepts"][cause]
            notes = [n["text"] for n in node["notes"]]
            msg = f"Revise {node['name']} first, then come back to {pid}."
            log("Brain", "recall", msg + (f" Your own note: “{notes[-1]}”" if notes else ""))
        else:
            notes, msg = [], f"Stay on {name} for now. No earlier topic is proven to be the cause."
        out.append({"problem": pid, "topic": name, "guess": gname,
                    "cause": brain["concepts"][cause]["name"] if cause else None,
                    "confirmed": cause == guess, "why": why, "message": msg, "notes": notes})
    return out
