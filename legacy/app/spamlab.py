"""Spam Lab: Naive Bayes built from basic probability.

The student does the maths (the probability table, and one email by hand); the Reviewer checks it;
then the colleague runs the student's own numbers through the real classifier code on a whole inbox.
The emails are generated from fixed templates with a fixed seed, so every run of the demo is the same.
The code shown to the student is exactly the code that runs (CODE_BLOCKS is joined and executed)."""
import random
import re
from fractions import Fraction

from .mathcheck import evaluate, fmt, parse_steps

# ---------------------------------------------------------------- the emails

NAMES = ["Thando", "Lerato", "Sipho", "Ayanda", "Pieter", "Naledi", "Kagiso", "Zanele", "Musa", "Priya", "Bongani", "Lindiwe"]
PLACES = ["Maponya Mall", "the library", "the school hall", "Menlyn", "the taxi rank", "Gold Reef City"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
PRIZES = ["Samsung phone", "PlayStation 5", "R5000 voucher", "trip to Durban", "smart TV", "year of free data"]
BANKS = ["FNB", "Capitec", "Absa", "Standard Bank"]
TEAMS = ["Rosebank High", "Soweto Stars", "Pretoria Boys"]

SPAM = [
    ("You are a WINNER", "Congratulations! You win a {prize}. Click here to claim your prize today."),
    ("FREE {prize}", "Free {prize} for the first 100 people. Click the link to claim yours."),
    ("Account locked", "Urgent: your {bank} account is locked. Click to verify your details now."),
    ("Cash prize", "You have been selected to win R{amount} cash. Reply WIN to claim."),
    ("Loans in 5 minutes", "Limited offer: cheap loans approved in 5 minutes. Click for a free quote."),
    ("Free airtime", "Free airtime! Dial now and win a {prize} every day this week."),
    ("Final notice", "Final notice: claim your R{amount} prize before midnight."),
    ("90% off", "Hot offer just for you: {prize} at 90% off. Click now before it is gone."),
    ("Parcel waiting", "Your parcel is waiting at the depot. Pay the R{fee} delivery fee here to release it."),
    ("Work from home", "Make R{amount} a week from home. No experience needed. Join for free."),
    ("Winner notification", "Urgent winner notification: you won a {prize}. Click to collect."),
    ("Sign-up gift", "Get a free {prize} when you sign up today. Offer ends soon."),
]
HAM = [
    ("Meeting", "Hi {name}, are we still meeting at {place} on {day}?"),
    ("Homework", "Reminder: Maths homework on probability is due {day}."),
    ("Notes", "{name}, can you send me the notes from today's science lesson?"),
    ("Soccer", "Soccer practice moved to 4pm on {day}. Bring water."),
    ("Bread", "Mom here. Please buy bread and milk on your way home."),
    ("Study?", "Are you free on {day}? Let's study for the test together."),
    ("School trip", "The school trip to {place} costs R{fee}. Forms are due {day}."),
    ("Well done", "Great job on your project! See you at the meeting on {day}."),
    ("Report", "Your term report is ready. Please collect it from the office."),
    ("Netball", "We win the league if we beat {team} on {day}. Practice at 3pm."),
    ("Library", "{name} says the library is free to use after school on {day}."),
    ("Group chat", "Can you click the link I sent for the homework group chat?"),
    ("Choir", "Choir practice is cancelled on {day}. The hall is booked."),
    ("Lift", "Dad here. I will fetch you at {place} at 5pm."),
]
SPAM_FROM = ["promo@winbig.co", "noreply@prizes-sa.net", "alerts@secure-verify.com", "deals@cheapoffers.biz", "gift@luckydraw.info"]


def _words(text: str) -> list:
    return sorted(set(re.findall(r"[a-z]+", text.lower())))


# templates that trick a filter watching free / win / click (a normal email with a spammy word, a spam without one)
TRICKY = {"Parcel waiting", "Study?", "Netball", "Library", "Group chat"}


def _make(rng, label, n, start):
    out, templates = [], SPAM if label == "spam" else HAM
    weights = [.25 if t[0] in TRICKY else 1 for t in templates]  # tricky ones are rarer, as in a real inbox
    for i in range(n):
        subject, body = templates[(start + i) % len(templates)] if i < len(templates) else rng.choices(templates, weights)[0]
        fill = {"name": rng.choice(NAMES), "place": rng.choice(PLACES), "day": rng.choice(DAYS), "prize": rng.choice(PRIZES),
                "bank": rng.choice(BANKS), "team": rng.choice(TEAMS), "amount": rng.choice([500, 1000, 2500, 10000]),
                "fee": rng.choice([25, 49, 120, 350])}
        subject, body = subject.format(**fill), body.format(**fill)
        sender = rng.choice(SPAM_FROM) if label == "spam" else f"{fill['name'].lower()}@school.za" if rng.random() < .6 else "family"
        out.append({"subject": subject, "body": body, "from": sender, "label": label, "words": _words(subject + " " + body)})
    return out


def _build():
    rng = random.Random(10)
    training = _make(rng, "spam", 10, 0) + _make(rng, "ham", 10, 0)
    inbox = _make(rng, "spam", 45, 3) + _make(rng, "ham", 75, 5)
    rng.shuffle(training)
    rng.shuffle(inbox)
    for i, e in enumerate(training):
        e["id"] = f"T{i + 1}"
    for i, e in enumerate(inbox):
        e["id"] = f"M{i + 1}"
    return training, inbox


TRAINING, INBOX = _build()
CANDIDATES = ["free", "win", "click", "claim", "prize", "urgent", "offer", "homework", "meeting", "practice"]
DEFAULT_WORDS = ["free", "win", "click"]

# ---------------------------------------------------------------- the code, with its explanation

CODE_BLOCKS = [
    ("from fractions import Fraction as F",
     "Use exact fractions, like you do by hand, so nothing gets rounded."),
    ('''def learn(training, words, smoothing=False):
    spam = [e for e in training if e["label"] == "spam"]
    ham = [e for e in training if e["label"] == "ham"]''',
     "Split the labelled emails into two piles: spam and ham (normal email). Each pile becomes a sample space."),
    ('''    p_spam = F(len(spam), len(training))
    p_ham = F(len(ham), len(training))''',
     "P(spam) = number of spam emails ÷ all emails. This is P(E) = n(E) / n(S) from your chapter."),
    ('''    add = 1 if smoothing else 0
    p_word_spam = {w: F(sum(w in e["words"] for e in spam) + add, len(spam) + 2 * add) for w in words}
    p_word_ham = {w: F(sum(w in e["words"] for e in ham) + add, len(ham) + 2 * add) for w in words}
    return p_spam, p_ham, p_word_spam, p_word_ham''',
     "For each word: count the spam emails that contain it and divide by the size of the spam pile. Same again for ham. "
     "That is basic probability again, but inside one pile (the word's probability GIVEN spam). Smoothing adds 1 to each "
     "count so a word never gets a probability of exactly 0."),
    ('''def classify(email, p_spam, p_ham, p_word_spam, p_word_ham):
    score_spam, score_ham = p_spam, p_ham
    for w in p_word_spam:
        if w in email["words"]:
            score_spam = score_spam * p_word_spam[w]
            score_ham = score_ham * p_word_ham[w]''',
     "Start each score at P(spam) or P(ham). For every watched word that is in this email, multiply in that word's "
     "probability. Multiplying treats the words as if they had nothing to do with each other: that is the 'naive' part."),
    ('''    total = score_spam + score_ham
    p = score_spam / total if total else F(1, 2)
    return p, score_spam, score_ham''',
     "Compare the two scores: P(spam | this email) = score_spam ÷ (score_spam + score_ham). If both scores are 0, "
     "the filter cannot tell, so it says 1/2."),
]
SOURCE = "\n\n".join(code for code, _ in CODE_BLOCKS)
_SAFE = {"__import__": __import__, "len": len, "sum": sum, "range": range}
_NS = {"__builtins__": _SAFE}
exec(compile(SOURCE, "<spam filter>", "exec"), _NS)  # our own code; shown to the student exactly as written
learn, classify = _NS["learn"], _NS["classify"]

# ---------------------------------------------------------------- helpers for the agents


def cell_names(words):
    return ["p_spam", "p_ham"] + [f"p_{w}_spam" for w in words] + [f"p_{w}_ham" for w in words]


def true_table(words, smoothing=False):
    p_spam, p_ham, ws, wh = learn(TRAINING, words, smoothing)
    table = {"p_spam": p_spam, "p_ham": p_ham}
    for w in words:
        table[f"p_{w}_spam"], table[f"p_{w}_ham"] = ws[w], wh[w]
    return table


def counts(words):
    spam = [e for e in TRAINING if e["label"] == "spam"]
    ham = [e for e in TRAINING if e["label"] == "ham"]
    return {"spam": len(spam), "ham": len(ham), "total": len(TRAINING),
            "words": {w: {"spam": sum(w in e["words"] for e in spam), "ham": sum(w in e["words"] for e in ham)} for w in words}}


def parse_value(text):
    """A student's cell: '7/10', '0.7' or '70%'. Returns a Fraction or None."""
    t = str(text or "").strip().replace(" ", "")
    if t.endswith("%"):
        v = evaluate(t[:-1])
        return v / 100 if v is not None else None
    return evaluate(t)


def review_table(words, entries: dict) -> dict:
    """Reviewer: every cell must equal the count-based probability. Wrong cells get a counting hint, not the answer."""
    truth, c, cells = true_table(words), counts(words), {}
    for name in cell_names(words):
        v = parse_value(entries.get(name))
        if v is None:
            cells[name] = {"ok": False, "hint": "Write a fraction like 7/10."}
        elif v == truth[name]:
            cells[name] = {"ok": True}
        else:
            if name in ("p_spam", "p_ham"):
                pile = name[2:]
                hint = f"How many of the {c['total']} labelled emails are {pile}? Put that over {c['total']}."
            else:
                w, pile = name[2:].rsplit("_", 1)
                hint = f"Count the {pile} emails that contain '{w}', then divide by the {c[pile]} {pile} emails."
            cells[name] = {"ok": False, "hint": hint, "got": fmt(v)}
    return {"cells": cells, "all_ok": all(x["ok"] for x in cells.values()),
            "wrong": [n for n, x in cells.items() if not x["ok"]]}


def table_from(words, entries):
    vals = {n: parse_value(entries.get(n)) for n in cell_names(words)}
    if any(v is None for v in vals.values()):
        return None
    return vals


def run(words, table, threshold=Fraction(1, 2)):
    """The colleague's part: classify the whole inbox with the given table, using the code shown."""
    ws = {w: table[f"p_{w}_spam"] for w in words}
    wh = {w: table[f"p_{w}_ham"] for w in words}
    results, tally = [], {"caught": 0, "missed": 0, "blocked": 0, "delivered": 0}
    for e in INBOX:
        p, s, h = classify(e, table["p_spam"], table["p_ham"], ws, wh)
        verdict = "spam" if p > threshold else "ham"
        key = {("spam", "spam"): "caught", ("spam", "ham"): "missed",
               ("ham", "spam"): "blocked", ("ham", "ham"): "delivered"}[(e["label"], verdict)]
        tally[key] += 1
        results.append({"id": e["id"], "verdict": verdict, "p": fmt(p), "pf": float(p), "correct": verdict == e["label"]})
    right = tally["caught"] + tally["delivered"]
    return {"results": results, "tally": tally, "accuracy": right / len(INBOX), "right": right, "total": len(INBOX)}


def explain(email_id, words, table, threshold=Fraction(1, 2)):
    """One email's maths in English and in Python, with the student's own numbers."""
    e = next(x for x in INBOX if x["id"] == email_id)
    present = [w for w in words if w in e["words"]]
    ws = {w: table[f"p_{w}_spam"] for w in words}
    wh = {w: table[f"p_{w}_ham"] for w in words}
    p, s, h = classify(e, table["p_spam"], table["p_ham"], ws, wh)
    s_terms = [fmt(table["p_spam"])] + [fmt(ws[w]) for w in present]
    h_terms = [fmt(table["p_ham"])] + [fmt(wh[w]) for w in present]
    verdict = "spam" if p > threshold else "ham"
    english = [
        f"Watched words in this email: {', '.join(present) if present else 'none'}.",
        f"score_spam = P(spam){''.join(f' × P({w}|spam)' for w in present)} = {' × '.join(s_terms)} = {fmt(s)}",
        f"score_ham = P(ham){''.join(f' × P({w}|ham)' for w in present)} = {' × '.join(h_terms)} = {fmt(h)}",
        f"P(spam | email) = {fmt(s)} ÷ ({fmt(s)} + {fmt(h)}) = {fmt(p)} ≈ {float(p):.2f}",
        f"{fmt(p)} is {'more' if p > threshold else 'not more'} than {fmt(threshold)}, so it goes to {'Spam' if verdict == 'spam' else 'the Inbox'}.",
    ]
    python = [
        f'email["words"] contains {present}',
        f"score_spam = {' * '.join('F(' + t.replace('/', ', ') + ')' if '/' in t else t for t in s_terms)}   # {fmt(s)}",
        f"score_ham = {' * '.join('F(' + t.replace('/', ', ') + ')' if '/' in t else t for t in h_terms)}   # {fmt(h)}",
        f"p = score_spam / (score_spam + score_ham)   # {fmt(p)}",
        f'verdict = "spam" if p > {fmt(threshold)} else "ham"   # "{verdict}"',
    ]
    return {"id": e["id"], "subject": e["subject"], "body": e["body"], "from": e["from"], "label": e["label"],
            "verdict": verdict, "english": english, "python": python}


HAND_EMAIL = next(e for e in INBOX if e["label"] == "spam" and sum(w in e["words"] for w in DEFAULT_WORDS) >= 2)["id"]


def review_hand(email_id, words, text):
    """Reviewer: the student's hand classification of one email, against the code with the correct table."""
    table = true_table(words)
    e = next(x for x in INBOX if x["id"] == email_id)
    ws = {w: table[f"p_{w}_spam"] for w in words}
    wh = {w: table[f"p_{w}_ham"] for w in words}
    p, s, h = classify(e, table["p_spam"], table["p_ham"], ws, wh)
    expected = {"score_spam": s, "score_ham": h, "p_spam": p}
    steps = parse_steps([l for l in str(text).splitlines() if l.strip()])
    problems = []
    for i, name in enumerate(expected):
        st = next((x for x in steps if x.label == name), steps[i] if i < len(steps) else None)
        if st is None:
            problems.append(f"{name}: missing")
        elif not st.consistent:
            problems.append(f"{name}: '{st.text}' does not add up ({st.first_expr} = {fmt(st.values[0])})")
        elif st.value != expected[name]:
            problems.append(f"{name}: you got {fmt(st.value)}, the code gets {fmt(expected[name])}")
    if problems:
        return {"ok": False, "msg": "Not yet. " + " | ".join(problems)}
    return {"ok": True, "msg": f"Every line adds up and matches the code: score_spam = {fmt(s)}, score_ham = {fmt(h)}, "
                               f"P(spam | email) = {fmt(p)}, so this email is {'spam' if p > Fraction(1, 2) else 'ham'}."}


def demo_hand(email_id, words, slip=False):
    """Demo helper: correct hand working for one email (optionally with a slip)."""
    table = true_table(words)
    e = next(x for x in INBOX if x["id"] == email_id)
    present = [w for w in words if w in e["words"]]
    ws = {w: table[f"p_{w}_spam"] for w in words}
    wh = {w: table[f"p_{w}_ham"] for w in words}
    p, s, h = classify(e, table["p_spam"], table["p_ham"], ws, wh)
    s_line = " * ".join([fmt(table["p_spam"])] + [fmt(ws[w]) for w in present])
    h_line = " * ".join([fmt(table["p_ham"])] + [fmt(wh[w]) for w in present])
    wrong = s * 2 if slip else s
    return "\n".join([f"score_spam = {s_line} = {fmt(wrong)}", f"score_ham = {h_line} = {fmt(h)}",
                      f"p_spam = {fmt(s)} / ({fmt(s)} + {fmt(h)}) = {fmt(p)}"])


def payload():
    strip = lambda e: {k: e[k] for k in ("id", "subject", "body", "from", "label")}  # noqa: E731
    return {"training": [strip(e) for e in TRAINING], "inbox": [strip(e) for e in INBOX],
            "candidates": CANDIDATES, "default_words": DEFAULT_WORDS, "hand_email": HAND_EMAIL,
            "code": [{"python": code, "english": text} for code, text in CODE_BLOCKS]}
