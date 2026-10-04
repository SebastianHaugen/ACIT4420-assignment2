"""Writes the three required report files into the output directory,
creating that directory first if it doesn't already exist.
"""

import csv
from pathlib import Path

SUMMARY_FIELDNAMES = [
    "session_id",
    "participant_id",
    "classification",
    "recovery_detected",
    "usable_observations",
    "rejected_observations",
    "heart_rate_vs_reference",
]


def ensure_output_dir(output_dir):
    """Create the output directory (and parents) if it doesn't exist yet."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_summary_csv(output_dir, results):
    """One row per processed session analysis_summary.csv."""
    path = Path(output_dir) / "analysis_summary.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        for result in results:
            writer.writerow({key: result.get(key, "") for key in SUMMARY_FIELDNAMES})
    return path


def write_report_txt(output_dir, results):
    """A readable explanation of each result - analysis_report.txt."""
    path = Path(output_dir) / "analysis_report.txt"
    lines = []
    for result in results:
        lines.append(f"Session {result['session_id']} (participant {result['participant_id']})")
        lines.append(
            f"  Observations: {result['total_observations']} total, "
            f"{result['usable_observations']} usable, "
            f"{result['rejected_observations']} rejected"
        )
        lines.append(f"  Classification: {result['classification'].upper()}")
        lines.append(f"  Recovery detected: {'Yes' if result['recovery_detected'] else 'No'}")
        lines.append(f"  Reasoning: {result['reasoning']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_rejected_records_txt(output_dir, rejected_records):
    """Every rejected row with filename, row number, field and reason."""
    path = Path(output_dir) / "rejected_records.txt"
    lines = [str(record) for record in rejected_records]
    if not lines:
        lines = ["No records were rejected."]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path