"""
Smart Fitness Session Analyzer.

The application converts the supplied raw dictionaries into domain objects,
validates them, analyzes each session, and prints a report.
"""

from data.data_generator import generate_fitness_data
from helpers.calculations import (
    calculate_average,
    calculate_maximum,
    calculate_minimum,
    calculate_recovery,
    compare_to_baseline,
)
from helpers.reporting import format_report
from helpers.validation import validate_observation, validate_profile


class ReferenceProfile: # Personal reference measurements for a participant

    def __init__(self, baseline_heart_rate, baseline_skin_response, baseline_temperature):
        self.baseline_heart_rate = baseline_heart_rate
        self.baseline_skin_response = baseline_skin_response
        self.baseline_temperature = baseline_temperature


class Participant: # A participant and their personal reference profile

    def __init__(self, participant_id, reference_profile):
        self._participant_id = participant_id
        self.reference_profile = reference_profile

    @property
    def participant_id(self): # Return the participant identifier without exposing the stored attribute
        return self._participant_id

    @classmethod
    def from_profile_dict(cls, profile): # Create a participant from the supplied generator's profile dictionary
        problems = validate_profile(profile)
        if problems:
            raise ValueError("Invalid participant profile: " + "; ".join(problems))

        reference = ReferenceProfile(
            profile["baseline_heart_rate"],
            profile["baseline_skin_response"],
            profile["baseline_temperature"],
        )
        return cls(profile["participant_id"], reference)


class ObservationWindow: # One measurement window, including any validation problems

    def __init__(self, timestamp, heart_rate, skin_response, temperature, activity_level, signal_quality, problems=None):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality
        self.problems = problems or []

    @property
    def is_usable(self): # True when the observation has no validation problems
        return not self.problems

    @staticmethod
    def from_dict(observation): # create and validate an observation from a raw dictionary
        problems = validate_observation(observation)
        return ObservationWindow(
            observation.get("timestamp"),
            observation.get("heart_rate"),
            observation.get("skin_response"),
            observation.get("temperature"),
            observation.get("activity_level"),
            observation.get("signal_quality"),
            problems,
        )


class FitnessSession: # a participant's ordered collection of observation windows

    def __init__(self, participant):
        self.participant = participant
        self.observations = []

    def add_observation(self, observation):
        self.observations.append(observation)

    @property
    def usable_observations(self):
        return [observation for observation in self.observations if observation.is_usable]


class BaseAnalyzer: # base interface for session analyzers

    def analyze(self, session):
        raise NotImplementedError


