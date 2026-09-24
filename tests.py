"""Tests for the Smart Fitness Session Analyzer."""

import unittest

from data.data_generator import generate_fitness_data
from helpers.calculations import calculate_average, calculate_maximum, calculate_minimum, compare_to_baseline
from helpers.validation import validate_observation
from main import FitnessAnalyzer, ObservationWindow, build_session


class CalculationTests(unittest.TestCase):
    def test_average(self):
        self.assertEqual(calculate_average([2, 4, 6]), 4)

    def test_minimum_and_maximum(self):
        self.assertEqual(calculate_minimum([3, 1, 5]), 1)
        self.assertEqual(calculate_maximum([3, 1, 5]), 5)

    def test_baseline_comparison(self):
        result = compare_to_baseline(90, 75)
        self.assertEqual(result["difference"], 15)
        self.assertAlmostEqual(result["percent_change"], 20)


class ValidationTests(unittest.TestCase):
    def test_valid_observation(self):
        observation = {
            "timestamp": 0,
            "heart_rate": 70,
            "skin_response": 2.0,
            "temperature": 32.0,
            "activity_level": 0.2,
            "signal_quality": 0.9,
        }
        self.assertEqual(validate_observation(observation), [])
        self.assertTrue(ObservationWindow.from_dict(observation).is_usable)

    def test_invalid_observation(self):
        observation = {
            "timestamp": 0,
            "heart_rate": 265,
            "skin_response": 2.0,
            "temperature": 32.0,
            "activity_level": -0.2,
            "signal_quality": 0.9,
        }
        problems = validate_observation(observation)
        self.assertEqual(len(problems), 2)

    def test_missing_value(self):
        observation = {
            "timestamp": 0,
            "heart_rate": None,
            "skin_response": 2.0,
            "temperature": 32.0,
            "activity_level": 0.2,
            "signal_quality": 0.9,
        }
        self.assertTrue(any("missing heart_rate" in problem for problem in validate_observation(observation)))


class ScenarioTests(unittest.TestCase):
    def analyze_scenario(self, scenario, seed):
        profile, observations = generate_fitness_data(
            participant_id="TEST",
            scenario=scenario,
            seed=seed,
            number_of_windows=12,
        )
        return FitnessAnalyzer().analyze(build_session(profile, observations))

    def test_resting_scenario(self):
        self.assertEqual(self.analyze_scenario("resting", 1)["classification"], "resting")

    def test_moderate_scenario(self):
        self.assertEqual(self.analyze_scenario("moderate_activity", 2)["classification"], "moderate activity")

    def test_high_scenario(self):
        self.assertEqual(self.analyze_scenario("high_activity", 3)["classification"], "high activity")

    def test_recovery_scenario(self):
        result = self.analyze_scenario("recovery", 42)
        self.assertEqual(result["classification"], "recovering")
        self.assertTrue(result["recovery"]["detected"])

    def test_poor_quality_scenario(self):
        result = self.analyze_scenario("poor_quality", 5)
        self.assertGreater(result["invalid_observations"], 0)
        self.assertGreater(len(result["invalid_reasons"]), 0)

    def test_insufficient_data(self):
        profile, observations = generate_fitness_data(
            participant_id="TEST",
            scenario="resting",
            seed=1,
            number_of_windows=6,
        )
        session = build_session(profile, observations[:3])
        result = FitnessAnalyzer().analyze(session)
        self.assertEqual(result["classification"], "insufficient data")


if __name__ == "__main__":
    unittest.main(verbosity=2)
