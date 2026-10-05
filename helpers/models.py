"""
Domain classes: participants, observation windows, sessions and rejected records.
"""


class ReferenceProfile:  # Personal reference measurements for a participant

    def __init__(self, baseline_heart_rate, baseline_skin_response, baseline_temperature):
        self.baseline_heart_rate = baseline_heart_rate
        self.baseline_skin_response = baseline_skin_response
        self.baseline_temperature = baseline_temperature


class Participant:  # A participant and their personal reference profile

    def __init__(self, participant_id, name, reference_profile):
        self._participant_id = participant_id
        self.name = name
        self.reference_profile = reference_profile

    @property
    def participant_id(self):  # Read-only access to the stored identifier
        return self._participant_id


class ObservationWindow:  # One validated measurement window

    def __init__(self, timestamp, heart_rate, skin_response, temperature, activity_level, signal_quality):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality


class FitnessSession:  # One session: a participant plus their validated observation windows

    def __init__(self, session_id, participant=None):
        self.session_id = session_id
        self.participant = participant  # None when no row of the session was accepted
        self.rejected_count = 0
        self._observations = []

    def add_observation(self, observation):
        self._observations.append(observation)

    def has_timestamp(self, timestamp):
        return any(item.timestamp == timestamp for item in self._observations)

    @property
    def observations(self):  # Observations ordered by timestamp
        return sorted(self._observations, key=lambda item: item.timestamp)

    @property
    def participant_id(self):
        return self.participant.participant_id if self.participant else "unknown"


class RejectedRecord:  # One reason why a row (or one of its fields) was rejected

    def __init__(self, source, row_number, field, reason):
        self.source = source
        self.row_number = row_number
        self.field = field
        self.reason = reason