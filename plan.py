#!/usr/bin/env python3
"""AI Travel Planner CLI.

A rule-based / constraint-based trip itinerary generator. No LLM calls, no
live maps or flights APIs -- every recommendation comes from the local
dataset in data/destinations.json.

Example:
    python plan.py --destination "Kyoto" --days 5 --budget mid \
        --interests culture,food --pace moderate
"""
from __future__ import annotations

import argparse
import sys

from travel_planner.itinerary import (
    BUDGET_TIERS,
    PACE_ACTIVITIES_PER_DAY,
    PlannerError,
    generate_itinerary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plan.py",
        description="Generate a rule-based, day-by-day trip itinerary.",
    )
    parser.add_argument(
        "--destination",
        default="surprise me",
        help='Destination name (e.g. "Kyoto"), or "surprise me" to auto-pick '
        "one matching your interests. Default: surprise me.",
    )
    parser.add_argument(
        "--days", type=int, required=True, help="Number of days for the trip."
    )
    parser.add_argument(
        "--budget",
        choices=BUDGET_TIERS,
        default="mid",
        help="Budget tier ceiling. Default: mid.",
    )
    parser.add_argument(
        "--interests",
        default="",
        help="Comma-separated interest categories, e.g. culture,food. "
        "Options: culture, nature, food, nightlife, adventure, relaxation.",
    )
    parser.add_argument(
        "--pace",
        choices=list(PACE_ACTIVITIES_PER_DAY),
        default="moderate",
        help="Activities per day. Default: moderate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible itineraries.",
    )
    return parser


def format_itinerary(itinerary: dict) -> str:
    lines = []
    header = (
        f"Trip to {itinerary['destination']}, {itinerary['country']} "
        f"({itinerary['region']})"
    )
    lines.append(header)
    lines.append("=" * len(header))
    lines.append(
        f"Days: {itinerary['days']}  |  Budget: {itinerary['budget']}  |  "
        f"Pace: {itinerary['pace']}"
    )
    if itinerary["interests"]:
        lines.append(f"Interests: {', '.join(itinerary['interests'])}")
    lines.append("")

    for day_plan in itinerary["day_plans"]:
        lines.append(f"Day {day_plan['day']}:")
        if not day_plan["activities"]:
            lines.append("  (no more unique activities available)")
        for activity in day_plan["activities"]:
            cost_str = "free" if activity["cost"] == 0 else f"${activity['cost']}"
            lines.append(
                f"  - {activity['name']} "
                f"[{activity['category']}, {activity['cost_tier']}, {cost_str}]"
            )
        lines.append(f"  Day cost: ${day_plan['day_cost']}")
        lines.append("")

    lines.append(f"Estimated total cost: ${itinerary['total_cost']:.0f}")
    if itinerary["ran_out_of_activities"]:
        lines.append(
            "Note: ran out of unique activities for this destination before "
            "the trip ended; consider a shorter trip or a different pace."
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    interests = [i for i in args.interests.split(",") if i.strip()]

    try:
        itinerary = generate_itinerary(
            destination=args.destination,
            days=args.days,
            budget=args.budget,
            interests=interests,
            pace=args.pace,
            seed=args.seed,
        )
    except PlannerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(format_itinerary(itinerary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
