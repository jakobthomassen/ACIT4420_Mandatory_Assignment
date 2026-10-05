"""
Reading the CSV files, converting rows to domain objects and grouping them by session.
"""

import csv
from pathlib import Path

from helpers.exceptions import DataFileError, InvalidRecordError
from helpers.models import (
    FitnessSession,
    ObservationWindow,
    Participant,
    ReferenceProfile,
    RejectedRecord,
)
from helpers.validation import (
    PROFILE_COLUMNS,
    SESSION_COLUMNS,
    is_valid_session_id,
    parse_profile_row,
    parse_session_row,
)


def read_csv_rows(path, expected_header):
    """Yield (line_number, fields) for each data row of a CSV file; the header is line 1."""
    path = Path(path)
    reader = None
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if header is None:
                raise DataFileError(path, "file is empty")
            header = [name.strip().lstrip("\ufeff") for name in header]
            if header != list(expected_header):
                raise DataFileError(path, f"unexpected header {header}; expected {list(expected_header)}")
            for fields in reader:
                yield reader.line_num, fields
    except FileNotFoundError as error:
        raise DataFileError(path, "file not found") from error
    except PermissionError as error:
        raise DataFileError(path, "permission denied") from error
    except UnicodeDecodeError as error:
        raise DataFileError(path, f"file is not valid UTF-8 ({error.reason})") from error
    except csv.Error as error:
        line = reader.line_num if reader else "?"
        raise DataFileError(path, f"CSV error near line {line}: {error}") from error
    except OSError as error:
        raise DataFileError(path, f"cannot be read ({error.strerror or error})") from error


class DataLoader:  # Loads profiles and sessions and keeps track of everything that was rejected

    def __init__(self):
        self.participants = {}  # participant_id -> Participant
        self.sessions = {}  # session_id -> FitnessSession
        self.rejections = []  # RejectedRecord objects
        self.accepted_rows = {}  # file name -> accepted row count
        self.rejected_rows = {}  # file name -> rejected row count
        self.skipped_files = []  # messages about files that could not be read
        self._raw_participants = {}  # session_id -> participant seen on a rejected row

    # ----- participants -------------------------------------------------

    def load_profiles(self, path):
        """Load participants. A missing or unreadable profile file raises DataFileError."""
        path = Path(path)
        name = path.name
        self.accepted_rows[name] = 0
        self.rejected_rows[name] = 0

        for row_number, fields in read_csv_rows(path, PROFILE_COLUMNS):
            try:
                values, problems = parse_profile_row(fields)
                if not problems and values["participant_id"] in self.participants:
                    raise InvalidRecordError("participant_id", f"duplicate participant {values['participant_id']}")
            except InvalidRecordError as error:
                problems = [(error.field, error.reason)]

            if problems:
                self._reject(name, row_number, problems)
                continue

            reference = ReferenceProfile(
                values["baseline_heart_rate"],
                values["baseline_skin_response"],
                values["baseline_temperature"],
            )
            participant = Participant(values["participant_id"], values["name"], reference)
            self.participants[participant.participant_id] = participant
            self.accepted_rows[name] += 1

    # ----- sessions -----------------------------------------------------

    def load_session_files(self, paths):
        """Load several session files. A file that cannot be read is skipped and reported."""
        for path in paths:
            try:
                self._load_session_file(Path(path))
            except DataFileError as error:
                self.skipped_files.append(str(error))
        self._attach_participants_to_empty_sessions()

    def _load_session_file(self, path):
        name = path.name
        self.accepted_rows[name] = 0
        self.rejected_rows[name] = 0

        for row_number, fields in read_csv_rows(path, SESSION_COLUMNS):
            try:
                values, problems = parse_session_row(fields, self.participants)
                if not problems:
                    self._add_observation(values)
            except InvalidRecordError as error:
                problems = [(error.field, error.reason)]

            if problems:
                self._reject(name, row_number, problems)
                self._note_rejected_session(fields)
            else:
                self.accepted_rows[name] += 1

    def _add_observation(self, values):
        session_id = values["session_id"]
        participant = self.participants[values["participant_id"]]

        session = self.sessions.get(session_id)
        if session is None:
            session = FitnessSession(session_id, participant)
            self.sessions[session_id] = session
        elif session.participant is None:
            session.participant = participant
        elif session.participant.participant_id != participant.participant_id:
            raise InvalidRecordError(
                "participant_id",
                f"session {session_id} belongs to {session.participant.participant_id}, not {participant.participant_id}",
            )

        if session.has_timestamp(values["timestamp"]):
            raise InvalidRecordError("timestamp", f"duplicate timestamp {values['timestamp']} in session {session_id}")

        session.add_observation(
            ObservationWindow(
                values["timestamp"],
                values["heart_rate"],
                values["skin_response"],
                values["temperature"],
                values["activity_level"],
                values["signal_quality"],
            )
        )

    # ----- bookkeeping --------------------------------------------------

    def _reject(self, source, row_number, problems):
        for field, reason in problems:
            self.rejections.append(RejectedRecord(source, row_number, field, reason))
        self.rejected_rows[source] += 1

    def _note_rejected_session(self, fields):
        # A rejected row with a well-formed session ID still counts against that session.
        session_id = fields[0].strip() if fields else ""
        if not is_valid_session_id(session_id):
            return
        session = self.sessions.get(session_id)
        if session is None:
            session = FitnessSession(session_id)
            self.sessions[session_id] = session
        session.rejected_count += 1
        if len(fields) > 1 and fields[1].strip() in self.participants:
            self._raw_participants.setdefault(session_id, self.participants[fields[1].strip()])

    def _attach_participants_to_empty_sessions(self):
        # Sessions with no accepted row still show the participant named on a rejected row, if known.
        for session_id, session in self.sessions.items():
            if session.participant is None and session_id in self._raw_participants:
                session.participant = self._raw_participants[session_id]

    @property
    def total_accepted(self):
        return sum(self.accepted_rows.values())

    @property
    def total_rejected(self):
        return sum(self.rejected_rows.values())