"""Runs the agents for one upload and records every action in a live log."""
import threading
import time

from .agents import Checker, Planner


class Run:
    def __init__(self):
        self.events = []
        self.status = "idle"
        self.results = {}
        self.concepts = []
        self.problems = []
        self.counters = {"reviewer_corrections": 0, "human_interventions": 0}
        self._lock = threading.Lock()

    def log(self, agent, kind, msg, data=None):
        with self._lock:
            self.events.append({"i": len(self.events), "t": time.strftime("%H:%M:%S"),
                                "agent": agent, "kind": kind, "msg": msg, "data": data})

    def snapshot(self, since=0):
        with self._lock:
            return {"status": self.status, "events": self.events[since:], "results": self.results,
                    "concepts": self.concepts, "problems": self.problems, "counters": self.counters}

    def execute(self, chapter_text, working_text):
        self.status = "running"
        try:
            planner, checker = Planner(self.log), Checker(self.log)
            self.log("Orchestrator", "info", "Goal received: chapter → proven understanding → career application.")
            chapter = planner.read_chapter(chapter_text)
            self.concepts, self.problems = chapter["concepts"], chapter["problems"]
            self.log("Planner", "handoff", "Handing the chapter to the Checker to read the student's working.")
            work = checker.read_working(working_text, chapter)
            plan = planner.plan(chapter, work)
            by_id = {p["id"]: p for p in chapter["problems"]}
            for step in plan:
                p = by_id[step["target"]]
                if step["action"] == "ask_student":
                    self.results[p["id"]] = {"concept": p["concept"], "level": "not attempted", "step": None,
                                             "detail": "Not attempted yet. Student asked to try it."}
                    self.log("Planner", "ask", f"{p['id']} not attempted. Asking the student: {p['question']}")
                    continue
                mark = checker.check(p, work[p["id"]])
                self.results[p["id"]] = {"concept": p["concept"], "checker": dict(mark), **mark}
                self.log("Checker", "mark", f"{p['id']}: {mark['level'].upper()}. {mark['detail']}",
                         {"problem": p["id"], **mark})
            self.log("Orchestrator", "done", "Run complete.")
            self.status = "done"
        except ValueError as e:
            self.log("Orchestrator", "error", str(e))
            self.status = "error"
        except Exception as e:  # keep the demo alive and show what happened
            self.log("Orchestrator", "error", f"Unexpected error: {type(e).__name__}: {e}")
            self.status = "error"
