# Contributing

AI Travel Planner is a small, fully offline, rule-based itinerary generator.
There's no LLM and no live API in the loop — contributions should keep it
that way (deterministic, seedable, pure standard library).

## Running the tests

```bash
pip install pytest
pytest -v
```

or with zero third-party dependencies:

```bash
python -m unittest discover -s tests -v
```

Please run the full suite before opening a pull request. If you touch the
weighted-selection logic in `travel_planner/itinerary.py`, pay special
attention to `test_interest_weighting_favors_requested_category` — it's a
statistical test over 200 seeds and is sensitive to changes in how weights
are computed.

## Code style

- Pure Python standard library only — no new runtime dependencies.
- Keep `travel_planner/itinerary.py` deterministic: any randomness must go
  through the `rng: random.Random` instance passed in, never `random`'s
  module-level functions, so seeded output stays reproducible.
- Raise `PlannerError` (not a bare `ValueError` or an unhandled exception)
  for any invalid user input, with a message that tells the user what
  valid values look like.
- Match the existing style: `from __future__ import annotations`, type
  hints on public functions, docstrings on non-trivial functions.

## Adding or editing destinations

`data/destinations.json` is hand-curated. If you add a destination or
activity, make sure every activity has a valid `category` (one of
`culture`, `nature`, `food`, `nightlife`, `adventure`, `relaxation`), a
valid `cost_tier` (`budget`, `mid`, `luxury`), and a non-negative numeric
`cost`. `DatasetSanityTests` in `tests/test_itinerary.py` enforces this —
run the tests after editing the dataset.

## Submitting changes

1. Fork the repo and create a branch for your change.
2. Add or update tests for any behavior change.
3. Run the full test suite locally and make sure it's green.
4. Open a pull request describing what changed and why.
