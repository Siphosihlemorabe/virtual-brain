"""Virtual Brain web server. Run: python -m uvicorn app.main:app --port 8000"""
import json
import re
import threading
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import brain as brainstore
from . import career
from . import llm, simulate, spamlab
from .orchestrator import Session

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
app = FastAPI(title="Virtual Brain")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
current = Session()

# Sample chapters a student can try, with optional sample answers and notes for the demo.
CHAPTERS = {
    "probability": {"title": "Probability (with worked solutions)", "chapter": "probability_chapter.txt",
                    "answers": "student_working.txt", "answers_retry": "student_working_retry.txt",
                    "notes": "student_notes.txt"},
    "probability_explainer": {"title": "Probability (explanation only, no examples)",
                              "chapter": "probability_explainer.txt"},
    "algebra": {"title": "Algebra: solving equations", "chapter": "algebra_chapter.txt",
                "answers": "algebra_working.txt", "notes": "algebra_notes.txt"},
    "geometry": {"title": "Euclidean geometry", "chapter": "geometry_chapter.txt", "answers": "geometry_working.txt"},
}


def _busy():
    if current.stage in ("preparing", "checking", "designing", "careering"):
        raise HTTPException(409, "Your colleague is still working. Give it a moment.")


def _split(text: str, pattern: str) -> dict:
    """'P1: ...' or 'C2: ...' blocks -> {id: text}."""
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(pattern + r"\s*[:.)]\s*(.*?)(?=^\s*[PC]\d+\s*[:.)]|\Z)", text, flags=re.M | re.S)}


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/sim/events")
def sim_events():
    return simulate.catalogue()


def _threshold(t):
    from fractions import Fraction
    try:
        v = Fraction(str(t)).limit_denominator(100)
    except (ValueError, ZeroDivisionError):
        v = Fraction(1, 2)
    return min(max(v, Fraction(1, 20)), Fraction(19, 20))


@app.get("/api/spamlab")
def spam_payload():
    current.spam_open()
    return spamlab.payload()


def _spam_call(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/spamlab/table")
def spam_table(words: str = Form("[]"), table: str = Form("{}")):
    return _spam_call(current.spam_table, json.loads(words), json.loads(table))


@app.post("/api/spamlab/hand")
def spam_hand(words: str = Form("[]"), working: str = Form("")):
    return _spam_call(current.spam_hand, json.loads(words), working)


@app.get("/api/spamlab/demo")
def spam_demo(words: str = "[]", slip: bool = False, part: str = "table"):
    w = _spam_call(current._spam_words, json.loads(words))
    if part == "hand":
        return {"working": spamlab.demo_hand(spamlab.HAND_EMAIL, w, slip)}
    table = {k: str(v) for k, v in spamlab.true_table(w).items()}
    if slip:  # a realistic mistake: the two piles mixed up for the first word
        table[f"p_{w[0]}_spam"], table[f"p_{w[0]}_ham"] = table[f"p_{w[0]}_ham"], table[f"p_{w[0]}_spam"]
    return {"table": table}


@app.post("/api/spamlab/run")
def spam_run(words: str = Form("[]"), table: str = Form("{}"), mode: str = Form("mine"), threshold: str = Form("0.5")):
    return _spam_call(current.spam_run, json.loads(words), json.loads(table), mode, _threshold(threshold))


@app.post("/api/spamlab/explain")
def spam_explain(email: str = Form(...), words: str = Form("[]"), table: str = Form("{}"), mode: str = Form("mine"),
                 threshold: str = Form("0.5")):
    return _spam_call(current.spam_explain, email, json.loads(words), json.loads(table), mode, _threshold(threshold))


@app.get("/api/samples")
def samples():
    return [{"id": k, "title": v["title"], "has_answers": "answers" in v, "has_retry": "answers_retry" in v}
            for k, v in CHAPTERS.items()]


@app.get("/api/sample/{name}", response_class=PlainTextResponse)
def sample_text(name: str):
    if name not in CHAPTERS:
        raise HTTPException(404)
    return (SAMPLES / CHAPTERS[name]["chapter"]).read_text(encoding="utf-8")


@app.get("/api/sample/{name}/answers")
def sample_answers(name: str, retry: bool = False):
    info = CHAPTERS.get(name, {})
    file = info.get("answers_retry" if retry else "answers")
    answers = _split((SAMPLES / file).read_text(encoding="utf-8"), r"^\s*(P\d+)") if file else {}
    notes = _split((SAMPLES / info["notes"]).read_text(encoding="utf-8"), r"^\s*(C\d+)") if info.get("notes") else {}
    return {"answers": answers, "notes": notes}


@app.post("/api/prepare")
def prepare(chapter: str = Form("")):
    global current
    _busy()
    current = Session()
    current.stage = "preparing"
    threading.Thread(target=current.prepare, args=(chapter,), daemon=True).start()
    return {"ok": True}


@app.post("/api/check")
def check(answers: str = Form("{}"), notes: str = Form("{}")):
    _busy()
    if current.chapter is None:
        raise HTTPException(400, "Open a chapter first.")
    try:
        a, n = json.loads(answers), json.loads(notes)
    except json.JSONDecodeError:
        raise HTTPException(400, "Answers were not sent correctly.")
    current.stage = "checking"
    threading.Thread(target=current.check, args=(a, n), daemon=True).start()
    return {"ok": True}


@app.post("/api/practice/next")
def practice_next():
    _busy()
    if current.chapter is None:
        raise HTTPException(400, "Open a chapter first.")
    current.stage = "designing"
    threading.Thread(target=current.next_round, daemon=True).start()
    return {"ok": True}


@app.get("/api/state")
def state(since: int = 0):
    return {**current.snapshot(since), "llm": llm.provider()}


@app.post("/api/interests")
def save_interests(interests: str = Form("[]")):
    _busy()
    try:
        chosen = json.loads(interests)
    except json.JSONDecodeError:
        raise HTTPException(400, "Interests were not sent correctly.")
    prev, current.stage = current.stage, "careering"
    threading.Thread(target=current.plan_careers, args=(chosen if isinstance(chosen, list) else [], prev), daemon=True).start()
    return {"ok": True}


@app.post("/api/career/whatif")
def career_whatif(card: str = Form(...), params: str = Form("{}")):
    try:
        return career.whatif(current.card(card), json.loads(params))
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/career/demo/{card_id}", response_class=PlainTextResponse)
def career_demo(card_id: str, slip: bool = False):
    try:
        return career.demo_hand(current.card(card_id), slip)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/career/check")
def career_check(card: str = Form(...), working: str = Form("")):
    _busy()
    try:
        return current.check_career(card, working)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/brain/reset")
def reset_brain():
    _busy()
    brainstore.reset()
    current.brain = brainstore.load()
    return {"ok": True}
