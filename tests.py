"""Tests for the Smart Fitness Session Analyzer. Run with: python3 -m unittest tests -v"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
from helpers.analysis import FitnessAnalyzer
from helpers.exceptions import DataFileError, InvalidIdentifierError, InvalidRecordError
from helpers.loader import DataLoader
from helpers.models import FitnessSession, ObservationWindow, Participant, ReferenceProfile
from helpers.validation import (
    parse_session_row,
    validate_participant_id,
    validate_session_id,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
PROFILES_HEADER = "participant_id,name,baseline_heart_rate,baseline_skin_response,baseline_temperature\n"
SESSIONS_HEADER = (
    "session_id,participant_id,timestamp,heart_rate,skin_response,temperature,activity_level,signal_quality\n"
)
ONE_PROFILE = PROFILES_HEADER + "P001,Amina Noor,68,1.20,32.4\n"
KNOWN = {"P001": None}


def row(session="FIT-2026-001", person="P001", timestamp="0", heart_rate="70", skin="1.2",
        temperature="32.4", activity="0.2", quality="0.9"):
    return [session, person, timestamp, heart_rate, skin, temperature, activity, quality]


def make_session(pairs, rejected=0):
    """Build a session from (heart_rate, activity) pairs for participant P001 (baseline 68)."""
    participant = Participant("P001", "Test", ReferenceProfile(68, 1.2, 32.4))
    session = FitnessSession("FIT-2026-001", participant)
    for index, (heart_rate, activity) in enumerate(pairs):
        session.add_observation(ObservationWindow(index, heart_rate, 1.5, 33.0, activity, 0.9))
    session.rejected_count = rejected
    return session


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.dir = Path(self._temp.name)

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8", newline="")
        return path


class IdentifierTests(unittest.TestCase):
    def test_valid_identifiers(self):
        self.assertEqual(validate_participant_id("P001"), "P001")
        self.assertEqual(validate_session_id("FIT-2026-001"), "FIT-2026-001")

    def test_invalid_participant_ids(self):
        for value in ("001", "p001", "P01", "P0001", "P00A", "P001\n", " P001", ""):
            with self.subTest(value=value):
                with self.assertRaises(InvalidIdentifierError):
                    validate_participant_id(value)

    def test_invalid_session_ids(self):
        for value in ("FIT-26-102", "FIT-2026-1", "FIT-2026-0001", "fit-2026-001", "REC-2026-001", "FIT-2026-001\n"):
            with self.subTest(value=value):
                with self.assertRaises(InvalidIdentifierError):
                    validate_session_id(value)


class RowValidationTests(unittest.TestCase):
    def problems(self, **changes):
        values, problems = parse_session_row(row(**changes), KNOWN)
        return problems

    def test_valid_row_is_converted_to_numbers(self):
        values, problems = parse_session_row(row(), KNOWN)
        self.assertEqual(problems, [])
        self.assertIsInstance(values["timestamp"], int)
        self.assertIsInstance(values["heart_rate"], float)

    def test_bad_types(self):
        self.assertEqual(self.problems(heart_rate="fast")[0][0], "heart_rate")
        self.assertEqual(self.problems(timestamp="two")[0][0], "timestamp")
        self.assertEqual(self.problems(timestamp="1.5")[0][0], "timestamp")
        self.assertEqual(self.problems(heart_rate="nan")[0][0], "heart_rate")

    def test_missing_value(self):
        problems = self.problems(activity="")
        self.assertEqual(problems, [("activity_level", "missing value")])

    def test_unknown_participant(self):
        problems = self.problems(person="P999")
        self.assertEqual(problems[0][0], "participant_id")
        self.assertIn("unknown", problems[0][1])

    def test_wrong_row_length(self):
        with self.assertRaises(InvalidRecordError):
            parse_session_row(row()[:7], KNOWN)
        with self.assertRaises(InvalidRecordError):
            parse_session_row([], KNOWN)

    def test_several_problems_in_one_row(self):
        problems = self.problems(skin="-0.5", temperature="55", activity="1.3")
        self.assertEqual([field for field, _ in problems], ["skin_response", "temperature", "activity_level"])

    def test_heart_rate_boundaries(self):
        self.assertEqual(self.problems(heart_rate="35"), [])
        self.assertEqual(self.problems(heart_rate="205"), [])
        self.assertEqual(self.problems(heart_rate="34.9")[0][0], "heart_rate")
        self.assertEqual(self.problems(heart_rate="205.1")[0][0], "heart_rate")

    def test_temperature_and_activity_boundaries(self):
        self.assertEqual(self.problems(temperature="25"), [])
        self.assertEqual(self.problems(temperature="42"), [])
        self.assertEqual(self.problems(temperature="42.1")[0][0], "temperature")
        self.assertEqual(self.problems(activity="0"), [])
        self.assertEqual(self.problems(activity="1"), [])
        self.assertEqual(self.problems(activity="1.01")[0][0], "activity_level")
        self.assertEqual(self.problems(skin="0"), [])
        self.assertEqual(self.problems(timestamp="0"), [])
        self.assertEqual(self.problems(timestamp="-1")[0][0], "timestamp")

    def test_signal_quality_boundary(self):
        self.assertEqual(self.problems(quality="0.60"), [])
        problems = self.problems(quality="0.59")
        self.assertEqual(problems[0][0], "signal_quality")
        self.assertIn("poor signal quality", problems[0][1])
        self.assertIn("outside", self.problems(quality="1.4")[0][1])


class LoaderTests(TempDirTestCase):
    def test_valid_files_are_loaded_and_grouped(self):
        profiles = self.write("p.csv", ONE_PROFILE)
        sessions = self.write(
            "s.csv",
            SESSIONS_HEADER
            + "FIT-2026-001,P001,0,70,1.2,32.4,0.2,0.9\n"
            + "FIT-2026-001,P001,1,71,1.2,32.4,0.2,0.9\n"
            + "FIT-2026-002,P001,0,80,1.2,32.4,0.2,0.9\n",
        )
        loader = DataLoader()
        loader.load_profiles(profiles)
        loader.load_session_files([sessions])
        self.assertEqual(sorted(loader.sessions), ["FIT-2026-001", "FIT-2026-002"])
        self.assertEqual(len(loader.sessions["FIT-2026-001"].observations), 2)
        self.assertEqual(loader.sessions["FIT-2026-001"].participant_id, "P001")
        self.assertEqual(loader.total_rejected, 0)

    def test_missing_profile_file_raises(self):
        with self.assertRaises(DataFileError) as context:
            DataLoader().load_profiles(self.dir / "nope.csv")
        self.assertIn("not found", str(context.exception))

    def test_missing_session_file_is_skipped(self):
        profiles = self.write("p.csv", ONE_PROFILE)
        sessions = self.write("s.csv", SESSIONS_HEADER + "FIT-2026-001,P001,0,70,1.2,32.4,0.2,0.9\n")
        loader = DataLoader()
        loader.load_profiles(profiles)
        loader.load_session_files([self.dir / "missing.csv", sessions])
        self.assertEqual(len(loader.skipped_files), 1)
        self.assertIn("missing.csv", loader.skipped_files[0])
        self.assertEqual(loader.accepted_rows["s.csv"], 1)

    def test_permission_error_becomes_data_file_error(self):
        path = self.write("p.csv", ONE_PROFILE)
        with mock.patch("builtins.open", side_effect=PermissionError):
            with self.assertRaises(DataFileError) as context:
                DataLoader().load_profiles(path)
        self.assertIn("permission denied", str(context.exception))

    def test_wrong_header_and_empty_file(self):
        with self.assertRaises(DataFileError):
            DataLoader().load_profiles(self.write("bad.csv", "id,name\nP001,Amina\n"))
        with self.assertRaises(DataFileError):
            DataLoader().load_profiles(self.write("empty.csv", ""))

    def test_bad_profile_rows_are_rejected(self):
        text = (
            PROFILES_HEADER
            + "P001,Amina,68,1.2,32.4\n"
            + "P001,Duplicate,70,1.2,32.4\n"
            + "X002,Bad Id,70,1.2,32.4\n"
            + "P003,Too Hot,70,1.2,50\n"
            + "P004,Short,70\n"
        )
        loader = DataLoader()
        loader.load_profiles(self.write("p.csv", text))
        self.assertEqual(list(loader.participants), ["P001"])
        self.assertEqual(loader.rejected_rows["p.csv"], 4)

    def test_session_cannot_switch_participant_or_repeat_timestamp(self):
        profiles = self.write("p.csv", ONE_PROFILE + "P002,Jonas,74,1.4,32.7\n")
        sessions = self.write(
            "s.csv",
            SESSIONS_HEADER
            + "FIT-2026-001,P001,0,70,1.2,32.4,0.2,0.9\n"
            + "FIT-2026-001,P002,1,70,1.2,32.4,0.2,0.9\n"
            + "FIT-2026-001,P001,0,72,1.2,32.4,0.2,0.9\n",
        )
        loader = DataLoader()
        loader.load_profiles(profiles)
        loader.load_session_files([sessions])
        reasons = [record.reason for record in loader.rejections]
        self.assertTrue(any("belongs to P001" in reason for reason in reasons))
        self.assertTrue(any("duplicate timestamp" in reason for reason in reasons))
        self.assertEqual(loader.sessions["FIT-2026-001"].rejected_count, 2)

    def test_rejected_record_has_file_row_field_reason(self):
        profiles = self.write("p.csv", ONE_PROFILE)
        sessions = self.write("s.csv", SESSIONS_HEADER + "FIT-2026-001,P001,0,fast,1.2,32.4,0.2,0.9\n")
        loader = DataLoader()
        loader.load_profiles(profiles)
        loader.load_session_files([sessions])
        record = loader.rejections[0]
        self.assertEqual((record.source, record.row_number, record.field), ("s.csv", 2, "heart_rate"))
        self.assertIn("fast", record.reason)


class AnalysisTests(unittest.TestCase):
    def classify(self, pairs, rejected=0):
        return FitnessAnalyzer().analyze(make_session(pairs, rejected))

    def test_insufficient_data_boundary(self):
        self.assertEqual(self.classify([(70, 0.1)] * 3)["classification"], "insufficient data")
        self.assertEqual(self.classify([(70, 0.1)] * 4)["classification"], "resting")
        self.assertEqual(self.classify([])["classification"], "insufficient data")

    def test_activity_thresholds(self):
        self.assertEqual(self.classify([(70, 0.29)] * 4)["classification"], "resting")
        self.assertEqual(self.classify([(90, 0.30)] * 4)["classification"], "moderate activity")
        self.assertEqual(self.classify([(100, 0.67)] * 4)["classification"], "moderate activity")
        self.assertEqual(self.classify([(140, 0.68)] * 4)["classification"], "high activity")

    def test_recovery_detected(self):
        result = self.classify([(100, 0.5), (150, 0.9), (140, 0.7), (110, 0.3), (90, 0.2), (80, 0.1)])
        self.assertEqual(result["classification"], "recovering")
        self.assertTrue(result["recovery"]["detected"])
        self.assertTrue(any("fell from a peak" in reason for reason in result["reasons"]))

    def test_recovery_heart_rate_boundary(self):
        # four windows -> final window only; decline of exactly 20 bpm counts, 19 does not
        self.assertTrue(self.classify([(100, 0.5), (150, 0.9), (140, 0.7), (130, 0.3)])["recovery"]["detected"])
        self.assertFalse(self.classify([(100, 0.5), (150, 0.9), (140, 0.7), (131, 0.3)])["recovery"]["detected"])

    def test_no_recovery_when_activity_stays_high(self):
        result = self.classify([(100, 0.5), (150, 0.9), (140, 0.9), (100, 0.8)])
        self.assertFalse(result["recovery"]["detected"])
        self.assertEqual(result["classification"], "high activity")

    def test_no_recovery_when_peak_is_at_the_end(self):
        result = self.classify([(80, 0.2), (85, 0.2), (90, 0.3), (160, 0.9)])
        self.assertFalse(result["recovery"]["detected"])

    def test_unusual_flag_for_high_heart_rate_at_rest(self):
        result = self.classify([(110, 0.1)] * 5)  # baseline 68 -> +62%
        self.assertEqual(result["classification"], "resting")
        self.assertEqual(len(result["flags"]), 1)
        self.assertEqual(self.classify([(70, 0.1)] * 5)["flags"], [])

    def test_result_structure_and_rejected_note(self):
        result = self.classify([(70, 0.1)] * 5, rejected=2)
        self.assertEqual(result["total_rows"], 7)
        self.assertEqual(result["usable_rows"], 5)
        self.assertEqual(result["rejected_rows"], 2)
        for key in ("summaries", "baseline_comparison", "recovery", "flags", "reasons"):
            self.assertIn(key, result)
        self.assertTrue(any("rejected" in reason for reason in result["reasons"]))


@unittest.skipUnless((DATA_DIR / "participants.csv").exists(), "official data files not found")
class OfficialDataTests(TempDirTestCase):
    def run_official(self):
        loader = DataLoader()
        loader.load_profiles(DATA_DIR / "participants.csv")
        loader.load_session_files([DATA_DIR / "fitness_sessions.csv", DATA_DIR / "fitness_sessions_invalid.csv"])
        analyzer = FitnessAnalyzer()
        results = {key: analyzer.analyze(loader.sessions[key]) for key in loader.sessions}
        return loader, results

    def test_expected_classifications(self):
        _, results = self.run_official()
        expected = {
            "FIT-2026-001": "resting",
            "FIT-2026-002": "moderate activity",
            "FIT-2026-003": "high activity",
            "FIT-2026-004": "recovering",
            "FIT-2026-005": "insufficient data",
            "FIT-2026-101": "insufficient data",
            "FIT-2026-102": "insufficient data",
            "FIT-2026-103": "insufficient data",
        }
        self.assertEqual({key: value["classification"] for key, value in results.items()}, expected)

    def test_row_counts(self):
        loader, _ = self.run_official()
        self.assertEqual(loader.accepted_rows["participants.csv"], 3)
        self.assertEqual(loader.accepted_rows["fitness_sessions.csv"], 24)
        self.assertEqual(loader.rejected_rows["fitness_sessions.csv"], 5)  # poor signal quality
        self.assertEqual(loader.accepted_rows["fitness_sessions_invalid.csv"], 1)
        self.assertEqual(loader.rejected_rows["fitness_sessions_invalid.csv"], 10)

    def test_invalid_file_rejections_by_field(self):
        loader, _ = self.run_official()
        found = {(r.row_number, r.field) for r in loader.rejections if r.source == "fitness_sessions_invalid.csv"}
        expected = {
            (3, "heart_rate"), (4, "participant_id"), (5, "activity_level"), (6, "signal_quality"),
            (7, "session_id"), (8, "participant_id"), (9, "timestamp"), (10, "heart_rate"),
            (11, "skin_response"), (11, "temperature"), (11, "activity_level"), (12, "row"),
        }
        self.assertEqual(found, expected)


class OutputTests(TempDirTestCase):
    def run_main(self, profiles, sessions, output):
        buffer, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
            code = main.run(profiles, sessions, output)
        return code, buffer.getvalue(), errors.getvalue()

    def setup_small_data(self):
        profiles = self.write("p.csv", ONE_PROFILE)
        lines = "".join(f"FIT-2026-001,P001,{i},70,1.2,32.4,0.2,0.9\n" for i in range(5))
        sessions = self.write("s.csv", SESSIONS_HEADER + lines + "FIT-2026-001,P001,9,70,1.2,32.4,0.2,0.1\n")
        return profiles, sessions

    def test_output_files_created_in_new_directory_and_rerun_is_identical(self):
        profiles, sessions = self.setup_small_data()
        output = self.dir / "new" / "output"
        code, text, _ = self.run_main(profiles, [sessions], output)
        self.assertEqual(code, 0)
        names = ("analysis_summary.csv", "analysis_report.txt", "rejected_records.txt")
        first = {name: (output / name).read_text(encoding="utf-8") for name in names}
        self.assertIn("accepted 5, rejected 1", text)
        self.assertIn("poor signal quality", first["rejected_records.txt"])
        self.assertEqual(len(first["analysis_summary.csv"].strip().splitlines()), 2)  # header + one session

        self.run_main(profiles, [sessions], output)
        second = {name: (output / name).read_text(encoding="utf-8") for name in names}
        self.assertEqual(first, second)

    def test_missing_profile_file_returns_error_code(self):
        _, sessions = self.setup_small_data()
        code, _, errors = self.run_main(self.dir / "none.csv", [sessions], self.dir / "out")
        self.assertEqual(code, 1)
        self.assertIn("none.csv", errors)

    def test_all_session_files_missing_returns_error_code(self):
        profiles, _ = self.setup_small_data()
        code, _, errors = self.run_main(profiles, [self.dir / "gone.csv"], self.dir / "out")
        self.assertEqual(code, 1)
        self.assertIn("gone.csv", errors)

    def test_one_missing_session_file_still_completes(self):
        profiles, sessions = self.setup_small_data()
        code, _, errors = self.run_main(profiles, [self.dir / "gone.csv", sessions], self.dir / "out")
        self.assertEqual(code, 0)
        self.assertIn("skipped", errors)
        self.assertIn("Files skipped", (self.dir / "out" / "rejected_records.txt").read_text(encoding="utf-8"))

    def test_unwritable_output_location_returns_error_code(self):
        profiles, sessions = self.setup_small_data()
        blocker = self.write("blocker.txt", "a file, not a directory")
        code, _, errors = self.run_main(profiles, [sessions], blocker / "output")
        self.assertEqual(code, 1)
        self.assertIn("cannot write output", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)