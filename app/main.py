"""Virtual Brain web server. Run: python -m uvicorn app.main:app --port 8000"""
import json
import re
import threading
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from . import brain as brainstore
from . import llm
from .orchestrator import Session

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
app = FastAPI(title="Virtual Brain")
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
HAND = {"hand": "student_hand_maths.txt", "hand_fixed": "student_hand_maths_fixed.txt"}


def _busy():
    if current.stage in ("preparing", "checking", "designing"):
        raise HTTPException(409, "Your colleague is still working. Give it a moment.")


def _split(text: str, pattern: str) -> dict:
    """'P1: ...' or 'C2: ...' blocks -> {id: text}."""
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(pattern + r"\s*[:.)]\s*(.*?)(?=^\s*[PC]\d+\s*[:.)]|\Z)", text, flags=re.M | re.S)}


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/samples")
def samples():
    return [{"id": k, "title": v["title"], "has_answers": "answers" in v, "has_retry": "answers_retry" in v}
            for k, v in CHAPTERS.items()]


@app.get("/api/sample/{name}", response_class=PlainTextResponse)
def sample_text(name: str):
    if name in HAND:
        return (SAMPLES / HAND[name]).read_text(encoding="utf-8")
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
    threading.Thread(target=current.check, args=(a, n), daemon=True).start()
    return {"ok": True}


@app.post("/api/practice/next")
def practice_next():
    _busy()
    if current.chapter is None:
        raise HTTPException(400, "Open a chapter first.")
    threading.Thread(target=current.next_round, daemon=True).start()
    return {"ok": True}


@app.get("/api/state")
def state(since: int = 0):
    return {**current.snapshot(since), "llm": llm.provider()}


@app.post("/api/career/check")
def career_check(concept: str = Form(...), working: str = Form("")):
    _busy()
    try:
        return current.check_career(concept, working)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/brain/reset")
def reset_brain():
    _busy()
    brainstore.reset()
    current.brain = brainstore.load()
    return {"ok": True}
