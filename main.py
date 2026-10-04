"""
Option A, Smart Fitness Session Analyzer for assignment 2

This can be run from the repository root.

python main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv --output output

You can also pas multiple fitness files to process the valid and invalid files in the same run.

"""

import argparse
import sys
 
from fitness_analyzer.analysis import SessionAnalyzer
from fitness_analyzer.loader import load_participants, load_sessions
from fitness_analyzer.reports import (
    ensure_output_dir,
    write_report_txt,
    write_rejected_records_txt,
    write_summary_csv,
)
 
 
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Smart Fitness Session Analyzer")
    parser.add_argument("--profiles", required=True, help="Path to participants.csv")
    parser.add_argument(
        "--sessions",
        required=True,
        nargs="+",
        help="Path(s) to one or more fitness-session CSV files",
    )
    parser.add_argument("--output", required=True, help="Output directory for reports")
    return parser.parse_args(argv)
 
 
def main(argv=None):
    args = parse_args(argv)
 
    try:
        participants, rejected = load_participants(args.profiles)
    except (FileNotFoundError, PermissionError) as exc:
        print(f"Could not read profiles file: {exc}")
        return 1
 
    all_rejected = list(rejected)
    all_sessions = {}
 
    for sessions_path in args.sessions:
        try:
            sessions, session_rejected = load_sessions(sessions_path, participants)
        except (FileNotFoundError, PermissionError) as exc:
            print(f"Could not read sessions file: {exc}")
            continue
        all_sessions.update(sessions)
        all_rejected.extend(session_rejected)
 
    results = [SessionAnalyzer(session).analyze() for session in all_sessions.values()]
    results.sort(key=lambda result: result["session_id"])
 
    output_dir = ensure_output_dir(args.output)
    write_summary_csv(output_dir, results)
    write_report_txt(output_dir, results)
    write_rejected_records_txt(output_dir, all_rejected)
 
    accepted_rows = sum(r["usable_observations"] for r in results)
    rejected_rows = len(all_rejected)
 
    print("=== Completion summary ===")
    print(f"Participants loaded: {len(participants)}")
    print(f"Sessions processed: {len(results)}")
    print(f"Accepted rows: {accepted_rows}")
    print(f"Rejected rows: {rejected_rows}")
    print(f"Reports written to: {output_dir}/")
 
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())