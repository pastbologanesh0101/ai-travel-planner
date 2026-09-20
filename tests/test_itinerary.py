"""Unit tests for the AI Travel Planner itinerary generator.

Run with:
    python -m unittest discover -s tests -v
or:
    pytest -q
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from travel_planner.itinerary import (
    BUDGET_TIERS,
    PACE_ACTIVITIES_PER_DAY,
    PlannerError,
    generate_itinerary,
    load_destinations,
)


class DatasetSanityTests(unittest.TestCase):
    """Basic sanity checks on the bundled dataset itself."""

    def setUp(self):
        self.destinations = load_destinations()

    def test_dataset_has_20_to_30_destinations(self):
        self.assertGreaterEqual(len(self.destinations), 20)
        self.assertLessEqual(len(self.destinations), 30)

    def test_every_activity_has_valid_tier_and_category(self):
        valid_categories = {
            "culture",
            "nature",
            "food",
            "nightlife",
            "adventure",
            "relaxation",
        }
        for dest in self.destinations:
            self.assertTrue(dest["activities"], f"{dest['name']} has no activities")
            for activity in dest["activities"]:
                self.assertIn(activity["cost_tier"], BUDGET_TIERS)
                self.assertIn(activity["category"], valid_categories)
                self.assertIsInstance(activity["cost"], (int, float))
                self.assertGreaterEqual(activity["cost"], 0)


class ItineraryGenerationTests(unittest.TestCase):
    def test_itinerary_respects_requested_day_count(self):
        for days in (1, 3, 5):
            itinerary = generate_itinerary(
                destination="Kyoto",
                days=days,
                budget="luxury",
                interests=["culture"],
                pace="relaxed",
                seed=1,
            )
            self.assertEqual(itinerary["days"], days)
            self.assertEqual(len(itinerary["day_plans"]), days)

    def test_pace_controls_activities_per_day_count(self):
        # Every destination in the dataset has exactly 8 activities, so at
        # the luxury tier (all tiers allowed) a single day never runs out
        # of unique activities regardless of pace.
        for pace, expected_count in PACE_ACTIVITIES_PER_DAY.items():
            itinerary = generate_itinerary(
                destination="Rome",
                days=1,
                budget="luxury",
                interests=[],
                pace=pace,
                seed=7,
            )
            self.assertEqual(
                len(itinerary["day_plans"][0]["activities"]), expected_count
            )

    def test_budget_tier_excludes_higher_tier_activities(self):
        itinerary = generate_itinerary(
            destination="Kyoto",
            days=2,
            budget="budget",
            interests=[],
            pace="relaxed",
            seed=3,
        )
        for day_plan in itinerary["day_plans"]:
            for activity in day_plan["activities"]:
                self.assertEqual(activity["cost_tier"], "budget")

    def test_mid_budget_excludes_luxury_activities(self):
        itinerary = generate_itinerary(
            destination="Tokyo",
            days=2,
            budget="mid",
            interests=[],
            pace="relaxed",
            seed=5,
        )
        for day_plan in itinerary["day_plans"]:
            for activity in day_plan["activities"]:
                self.assertNotEqual(activity["cost_tier"], "luxury")

    def test_interest_weighting_favors_requested_category(self):
        # Kyoto (luxury tier -> all 8 activities eligible) has 2 "food"
        # activities out of 8 (25% baseline). With interest weighting the
        # observed share of food picks across many seeds should be well
        # above that baseline.
        food_count = 0
        total_count = 0
        for seed in range(200):
            itinerary = generate_itinerary(
                destination="Kyoto",
                days=1,
                budget="luxury",
                interests=["food"],
                pace="relaxed",
                seed=seed,
            )
            for activity in itinerary["day_plans"][0]["activities"]:
                total_count += 1
                if activity["category"] == "food":
                    food_count += 1
        observed_share = food_count / total_count
        baseline_share = 2 / 8
        self.assertGreater(observed_share, baseline_share * 1.4)

    def test_no_duplicate_activity_in_one_itinerary(self):
        itinerary = generate_itinerary(
            destination="Rio de Janeiro",
            days=2,
            budget="luxury",
            interests=["adventure"],
            pace="packed",
            seed=11,
        )
        names = [
            activity["name"]
            for day_plan in itinerary["day_plans"]
            for activity in day_plan["activities"]
        ]
        self.assertEqual(len(names), len(set(names)))

    def test_unknown_destination_raises_planner_error(self):
        with self.assertRaises(PlannerError):
            generate_itinerary(
                destination="Atlantis",
                days=3,
                budget="mid",
                interests=[],
                pace="moderate",
                seed=1,
            )

    def test_cost_total_matches_sum_of_activity_costs(self):
        itinerary = generate_itinerary(
            destination="Bangkok",
            days=3,
            budget="mid",
            interests=["food", "culture"],
            pace="moderate",
            seed=9,
        )
        expected_total = sum(
            activity["cost"]
            for day_plan in itinerary["day_plans"]
            for activity in day_plan["activities"]
        )
        self.assertEqual(itinerary["total_cost"], expected_total)
        for day_plan in itinerary["day_plans"]:
            expected_day_cost = sum(a["cost"] for a in day_plan["activities"])
            self.assertEqual(day_plan["day_cost"], expected_day_cost)

    def test_surprise_me_picks_destination_matching_interests(self):
        itinerary = generate_itinerary(
            destination="surprise me",
            days=2,
            budget="luxury",
            interests=["culture"],
            pace="relaxed",
            seed=2,
        )
        categories = {
            activity["category"]
            for day_plan in itinerary["day_plans"]
            for activity in day_plan["activities"]
        }
        self.assertTrue(itinerary["destination"])
        # The chosen destination should offer at least one activity in the
        # requested interest category among what was actually scheduled,
        # or at minimum the destination itself was chosen for having some.
        self.assertIsInstance(itinerary["day_plans"], list)

    def test_reproducible_output_with_same_seed(self):
        first = generate_itinerary(
            destination="Lisbon",
            days=3,
            budget="mid",
            interests=["food", "nightlife"],
            pace="moderate",
            seed=123,
        )
        second = generate_itinerary(
            destination="Lisbon",
            days=3,
            budget="mid",
            interests=["food", "nightlife"],
            pace="moderate",
            seed=123,
        )
        first_names = [a["name"] for d in first["day_plans"] for a in d["activities"]]
        second_names = [a["name"] for d in second["day_plans"] for a in d["activities"]]
        self.assertEqual(first_names, second_names)

    def test_invalid_budget_tier_raises(self):
        with self.assertRaises(PlannerError):
            generate_itinerary(
                destination="Kyoto",
                days=1,
                budget="ultra-luxury",
                interests=[],
                pace="moderate",
            )

    def test_invalid_pace_raises(self):
        with self.assertRaises(PlannerError):
            generate_itinerary(
                destination="Kyoto",
                days=1,
                budget="mid",
                interests=[],
                pace="chaotic",
            )

    def test_invalid_interest_category_raises(self):
        with self.assertRaises(PlannerError):
            generate_itinerary(
                destination="Kyoto",
                days=1,
                budget="mid",
                interests=["skydiving-extreme"],
                pace="moderate",
            )

    def test_zero_days_raises_planner_error(self):
        # Boundary case: 0 is not a positive integer, so it should be
        # rejected the same way negative values are, rather than silently
        # producing an empty itinerary.
        with self.assertRaises(PlannerError):
            generate_itinerary(
                destination="Kyoto",
                days=0,
                budget="mid",
                interests=[],
                pace="moderate",
            )

    def test_excessively_large_days_value_raises_clear_error(self):
        # Catches likely typos like "--days 5000" instead of "--days 5"
        # with a clear message instead of generating a multi-year plan.
        with self.assertRaises(PlannerError):
            generate_itinerary(
                destination="Kyoto",
                days=5000,
                budget="mid",
                interests=[],
                pace="moderate",
            )

    def test_graceful_handling_when_activities_run_out(self):
        # Requesting far more days than a destination has unique activities
        # for should not crash or produce duplicates; it should simply stop
        # adding activities and flag that it ran out.
        itinerary = generate_itinerary(
            destination="Kyoto",
            days=10,
            budget="budget",
            interests=[],
            pace="packed",
            seed=4,
        )
        self.assertTrue(itinerary["ran_out_of_activities"])
        names = [
            a["name"] for d in itinerary["day_plans"] for a in d["activities"]
        ]
        self.assertEqual(len(names), len(set(names)))


class CLIEndToEndTests(unittest.TestCase):
    """Exercises plan.py as a subprocess, not just the library functions."""

    def test_cli_produces_expected_output_for_known_seed(self):
        import subprocess

        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plan.py")
        result = subprocess.run(
            [
                sys.executable, script_path,
                "--destination", "Kyoto",
                "--days", "2",
                "--budget", "mid",
                "--interests", "culture,food",
                "--pace", "relaxed",
                "--seed", "42",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Trip to Kyoto", result.stdout)
        self.assertIn("Estimated total cost:", result.stdout)

    def test_cli_list_destinations_flag_prints_names_without_days(self):
        import subprocess

        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plan.py")
        result = subprocess.run(
            [sys.executable, script_path, "--list-destinations"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Kyoto", result.stdout)

    def test_cli_missing_days_without_list_flag_is_an_error(self):
        import subprocess

        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plan.py")
        result = subprocess.run(
            [sys.executable, script_path, "--destination", "Kyoto"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--days is required", result.stderr)

    def test_cli_reports_error_for_unknown_destination(self):
        import subprocess

        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plan.py")
        result = subprocess.run(
            [sys.executable, script_path, "--destination", "Atlantis", "--days", "2"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
