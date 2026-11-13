"""Career guide agent: for each concept the student has mastered, choose careers from a curated
South African catalogue that fit the student's interests and way of learning, and set a mission in
that job. The Reviewer checks every pick, every number and every brief, and later the hand maths."""
import json
import re
import time
from fractions import Fraction
from pathlib import Path

from . import learner, llm
from .missions import TEMPLATES, clean_params, plain_brief, run
from .mathcheck import fmt, parse_steps

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "samples" / "careers.json"


def catalogue() -> dict:
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))


def interests(brain: dict) -> list:
    return learner._profile(brain).setdefault("interests", [])


def set_interests(brain: dict, chosen: list) -> list:
    valid = catalogue()["interests"]
    learner._profile(brain)["interests"] = [i for i in chosen if i in valid]
    return brain["learner"]["interests"]


def pathways(brain: dict) -> list:
    """Every career with how far the student is along it: mastered Grade 10 concepts it builds on."""
    cat, mine, out = catalogue(), set(interests(brain)), []
    concepts = brain["concepts"]
    for cid, c in cat["careers"].items():
        needs = [{"key": k, "name": concepts.get(k, {}).get("name", k), "level": concepts.get(k, {}).get("level")}
                 for k in c["needs"]]
        done = sum(n["level"] == "understood" for n in needs)
        out.append({"id": cid, "name": c["name"], "about": c["about"], "subjects": c["subjects"],
                    "match": sorted(mine & set(c["interests"])), "needs": needs, "done": done, "total": len(needs)})
    out.sort(key=lambda p: (-len(p["match"]), -p["done"] / p["total"], p["name"]))
    return out


def _numbers(text: str) -> set:
    return set(re.findall(r"\d+", text))


def _faithful_brief(brief: str, params: dict) -> list:
    """Numbers the brief should mention but does not."""
    have = _numbers(brief)
    return [f"{k}={v}" for k, v in params.items() if str(v) not in have]


class CareerGuide:
    name = "Career guide"

    def __init__(self, log, counters):
        self.log, self.counters = log, counters

    def eligible(self, brain: dict) -> list:
        cat, ready = catalogue(), {k for k, c in brain["concepts"].items() if c["level"] == "understood"}
        return [(cid, c, m) for cid, c in cat["careers"].items() for m in c["missions"]
                if TEMPLATES[m]["concept"] in ready]

    def plan(self, brain: dict) -> list:
        cat, mine = catalogue(), interests(brain)
        options = self.eligible(brain)
        if not options:
            self.log(self.name, "info", "No concept is mastered yet, so there is no mission to set. "
                                        "Your pathways show what each career needs.")
            return []
        names = {k: c["name"] for k, c in brain["concepts"].items()}
        menu = [(cid, c["name"], c["interests"], m, TEMPLATES[m]["title"], names.get(TEMPLATES[m]["concept"]),
                 {n: f"{TEMPLATES[m]['labels'][n]} ({lo}-{hi})" for n, (_, lo, hi) in TEMPLATES[m]["params"].items()})
                for cid, c, m in options]
        picks, reasoning = None, ""
        try:
            data = llm.complete_json(
                "You are the Career guide agent for a South African Grade 10 learner. Choose up to 2 different careers "
                "from the menu, with one mission each, that best fit this learner. Prefer careers that match their "
                f"interests ({[cat['interests'][i] for i in mine] or 'not given'}), and use how they learn: "
                f"{learner.summary(brain)}\n"
                "For each pick, choose realistic whole-number inputs within the ranges, and write a 2-3 sentence brief "
                "that puts the learner in that job today (South African setting), using EVERY input number.\n"
                f"Menu (career id, career, interests, mission key, mission, maths it uses, inputs): {menu}\n"
                'Return {"reasoning":"one sentence","picks":[{"career":"id","mission":"key","why":"one sentence for the '
                'learner","inputs":{"name":0},"brief":"..."}]}', timeout=120)
            picks, reasoning = data.get("picks"), data.get("reasoning", "")
        except (llm.LLMError, AttributeError) as e:
            self.log(self.name, "warn", f"Model unavailable ({e}). Choosing by your interests instead.")
        if reasoning:
            self.log(self.name, "reason", reasoning)

        allowed = {(cid, m) for cid, _, m in options}
        chosen, used = [], set()
        for p in picks or []:
            key = (p.get("career"), p.get("mission"))
            if key not in allowed:
                self.log("Reviewer", "flag", f"Rejected the pick {key}: not in the catalogue, or its maths is not mastered yet.")
                continue
            if key[0] not in used and len(chosen) < 2:
                chosen.append(p)
                used.add(key[0])
        if len(chosen) < 2:  # top up with a different career: interest match first, then the one closest to complete
            ranked = sorted(options, key=lambda o: (-len(set(mine) & set(o[1]["interests"])),
                                                    -sum(brain["concepts"].get(n, {}).get("level") == "understood"
                                                         for n in o[1]["needs"]) / len(o[1]["needs"])))
            for cid, c, m in ranked:
                if cid not in used and len(chosen) < 2:
                    match = [cat["interests"][i] for i in mine if i in c["interests"]]
                    why = (f"It matches your interest in {' and '.join(match)} and uses "
                           if match else "It uses ") + f"{names.get(TEMPLATES[m]['concept'])}, which you have mastered."
                    chosen.append({"career": cid, "mission": m, "inputs": {}, "brief": "", "why": why})
                    used.add(cid)
                    if picks:
                        self.log(self.name, "info", f"Added {c['name']} so you see two different careers.")

        cards = [self._card(i, p, brain, cat) for i, p in enumerate(chosen)]
        self._review_briefs(cards)
        for c in cards:
            article = "an" if c["name"][0].lower() in "aeiou" else "a"
            self.log(self.name, "career", f"Mission for you as {article} {c['name'].lower()}: {c['title']} "
                                          f"({c['concept_name']}). {c['why']}")
        return cards

    def _card(self, i, pick, brain, cat):
        cid, m = pick["career"], pick["mission"]
        t, c = TEMPLATES[m], cat["careers"][cid]
        params, problems = clean_params(m, pick.get("inputs"))
        if problems:
            self.log("Reviewer", "flag", f"{c['name']} mission inputs fixed: {'; '.join(problems)}. Using safe defaults.")
        concept_name = brain["concepts"][t["concept"]]["name"]
        card = {"id": f"K{i + 1}", "career": cid, "name": c["name"], "about": c["about"], "subjects": c["subjects"],
                "mission": m, "title": t["title"], "concept": t["concept"], "concept_name": concept_name,
                "chain": [concept_name, t["title"], c["name"]], "why": pick.get("why", ""),
                "brief": str(pick.get("brief") or ""), "params": params, "check": t["check"], "task": t["task"],
                "labels": t["labels"], "whatif": [{"name": n, "label": t["labels"][n], "min": t["params"][n][1],
                                                   "max": t["params"][n][2]} for n in t["whatif"]]}
        self._run(card)
        return card

    @staticmethod
    def _run(card):
        card["code"], card["output"], values = run(card["mission"], card["params"])
        card["answers"] = {k: fmt(v) for k, v in values.items()}

    def _review_briefs(self, cards):
        """Reviewer: a brief must use the mission's real numbers, or the student would compute from a different story."""
        missing = [c for c in cards if not c["brief"]]  # rule-based picks: no story written yet
        bad = [c for c in cards if c["brief"] and _faithful_brief(c["brief"], c["params"])]
        for c in bad:
            self.log("Reviewer", "flag", f"FLAG {c['name']} brief: it does not use the mission's numbers "
                                         f"({', '.join(_faithful_brief(c['brief'], c['params']))}). Sending back to the Career guide.")
        if not bad and not missing:
            if cards:
                self.log("Reviewer", "info", "Checked every mission: inputs are valid and each brief uses the exact numbers the code runs on.")
            return
        try:
            data = llm.complete_json(
                "You are the Career guide. Rewrite each brief in 2-3 sentences for a South African Grade 10 learner doing "
                "this job today. Use EVERY number given, exactly as written, with its meaning.\n"
                f"{[(c['id'], c['name'], c['title'], {c['labels'][k]: v for k, v in c['params'].items()}) for c in bad + missing]}\n"
                'Return {"K1":"brief", ...}', timeout=90)
        except llm.LLMError:
            data = {}
        for c in bad + missing:
            new = str((data or {}).get(c["id"], "")) if isinstance(data, dict) else ""
            if new and not _faithful_brief(new, c["params"]):
                c["brief"] = new
                if c in bad:
                    self.counters["reviewer_corrections"] += 1
                    self.log("Reviewer", "recheck", f"Re-check passed: the {c['name']} brief now uses every number.")
            elif c in missing:
                c["brief"] = plain_brief(c["mission"], c["params"])
            else:
                c["brief"] = plain_brief(c["mission"], c["params"])
                self.log("Reviewer", "info", f"Using a plain brief for {c['name']} so the numbers are guaranteed right.")


