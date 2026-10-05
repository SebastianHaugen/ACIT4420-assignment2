"""CSV loading: reads the participants and session files, validates every
row, converts values to the right types, and groups usable rows into
Session objects. Every rejected row is recorded with its source file,
row number, field and reason instead of just being silently dropped.

A session is registered as soon as its session_id/participant_id are
valid, even if every measurement row for that session turns out to be
rejected - otherwise a session whose data is entirely bad would just
vanish from the output instead of being reported as insufficient data.
"""

import csv
from pathlib import Path

from .exceptions import InvalidIdentifierError, InvalidRecordError
from .models import Observation, Participant, Session
from .validation import validate_participant_id, validate_session_id

MEASUREMENT_FIELDS = (
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
)


class RejectedRecord:
    """One rejected CSV row, with enough detail to explain why."""

    def __init__(self, source_file, row_number, field, reason):
        self.source_file = source_file
        self.row_number = row_number
        self.field = field
        self.reason = reason

    def __str__(self):
        return (
            f"{self.source_file} (row {self.row_number}): "
            f"field '{self.field}' - {self.reason}"
        )


def _row_has_any_value(values):
    return any((value or "").strip() for value in values)


def load_participants(path):
    """Read a participants CSV file.

    Returns (dict[participant_id -> Participant], list[RejectedRecord]).
    Raises FileNotFoundError / PermissionError with the path attached,
    so the caller (main.py) can report a clear message and move on.
    """
    path = Path(path)
    participants = {}
    rejected = []
    row_number = 1  # the header line

    try:
        with open(path, encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_number, row in enumerate(reader, start=2):
                if not _row_has_any_value(row.values()):
                    continue
                try:
                    participant = _parse_participant_row(row)
                    participants[participant.participant_id] = participant
                except (InvalidIdentifierError, InvalidRecordError) as exc:
                    field = exc.field or "participant_id"
                    rejected.append(RejectedRecord(path.name, row_number, field, str(exc)))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Participants file not found: {path}") from exc
    except PermissionError as exc:
        raise PermissionError(f"Cannot read participants file (permission denied): {path}") from exc
    except csv.Error as exc:
        # The file is malformed at the csv level. Keep what was read so far.
        rejected.append(RejectedRecord(
            path.name, row_number + 1, "csv_format",
            f"csv could not parse the file, stopped reading here: {exc}",
        ))

    return participants, rejected


def _parse_participant_row(row):
    raw_id = (row.get("participant_id") or "").strip()
    participant_id = validate_participant_id(raw_id)

    try:
        baseline_heart_rate = float(row["baseline_heart_rate"])
        baseline_skin_response = float(row["baseline_skin_response"])
        baseline_temperature = float(row["baseline_temperature"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidRecordError(
            f"could not convert baseline values to numbers: {exc}",
            field="baseline_values",
        ) from exc

    return Participant.from_row({
        "participant_id": participant_id,
        "name": (row.get("name") or "").strip(),
        "baseline_heart_rate": baseline_heart_rate,
        "baseline_skin_response": baseline_skin_response,
        "baseline_temperature": baseline_temperature,
    })


def load_sessions(path, participants):
    """Read a fitness-sessions CSV file (valid or intentionally invalid).

    `participants` is the dict returned by load_participants - used to
    reject rows referencing a participant_id that doesn't exist.

    Returns (dict[session_id -> Session], list[RejectedRecord]).
    """
    path = Path(path)
    grouped_observations = {}
    session_participant_ids = {}
    rejected = []
    row_number = 0

    try:
        with open(path, encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if header is None:
                return {}, rejected
            row_number = 1  # the header line

            for row_number, raw_row in enumerate(reader, start=2):
                if not raw_row or not _row_has_any_value(raw_row):
                    continue

                try:
                    session_id, participant_id, row = _resolve_session_identity(raw_row, header)
                except (InvalidRecordError, InvalidIdentifierError) as exc:
                    field = exc.field or "unknown"
                    rejected.append(RejectedRecord(path.name, row_number, field, str(exc)))
                    continue

                if participant_id not in participants:
                    rejected.append(RejectedRecord(
                        path.name, row_number, "participant_id",
                        f"unknown participant_id '{participant_id}'",
                    ))
                    continue

                # The session is now known to exist, even if this row's
                # own measurements turn out to be invalid below - so a
                # session with every row rejected still gets reported
                # as insufficient data instead of disappearing.
                grouped_observations.setdefault(session_id, [])
                session_participant_ids[session_id] = participant_id

                try:
                    observation = _parse_measurements(row)
                except InvalidRecordError as exc:
                    field = exc.field or "unknown"
                    rejected.append(RejectedRecord(path.name, row_number, field, str(exc)))
                    continue

                grouped_observations[session_id].append(observation)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Sessions file not found: {path}") from exc
    except PermissionError as exc:
        raise PermissionError(f"Cannot read sessions file (permission denied): {path}") from exc
    except csv.Error as exc:
        # The file is malformed at the csv level. Keep what was read so far.
        rejected.append(RejectedRecord(
            path.name, row_number + 1, "csv_format",
            f"csv could not parse the file, stopped reading here: {exc}",
        ))

    sessions = {}
    for session_id, observations in grouped_observations.items():
        participant = participants[session_participant_ids[session_id]]
        sessions[session_id] = Session(session_id, participant, observations)

    return sessions, rejected


def _resolve_session_identity(raw_row, header):
    """Validate the row shape and the session_id / participant_id
    columns, before anything numeric is touched. Returns
    (session_id, participant_id, row_dict).
    """
    if len(raw_row) != len(header):
        raise InvalidRecordError(
            f"expected {len(header)} columns, got {len(raw_row)}",
            field="row_length",
        )

    row = dict(zip(header, raw_row))

    for field in ("session_id", "participant_id"):
        if not (row.get(field) or "").strip():
            raise InvalidRecordError(f"missing required field '{field}'", field=field)

    session_id = validate_session_id(row["session_id"].strip())
    participant_id = validate_participant_id(row["participant_id"].strip())
    return session_id, participant_id, row


def _parse_measurements(row):
    """Validate and convert the measurement columns of an already
    identity-resolved row. Returns a usable Observation, or raises
    InvalidRecordError.
    """
    for field in MEASUREMENT_FIELDS:
        if not (row.get(field) or "").strip():
            raise InvalidRecordError(f"missing required field '{field}'", field=field)

    try:
        timestamp = int(row["timestamp"])
        heart_rate = int(row["heart_rate"])
        skin_response = float(row["skin_response"])
        temperature = float(row["temperature"])
        activity_level = float(row["activity_level"])
        signal_quality = float(row["signal_quality"])
    except ValueError as exc:
        raise InvalidRecordError(
            f"could not convert value to the required type: {exc}",
            field="type_conversion",
        ) from exc

    observation = Observation.from_dict({
        "timestamp": timestamp,
        "heart_rate": heart_rate,
        "skin_response": skin_response,
        "temperature": temperature,
        "activity_level": activity_level,
        "signal_quality": signal_quality,
    })

    is_valid, field, reason = observation.is_valid()
    if not is_valid:
        raise InvalidRecordError(reason, field=field)

    return observation