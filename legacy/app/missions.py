"""Career missions: small, real calculations a professional would run, as fixed code templates.
The language model only chooses whole-number inputs (validated here) and writes the story around them;
it never writes code. The code shown to the student is exactly the code that runs."""
import contextlib
import io
from fractions import Fraction
from string import Template

from .mathcheck import fmt

_SAFE = {"__import__": __import__, "print": print, "sum": sum, "len": len, "range": range}


def _code(src: str) -> Template:
    return Template(src.strip("\n"))


TEMPLATES = {
    "spam_filter": {
        "concept": "basic-probability", "title": "Naive Bayes spam filter",
        "params": {"spam": (4, 2, 20), "ham": (4, 2, 20), "free_spam": (3, 0, 20), "free_ham": (1, 0, 20),
                   "win_spam": (2, 0, 20), "win_ham": (1, 0, 20)},
        "whatif": ["free_spam", "free_ham", "win_spam"],
        "labels": {"spam": "spam emails", "ham": "normal emails", "free_spam": "spam emails with 'free'",
                   "free_ham": "normal emails with 'free'", "win_spam": "spam emails with 'win'", "win_ham": "normal emails with 'win'"},
        "check": ["score_spam", "score_ham", "p_spam"],
        "task": "score_spam = P(spam) x P(free in spam) x P(win in spam)\nscore_ham = P(ham) x P(free in ham) x P(win in ham)\n"
                "p_spam = score_spam / (score_spam + score_ham)",
        "code": _code("""
from fractions import Fraction as F

spam, ham = $spam, $ham                    # emails the filter learned from
free_spam, free_ham = $free_spam, $free_ham  # how many contain the word "free"
win_spam, win_ham = $win_spam, $win_ham      # how many contain the word "win"
total = spam + ham

# a new email says "free" and "win": multiply one fraction per word ("naive")
score_spam = F(spam, total) * F(free_spam, spam) * F(win_spam, spam)
score_ham = F(ham, total) * F(free_ham, ham) * F(win_ham, ham)
p_spam = score_spam / (score_spam + score_ham)
print("score_spam =", score_spam, " score_ham =", score_ham, " p_spam =", p_spam)
"""),
        "hand": lambda p, v: [f"score_spam = {p['spam']}/{p['spam'] + p['ham']} * {p['free_spam']}/{p['spam']} * {p['win_spam']}/{p['spam']} = {fmt(v['score_spam'])}",
                              f"score_ham = {p['ham']}/{p['spam'] + p['ham']} * {p['free_ham']}/{p['ham']} * {p['win_ham']}/{p['ham']} = {fmt(v['score_ham'])}",
                              f"p_spam = {fmt(v['score_spam'])} / ({fmt(v['score_spam'])} + {fmt(v['score_ham'])}) = {fmt(v['p_spam'])}"],
        "valid": lambda p: None if (p["free_spam"] <= p["spam"] and p["win_spam"] <= p["spam"] and p["free_ham"] <= p["ham"]
                                    and p["win_ham"] <= p["ham"] and (p["free_spam"] * p["win_spam"] + p["free_ham"] * p["win_ham"]) > 0)
                           else "word counts must fit inside each group, and at least one score must be above 0",
    },
    "success_rate": {
        "concept": "basic-probability", "title": "Success-rate model",
        "params": {"attempts": (20, 5, 200), "successes": (12, 0, 200), "upcoming": (10, 1, 100)},
        "whatif": ["successes", "upcoming"],
        "labels": {"attempts": "attempts recorded", "successes": "successful attempts", "upcoming": "attempts coming up"},
        "check": ["p_success", "expected"],
        "task": "p_success = successes / attempts\nexpected = p_success x upcoming",
        "code": _code("""
from fractions import Fraction as F

attempts = $attempts      # attempts recorded so far
successes = $successes    # how many worked
upcoming = $upcoming      # attempts in the next match or shift

p_success = F(successes, attempts)
expected = p_success * upcoming   # how many to expect next time
print("p_success =", p_success, " expected =", expected)
"""),
        "hand": lambda p, v: [f"p_success = {p['successes']}/{p['attempts']} = {fmt(v['p_success'])}",
                              f"expected = {fmt(v['p_success'])} * {p['upcoming']} = {fmt(v['expected'])}"],
        "valid": lambda p: None if p["successes"] <= p["attempts"] else "successes cannot be more than attempts",
    },
    "quality_check": {
        "concept": "complementary-events", "title": "Pass/fail rate check",
        "params": {"checked": (40, 5, 500), "failed": (3, 0, 500), "batch": (200, 5, 5000)},
        "whatif": ["failed", "batch"],
        "labels": {"checked": "items checked", "failed": "items that failed", "batch": "items in the next batch"},
        "check": ["p_fail", "p_pass", "expected_pass"],
        "task": "p_fail = failed / checked\np_pass = 1 - p_fail\nexpected_pass = p_pass x batch",
        "code": _code("""
from fractions import Fraction as F

checked = $checked   # items tested
failed = $failed     # items that failed the test
batch = $batch       # size of the next batch

p_fail = F(failed, checked)
p_pass = 1 - p_fail             # complement: an item either fails or passes
expected_pass = p_pass * batch
print("p_fail =", p_fail, " p_pass =", p_pass, " expected_pass =", expected_pass)
"""),
        "hand": lambda p, v: [f"p_fail = {p['failed']}/{p['checked']} = {fmt(v['p_fail'])}",
                              f"p_pass = 1 - {fmt(v['p_fail'])} = {fmt(v['p_pass'])}",
                              f"expected_pass = {fmt(v['p_pass'])} * {p['batch']} = {fmt(v['expected_pass'])}"],
        "valid": lambda p: None if p["failed"] <= p["checked"] else "failed cannot be more than checked",
    },
    "overlap_screening": {
        "concept": "addition-rule-for-inclusive-events", "title": "Overlap screening",
        "params": {"total": (50, 10, 1000), "group_a": (20, 0, 1000), "group_b": (15, 0, 1000), "both": (5, 0, 1000)},
        "whatif": ["group_a", "group_b", "both"],
        "labels": {"total": "people in total", "group_a": "people in group A", "group_b": "people in group B", "both": "people in both"},
        "check": ["p_either", "p_neither"],
        "task": "p_either = (group_a + group_b - both) / total\np_neither = 1 - p_either",
        "code": _code("""
from fractions import Fraction as F

total = $total       # everyone screened
group_a = $group_a   # people with sign A
group_b = $group_b   # people with sign B
both = $both         # people with both, counted in A and in B

p_either = F(group_a + group_b - both, total)   # subtract the overlap once
p_neither = 1 - p_either
print("p_either =", p_either, " p_neither =", p_neither)
"""),
        "hand": lambda p, v: [f"p_either = ({p['group_a']} + {p['group_b']} - {p['both']})/{p['total']} = {fmt(v['p_either'])}",
                              f"p_neither = 1 - {fmt(v['p_either'])} = {fmt(v['p_neither'])}"],
        "valid": lambda p: None if (p["both"] <= min(p["group_a"], p["group_b"])
                                    and p["group_a"] + p["group_b"] - p["both"] <= p["total"])
                           else "'both' must fit inside each group, and the groups must fit inside the total",
    },
    "dosage": {
        "concept": "solving-algebraic-equations", "title": "Medicine dose calculator",
        "params": {"mg_per_kg": (15, 1, 50), "weight": (18, 2, 120), "tablet_mg": (90, 5, 1000)},
        "whatif": ["mg_per_kg", "weight"],
        "labels": {"mg_per_kg": "mg per kg of body weight", "weight": "patient weight in kg", "tablet_mg": "mg in one tablet"},
        "check": ["dose", "tablets"],
        "task": "dose = mg_per_kg x weight\ntablets = dose / tablet_mg",
        "code": _code("""
from fractions import Fraction as F

mg_per_kg = $mg_per_kg   # prescribed strength
weight = $weight         # patient's mass in kg
tablet_mg = $tablet_mg   # strength of one tablet

dose = mg_per_kg * weight          # total mg needed
tablets = F(dose, tablet_mg)       # solve: tablets x tablet_mg = dose
print("dose =", dose, "mg  tablets =", tablets)
"""),
        "hand": lambda p, v: [f"dose = {p['mg_per_kg']} * {p['weight']} = {fmt(v['dose'])}",
                              f"tablets = {fmt(v['dose'])}/{p['tablet_mg']} = {fmt(v['tablets'])}"],
        "valid": lambda p: None,
    },
    "ohms_law": {
        "concept": "solving-algebraic-equations", "title": "Circuit check (Ohm's law)",
        "params": {"voltage": (230, 1, 400), "resistance": (46, 1, 1000)},
        "whatif": ["voltage", "resistance"],
        "labels": {"voltage": "volts", "resistance": "ohms"},
        "check": ["current", "power"],
        "task": "current = voltage / resistance   (solve V = I x R for I)\npower = voltage x current",
        "code": _code("""
from fractions import Fraction as F

voltage = $voltage         # volts from the supply
resistance = $resistance   # ohms in the appliance

current = F(voltage, resistance)   # V = I x R, so I = V / R
power = voltage * current          # watts
print("current =", current, "A  power =", power, "W")
"""),
        "hand": lambda p, v: [f"current = {p['voltage']}/{p['resistance']} = {fmt(v['current'])}",
                              f"power = {p['voltage']} * {fmt(v['current'])} = {fmt(v['power'])}"],
        "valid": lambda p: None,
    },
    "roof_truss": {
        "concept": "euclidean-geometry", "title": "Roof truss angles",
        "params": {"base_angle": (35, 5, 85)},
        "whatif": ["base_angle"],
        "labels": {"base_angle": "degrees at each base of the roof"},
        "check": ["apex_angle"],
        "task": "The truss is an isosceles triangle, so both base angles are equal.\napex_angle = 180 - 2 x base_angle",
        "code": _code("""
base_angle = $base_angle    # degrees where the roof meets each wall

# isosceles triangle: equal base angles, and the angles in a triangle add to 180
apex_angle = 180 - 2 * base_angle
print("apex_angle =", apex_angle, "degrees")
"""),
        "hand": lambda p, v: [f"apex_angle = 180 - 2 * {p['base_angle']} = {fmt(v['apex_angle'])}"],
        "valid": lambda p: None,
    },
}


