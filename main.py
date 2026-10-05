"""
Smart Fitness Session Analyzer (Assignment II).

Loads participant and session CSV files, validates every row, analyzes each session and
writes a summary CSV, a readable report and a list of rejected records.

Example:
    python3 main.py --profiles data/participants.csv \
        --sessions data/fitness_sessions.csv data/fitness_sessions_invalid.csv --output output
"""

import argparse
import sys
from pathlib import Path

from helpers.analysis import FitnessAnalyzer
from helpers.exceptions import DataFileError
from helpers.loader import DataLoader
from helpers.reporting import write_outputs

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_PROFILES = DATA_DIR / "participants.csv"
DEFAULT_SESSIONS = (DATA_DIR / "fitness_sessions.csv", DATA_DIR / "fitness_sessions_invalid.csv")
DEFAULT_OUTPUT = Path("output")


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description="Smart Fitness Session Analyzer")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES, help="participants CSV file")
    parser.add_argument(
        "--sessions", type=Path, nargs="+", default=list(DEFAULT_SESSIONS), help="one or more session CSV files"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output directory")
    return parser.parse_args(argv)


def print_summary(loader, results, created_files):
    print("Smart Fitness Session Analyzer - completed")
    for name in loader.accepted_rows:
        print(f"  {name}: accepted {loader.accepted_rows[name]}, rejected {loader.rejected_rows[name]}")
    print(f"Total accepted rows: {loader.total_accepted}")
    print(f"Total rejected rows: {loader.total_rejected}")
    print(f"Sessions analysed: {len(results)}")
    print("Files created:")
    for path in created_files:
        print(f"  {path}")


def run(profiles, sessions, output):
    """Run the whole pipeline. Returns 0 on success and 1 on a fatal error."""
    loader = DataLoader()
    try:
        loader.load_profiles(profiles)
    except DataFileError as error:
        print(f"ERROR: cannot load profiles - {error}", file=sys.stderr)
        return 1

    loader.load_session_files(sessions)
    for message in loader.skipped_files:
        print(f"WARNING: skipped file - {message}", file=sys.stderr)
    if len(loader.skipped_files) == len(sessions):
        print("ERROR: none of the session files could be read.", file=sys.stderr)
        return 1

    analyzer = FitnessAnalyzer()
    results = [analyzer.analyze(loader.sessions[key]) for key in sorted(loader.sessions)]

    try:
        created_files = write_outputs(results, loader, output)
    except DataFileError as error:
        print(f"ERROR: cannot write output - {error}", file=sys.stderr)
        return 1

    print_summary(loader, results, created_files)
    return 0


def main(argv=None):
    arguments = parse_arguments(argv)
    return run(arguments.profiles, arguments.sessions, arguments.output)


if __name__ == "__main__":
    sys.exit(main())