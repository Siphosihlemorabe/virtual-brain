"""Chance experiments for the 3D lab. Each event's exact probability is worked out here by listing every
equally likely outcome, so the Reviewer and the lab share one source of truth. The browser only
receives the list of favourable outcomes and counts how often a roll lands in it."""
from fractions import Fraction
from itertools import product

from .mathcheck import fmt

FACES = {"dice": [str(i) for i in range(1, 7)], "coins": ["H", "T"]}

# id: (objects, how many, label, concepts it illustrates, rule on the outcome tuple)
EVENTS = {
    "die_3": ("dice", 1, "Roll a 3", ["basic-probability"], lambda o: o == ("3",)),
    "die_even": ("dice", 1, "Roll an even number", ["basic-probability"], lambda o: int(o[0]) % 2 == 0),
    "die_gt4": ("dice", 1, "Roll more than 4", ["basic-probability"], lambda o: int(o[0]) > 4),
    "die_not_1_or_2": ("dice", 1, "Do NOT roll a 1 or a 2", ["complementary-events"], lambda o: o[0] not in ("1", "2")),
    "die_even_or_gt3": ("dice", 1, "Roll an even number OR more than 3", ["addition-rule-for-inclusive-events"],
                        lambda o: int(o[0]) % 2 == 0 or int(o[0]) > 3),
    "dice_sum_7": ("dice", 2, "Two dice add up to 7", ["basic-probability"], lambda o: int(o[0]) + int(o[1]) == 7),
    "dice_doubles": ("dice", 2, "Roll a double", ["basic-probability"], lambda o: o[0] == o[1]),
    "dice_at_least_one_6": ("dice", 2, "At least one six on two dice", ["complementary-events"], lambda o: "6" in o),
    "dice_six_or_double": ("dice", 2, "A six on the first die OR a double", ["addition-rule-for-inclusive-events"],
                           lambda o: o[0] == "6" or o[0] == o[1]),
    "coin_heads": ("coins", 1, "Toss heads", ["basic-probability"], lambda o: o == ("H",)),
    "coins_two_heads": ("coins", 2, "Two coins both land heads", ["basic-probability"], lambda o: o == ("H", "H")),
    "coins_not_two_heads": ("coins", 2, "NOT two heads", ["complementary-events"], lambda o: o != ("H", "H")),
    "coins_at_least_one_head": ("coins", 2, "At least one head", ["complementary-events"], lambda o: "H" in o),
}


def outcomes(objects: str, count: int) -> list:
    return list(product(FACES[objects], repeat=count))


def exact(event_id: str) -> Fraction:
    objects, count, _, _, rule = EVENTS[event_id]
    space = outcomes(objects, count)
    return Fraction(sum(1 for o in space if rule(o)), len(space))


def describe(event_id: str) -> dict:
    objects, count, label, concepts, rule = EVENTS[event_id]
    space = outcomes(objects, count)
    fav = ["-".join(o) for o in space if rule(o)]
    return {"id": event_id, "label": label, "objects": objects, "count": count, "concepts": concepts,
            "favourable": fav, "total": len(space), "p": fmt(exact(event_id))}


def catalogue() -> list:
    return [describe(e) for e in EVENTS]


def menu() -> list:
    """For the Tutor: the only experiments a Simulate question may use."""
    return [(e, EVENTS[e][2]) for e in EVENTS]
