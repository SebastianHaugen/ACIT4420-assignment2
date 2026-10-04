"""Smart Fitness Session Analyzer package."""

from .analysis import SessionAnalyzer
from .exceptions import InvalidIdentifierError, InvalidRecordError
from .models import Observation, Participant, Session
from .validation import (
    validate_participant_id,
    validate_session_id,
    is_within_range,
    MIN_HEART_RATE,
    MAX_HEART_RATE,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    SIGNAL_QUALITY_THRESHOLD,
    REQUIRED_SESSION_FIELDS,
    REQUIRED_PARTICIPANT_FIELDS,
)

__all__ = [
    "SessionAnalyzer",
    "InvalidIdentifierError",
    "InvalidRecordError",
    "Observation",
    "Participant",
    "Session",
]