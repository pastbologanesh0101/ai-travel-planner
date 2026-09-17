"""Core rule-based / constraint-based itinerary generation logic.

This module contains no network calls, no LLM API calls, and no live
maps/flights integrations. All data comes from the bundled JSON dataset in
``data/destinations.json`` and all selection logic is deterministic given a
random seed.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "destinations.json"

# Budget tiers are ordered from cheapest to most expensive. A trip booked at
# a given tier may use activities at that tier or any cheaper tier, but never
# a pricier one (e.g. a "budget" trip never gets "luxury" activities).
BUDGET_TIERS = ["budget", "mid", "luxury"]

# How many activities are scheduled per day for each pace setting.
PACE_ACTIVITIES_PER_DAY = {
    "relaxed": 2,
    "moderate": 3,
    "packed": 4,
}

VALID_CATEGORIES = {
    "culture",
    "nature",
    "food",
    "nightlife",
    "adventure",
    "relaxation",
}

# Activities matching a requested interest are this many times more likely
# to be picked than a non-matching activity of equal availability.
INTEREST_WEIGHT_MULTIPLIER = 4


class PlannerError(ValueError):
    """Raised for invalid planner input, such as an unknown destination."""


def load_destinations(path: Optional[str] = None) -> List[dict]:
    """Load the bundled destinations dataset from disk."""
    resolved = Path(path) if path else DATA_PATH
    with open(resolved, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw["destinations"]


def _allowed_tiers(budget: str) -> set:
    if budget not in BUDGET_TIERS:
        raise PlannerError(
            f"Unknown budget tier: {budget!r}. Choose from {BUDGET_TIERS}."
        )
    idx = BUDGET_TIERS.index(budget)
    return set(BUDGET_TIERS[: idx + 1])


def find_destination(name: str, destinations: Sequence[dict]) -> Optional[dict]:
    """Case-insensitive exact-name lookup of a destination."""
    target = name.strip().lower()
    for dest in destinations:
        if dest["name"].lower() == target:
            return dest
    return None


def _eligible_activities(dest: dict, allowed_tiers: set) -> List[dict]:
    return [a for a in dest["activities"] if a["cost_tier"] in allowed_tiers]


def pick_surprise_destination(
    destinations: Sequence[dict],
    interests: Sequence[str],
    budget: str,
    rng: random.Random,
) -> dict:
    """Pick a destination that best matches the requested interests and is
    affordable at the requested budget tier. Ties are broken randomly (via
    the supplied rng) so results stay reproducible under a fixed seed.
    """
    allowed_tiers = _allowed_tiers(budget)
    scored = []
    for dest in destinations:
        eligible = _eligible_activities(dest, allowed_tiers)
        if not eligible:
            continue
        score = sum(1 for a in eligible if a["category"] in interests) if interests else 0
        scored.append((score, dest))
    if not scored:
        raise PlannerError(f"No destinations have activities within budget tier {budget!r}.")
    best_score = max(s for s, _ in scored)
    top_choices = [d for s, d in scored if s == best_score]
    return rng.choice(top_choices)


def _weighted_choice(pool: List[dict], interests: Sequence[str], rng: random.Random) -> dict:
    if interests:
        weights = [
            INTEREST_WEIGHT_MULTIPLIER if a["category"] in interests else 1
            for a in pool
        ]
    else:
        weights = [1 for _ in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


def generate_itinerary(
    destination: str,
    days: int,
    budget: str,
    interests: Optional[Iterable[str]] = None,
    pace: str = "moderate",
    seed: Optional[int] = None,
    destinations: Optional[Sequence[dict]] = None,
) -> dict:
    """Generate a day-by-day itinerary.

    Parameters
    ----------
    destination: destination name, or "surprise me" to auto-pick one that
        best matches the requested interests within budget.
    days: number of days in the trip (>= 1).
    budget: one of "budget", "mid", "luxury". Activities priced at a tier
        more expensive than requested are excluded entirely.
    interests: iterable of category names to weight towards
        (culture, nature, food, nightlife, adventure, relaxation).
    pace: one of "relaxed" (2/day), "moderate" (3/day), "packed" (4/day).
    seed: optional RNG seed for reproducible output.
    destinations: optional pre-loaded destination list (mainly for testing);
        defaults to loading data/destinations.json.

    Returns a dict describing the trip, with a ``day_plans`` list and a
    ``total_cost`` running total.
    """
    if not isinstance(days, int) or days < 1:
        raise PlannerError("days must be a positive integer")
    if pace not in PACE_ACTIVITIES_PER_DAY:
        raise PlannerError(
            f"Unknown pace: {pace!r}. Choose from {list(PACE_ACTIVITIES_PER_DAY)}."
        )

    normalized_interests = sorted(
        {i.strip().lower() for i in (interests or []) if i and i.strip()}
    )
    for interest in normalized_interests:
        if interest not in VALID_CATEGORIES:
            raise PlannerError(
                f"Unknown interest category: {interest!r}. "
                f"Choose from {sorted(VALID_CATEGORIES)}."
            )

    allowed_tiers = _allowed_tiers(budget)
    rng = random.Random(seed)

    all_destinations = destinations if destinations is not None else load_destinations()

    if destination.strip().lower() in ("surprise me", "surprise", ""):
        dest = pick_surprise_destination(all_destinations, normalized_interests, budget, rng)
    else:
        dest = find_destination(destination, all_destinations)
        if dest is None:
            known = ", ".join(sorted(d["name"] for d in all_destinations))
            raise PlannerError(
                f"Unknown destination: {destination!r}. Try 'surprise me', "
                f"or one of: {known}."
            )

    eligible = _eligible_activities(dest, allowed_tiers)
    if not eligible:
        raise PlannerError(
            f"No activities available in {dest['name']!r} at budget tier {budget!r}."
        )

    per_day = PACE_ACTIVITIES_PER_DAY[pace]

    used_names = set()
    day_plans = []
    total_cost = 0.0
    ran_out_of_activities = False

    for day_num in range(1, days + 1):
        pool = [a for a in eligible if a["name"] not in used_names]
        day_activities = []
        for _ in range(per_day):
            if not pool:
                ran_out_of_activities = True
                break
            choice = _weighted_choice(pool, normalized_interests, rng)
            day_activities.append(choice)
            used_names.add(choice["name"])
            pool = [a for a in pool if a["name"] != choice["name"]]
        day_cost = sum(a["cost"] for a in day_activities)
        total_cost += day_cost
        day_plans.append(
            {
                "day": day_num,
                "activities": day_activities,
                "day_cost": day_cost,
            }
        )

    return {
        "destination": dest["name"],
        "country": dest["country"],
        "region": dest["region"],
        "days": days,
        "budget": budget,
        "pace": pace,
        "interests": normalized_interests,
        "day_plans": day_plans,
        "total_cost": total_cost,
        "ran_out_of_activities": ran_out_of_activities,
    }
