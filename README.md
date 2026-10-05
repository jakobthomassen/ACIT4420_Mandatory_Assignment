# Smart Fitness Session Analyzer

**Python Programming Assignment (II), Option A**

Student name: **Jakob Thomassen**

Student number: **421970**

## Description

The Smart Fitness Session Analyzer is a file-based application that processes simulated wearable-device measurements from fitness sessions. It loads participant and session data from CSV files, validates identifiers and measurements, converts valid records into Python objects, groups observations into sessions, summarizes measurements, compares measurements with a participant's personal reference values, detects recovery, classifies sessions, and produces readable analysis reports.

Assignment II extends the object-oriented application from Assignment I with file handling, structured validation, custom exceptions, error reporting, command-line arguments, and persistent output files.

The supplied CSV files contain both valid and intentionally invalid records. Invalid records are rejected with a recorded source filename, row number, field, and reason where appropriate. Valid records are processed without allowing individual invalid rows to stop the complete analysis.

## Running the application

Run the main program from the repository root:

```bash
python3 main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv --invalid-sessions data/fitness_sessions_invalid.csv --output output
```

On systems where the Python command is `python`, use:

```bash
python main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv --invalid-sessions data/fitness_sessions_invalid.csv --output output
```

Run the tests with:

```bash
python3 tests.py
```

or:

```bash
python tests.py
```

The main program prints a short completion summary showing accepted rows, rejected rows, and the created report files.

The test suite runs directly and does not require command-line arguments.

## Project structure

```text
.

├── README.md
├── main.py
├── requirements.txt
├── tests.py
├── Assignment I.pdf
├── Assignment II.pdf
│
├── data
│   ├── DATA_DESCRIPTION.md
│   ├── fitness_sessions.csv
│   ├── fitness_sessions_invalid.csv
│   └── participants.csv
│
└── helpers
    ├── __init__.py
    ├── analysis.py
    ├── calculations.py
    ├── exceptions.py
    ├── loader.py
    ├── models.py
    ├── reporting.py
    └── validation.py
```

The `data` directory contains the supplied participant and fitness-session CSV files.

The `helpers` package contains the domain models, CSV loading, validation, analysis, calculations, exception classes, and reporting functions.

## Classes

| Class               | Description                                                                                                                                |
| :------------------ | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `ReferenceProfile`  | Stores a participant's baseline heart rate, skin response, and temperature.                                                                |
| `Participant`       | Represents a participant and contains a `ReferenceProfile`. The stored identifier (`_participant_id`) is exposed through `participant_id`. |
| `ObservationWindow` | Represents one measurement window and stores sensor values and validation information.                                                     |
| `FitnessSession`    | Groups a participant and their observation windows and provides access to usable observations.                                             |
| `BaseAnalyzer`      | Defines the general analysis interface.                                                                                                    |
| `FitnessAnalyzer`   | Inherits from `BaseAnalyzer` and implements the fitness-specific `analyze` method and classification rules.                                |

## OOP requirements

| OOP Concept                  | Application                     | Details                                                                                                                           |
| :--------------------------- | :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------- |
| **Composition**              | `Participant`, `FitnessSession` | `Participant` contains a `ReferenceProfile`; `FitnessSession` contains a `Participant` and a list of `ObservationWindow` objects. |
| **Encapsulation**            | `Participant._participant_id`   | Uses a protected-style attribute exposed through a read-only `participant_id` property instead of direct access.                  |
| **Inheritance & Overriding** | `FitnessAnalyzer`               | Inherits from `BaseAnalyzer` and overrides `analyze` with a fitness-session-specific implementation.                              |
| **Class Method**             | `Participant.from_profile_dict` | Provides an alternative constructor for creating a `Participant` from profile data.                                               |
| **Static Method**            | `ObservationWindow.from_dict`   | Converts raw record data into an `ObservationWindow` without requiring an existing instance.                                      |

## CSV loading

The application reads the supplied CSV files using Python's standard `csv` module.

The participant file provides the participant identifiers and personal reference values. The session files contain measurement observations that are grouped by session ID and connected to the corresponding participant.

Files are opened using context managers with explicit UTF-8 encoding and newline handling.

The application converts CSV string values into suitable Python types before validation and analysis.

The official CSV column names are used without modification.

## Validation rules

The application validates participant and session identifiers using regular expressions.

| Identifier       | Rule                                 |
| :--------------- | :----------------------------------- |
| `participant_id` | `P` followed by exactly three digits |
| `session_id`     | `FIT-YYYY-NNN`                       |

Measurement fields are checked against the documented ranges:

