"""
Validation of CSV rows: identifiers (regular expressions), types, ranges and signal quality.
"""

import math
import re

from helpers.exceptions import InvalidIdentifierError, InvalidRecordError

# Regular expressions are used for identifier formats only (matched with fullmatch).
PARTICIPANT_ID_PATTERN = re.compile(r"P\d{3}", re.ASCII)
SESSION_ID_PATTERN = re.compile(r"FIT-\d{4}-\d{3}", re.ASCII)

# Data-quality rule: a window with signal_quality below this value is rejected.
SIGNAL_QUALITY_THRESHOLD = 0.60

PROFILE_COLUMNS = (
    "participant_id",
    "name",
    "baseline_heart_rate",
    "baseline_skin_response",
    "baseline_temperature",
)
SESSION_COLUMNS = (
    "session_id",
    "participant_id",
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
)

# (minimum, maximum); maximum None means "no upper limit". Plain comparisons, no regex.
PROFILE_RULES = {
    "baseline_heart_rate": (35, 205),
    "baseline_skin_response": (0, None),
    "baseline_temperature": (25, 42),
}
SESSION_RULES = {
    "heart_rate": (35, 205),
    "skin_response": (0, None),
    "temperature": (25, 42),
    "activity_level": (0, 1),
    "signal_quality": (0, 1),
}


def validate_participant_id(value):
    if not PARTICIPANT_ID_PATTERN.fullmatch(value):
        raise InvalidIdentifierError("participant_id", f"{value!r} does not match P followed by three digits")
    return value


def validate_session_id(value):
    if not SESSION_ID_PATTERN.fullmatch(value):
        raise InvalidIdentifierError("session_id", f"{value!r} does not match FIT-YYYY-NNN")
    return value


def is_valid_session_id(value):
    return SESSION_ID_PATTERN.fullmatch(value) is not None


def parse_number(field, text):  # Convert text to a finite float or raise InvalidRecordError
    try:
        value = float(text)
    except ValueError as error:
        raise InvalidRecordError(field, f"cannot convert {text!r} to a number") from error
    if not math.isfinite(value):
        raise InvalidRecordError(field, f"{text!r} is not a finite number")
    return value


def parse_integer(field, text):
    try:
        return int(text)
    except ValueError as error:
        raise InvalidRecordError(field, f"cannot convert {text!r} to an integer") from error


def check_range(field, value, minimum, maximum=None):
    if maximum is None:
        if value < minimum:
            raise InvalidRecordError(field, f"{value:g} is below the minimum of {minimum}")
    elif not minimum <= value <= maximum:
        raise InvalidRecordError(field, f"{value:g} is outside the allowed range {minimum} to {maximum}")


def _parse_fields(columns, fields, parse_field):
    # Parse every field and collect all problems, so one bad row can report several fields.
    values = {}
    problems = []
    for name, text in zip(columns, fields):
        try:
            values[name] = parse_field(name, text.strip())
        except (InvalidIdentifierError, InvalidRecordError) as error:
            problems.append((error.field, error.reason))
    return values, problems


def _check_row_length(columns, fields):
    if len(fields) != len(columns):
        raise InvalidRecordError("row", f"expected {len(columns)} fields but found {len(fields)}")


def parse_profile_row(fields):
    """Return (values, problems) for one participant row. Raises InvalidRecordError for a wrong row length."""
    _check_row_length(PROFILE_COLUMNS, fields)

    def parse_field(name, text):
        if text == "":
            raise InvalidRecordError(name, "missing value")
        if name == "participant_id":
            return validate_participant_id(text)
        if name == "name":
            return text
        value = parse_number(name, text)
        check_range(name, value, *PROFILE_RULES[name])
        return value

    return _parse_fields(PROFILE_COLUMNS, fields, parse_field)


def parse_session_row(fields, known_participants):
    """Return (values, problems) for one session row. Raises InvalidRecordError for a wrong row length."""
    _check_row_length(SESSION_COLUMNS, fields)

    def parse_field(name, text):
        if text == "":
            raise InvalidRecordError(name, "missing value")
        if name == "session_id":
            return validate_session_id(text)
        if name == "participant_id":
            validate_participant_id(text)
            if text not in known_participants:
                raise InvalidRecordError(name, f"unknown participant {text}")
            return text
        if name == "timestamp":
            value = parse_integer(name, text)
            check_range(name, value, 0)
            return value
        value = parse_number(name, text)
        check_range(name, value, *SESSION_RULES[name])
        if name == "signal_quality" and value < SIGNAL_QUALITY_THRESHOLD:
            raise InvalidRecordError(
                name, f"poor signal quality ({value:.2f} is below {SIGNAL_QUALITY_THRESHOLD:.2f})"
            )
        return value

    return _parse_fields(SESSION_COLUMNS, fields, parse_field)