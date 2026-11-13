"""Runs the agents for one upload and records every action in a live log."""
import threading
import time

from .agents import Checker, Planner, Reviewer, explain
from .mathcheck import fmt


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

    # Policy the Checker switches to when the Reviewer sends a mark back, by the Reviewer's reason.
    FIXES = {"valid_alternative_method": ({"accept_alternative": True}, "accept any valid method, not only the textbook's"),
             "wrong_step": ({"align": "label"}, "match steps by what they calculate, not by position"),
             "wrong_level": ({"align": "label"}, "match steps by what they calculate, not by position")}
    MAX_ROUNDS = 2

    def mark_and_review(self, p, lines, checker, reviewer):
        pid = p["id"]
        mark = checker.check(p, lines)
        first = dict(mark)
        self.log("Checker", "mark", f"{pid}: {mark['level'].upper()}. {mark['detail']}", {"problem": pid, **mark})
        self.log("Checker", "handoff", f"Handing {pid} to the Reviewer.")
        for rnd in range(1, self.MAX_ROUNDS + 1):
            rv = reviewer.review(p, lines, mark)
            own = rv["own"]
            if rv["agree"]:
                verb = "Re-check passed" if rnd > 1 else "Confirmed"
                self.log("Reviewer", "recheck" if rnd > 1 else "info",
                         f"{verb} {pid}: {mark['level'].upper()}. I redid the maths: correct answer is "
                         f"{fmt(own['truth'])}{'; ' + own['why'] if own.get('why') else ''}.")
                if rnd > 1:
                    self.counters["reviewer_corrections"] += 1
                break
            self.log("Reviewer", "flag",
                     f"FLAG {pid}: Checker said {mark['level'].upper()}"
                     f"{' at step ' + str(mark['step']) if mark['step'] else ''}, but my recomputation says "
                     f"{own['level'].upper()}{' at step ' + str(own['step']) if own['step'] else ''} "
                     f"({own.get('why', '')}). Reason: {rv['reason'].replace('_', ' ')}. Sending back to the Checker.")
            fix, policy = self.FIXES[rv["reason"]]
            mark = checker.check(p, lines, **fix)
            self.log("Checker", "fix", f"Re-marked {pid} with new policy ({policy}): {mark['level'].upper()}. {mark['detail']}")
        else:
            self.counters["human_interventions"] += 1
            self.log("Reviewer", "error", f"{pid}: Checker and Reviewer still disagree after {self.MAX_ROUNDS} rounds. "
                                          "Escalating to the teacher; the mark is held as the Reviewer's verdict.")
            mark = {"level": own["level"], "step": own["step"], "detail": own.get("why", "")}
        if mark["level"] != "understood":
            mark["detail"] = explain(p, lines, mark, self.log)
        self.results[pid] = {"concept": p["concept"], "checker": first, **mark}

    def execute(self, chapter_text, working_text):
        self.status = "running"
        try:
            planner, checker, reviewer = Planner(self.log), Checker(self.log), Reviewer(self.log)
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
                self.mark_and_review(p, work[p["id"]], checker, reviewer)
            self.log("Orchestrator", "done", "Run complete.")
            self.status = "done"
        except ValueError as e:
            self.log("Orchestrator", "error", str(e))
            self.status = "error"
        except Exception as e:  # keep the demo alive and show what happened
            self.log("Orchestrator", "error", f"Unexpected error: {type(e).__name__}: {e}")
            self.status = "error"