| Field            | Rule                  |
| :--------------- | :-------------------- |
| `timestamp`      | integer, 0 or greater |
| `heart_rate`     | 35-205 bpm            |
| `skin_response`  | 0 or greater          |
| `temperature`    | 25-42 C               |
| `activity_level` | 0-1                   |
| `signal_quality` | 0-1                   |

Missing values and values that cannot be converted to the required type are invalid.

Unknown participant IDs are rejected.

Unexpected row lengths, missing required fields, invalid identifiers, conversion failures, and impossible measurement values are reported rather than silently ignored.

An observation with valid numeric values but signal quality below `0.60` is excluded from usable analysis as a data-quality issue.

Invalid observations are not repaired or replaced with guessed values.

## Custom exceptions

The application defines and uses custom exceptions for validation errors.

| Exception                | Purpose                                                                |
| :----------------------- | :--------------------------------------------------------------------- |
| `InvalidIdentifierError` | Raised when a participant or session identifier has an invalid format. |
| `InvalidRecordError`     | Raised when a session record contains invalid or unusable data.        |

The exceptions inherit from `ValueError` and are raised during validation and handled by the appropriate loading or processing code.

File-related errors such as missing files and permission errors are handled separately from record-level validation errors.

## Rejected records

Rejected records are tracked during CSV processing.

Each rejection records relevant information including:

- source filename
- CSV row number
- field
- reason for rejection

This allows invalid input to be investigated without stopping the processing of other valid records.

The invalid session file supplied with the assignment is intentionally used to demonstrate this behaviour.

## Calculations

The project uses standalone functions for:

- average
- minimum
- maximum
- comparison with a baseline
- recovery decline calculation
- observation validation
- profile validation
- report formatting

Session summaries are calculated for:

- heart rate
- skin response
- temperature
- activity level
- signal quality

The analysis distinguishes between a meaningful result and a session with insufficient usable data.

## Classification rules

The classification rules remain intentionally simple and deterministic.

1. Fewer than four usable observations results in **insufficient data**.

2. Recovery is checked before the activity classification.

3. Recovery is detected when both heart rate and activity decline sufficiently between the beginning and end of the usable session.

4. Average activity below `0.25` is classified as **resting**.

5. Average activity at or above `0.68` is classified as **high activity**.

6. Other sufficiently active sessions are classified as **moderate activity**.

7. A detected recovery trend is classified as **recovering**.

The activity thresholds are based on the ranges used by the supplied fitness data and the classification rules from Assignment I.

## Recovery detection

The analyzer compares the first and final third of the usable observations.

Recovery requires both:

- a heart-rate decline of at least 20 bpm; and
- an activity-level decline of at least 0.25.

This prevents a low final value alone from being treated as recovery.

## Output files

The application creates the output directory if it does not already exist.

The following files are produced:

```text
output/
├── analysis_summary.csv
├── analysis_report.txt
└── rejected_records.txt
```

### `analysis_summary.csv`

Contains one summary row for each analyzed fitness session, including the participant, session, calculated measurements, classification, and relevant analysis information.

### `analysis_report.txt`

Contains a readable text report describing the analyzed sessions and their results.

### `rejected_records.txt`

Contains rejected CSV records and the reasons they were rejected.

The output files are recreated predictably when the program is run again.

## Example output

A shortened console completion summary is:

```text
SMART FITNESS SESSION ANALYZER

Analysis complete.

Accepted rows: 29
Rejected rows: 11

Created files:
- output/analysis_summary.csv
- output/analysis_report.txt
- output/rejected_records.txt
```

The detailed analysis is stored in the generated report files rather than being limited to console output.

Exact numerical values depend on the supplied CSV data and the records that pass validation.

## Known limitations

- The application analyzes simulated measurements rather than real wearable-device data.
- Classification thresholds are simple assignment rules and are not medical or sports-science standards.
- Recovery detection only examines the beginning and final parts of a session.
- Invalid observations are excluded rather than repaired.
- Poor signal quality is treated as a data-quality problem according to the documented project threshold.
- The application does not use a database or persist domain objects between runs.
- CSV input is expected to follow the supplied file structure and column names.

## Testing

The test suite covers:

- valid participant identifiers
- invalid participant identifiers
- valid session identifiers
- invalid session identifiers
- valid measurements
- invalid measurements
- conversion failures
- unknown participant IDs
- insufficient usable data
- boundary cases
- valid session analysis
- invalid sensor data
- missing files
- custom exception handling

No external packages are used. `requirements.txt` therefore contains no third-party package dependencies.
