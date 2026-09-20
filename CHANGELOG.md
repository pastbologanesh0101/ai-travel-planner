# Changelog

## [0.1.0] - Initial release

The first working version of AI Travel Planner: a fully offline,
rule-based/constraint-based trip itinerary generator with no LLM or live
API calls.

Included in the initial commit:

- `data/destinations.json` — a bundled dataset of 26 real-world
  destinations, each with ~8 hand-curated activities tagged by category,
  cost tier, and approximate USD cost.
- `travel_planner/itinerary.py` — core generation logic:
  - Destination resolution by exact name or "surprise me" auto-pick,
    scored by interest match within budget.
  - Budget-tier filtering (`budget` < `mid` < `luxury`).
  - Pace-controlled activity count per day (`relaxed`/`moderate`/`packed`).
  - Interest-weighted, no-repeat activity selection using a seeded RNG.
  - Graceful handling when a destination runs out of unique activities.
  - `PlannerError` raised for invalid input (unknown destination, budget,
    pace, or interest category).
- `plan.py` — the CLI entry point (`--destination`, `--days`, `--budget`,
  `--interests`, `--pace`, `--seed`).
- `tests/test_itinerary.py` — a unit test suite covering day-count
  correctness, pace/budget filtering, interest-weighting (statistically,
  over 200 seeds), no-duplicate guarantees, reproducibility, and error
  handling for invalid input.
- A GitHub Actions workflow running the test suite and a CLI sanity check
  on Python 3.11 and 3.12.
- MIT license.

## [Unreleased]

- `CONTRIBUTING.md` with test/style guidelines.
- Additional tests for the zero-days boundary case and end-to-end CLI
  behavior (previously only the library functions were tested directly).
- A `MAX_DAYS` cap (90) that rejects unreasonably large `--days` values
  with a clear error instead of silently generating a multi-year plan.
- Troubleshooting/FAQ section in the README.