def whatif(card: dict, changes: dict) -> dict:
    """Re-run the mission with new inputs from the sliders. Does not change the hand task."""
    allowed = {w["name"] for w in card["whatif"]}
    proposed = {**card["params"], **{k: v for k, v in (changes or {}).items() if k in allowed}}
    params, problems = clean_params(card["mission"], proposed)
    if problems:
        return {"ok": False, "msg": "; ".join(problems)}
    _, output, values = run(card["mission"], params)
    return {"ok": True, "output": output, "values": {k: fmt(v) for k, v in values.items()}, "params": params}


def demo_hand(card: dict, slip: bool) -> str:
    """Demo helper: the correct hand working, or the same with one arithmetic slip for the Reviewer to catch."""
    values = {k: Fraction(v) for k, v in card["answers"].items()}
    lines = TEMPLATES[card["mission"]]["hand"](card["params"], values)
    if slip:
        first = lines[0].rsplit("=", 1)
        wrong = values[card["check"][0]] + Fraction(1, 2) if values[card["check"][0]].denominator == 1 else \
            Fraction(values[card["check"][0]].numerator, values[card["check"][0]].denominator * 2)
        lines[0] = f"{first[0]}= {fmt(wrong)}"
    return "\n".join(lines)


def check_hand_maths(card: dict, text: str) -> dict:
    """Reviewer's check: every hand step must add up and match the value the code computed."""
    expected = {k: Fraction(v) for k, v in card["answers"].items()}
    steps = parse_steps([l for l in text.splitlines() if l.strip()])
    if not steps:
        return {"ok": False, "msg": f"I could not find any calculations. Write one line per value, starting with "
                                    f"'{card['check'][0]} = ...'."}
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
    node["careers"] = [c for c in node.get("careers", []) if c["career"] != card["name"]]
    node["careers"].append({"career": card["name"], "application": card["title"], "use": card["about"],
                            "proven": time.strftime("%Y-%m-%d %H:%M")})
