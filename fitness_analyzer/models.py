"""Domain classes: Observation, Participant and Session.

Carried over from Assignment I with the same design: Session uses
composition (it HAS a Participant and a list of Observations, rather
than being either one), and Participant keeps its baseline values
behind a protected attribute reached only through a property.
"""

from .validation import (
    MAX_HEART_RATE,
    MAX_TEMPERATURE,
    MIN_HEART_RATE,
    MIN_TEMPERATURE,
    SIGNAL_QUALITY_THRESHOLD,
    is_within_range,
)

class Observation:
    """A single measurement window for one fitness session."""

    def __init__(self, timestamp, heart_rate, skin_response, temperature,
                 activity_level, signal_quality):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality

    @classmethod
    def from_dict(cls, data):
        """Build an Observation from a dict of already-converted values."""
        return cls(
            timestamp=data["timestamp"],
            heart_rate=data["heart_rate"],
            skin_response=data["skin_response"],
            temperature=data["temperature"],
            activity_level=data["activity_level"],
            signal_quality=data["signal_quality"],
        )

    @staticmethod
    def is_within_range(value, lower, upper):
        """Static because it doesn't need any instance data - it's a
        small reusable check applied to several different fields.
        """
        return is_within_range(value, lower, upper)

    def is_valid(self):
        """Return (True, "", "") if usable, else (False, field, reason)."""
        if self.heart_rate is None:
            return False, "heart_rate", "missing value"
        if self.skin_response is None:
            return False, "skin_response", "missing value"
        if self.timestamp is None or self.timestamp < 0:
            return False, "timestamp", "timestamp must be non-negative"
        if self.skin_response < 0:
            return False, "skin_response", "skin response must be non-negative"
        if not self.is_within_range(self.heart_rate, MIN_HEART_RATE, MAX_HEART_RATE):
            return False, "heart_rate", "heart rate out of realistic range"
        if not self.is_within_range(self.temperature, MIN_TEMPERATURE, MAX_TEMPERATURE):
            return False, "temperature", "temperature out of realistic range"
        if not self.is_within_range(self.activity_level, 0, 1):
            return False, "activity_level", "activity level out of range"
        if not self.is_within_range(self.signal_quality, 0, 1):
            return False, "signal_quality", "signal quality out of range"
        if self.signal_quality < SIGNAL_QUALITY_THRESHOLD:
            return False, "signal_quality", "signal quality below acceptable threshold"
        return True, "", ""


class Participant:
    """A participant and their personal baseline reference values."""

    def __init__(self, participant_id, name, baseline_heart_rate,
                 baseline_skin_response, baseline_temperature):
        self.participant_id = participant_id
        self.name = name
        # Protected attribute: only reachable through the `reference`
        # property and `update_reference`, which validates new values.
        self._reference = {
            "heart_rate": baseline_heart_rate,
            "skin_response": baseline_skin_response,
            "temperature": baseline_temperature,
        }

    @classmethod
    def from_row(cls, row):
        """Build a Participant from an already-validated participants.csv row."""
        return cls(
            participant_id=row["participant_id"],
            name=row["name"],
            baseline_heart_rate=row["baseline_heart_rate"],
            baseline_skin_response=row["baseline_skin_response"],
            baseline_temperature=row["baseline_temperature"],
        )

    @property
    def reference(self):
        """Read-only view of the personal reference values."""
        return dict(self._reference)

    def update_reference(self, field, value):
        """Update one reference value, with a basic sanity check."""
        if field not in self._reference:
            raise ValueError(f"Field '{field}' is not a valid reference attribute.")
        if value is None or value < 0:
            raise ValueError(f"Value for '{field}' must be a non-negative number.")
        self._reference[field] = value


class Session:
    """A participant plus the observations recorded during one session.

    This is the composition example in the project: a Session HAS a
    Participant and HAS a list of Observations, rather than being a
    type of either one.
    """

    def __init__(self, session_id, participant, observations):
        self.session_id = session_id
        self.participant = participant
        self.observations = observations

    def valid_observations(self):
        return [obs for obs in self.observations if obs.is_valid()[0]]

    def invalid_count(self):
        return len(self.observations) - len(self.valid_observations())