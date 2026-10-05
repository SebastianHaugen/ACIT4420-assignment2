"""
Tests for the Smart Fitness Session Analyzer package.

Run with: python -m unittest discover tests
"""

import tempfile
import unittest
from pathlib import Path

from fitness_analyzer.analysis import SessionAnalyzer
from fitness_analyzer.exceptions import InvalidIdentifierError
from fitness_analyzer.loader import load_participants, load_sessions
from fitness_analyzer.models import Observation, Participant, Session
from fitness_analyzer.validation import validate_participant_id, validate_session_id


PARTICIPANTS_CSV = """participant_id,name,baseline_heart_rate,baseline_skin_response,baseline_temperature
P001,Amina Noor,68,1.20,32.4
P002,Jonas Berg,74,1.45,32.7
"""

VALID_SESSIONS_CSV = """session_id,participant_id,timestamp,heart_rate,skin_response,temperature,activity_level,signal_quality
FIT-2026-001,P001,0,68,1.18,32.4,0.08,0.98
FIT-2026-001,P001,1,69,1.20,32.4,0.10,0.97
FIT-2026-001,P001,2,70,1.22,32.5,0.12,0.96
FIT-2026-001,P001,3,69,1.19,32.4,0.09,0.98
"""

# Every row here has exactly one problem, matching the official
# fitness_sessions_invalid.csv style of mistake.
INVALID_SESSIONS_CSV = """session_id,participant_id,timestamp,heart_rate,skin_response,temperature,activity_level,signal_quality
FIT-2026-101,P001,0,fast,1.30,32.5,0.10,0.96
FIT-2026-101,001,1,105,2.10,33.0,0.60,0.92
FIT-2026-101,P001,2,118,2.50,33.2,,0.90
FIT-2026-101,P001,3,124,2.80,33.4,0.78,1.40
FIT-2026-102,P999,0,96,1.90,33.0,0.48,0.94
FIT-2026-103,P001,0,70,1.20,32.4,0.12
"""


def _write(tmp_dir, name, content):
    path = Path(tmp_dir) / name
    path.write_text(content, encoding="utf-8")
    return path


class LoaderTests(unittest.TestCase):
    """Covers valid rows, invalid rows and a missing file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.participants_path = _write(self.tmp.name, "participants.csv", PARTICIPANTS_CSV)

    def test_valid_participants_load(self):
        participants, rejected = load_participants(self.participants_path)
        self.assertEqual(len(participants), 2)
        self.assertEqual(rejected, [])
        self.assertIn("P001", participants)

    def test_missing_participants_file_raises(self):
        missing_path = Path(self.tmp.name) / "does_not_exist.csv"
        with self.assertRaises(FileNotFoundError):
            load_participants(missing_path)

    def test_valid_sessions_load_with_nothing_rejected(self):
        participants, _ = load_participants(self.participants_path)
        sessions_path = _write(self.tmp.name, "sessions.csv", VALID_SESSIONS_CSV)
        sessions, rejected = load_sessions(sessions_path, participants)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(rejected, [])
        self.assertEqual(len(sessions["FIT-2026-001"].observations), 4)

    def test_invalid_sessions_are_rejected_not_crashed(self):
        participants, _ = load_participants(self.participants_path)
        sessions_path = _write(self.tmp.name, "invalid.csv", INVALID_SESSIONS_CSV)
        sessions, rejected = load_sessions(sessions_path, participants)
        # Every row in this file has exactly one problem, so all six
        # should be rejected and none should load as usable.
        self.assertEqual(len(rejected), 6)

    def test_unknown_participant_is_rejected(self):
        participants, _ = load_participants(self.participants_path)
        sessions_path = _write(self.tmp.name, "invalid.csv", INVALID_SESSIONS_CSV)
        _, rejected = load_sessions(sessions_path, participants)
        reasons = [record.reason for record in rejected]
        self.assertTrue(any("unknown participant_id" in reason for reason in reasons))

    def test_wrong_row_length_is_rejected(self):
        participants, _ = load_participants(self.participants_path)
        sessions_path = _write(self.tmp.name, "invalid.csv", INVALID_SESSIONS_CSV)
        _, rejected = load_sessions(sessions_path, participants)
        fields = [record.field for record in rejected]
        self.assertIn("row_length", fields)

    def test_csv_error_is_logged_and_earlier_rows_are_kept(self):
        # A field bigger than the csv module's size limit makes the
        # reader raise csv.Error. The loader should log it and keep the
        # rows it already read instead of crashing.
        header = "session_id,participant_id,timestamp,heart_rate,skin_response,temperature,activity_level,signal_quality\n"
        good_row = "FIT-2026-001,P001,0,68,1.18,32.4,0.08,0.98\n"
        broken_row = "FIT-2026-001,P001,1," + ("9" * 200000) + ",1.20,32.4,0.10,0.97\n"
        participants, _ = load_participants(self.participants_path)
        sessions_path = _write(self.tmp.name, "broken.csv", header + good_row + broken_row)
        sessions, rejected = load_sessions(sessions_path, participants)
        self.assertIn("FIT-2026-001", sessions)
        self.assertEqual(len(sessions["FIT-2026-001"].observations), 1)
        self.assertEqual([record.field for record in rejected], ["csv_format"])
        self.assertEqual(rejected[0].row_number, 3)

    def test_session_with_every_row_rejected_still_appears(self):
        # A session whose rows all have valid identifiers but fail the
        # measurement check (poor signal quality) must still show up as
        # a Session, not disappear from the results entirely.
        all_poor_signal = """session_id,participant_id,timestamp,heart_rate,skin_response,temperature,activity_level,signal_quality
