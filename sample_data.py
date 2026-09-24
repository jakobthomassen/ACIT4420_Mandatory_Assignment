"""Convenience functions for generating the assignment's sample scenarios."""

from data.data_generator import generate_fitness_data


SCENARIOS = (
    ("resting", 1),
    ("moderate_activity", 2),
    ("high_activity", 3),
    ("recovery", 42),
    ("poor_quality", 5),
)


def generate_scenarios(number_of_windows=12): # Return the five required scenarios as raw generator data
    return {
        name: generate_fitness_data(
            participant_id="P001",
            scenario=name,
            seed=seed,
            number_of_windows=number_of_windows,
        )
        for name, seed in SCENARIOS
    }
