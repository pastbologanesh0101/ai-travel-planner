# AI Travel Planner

A small, fully offline, rule-based trip itinerary generator. Give it a
destination (or let it surprise you), a trip length, a budget tier, your
interests, and a pace — it produces a day-by-day itinerary with a running
cost estimate.

There is **no LLM in the loop and no live maps/flights API**. "AI" here
means the classic sense: a constraint-based expert system. All content comes
from a bundled local dataset (`data/destinations.json`) and all selection
logic is deterministic, seedable Python.

## Methodology

1. **Dataset.** `data/destinations.json` bundles 26 real-world destinations,
   each with ~8 hand-curated activities/attractions. Every activity is
   tagged with:
   - `category`: one of `culture`, `nature`, `food`, `nightlife`,
     `adventure`, `relaxation`
   - `cost_tier`: `budget`, `mid`, or `luxury`
   - `cost`: an approximate USD price per person
   - `days_needed`: rough fraction of a day the activity typically takes
     (descriptive metadata, shown for flavor; pace is what actually
     controls how many activities are scheduled per day)

2. **Destination resolution.** If you pass a known destination name
   (case-insensitive), it's looked up directly. If you pass `"surprise me"`
   (the default), the planner scores every destination by how many of its
   affordable activities (at your budget tier) match your requested
   interests, and picks the best match — ties are broken with the seeded
   RNG so results are reproducible.

3. **Budget filtering.** Budget tiers are ordered `budget < mid < luxury`.
   A trip at tier *T* only ever considers activities at tier *T* or
   cheaper. A `"budget"` trip will never be handed a `"luxury"` activity.

4. **Pace.** Controls how many activities are scheduled per day:
   - `relaxed` → 2/day
   - `moderate` → 3/day
   - `packed` → 4/day

5. **Interest-weighted, no-repeat selection.** For each day, the planner
   builds a pool of eligible activities that haven't been used yet anywhere
   in the trip, then does a weighted random draw: activities matching one
   of your requested interest categories are 4x more likely to be picked
   than non-matching ones. Because each activity is removed from the pool
   once chosen, **no activity is ever repeated within a single itinerary**.

6. **Graceful exhaustion.** Small destinations only have so many unique
   activities. If a long/packed trip runs through all of them, the planner
   stops adding activities for the remaining days, prints a note
   explaining why, and still reports an accurate cost total — it never
   invents content or silently repeats an activity.

7. **Cost total.** Each day's cost is the sum of its scheduled activities'
   `cost` values; the trip total is the sum of all day costs.

All randomness goes through a single `random.Random(seed)` instance, so
passing `--seed` makes output fully reproducible (this is also how the test
suite gets deterministic, non-flaky assertions on a "random" weighting
algorithm).

## Installation

Requires Python 3.11+ and nothing else to run (pure standard library).
Tests use `pytest`.

```bash
git clone https://github.com/pastbologanesh0101/ai-travel-planner.git
cd ai-travel-planner
```

## How to run

```bash
python plan.py --destination "Kyoto" --days 5 --budget mid --interests culture,food --pace moderate
```

Arguments:

| Flag | Description | Default |
|---|---|---|
| `--destination` | Destination name, or `"surprise me"` | `surprise me` |
| `--days` | Trip length in days | required |
| `--budget` | `budget`, `mid`, or `luxury` | `mid` |
| `--interests` | Comma-separated: `culture,nature,food,nightlife,adventure,relaxation` | none |
| `--pace` | `relaxed`, `moderate`, or `packed` | `moderate` |
| `--seed` | Optional integer seed for reproducible output | random |
| `--list-destinations` | Print every known destination name (with country/region) and exit | off |

## Example output

```
$ python plan.py --destination "Barcelona" --days 2 --budget luxury --interests culture,food --pace moderate --seed 1

Trip to Barcelona, Spain (Europe)
=================================
Days: 2  |  Budget: luxury  |  Pace: moderate
Interests: culture, food

Day 1:
  - Sagrada Familia guided tour [culture, mid, $30]
  - Fine-dining Catalan tasting menu [food, luxury, $130]
  - Gothic Quarter flamenco show [nightlife, mid, $38]
  Day cost: $198

Day 2:
  - Park Guell mosaic wander [culture, budget, $10]
  - La Boqueria tapas crawl [food, budget, $20]
  - Beach club night with DJs [nightlife, luxury, $95]
  Day cost: $125

Estimated total cost: $323
```

A longer, budget-constrained trip against a small destination will
gracefully report when it runs out of unique activities instead of
repeating one, e.g. `python plan.py --destination "Kyoto" --days 5 --budget
mid --interests culture,food --pace moderate --seed 42` schedules 2 full
days from Kyoto's 6 mid-and-under activities, then prints a note that it
ran out rather than repeating or inventing an activity for days 3-5.

## Running the tests

```bash
pip install pytest
pytest -v
```

or, with only the standard library:

```bash
python -m unittest discover -s tests -v
```

The suite (`tests/test_itinerary.py`) covers, among other things:

- itinerary length matches the requested number of days
- pace correctly controls activities-per-day
- budget tier filtering excludes higher-tier activities
- interest weighting statistically favors requested categories (seeded
  over 200 trials for a stable, non-flaky assertion)
- no duplicate activity ever appears twice in one itinerary
- unknown destinations raise a clear `PlannerError` instead of crashing
- the reported cost total is always the exact sum of chosen activities
- "surprise me" destination picking and full seed-reproducibility

## Troubleshooting / FAQ

**"Error: Unknown destination: 'Paris'..."** — destination lookup is an
exact (case-insensitive) match against `data/destinations.json`. The error
message lists every known destination name; check spelling/accents (e.g.
it's `"Rio de Janeiro"`, not `"Rio"`), or use `--destination "surprise me"`
to let the planner pick one for you.

**"Note: ran out of unique activities..." after just 1-2 days.** Small
destinations have a fixed pool of ~8 activities. A `packed` pace (4/day) on
a `budget` tier trip (which excludes `mid`/`luxury` activities) can run out
of eligible, not-yet-used activities well before the requested day count.
Try a lower pace, a higher budget tier, or a shorter trip.

**"Error: days=5000 is unreasonably large..."** — this is almost always a
typo (e.g. `--days 5000` instead of `--days 5`). The planner caps trips at
`MAX_DAYS` (90) days.

**Why does the same `--seed` sometimes give a different itinerary after I
upgrade?** All randomness is seeded through `random.Random(seed)`, so
results are reproducible *for a given version of the code and dataset*.
Adding/removing destinations or activities, or changing the weighting
algorithm, can change which draws come out of the same seed.

## Project layout

```
ai-travel-planner/
├── data/destinations.json      # bundled dataset (26 destinations, ~208 activities)
├── travel_planner/
│   ├── __init__.py
│   └── itinerary.py            # core rule-based generation logic
├── plan.py                     # CLI entry point
├── tests/test_itinerary.py     # unit tests
└── .github/workflows/tests.yml # CI: runs tests on Python 3.11 and 3.12
```

## License

MIT — see [LICENSE](LICENSE).
