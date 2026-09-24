"""Console-report formatting."""


def _format_number(value, digits=1):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def format_report(result): # formats the analysis into a readable console report
    lines = [
        "=" * 60,
        "SMART FITNESS SESSION ANALYZER",
        f"Participant: {result['participant_id']}",
        f"Classification: {result['classification'].upper()}",
        "=" * 60,
        "",
        "Observations",
        f"  Total:  {result['total_observations']}",
        f"  Usable: {result['usable_observations']}",
        f"  Invalid: {result['invalid_observations']}",
        "",
        "Heart rate (bpm)",
        f"  Average: {_format_number(result['summaries']['heart_rate']['average'])}",
        f"  Minimum: {_format_number(result['summaries']['heart_rate']['minimum'])}",
        f"  Maximum: {_format_number(result['summaries']['heart_rate']['maximum'])}",
        f"  Baseline: {_format_number(result['baseline_comparison']['heart_rate']['baseline'])}",
        "",
        "Activity level",
        f"  Average: {_format_number(result['summaries']['activity_level']['average'], 2)}",
        f"  Minimum: {_format_number(result['summaries']['activity_level']['minimum'], 2)}",
        f"  Maximum: {_format_number(result['summaries']['activity_level']['maximum'], 2)}",
        "",
        "Other measurements",
        f"  Skin response average: {_format_number(result['summaries']['skin_response']['average'])}",
        f"  Temperature average: {_format_number(result['summaries']['temperature']['average'])} C",
        f"  Signal quality average: {_format_number(result['summaries']['signal_quality']['average'], 2)}",
        "",
        "Recovery",
        f"  Detected: {'Yes' if result['recovery']['detected'] else 'No'}",
        f"  Heart-rate decline: {_format_number(result['recovery']['heart_rate_decline'])} bpm",
        f"  Activity decline: {_format_number(result['recovery']['activity_decline'], 2)}",
        "",
        f"Explanation: {result['explanation']}",
    ]

    if result["invalid_reasons"]:
        lines.extend(["", "Invalid-data details"])
        for reason, count in result["invalid_reasons"].items():
            lines.append(f"  {reason}: {count}")

    return "\n".join(lines)
