"""The learner's virtual brain: a growing map of concepts, levels, notes and links.
All updates are plain code so they are reliable and explainable."""
import json
import re
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "brain.json"
SEED = ROOT / "samples" / "curriculum.json"
RANK = {"gap": 0, "partly": 1, "understood": 2}
_lock = threading.Lock()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _seed() -> dict:
    seed = json.loads(SEED.read_text(encoding="utf-8"))["concepts"]
    return {"concepts": {k: {**v, "level": None, "history": [], "notes": [], "careers": []} for k, v in seed.items()}}


def load() -> dict:
    with _lock:
        if PATH.exists():
            return json.loads(PATH.read_text(encoding="utf-8"))
        return _seed()


def save(brain: dict):
    with _lock:
        PATH.parent.mkdir(exist_ok=True)
        PATH.write_text(json.dumps(brain, indent=2), encoding="utf-8")


def reset():
    save(_seed())


def summary(brain: dict) -> list:
    """(key, name, level) for the Planner and model prompts."""
    return [(k, c["name"], c["level"]) for k, c in brain["concepts"].items()]


def resolve_key(brain: dict, concept: dict) -> str:
    """Map a chapter concept onto the brain: model's suggested key if it exists, else by name."""
    k = concept.get("brain_key")
    if k in brain["concepts"]:
        return k
    return slug(concept["name"])


def update(brain: dict, chapter: dict, results: dict, notes: str, log) -> dict:
    """Apply one upload: levels from verified marks, the student's notes, and new links."""
    today = time.strftime("%Y-%m-%d %H:%M")
    keymap = {}
    for c in chapter["concepts"]:
        key = resolve_key(brain, c)
        keymap[c["id"]] = key
        node = brain["concepts"].get(key)
        if node is None:
            node = brain["concepts"][key] = {"name": c["name"], "subject": chapter.get("subject", ""),
                                             "builds_on": [], "level": None, "history": [], "notes": [], "careers": []}
            log("Brain", "info", f"New concept added: {c['name']}.")
        for b in c.get("builds_on", []):
            if b in brain["concepts"] and b != key and b not in node["builds_on"]:
                node["builds_on"].append(b)
                log("Brain", "info", f"New link: {node['name']} builds on {brain['concepts'][b]['name']}.")

    # level per concept = weakest verified mark among its problems in this upload
    evidence = {}
    for pid, r in results.items():
        if r["level"] in RANK:
            key = keymap[r["concept"]]
            evidence.setdefault(key, []).append((r["level"], pid))
    for key, marks in evidence.items():
        node = brain["concepts"][key]
        level = min((m[0] for m in marks), key=RANK.get)
        old = node["level"]
        node["level"] = level
        node["history"].append({"when": today, "level": level, "from": [m[1] for m in marks]})
        change = "new" if old is None else ("unchanged" if old == level else f"{old} → {level}")
        log("Brain", "update", f"{node['name']}: {level.upper()} ({change}).")

    for line in [l.strip() for l in notes.splitlines() if l.strip()]:
        m = re.match(r"(C\d+)\s*:\s*(.+)", line)
        targets = [keymap[m.group(1)]] if m and m.group(1) in keymap else list(keymap.values())
        text = m.group(2) if m and m.group(1) in keymap else line
        targets = [k for k in targets if text not in (n["text"] for n in brain["concepts"][k]["notes"])]
        for key in targets:
            brain["concepts"][key]["notes"].append({"when": today, "text": text})
        if targets:
            log("Brain", "info", f"Saved your note to {', '.join(brain['concepts'][k]['name'] for k in targets)}.")
    save(brain)
    return keymap
