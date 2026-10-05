"""Writing the output files: analysis_summary.csv, analysis_report.txt and rejected_records.txt."""

import csv
from pathlib import Path

from helpers.exceptions import DataFileError
from helpers.validation import SIGNAL_QUALITY_THRESHOLD

SUMMARY_COLUMNS = (
    "session_id",
    "participant_id",
    "classification",
    "total_rows",
    "usable_rows",
    "rejected_rows",
    "avg_heart_rate",
    "min_heart_rate",
    "max_heart_rate",
    "baseline_heart_rate",
    "heart_rate_vs_baseline_percent",
    "avg_activity",
    "avg_skin_response",
    "avg_temperature",
    "avg_signal_quality",
    "recovery_detected",
    "flags",
)


def _number(value, digits=2, missing=""):
    return missing if value is None else f"{value:.{digits}f}"


def _summary_row(result):
    summaries = result["summaries"]
    heart_rate = result["baseline_comparison"]["heart_rate"]
    return [
        result["session_id"],
        result["participant_id"],
        result["classification"],
        result["total_rows"],
        result["usable_rows"],
        result["rejected_rows"],
        _number(summaries["heart_rate"]["average"], 1),
        _number(summaries["heart_rate"]["minimum"], 0),
        _number(summaries["heart_rate"]["maximum"], 0),
        _number(heart_rate["baseline"], 1),
        _number(heart_rate["percent_change"], 1),
        _number(summaries["activity_level"]["average"]),
        _number(summaries["skin_response"]["average"]),
        _number(summaries["temperature"]["average"]),
        _number(summaries["signal_quality"]["average"]),
        "yes" if result["recovery"]["detected"] else "no",
        "; ".join(result["flags"]),
    ]


def _measure_line(label, summary, comparison, digits, unit=""):
    line = (
        f"  {label}: average {_number(summary['average'], digits, 'n/a')}{unit}, "
        f"minimum {_number(summary['minimum'], digits, 'n/a')}, "
        f"maximum {_number(summary['maximum'], digits, 'n/a')}"
    )
    if comparison and comparison["percent_change"] is not None:
        line += f" (baseline {comparison['baseline']:.2f}, {comparison['percent_change']:+.1f}%)"
    return line


def _report_block(result):
    summaries = result["summaries"]
    comparison = result["baseline_comparison"]
    recovery = result["recovery"]
    lines = [
        "=" * 64,
        f"Session {result['session_id']} | Participant {result['participant_id']}",
        f"Classification: {result['classification'].upper()}",
        "=" * 64,
        f"Rows: {result['total_rows']} total, {result['usable_rows']} usable, {result['rejected_rows']} rejected",
        _measure_line("Heart rate (bpm)", summaries["heart_rate"], comparison["heart_rate"], 1),
        _measure_line("Activity level", summaries["activity_level"], None, 2),
        _measure_line("Skin response", summaries["skin_response"], comparison["skin_response"], 2),
        _measure_line("Temperature (C)", summaries["temperature"], comparison["temperature"], 2),
        f"  Signal quality: average {_number(summaries['signal_quality']['average'], 2, 'n/a')}",
    ]
    if recovery["detected"]:
        lines.append(
            f"Recovery: detected (peak {recovery['peak_heart_rate']:.0f} bpm, "
            f"heart-rate decline {recovery['heart_rate_decline']:.1f} bpm, "
            f"activity decline {recovery['activity_decline']:.2f})"
        )
    else:
        lines.append("Recovery: not detected")
    lines.append("Flags: " + ("; ".join(result["flags"]) if result["flags"] else "none"))
    lines.append("Reasons:")
    lines.extend(f"  - {reason}" for reason in result["reasons"])
    lines.append("")
    return lines


def _report_text(results):
    lines = [
        "SMART FITNESS SESSION ANALYZER - ANALYSIS REPORT",
        f"Data-quality rule: windows with signal_quality below {SIGNAL_QUALITY_THRESHOLD:.2f} are rejected.",
        f"Sessions analysed: {len(results)}",
        "",
    ]
    for result in results:
        lines.extend(_report_block(result))
    return "\n".join(lines)


def _rejected_text(loader):
    lines = [
        "REJECTED RECORDS",
        "Format: file | row | field | reason (row 1 is the header line)",
        "",
    ]
    for record in loader.rejections:
        lines.append(f"{record.source} | row {record.row_number} | {record.field} | {record.reason}")
    if not loader.rejections:
        lines.append("No rows were rejected.")
    lines.extend(["", "Rejected rows per file"])
    for name, count in loader.rejected_rows.items():
        lines.append(f"  {name}: {count}")
    if loader.skipped_files:
        lines.extend(["", "Files skipped"])
        lines.extend(f"  {message}" for message in loader.skipped_files)
    return "\n".join(lines) + "\n"


def write_outputs(results, loader, output_dir):
    """Create the output directory if needed and write the three files. Returns the file paths."""
    output_dir = Path(output_dir)
    summary_path = output_dir / "analysis_summary.csv"
    report_path = output_dir / "analysis_report.txt"
    rejected_path = output_dir / "rejected_records.txt"
    current = output_dir
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        current = summary_path
        with open(summary_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(SUMMARY_COLUMNS)
            for result in results:
                writer.writerow(_summary_row(result))

        current = report_path
        with open(report_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(_report_text(results))

        current = rejected_path
        with open(rejected_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(_rejected_text(loader))
    except PermissionError as error:
        raise DataFileError(current, "permission denied while writing output") from error
    except OSError as error:
        raise DataFileError(current, f"could not be written ({error.strerror or error})") from error

    return [summary_path, report_path, rejected_path]