"""Regular-expression identifier checks and shared range constants.

Regex is used only for identifier formats, exactly as the assignment asks.
Ordinary numeric range checks (heart rate, activity level, ...) use plain
comparisons, done in models.py / loader.py, not regular expressions.
"""

import re

from .exceptions import InvalidIdentifierError

PARTICIPANT_ID_PATTERN = re.compile(r"^P\d{3}$")
SESSION_ID_PATTERN = re.compile(r"^FIT-\d{4}-\d{3}$")

MIN_HEART_RATE = 30
MAX_HEART_RATE = 220
MIN_TEMPERATURE = 25.0
MAX_TEMPERATURE = 42.0
SIGNAL_QUALITY_THRESHOLD = 0.6

# Required columns for a fitness_sessions.csv row.
REQUIRED_SESSION_FIELDS = (
    "session_id",
    "participant_id",
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
)

REQUIRED_PARTICIPANT_FIELDS = (
    "participant_id",
    "name",
    "baseline_heart_rate",
    "baseline_skin_response",
    "baseline_temperature",
)


def validate_participant_id(participant_id):
    """Return participant_id if it fully matches P### , else raise."""
    if not PARTICIPANT_ID_PATTERN.match(participant_id):
        raise InvalidIdentifierError(
            f"participant_id '{participant_id}' does not match the required format P###",
            field="participant_id",
        )
    return participant_id


def validate_session_id(session_id):
    """Return session_id if it fully matches FIT-YYYY-NNN, else raise."""
    if not SESSION_ID_PATTERN.match(session_id):
        raise InvalidIdentifierError(
            f"session_id '{session_id}' does not match the required format FIT-YYYY-NNN",
            field="session_id",
        )
    return session_id


def is_within_range(value, lower, upper):
    """Plain numeric range check, not a regex. Used for measurements."""
    if value is None:
        return False
    return lower <= value <= upper