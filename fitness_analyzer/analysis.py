"""Session analysis: summaries, comparison to baseline, classification
and recovery detection. Reused and fixed up from Assignment 1.
"""

import statistics

MIN_USABLE_OBSERVATIONS = 3

RESTING_HR_GAP = 10
RESTING_ACTIVITY = 0.25
MODERATE_HR_GAP = 35
MODERATE_ACTIVITY = 0.65

RECOVERY_HR_DROP = 5
RECOVERY_ACTIVITY_DROP = 0.1
MIN_OBSERVATIONS_FOR_RECOVERY_CHECK = 6


def compute_summary_stats(values):
    """Return the average, minimum and maximum of a list of numbers."""
    return {
        "average": round(statistics.mean(values), 2),
        "minimum": round(min(values), 2),
        "maximum": round(max(values), 2),
    }


def classify_intensity(avg_heart_rate, reference_heart_rate, avg_activity):
    """Classify a session as resting, moderate activity or high activity,
    based on how far heart rate and activity are from the personal baseline.
    """
    hr_gap = avg_heart_rate - reference_heart_rate
    if hr_gap <= RESTING_HR_GAP and avg_activity <= RESTING_ACTIVITY:
        return "resting"
    if hr_gap <= MODERATE_HR_GAP and avg_activity <= MODERATE_ACTIVITY:
        return "moderate activity"
    return "high activity"


def detect_recovery(observations):
    """Check whether heart rate and activity decline in the second half of
    a session compared with the first half.
    """
    if len(observations) < MIN_OBSERVATIONS_FOR_RECOVERY_CHECK:
        return False

    midpoint = len(observations) // 2
    first_half = observations[:midpoint]
    second_half = observations[midpoint:]

    first_hr = statistics.mean(obs.heart_rate for obs in first_half)
    second_hr = statistics.mean(obs.heart_rate for obs in second_half)
    first_activity = statistics.mean(obs.activity_level for obs in first_half)
    second_activity = statistics.mean(obs.activity_level for obs in second_half)

    return (
        second_hr < first_hr - RECOVERY_HR_DROP
        and second_activity < first_activity - RECOVERY_ACTIVITY_DROP
    )


def build_reasoning(classification, hr_summary, reference_hr, recovering):
    """Produce a short human-readable explanation for a classification."""
    gap = round(hr_summary["average"] - reference_hr, 1)
    text = f"Average heart rate was {hr_summary['average']} bpm ({gap:+} bpm vs reference)."
    if recovering:
        text += " Heart rate and activity declined toward the end of the session, indicating recovery."
    elif classification == "resting":
        text += " Values stayed close to the participant's resting reference."
    else:
        text += " Values remained elevated with no clear downward trend."
    return text


class SessionAnalyzer:
    """Computes summaries, classification and recovery status for a Session."""

    MIN_USABLE_OBSERVATIONS = MIN_USABLE_OBSERVATIONS

    def __init__(self, session):
        self.session = session

    def analyze(self):
        """Return a structured result dictionary describing the session."""
        usable = self.session.valid_observations()
        result = {
            "session_id": self.session.session_id,
            "participant_id": self.session.participant.participant_id,
            "total_observations": len(self.session.observations),
            "usable_observations": len(usable),
            "rejected_observations": self.session.invalid_count(),
        }

        if len(usable) < self.MIN_USABLE_OBSERVATIONS:
            result["classification"] = "insufficient_data"
            result["recovery_detected"] = False
            result["heart_rate_summary"] = None
            result["activity_level_summary"] = None
            result["heart_rate_vs_reference"] = None
            result["reasoning"] = (
                f"Fewer than {self.MIN_USABLE_OBSERVATIONS} usable observations were recorded."
            )
            return result

        heart_rates = [obs.heart_rate for obs in usable]
        activity_levels = [obs.activity_level for obs in usable]

        hr_summary = compute_summary_stats(heart_rates)
        activity_summary = compute_summary_stats(activity_levels)

        result["heart_rate_summary"] = hr_summary
        result["activity_level_summary"] = activity_summary

        reference_hr = self.session.participant.reference["heart_rate"]
        result["heart_rate_vs_reference"] = round(hr_summary["average"] - reference_hr, 2)

        recovering = detect_recovery(usable)
        classification = classify_intensity(
            hr_summary["average"], reference_hr, activity_summary["average"]
        )

        if recovering and classification != "resting":
            classification = "recovering"

        result["classification"] = classification
        result["recovery_detected"] = recovering
        result["reasoning"] = build_reasoning(classification, hr_summary, reference_hr, recovering)

        return result