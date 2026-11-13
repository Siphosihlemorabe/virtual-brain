"""Virtual Brain web server. Run: uvicorn app.main:app --reload"""
import threading
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from . import brain as brainstore
from . import llm
from .orchestrator import Run

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Virtual Brain")
current = Run()


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/sample/{name}", response_class=PlainTextResponse)
def sample(name: str):
    files = {"chapter": "probability_chapter.txt", "working": "student_working.txt", "notes": "student_notes.txt",
             "working_retry": "student_working_retry.txt", "hand": "student_hand_maths.txt",
             "hand_fixed": "student_hand_maths_fixed.txt", "algebra_chapter": "algebra_chapter.txt",
             "algebra_working": "algebra_working.txt", "algebra_notes": "algebra_notes.txt",
             "geometry_chapter": "geometry_chapter.txt", "geometry_working": "geometry_working.txt"}
    if name not in files:
        raise HTTPException(404)
    return (ROOT / "samples" / files[name]).read_text(encoding="utf-8")


@app.post("/api/run")
def run(chapter: str = Form(""), working: str = Form(""), notes: str = Form("")):
    global current
    if current.status == "running":
        raise HTTPException(409, "A run is already in progress.")
    current = Run()
    threading.Thread(target=current.execute, args=(chapter, working, notes), daemon=True).start()
    return {"ok": True}


@app.get("/api/state")
def state(since: int = 0):
    return {**current.snapshot(since), "llm": llm.provider()}


@app.post("/api/brain/reset")
def reset_brain():
    if current.status == "running":
        raise HTTPException(409, "Wait for the current run to finish.")
    brainstore.reset()
    current.brain = brainstore.load()
    return {"ok": True}


@app.post("/api/career/check")
def career_check(concept: str = Form(...), working: str = Form("")):
    if current.status == "running":
        raise HTTPException(409, "Wait for the current run to finish.")
    try:
        return current.check_career(concept, working)
    except ValueError as e:
        raise HTTPException(400, str(e))