FIT-2026-005,P002,0,76,1.50,32.7,0.12,0.34
FIT-2026-005,P002,1,79,1.62,32.8,0.18,0.29
FIT-2026-005,P002,2,95,1.90,33.0,0.35,0.25
"""
        participants, _ = load_participants(self.participants_path)
        sessions_path = _write(self.tmp.name, "poor_signal.csv", all_poor_signal)
        sessions, rejected = load_sessions(sessions_path, participants)
        self.assertIn("FIT-2026-005", sessions)
        self.assertEqual(len(sessions["FIT-2026-005"].observations), 0)
        self.assertEqual(len(rejected), 3)


class ValidationTests(unittest.TestCase):
    """Covers the regex identifier checks."""

    def test_participant_id_format(self):
        self.assertEqual(validate_participant_id("P001"), "P001")
        with self.assertRaises(InvalidIdentifierError):
            validate_participant_id("001")

    def test_session_id_format(self):
        self.assertEqual(validate_session_id("FIT-2026-001"), "FIT-2026-001")
        with self.assertRaises(InvalidIdentifierError):
            validate_session_id("FIT-26-001")


class ObservationBoundaryTests(unittest.TestCase):
    """Covers boundary values sitting exactly on the validation limits."""

    def _make(self, **overrides):
        data = {
            "timestamp": 0,
            "heart_rate": 90,
            "skin_response": 1.5,
            "temperature": 32.0,
            "activity_level": 0.3,
            "signal_quality": 0.9,
        }
        data.update(overrides)
        return Observation.from_dict(data)

    def test_signal_quality_exactly_at_threshold_is_valid(self):
        self.assertTrue(self._make(signal_quality=0.6).is_valid()[0])

    def test_signal_quality_just_below_threshold_is_invalid(self):
        self.assertFalse(self._make(signal_quality=0.59).is_valid()[0])

    def test_heart_rate_exactly_at_upper_bound_is_valid(self):
        self.assertTrue(self._make(heart_rate=220).is_valid()[0])

    def test_heart_rate_just_above_upper_bound_is_invalid(self):
        self.assertFalse(self._make(heart_rate=221).is_valid()[0])


class SessionAnalyzerTests(unittest.TestCase):
    """Covers classification outcomes, including insufficient data."""

    def _session(self, observations):
        participant = Participant("P001", "Test", 68, 1.2, 32.4)
        return Session("FIT-2026-001", participant, observations)

    def test_resting_session_classified_as_resting(self):
        observations = [
            Observation.from_dict({
                "timestamp": i, "heart_rate": 69, "skin_response": 1.2,
                "temperature": 32.4, "activity_level": 0.1, "signal_quality": 0.95,
            })
            for i in range(6)
        ]
        result = SessionAnalyzer(self._session(observations)).analyze()
        self.assertEqual(result["classification"], "resting")

    def test_insufficient_data_when_too_few_usable_observations(self):
        observations = [
            Observation.from_dict({
                "timestamp": 0, "heart_rate": None, "skin_response": 1.2,
                "temperature": 32.4, "activity_level": 0.1, "signal_quality": 0.95,
            })
        ]
        result = SessionAnalyzer(self._session(observations)).analyze()
        self.assertEqual(result["classification"], "insufficient_data")

    def test_recovery_detected_when_hr_and_activity_decline(self):
        high = [
            Observation.from_dict({
                "timestamp": i, "heart_rate": 150, "skin_response": 3.0,
                "temperature": 33.5, "activity_level": 0.85, "signal_quality": 0.95,
            })
            for i in range(3)
        ]
        declining = [
            Observation.from_dict({
                "timestamp": i, "heart_rate": 90, "skin_response": 1.5,
                "temperature": 32.6, "activity_level": 0.2, "signal_quality": 0.95,
            })
            for i in range(3, 6)
        ]
        result = SessionAnalyzer(self._session(high + declining)).analyze()
        self.assertTrue(result["recovery_detected"])


if __name__ == "__main__":
    unittest.main()