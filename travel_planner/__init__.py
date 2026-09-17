"""AI Travel Planner - a rule-based, constraint-based trip itinerary generator.

No LLM calls and no live maps/flights APIs are used anywhere in this package.
All recommendations come from the bundled local dataset in data/destinations.json
combined with a deterministic, seedable selection algorithm.
"""

from .itinerary import (
    PlannerError,
    generate_itinerary,
    load_destinations,
    find_destination,
    BUDGET_TIERS,
    PACE_ACTIVITIES_PER_DAY,
    VALID_CATEGORIES,
)

__all__ = [
    "PlannerError",
    "generate_itinerary",
    "load_destinations",
    "find_destination",
    "BUDGET_TIERS",
    "PACE_ACTIVITIES_PER_DAY",
    "VALID_CATEGORIES",
]
