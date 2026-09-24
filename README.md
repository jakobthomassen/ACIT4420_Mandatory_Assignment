# Smart Fitness Session Analyzer

**Python Programming Assignment (I), Option A**

Student name: **Jakob Thomassen**  
Student number: **421970**

## Description

The Smart Fitness Session Analyzer processes simulated wearable-device measurements from fitness sessions. It converts the supplied raw dictionaries into Python objects, validates observations, summarizes measurements, compares measurements with a participant's personal reference values, detects recovery, classifies the session, and prints a readable report.

The supplied generator remains responsible for producing simulated raw data. The application performs the object-oriented analysis of that data.

## Project structure

```text
.
├── README.md
├── main.py
├── requirements.txt
├── sample_data.py
├── tests.py
├── data
│   ├── DATA_DESCRIPTION.md
│   ├── data_generator.py
│   └── example_usage.py
└── helpers
    ├── __init__.py
    ├── calculations.py
    ├── reporting.py
    └── validation.py
```

`data/data_generator.py` is the supplied data generator. The `helpers` directory contains small reusable calculation, validation, and reporting functions.

## Classes

| Class               | Description                                                                                                                        |
| :------------------ | :--------------------------------------------------------------------------------------------------------------------------------- |
| `ReferenceProfile`  | Stores a participant's baseline heart rate, skin response, and temperature.                                                        |
| `Participant`       | Represents a participant and contains a `ReferenceProfile`. Stored identifier (`_participant_id`) is exposed via `participant_id`. |
| `ObservationWindow` | Represents one measurement window. Stores sensor values and validation problems found in raw dictionary data.                      |
| `FitnessSession`    | Groups a participant and their observation windows, providing access to usable observations.                                       |
| `BaseAnalyzer`      | Defines the analysis interface.                                                                                                    |
| `FitnessAnalyzer`   | Inherits from `BaseAnalyzer` and implements the fitness-specific `analyze` method and classification rules.                        |

## OOP requirements

| OOP Concept                  | Application                     | Details                                                                                                                           |
| :--------------------------- | :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------- |
| **Composition**              | `Participant`, `FitnessSession` | `Participant` contains a `ReferenceProfile`; `FitnessSession` contains a `Participant` and a list of `ObservationWindow` objects. |
| **Encapsulation**            | `Participant._participant_id`   | Uses a protected-style attribute exposed through a read-only `participant_id` property instead of direct access.                  |
| **Inheritance & Overriding** | `FitnessAnalyzer`               | Inherits from `BaseAnalyzer` and overrides `analyze` with fitness-session specific implementation.                                |
| **Class Method**             | `Participant.from_profile_dict` | Alternative constructor converting profile dictionary output from a generator into a `Participant` instance.                      |
| **Static Method**            | `ObservationWindow.from_dict`   | Utility method converting raw dictionary data to an `ObservationWindow` without needing an active instance.                       |

## Validation rules

The application checks the supplied observation fields against the documented ranges:

| Field            | Rule                  |
| ---------------- | --------------------- |
| `timestamp`      | integer, 0 or greater |
| `heart_rate`     | 35-205 bpm            |
| `skin_response`  | 0 or greater          |
| `temperature`    | 25-42 C               |
| `activity_level` | 0-1                   |
| `signal_quality` | 0-1                   |

Missing values and `None` values are invalid.

An observation with valid numeric values but signal quality below `0.60` is also excluded from usable analysis. Invalid observations are not repaired or replaced with guessed values. Their problems are reported instead.

## Calculations

The project uses standalone functions for:

- average
- minimum
- maximum
- comparison with a baseline
- recovery decline calculation
- observation and profile validation
- report formatting

Session summaries are calculated for heart rate, skin response, temperature, activity level, and signal quality.

## Classification rules

The rules are intentionally simple and deterministic.

1. Fewer than four usable observations results in **insufficient data**.
2. Recovery is checked before the activity classification. Recovery is detected when both heart rate and activity decline sufficiently between the beginning and end of the usable session.
3. Average activity below `0.25` is classified as **resting**.
4. Average activity at or above `0.68` is classified as **high activity**.
5. Other sufficiently active sessions are classified as **moderate activity**.
6. A detected recovery trend is classified as **recovering**.

The activity thresholds are based on the ranges used by the supplied generator. The generator's recovery scenario is specifically designed to begin at higher activity and heart rate and trend toward the participant's baseline.

## Recovery detection

The analyzer compares the first and final third of the usable observations. Recovery requires both:

- a heart-rate decline of at least 20 bpm; and
- an activity-level decline of at least 0.25.

This prevents a low final value alone from being treated as recovery.

## Required scenarios

`main.py` runs these five scenarios automatically:

1. resting session
2. moderate activity
3. high activity
4. activity followed by recovery
5. poor-quality or invalid sensor data

Fixed random seeds are used so the demonstrations are reproducible.

## Installation and running

The project requires Python 3 and no third-party packages.

```bash
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
python3 main.py
```

On systems where the Python command is `python`, use:

```bash
python main.py
```

Run the tests with:

```bash
python3 tests.py
```

or:

```bash
python tests.py
```

No input data or command-line arguments are required.

## Example output

A shortened example is:

```text
============================================================
SMART FITNESS SESSION ANALYZER
Participant: P001
Classification: MODERATE ACTIVITY
============================================================

Observations
  Total:  12
  Usable: 12
  Invalid: 0

Heart rate (bpm)
  Average: 100.4
  Minimum: 92.0
  Maximum: 112.0
  Baseline: 72.0

Activity level
  Average: 0.51
  Minimum: 0.39
  Maximum: 0.64

Recovery
  Detected: No

Explanation: The session shows sustained activity in the moderate range without a clear recovery trend.
```

Exact numerical values depend on the selected scenario and seed.

## Known limitations

- The application analyzes simulated measurements rather than real data.
- Classification thresholds are simple assignment rules and are not medical or sports-science standards.
- Recovery detection only examines the beginning and final parts of a session.
- Invalid observations are excluded rather than repaired.
- The program does not persist sessions between runs.

## Testing

The test suite covers calculations, validation, insufficient data, all five required scenarios, and invalid sensor data.

No external packages are used, so `requirements.txt` intentionally contains no package dependencies.