class FitnessAnalyzer(BaseAnalyzer): # analyze observations and classify the session

    SIGNAL_QUALITY_THRESHOLD = 0.60
    MINIMUM_USABLE_OBSERVATIONS = 4

    def analyze(self, session):
        usable = [
            observation
            for observation in session.usable_observations
            if observation.signal_quality >= self.SIGNAL_QUALITY_THRESHOLD
        ]
        invalid = [observation for observation in session.observations if observation not in usable]

        summaries = self._summaries(usable)
        recovery = self._recovery(usable)
        classification = self._classify(usable, recovery)
        invalid_reasons = self._invalid_reasons(session.observations, usable)

        return {
            "participant_id": session.participant.participant_id,
            "classification": classification,
            "total_observations": len(session.observations),
            "usable_observations": len(usable),
            "invalid_observations": len(invalid),
            "summaries": summaries,
            "baseline_comparison": self._baseline_comparison(session.participant, summaries),
            "recovery": recovery,
            "invalid_reasons": invalid_reasons,
            "explanation": self._explanation(classification, summaries, recovery, len(usable)),
        }

    def _summaries(self, observations):
        fields = ("heart_rate", "skin_response", "temperature", "activity_level", "signal_quality")
        summaries = {}
        for field in fields:
            values = [getattr(observation, field) for observation in observations]
            summaries[field] = {
                "average": calculate_average(values),
                "minimum": calculate_minimum(values),
                "maximum": calculate_maximum(values),
            }
        return summaries

    def _baseline_comparison(self, participant, summaries):
        reference = participant.reference_profile
        baselines = {
            "heart_rate": reference.baseline_heart_rate,
            "skin_response": reference.baseline_skin_response,
            "temperature": reference.baseline_temperature,
        }
        result = {}
        for field, baseline in baselines.items():
            comparison = compare_to_baseline(summaries[field]["average"], baseline)
            comparison["baseline"] = baseline
            result[field] = comparison
        return result

    def _recovery(self, observations):
        if len(observations) < 6:
            return {
                "detected": False,
                "heart_rate_decline": None,
                "activity_decline": None,
            }

        split = max(2, len(observations) // 3)
        first = observations[:split]
        last = observations[-split:]
        first_hr = calculate_average([item.heart_rate for item in first])
        last_hr = calculate_average([item.heart_rate for item in last])
        first_activity = calculate_average([item.activity_level for item in first])
        last_activity = calculate_average([item.activity_level for item in last])
        hr_decline = first_hr - last_hr
        activity_decline = first_activity - last_activity

        detected = calculate_recovery(
            [item.heart_rate for item in first],
            [item.heart_rate for item in last],
            20,
        ) and calculate_recovery(
            [item.activity_level for item in first],
            [item.activity_level for item in last],
            0.25,
        )

        return {
            "detected": detected,
            "heart_rate_decline": hr_decline,
            "activity_decline": activity_decline,
        }

    def _classify(self, observations, recovery):
        if len(observations) < self.MINIMUM_USABLE_OBSERVATIONS:
            return "insufficient data"
        if recovery["detected"]:
            return "recovering"

        average_hr = calculate_average([item.heart_rate for item in observations])
        average_activity = calculate_average([item.activity_level for item in observations])
        baseline_hr = observations[0]  # Only used to avoid passing extra state below.

        # Classification thresholds use activity first, with heart rate providing a secondary check against the participant's resting reference.
        if average_activity < 0.25:
            return "resting"
        if average_activity >= 0.68:
            return "high activity"

        # The generator's moderate range is 0.38-0.66. This also gives unusual mid-range data a sensible classification.
        if average_activity >= 0.30 and average_hr > 85:
            return "moderate activity"
        if average_activity < 0.30:
            return "resting"
        return "moderate activity"

    def _invalid_reasons(self, observations, usable):
        usable_ids = {id(observation) for observation in usable}
        reasons = {}
        for observation in observations:
            if id(observation) in usable_ids:
                continue
            problems = list(observation.problems)
            if not problems and observation.signal_quality < self.SIGNAL_QUALITY_THRESHOLD:
                problems.append("signal_quality below 0.60")
            for problem in problems:
                reasons[problem] = reasons.get(problem, 0) + 1
        return reasons

    @staticmethod
    def _explanation(classification, summaries, recovery, usable_count):
        if classification == "insufficient data":
            return f"Only {usable_count} usable observations were available, so the session cannot be classified reliably."
        if classification == "recovering":
            return "Heart rate and activity both declined substantially near the end of the session."
        if classification == "resting":
            return "Activity remained low and the session did not show a strong recovery trend."
        if classification == "high activity":
            return "Average activity was at or above the high-activity threshold."
        return "The session shows sustained activity in the moderate range without a clear recovery trend."


def build_session(profile_dict, observation_dicts): # convert raw generator output into a validated FitnessSession
    participant = Participant.from_profile_dict(profile_dict)
    session = FitnessSession(participant)
    for observation_dict in observation_dicts:
        session.add_observation(ObservationWindow.from_dict(observation_dict))
    return session


def run_scenario(name, seed): # run one scenario using static participant P001
    profile, observations = generate_fitness_data(
        participant_id="P001",
        scenario=name,
        seed=seed,
        number_of_windows=12,
    )
    session = build_session(profile, observations)
    result = FitnessAnalyzer().analyze(session)
    print(format_report(result))
    print()


def main():
    scenarios = ( # seeds (in this case 1-5) to ensure reproducibility
        ("resting", 1),
        ("moderate_activity", 2),
        ("high_activity", 3),
        ("recovery", 4),
        ("poor_quality", 5),
    )

    for scenario, seed in scenarios:
        print(f"SCENARIO: {scenario.replace('_', ' ').title()}")
        run_scenario(scenario, seed)


if __name__ == "__main__":
    main()
