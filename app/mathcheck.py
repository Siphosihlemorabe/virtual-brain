"""Exact arithmetic for the agents. No language model here: every number is checked in code."""
import ast
import re
from dataclasses import dataclass, field
from fractions import Fraction

_ARITH = re.compile(r"^[\d\s.+\-*/()]+$")


def _clean(expr: str) -> str:
    return expr.strip().replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-")


def _parse(expr: str):
    s = _clean(expr)
    if not s or not _ARITH.match(s) or not re.search(r"\d", s):
        return None
    try:
        return ast.parse(s, mode="eval").body
    except SyntaxError:
        return None


def _ev(n) -> Fraction:
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return Fraction(str(n.value))
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        v = _ev(n.operand)
        return -v if isinstance(n.op, ast.USub) else v
    if isinstance(n, ast.BinOp):
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Add):
            return a + b
        if isinstance(n.op, ast.Sub):
            return a - b
        if isinstance(n.op, ast.Mult):
            return a * b
        if isinstance(n.op, ast.Div):
            if b == 0:
                raise ZeroDivisionError
            return a / b
    raise ValueError("unsupported expression")


def evaluate(expr: str):
    """Exact value of an arithmetic expression, or None if it is not pure arithmetic."""
    node = _parse(expr)
    if node is None:
        return None
    try:
        return _ev(node)
    except (ValueError, ZeroDivisionError):
        return None


def terms(expr: str):
    """Top-level added/subtracted terms, sorted. 18/30 + 12/30 - 5/30 -> [-1/6, 2/5, 3/5]."""
    node = _parse(expr)
    if node is None:
        return None
    out = []

    def walk(n, sign):
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)):
            walk(n.left, sign)
            walk(n.right, sign if isinstance(n.op, ast.Add) else -sign)
        else:
            out.append(sign * _ev(n))

    try:
        walk(node, 1)
    except (ValueError, ZeroDivisionError):
        return None
    return sorted(out)


def fmt(v) -> str:
    if v is None:
        return "?"
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


@dataclass
class Step:
    text: str
    label: str  # e.g. "p(1or2)", "" if none
    exprs: list = field(default_factory=list)  # arithmetic segments of the "=" chain, in order
    values: list = field(default_factory=list)

    @property
    def value(self):
        return self.values[-1]

    @property
    def first_expr(self):
        return self.exprs[0]

    @property
    def consistent(self) -> bool:
        """Every side of the '=' chain has the same exact value."""
        return all(v == self.values[0] for v in self.values)


def _label(part: str) -> str:
    m = re.findall(r"P\([^)]*\)", part, flags=re.I)
    raw = m[-1] if m else part
    return re.sub(r"\s+", "", raw.lower())


def parse_steps(lines) -> list:
    """Turn lines like 'P(A or B) = 13/30 + 7/30 = 20/30' into Steps. Prose is skipped."""
    steps = []
    for line in lines:
        for chain in re.split(r"[,;]\s+|\.\s+|\.$", line):
            if "=" not in chain:
                continue
            parts = chain.split("=")
            exprs, label = [], ""
            for p in parts:
                if evaluate(p) is not None:
                    exprs.append(p.strip())
                elif not exprs and p.strip():
                    label = _label(p)
            if exprs:
                steps.append(Step(chain.strip(), label, exprs, [evaluate(e) for e in exprs]))
    return steps