def clean_params(key: str, proposed) -> tuple:
    """Whole numbers within each template's range; anything else falls back to the default.
    Returns (params, list of problems found) so the Reviewer can report them."""
    t, out, problems = TEMPLATES[key], {}, []
    proposed = proposed if isinstance(proposed, dict) else {}
    for name, (default, lo, hi) in t["params"].items():
        v = proposed.get(name, default)
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            if name in proposed:
                problems.append(f"{name}={v!r} is not a whole number from {lo} to {hi}")
            v = default
        out[name] = v
    err = t["valid"](out)
    if err:
        problems.append(err)
        out = {n: d for n, (d, _, _) in t["params"].items()}
    return out, problems


def run(key: str, params: dict):
    """Fill the template with validated numbers, run it, and return (source, printed output, checked values)."""
    t = TEMPLATES[key]
    src = t["code"].substitute({k: str(v) for k, v in params.items()})
    ns, out = {"__builtins__": _SAFE}, io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(src, f"<mission {key}>", "exec"), ns)  # our own template; inputs are validated ints
    values = {name: Fraction(ns[name]) for name in t["check"]}
    return src, out.getvalue().strip(), values


def plain_brief(key: str, params: dict) -> str:
    t = TEMPLATES[key]
    facts = ", ".join(f"{v} {t['labels'][k]}" for k, v in params.items())
    return f"Your data: {facts}."
