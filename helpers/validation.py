"""Validation helpers for fitness profiles and observations."""


def validate_profile(profile): # Return a list of problems found in a participant profile
    problems = []
    required = (
        "participant_id",
        "baseline_heart_rate",
        "baseline_skin_response",
        "baseline_temperature",
    )

    for field in required:
        if field not in profile or profile[field] is None:
            problems.append(f"missing {field}")

    if problems:
        return problems

    if not isinstance(profile["participant_id"], str) or not profile["participant_id"].strip():
        problems.append("participant_id must be a non-empty string")
    if not isinstance(profile["baseline_heart_rate"], (int, float)) or not 35 <= profile["baseline_heart_rate"] <= 205:
        problems.append("baseline_heart_rate must be between 35 and 205")
    if not isinstance(profile["baseline_skin_response"], (int, float)) or profile["baseline_skin_response"] < 0:
        problems.append("baseline_skin_response must be 0 or greater")
    if not isinstance(profile["baseline_temperature"], (int, float)) or not 25 <= profile["baseline_temperature"] <= 42:
        problems.append("baseline_temperature must be between 25 and 42")

    return problems


def validate_observation(observation): # Return a list of validation problems for one raw observation
    problems = []
    required = (
        "timestamp",
        "heart_rate",
        "skin_response",
        "temperature",
        "activity_level",
        "signal_quality",
    )

    for field in required:
        if field not in observation or observation[field] is None:
            problems.append(f"missing {field}")

    if "timestamp" in observation and observation["timestamp"] is not None:
        if not isinstance(observation["timestamp"], int) or observation["timestamp"] < 0:
            problems.append("timestamp must be an integer of 0 or greater")

    if "heart_rate" in observation and observation["heart_rate"] is not None:
        if not isinstance(observation["heart_rate"], (int, float)) or not 35 <= observation["heart_rate"] <= 205:
            problems.append("heart_rate must be between 35 and 205")

    if "skin_response" in observation and observation["skin_response"] is not None:
        if not isinstance(observation["skin_response"], (int, float)) or observation["skin_response"] < 0:
            problems.append("skin_response must be 0 or greater")

    if "temperature" in observation and observation["temperature"] is not None:
        if not isinstance(observation["temperature"], (int, float)) or not 25 <= observation["temperature"] <= 42:
            problems.append("temperature must be between 25 and 42")

    for field in ("activity_level", "signal_quality"):
        if field in observation and observation[field] is not None:
            value = observation[field]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                problems.append(f"{field} must be between 0 and 1")

    return problems
