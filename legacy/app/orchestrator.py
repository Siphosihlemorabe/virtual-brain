"""One study session: the student hands over a chapter, the agents prepare it, the student practises,
the agents check and remember. Every action is recorded in a live log."""
import threading
import time

from . import brain as brainstore
from . import learner, llm, recall, spamlab
from .agents import Checker, Planner, Reviewer, explain
from . import career as careers_mod
from .career import CareerGuide, check_hand_maths, record_proof
from .mathcheck import fmt
from .tutor import Tutor


class Session:
    def __init__(self, brain_path=None):
        self.brain_path = brain_path  # None means the default data/brain.json
        self.events = []
        self.stage = "start"  # start | preparing | ready | checking | checked | designing | careering | error
        self.error = ""
        self.chapter = None
        self.results = {}
        self.brain = brainstore.load(self.brain_path)
        self.careers = []
        self.recalls = []
        self.round, self.round_plan = 1, []
        self.noticed = []
        self.spam = {"table_ok": False, "hand_ok": False, "proven": False}
        self.counters = {"reviewer_corrections": 0, "human_interventions": 0}
        self._lock = threading.Lock()

    def log(self, agent, kind, msg, data=None):
        with self._lock:
            self.events.append({"i": len(self.events), "t": time.strftime("%H:%M:%S"),
                                "agent": agent, "kind": kind, "msg": msg, "data": data})

    def snapshot(self, since=0):
        with self._lock:
            chapter = None
            if self.chapter:
                # practice solutions stay hidden until that problem has been checked
                problems = [{**p, "solution": p["solution"] if p["id"] in self.results else [],
                             "has_memo": bool(p["solution"])} for p in self.chapter["problems"]]
                chapter = {**self.chapter, "problems": problems}
            return {"stage": self.stage, "error": self.error, "events": self.events[since:],
                    "round": self.round, "round_plan": self.round_plan, "round_ids": self.round_ids(),
                    "chapter": chapter, "results": self.results, "counters": self.counters,
                    "brain": self.brain, "careers": self.careers, "recalls": self.recalls,
                    "pathways": careers_mod.pathways(self.brain), "interests": careers_mod.interests(self.brain),
                    "interest_options": careers_mod.catalogue()["interests"],
                    "learner": learner.view(self.brain), "noticed": self.noticed, "spam": self.spam}

    def round_ids(self):
        if not self.chapter:
            return []
        return [p["id"] for p in self.chapter["problems"] if p.get("round", 1) == self.round]

    def round_results(self):
        return {pid: self.results[pid] for pid in self.round_ids() if pid in self.results}

    def _topics(self):
        return [n for _, n, _ in brainstore.summary(self.brain)] + [c["name"] for c in self.chapter["concepts"]]

    def _fail(self, e):
        msg = str(e) if isinstance(e, ValueError) else f"Unexpected error: {type(e).__name__}: {e}"
        self.log("Orchestrator", "error", msg)
        self.error = msg
        self.stage = "error"

    # ------------------------------------------------------------ phase 1: prepare the chapter

    def prepare(self, chapter_text):
        self.stage, self.error = "preparing", ""
        try:
            self.log("Orchestrator", "info", "Goal: take this chapter to proven understanding, then to a real career.")
            known = brainstore.summary(self.brain)
            chapter = Planner(self.log).read_chapter(chapter_text, known)
            Tutor(self.log, self.counters).fill(chapter, [n for _, n, _ in known] + [c["name"] for c in chapter["concepts"]])
            for p in chapter["problems"]:
                p.setdefault("round", 1)
                p.setdefault("form", "word")
            practice = [p for p in chapter["problems"] if p["solution"]]
            skipped = [p["id"] for p in chapter["problems"] if not p["solution"]]
            if skipped:
                self.log("Planner", "warn", f"No verified memo for {', '.join(skipped)}, so I left it out of practice.")
            chapter["problems"] = practice
            if not practice:
                raise ValueError("There are no practice questions I could verify for this chapter yet.")
            self.chapter = chapter
            self.log("Planner", "plan", f"Study plan: learn {len(chapter['concepts'])} concepts from "
                                        f"{len(chapter['examples'])} worked examples, then practise "
                                        f"{len(practice)} questions. I will check your work, update your brain, "
                                        "and unlock a career link for anything you master.")
            self.stage = "ready"
        except Exception as e:  # keep the session alive and show what happened
            self._fail(e)

    # ------------------------------------------------------------ phase 2: check the student's practice

    # How the Checker re-marks when the Reviewer sends a mark back. It first reads the working again with the
    # language model (any valid method counts); without a model it re-marks from the verified arithmetic.
    FIXES = {"valid_alternative_method": ({"accept_alternative": True}, "re-marked from the verified arithmetic: any valid method counts"),
             "wrong_step": ({"align": "label", "accept_alternative": True}, "matched steps by what they calculate"),
             "wrong_level": ({"align": "label", "accept_alternative": True}, "re-marked from the verified arithmetic")}
    MAX_ROUNDS = 2

    def remark(self, p, lines, checker, reason):
        fix, policy = self.FIXES[reason]
        try:
            mark = checker.model_mark(p, lines)
            return mark, "read the working again: any valid method counts"
        except (llm.LLMError, ValueError) as e:
            self.log("Checker", "warn", f"{p['id']}: model re-read unavailable ({e}); re-marking from the arithmetic.")
            mark = checker.check(p, lines, **fix)
            mark["method"] = checker.code_method(p, lines)
            return mark, policy

    def mark_and_review(self, p, lines, checker, reviewer):
        pid = p["id"]
        # fast first pass in code: does the working follow the textbook's steps?
        mark = checker.check(p, lines)
        mark["method"] = checker.code_method(p, lines)
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
            mark, policy = self.remark(p, lines, checker, rv["reason"])
            self.log("Checker", "fix", f"Re-marked {pid} ({policy}): {mark['level'].upper()}. {mark['detail']}")
        else:
            self.counters["human_interventions"] += 1
            self.log("Reviewer", "error", f"{pid}: Checker and Reviewer still disagree after {self.MAX_ROUNDS} rounds. "
                                          "Escalating to the teacher; the mark is held as the Reviewer's verdict.")
            mark = {"level": own["level"], "step": own["step"], "detail": own.get("why", "")}
        if mark["level"] != "understood":
            mark["detail"] = explain(p, lines, mark, self.log, learner.summary(self.brain))
        mark["method"] = mark.get("method") if mark["level"] == "understood" else None
        self.results[pid] = {"concept": p["concept"], "checker": first, **mark}

    def check(self, answers: dict, notes: dict):
        self.stage, self.error = "checking", ""
        try:
            chapter = self.chapter
            planner, checker, reviewer = Planner(self.log), Checker(self.log), Reviewer(self.log)
            known = brainstore.summary(self.brain)
            self.log("Orchestrator", "handoff", f"Student handed in round {self.round}. Handing it to the Checker.")
            ids = set(self.round_ids())
            chapter = {**chapter, "problems": [p for p in chapter["problems"] if p["id"] in ids]}
            work = checker.read_answers({k: v for k, v in answers.items() if k in ids}, chapter)
            for pid in checker.unreadable:
                p = next(x for x in chapter["problems"] if x["id"] == pid)
                self.results[pid] = {"concept": p["concept"], "level": "unreadable", "step": None,
                                     "detail": "I couldn't find a calculation or an answer in what you wrote. Write each "
                                               "step on its own line, like P(red) = 3/10, or just your final answer."}
            if not work:
                raise ValueError("I could not find any working to check. Write your calculations in the answer boxes.")
            plan = planner.plan(chapter, work, known)
            by_id = {p["id"]: p for p in chapter["problems"]}
            for step in plan:
                p = by_id[step["target"]]
                if step["action"] == "ask_student":
                    if p["id"] not in checker.unreadable:
                        self.log("Planner", "ask", f"{p['id']} not attempted yet. It stays open for you.")
                    continue
                self.mark_and_review(p, work[p["id"]], checker, reviewer)
            self.log("Reviewer", "handoff", "Verified marks handed to the brain.")
            note_text = "\n".join(f"{cid}: {line}" for cid, txt in notes.items() for line in str(txt).splitlines()
                                  if line.strip())
            latest = self.round_results()
            keymap = brainstore.update(self.brain, chapter, latest, note_text, self.log, self.brain_path)
            self.noticed = learner.observe(self.brain, chapter, latest, work, keymap, self.log)
            brainstore.save(self.brain, self.brain_path)
            self.recalls = []
            if any(r["level"] in ("gap", "partly") for r in latest.values()):
                self.log("Planner", "reason", "Some problems are not yet understood, so before moving on I am asking "
                                              "the brain whether an earlier topic is the cause.")
                self.recalls = recall.run(self.brain, keymap, chapter, latest, self.log)
            if careers_mod.interests(self.brain):
                self.log("Brain", "handoff", "Handing your mastered concepts and interests to the Career guide.")
                self.careers = CareerGuide(self.log, self.counters).plan(self.brain)
            else:
                self.log("Career guide", "info", "Pick your interests in Real world and I will find careers that use what you mastered.")
            self.log("Orchestrator", "done", "Checked. Your results and next steps are ready.")
            self.stage = "checked"
        except Exception as e:
            self._fail(e)
            self.stage = "ready" if self.chapter else "error"

    # ------------------------------------------------------------ phase 3: practise again, differently

    def next_round(self):
        self.stage, self.error = "designing", ""
        try:
            latest = self.round_results()
            if not latest:
                raise ValueError("Check this round first, so I know what to practise next.")
            self.log("Orchestrator", "handoff", "Student asked to practise again. Handing their results to the Planner.")
            ids, plan = Tutor(self.log, self.counters).variants(self.chapter, latest, self._topics(), self.brain)
            if not ids:
                raise ValueError("I could not prepare a new round I trust. Try again in a moment.")
            self.round, self.round_plan = self.round + 1, plan
            self.log("Planner", "plan", f"Round {self.round} is ready: {len(ids)} new questions, checked by the Reviewer.")
            self.stage = "ready"
        except Exception as e:
            self._fail(e)
            self.stage = "checked"

    def plan_careers(self, chosen=None, prev=None):
        """The student picked interests (or asked again): the Career guide plans missions for them."""
        prev = prev or self.stage
        self.stage, self.error = "careering", ""
        try:
            if chosen is not None:
                picked = careers_mod.set_interests(self.brain, chosen)
                brainstore.save(self.brain, self.brain_path)
                names = careers_mod.catalogue()["interests"]
                self.log("Brain", "learn", f"Saved your interests: {', '.join(names[i] for i in picked) or 'none'}.")
            self.careers = CareerGuide(self.log, self.counters).plan(self.brain)
        except Exception as e:
            self._fail(e)
        self.stage = prev if prev in ("checked", "ready", "start") else "checked"

    def card(self, card_id):
        card = next((c for c in self.careers if c["id"] == card_id), None)
        if card is None:
            raise ValueError("That mission is no longer open. Ask the Career guide for new missions.")
        return card

    def check_career(self, card_id, text):
        """Student uploads hand maths for a mission; the Reviewer checks it against the code."""
        card = self.card(card_id)
        self.log("Career guide", "handoff", f"Student uploaded hand maths for {card['chain'][1]}. Handing to the Reviewer.")
        res = check_hand_maths(card, text)
        if res["ok"]:
            self.log("Reviewer", "recheck", f"Hand maths verified. {res['msg']}")
            record_proof(self.brain, card)
            brainstore.save(self.brain, self.brain_path)
            self.log("Brain", "update", f"{card['concept_name']} linked to career: {' → '.join(card['chain'][1:])} (proven by hand).")
        else:
            self.log("Reviewer", "flag", f"Hand maths sent back to the student. {res['msg']}")
        card["result"] = res
        return res

    # ------------------------------------------------------------ Spam Lab: Naive Bayes from basic probability

    @staticmethod
    def _spam_words(words):
        words = [w for w in (words or []) if w in spamlab.CANDIDATES]
        if not 1 <= len(words) <= 5:
            raise ValueError("Choose between 1 and 5 words for the filter to watch.")
        return list(dict.fromkeys(words))

    def spam_open(self):
        self.log("Career guide", "career", "Opening the Spam Lab: a data scientist's Naive Bayes filter, built from the "
                                           "basic probability you learned, P(E) = n(E) / n(S), used inside each pile of email.")

    def spam_table(self, words, entries):
        words = self._spam_words(words)
        self.log("Career guide", "handoff", f"Student filled the probability table for {', '.join(words)}. Handing it to the Reviewer.")
        res = spamlab.review_table(words, entries)
        self.spam["table_ok"] = res["all_ok"]
        if res["all_ok"]:
            self.log("Reviewer", "recheck", "Every cell of the table matches the counts in the 20 labelled emails.")
        else:
            self.log("Reviewer", "flag", f"{len(res['wrong'])} cell(s) do not match the counts: {', '.join(res['wrong'])}. "
                                         "Sent back with counting hints (not the answers).")
        self._spam_proof(words)
        return res

    def spam_hand(self, words, text):
        words = self._spam_words(words)
        self.log("Career guide", "handoff", "Student classified one email by hand. Handing it to the Reviewer.")
        res = spamlab.review_hand(spamlab.HAND_EMAIL, words, text)
        self.spam["hand_ok"] = res["ok"]
        self.log("Reviewer", "recheck" if res["ok"] else "flag", res["msg"])
        self._spam_proof(words)
        return res

    def _table(self, words, entries, mode):
        if mode == "smoothed":
            return spamlab.true_table(words, smoothing=True)
        table = spamlab.table_from(words, entries)
        if table is None:
            raise ValueError("Fill in every cell of your table first (fractions like 7/10).")
        return table

    def spam_run(self, words, entries, mode, threshold):
        words = self._spam_words(words)
        table = self._table(words, entries, mode)
        res = spamlab.run(words, table, threshold)
        whose = "the colleague's smoothed table" if mode == "smoothed" else "your table"
        self.log("Career guide", "info", f"Ran {whose} through the filter code on all {res['total']} emails: "
                                         f"{res['right']} sorted correctly ({res['accuracy']:.0%}). Caught {res['tally']['caught']} "
                                         f"spam, missed {res['tally']['missed']}, wrongly blocked {res['tally']['blocked']} normal emails.")
        if mode != "smoothed":
            wrong = spamlab.review_table(words, entries)["wrong"]
            if wrong:
                self.log("Reviewer", "flag", f"Your table still has wrong cells ({', '.join(wrong)}), so these results are "
                                             "not what the real counts would give. Fix them and run again.")
        return res

    def spam_explain(self, email_id, words, entries, mode, threshold):
        words = self._spam_words(words)
        return spamlab.explain(email_id, words, self._table(words, entries, mode), threshold)

    def _spam_proof(self, words):
        if self.spam["table_ok"] and self.spam["hand_ok"] and not self.spam["proven"]:
            node = self.brain["concepts"].get("basic-probability")
            if node is not None:
                record_proof(self.brain, {"concept": "basic-probability", "name": "Data scientist",
                                          "title": "Naive Bayes spam filter",
                                          "about": "Builds filters that sort email using probability."})
                brainstore.save(self.brain, self.brain_path)
            self.spam["proven"] = True
            self.log("Brain", "update", "Basic probability linked to career: Naive Bayes spam filter → Data scientist "
                                        "(table and hand maths proven by the Reviewer).")
