"""
Session analysis: summaries, baseline comparison, recovery detection and classification.
"""

from helpers.calculations import (
    calculate_average,
    calculate_maximum,
    calculate_minimum,
    calculate_recovery,
    compare_to_baseline,
)

MINIMUM_USABLE_OBSERVATIONS = 4
HIGH_ACTIVITY_THRESHOLD = 0.68
MODERATE_ACTIVITY_THRESHOLD = 0.30
RECOVERY_HEART_RATE_DROP = 20  # bpm below the peak
RECOVERY_ACTIVITY_DROP = 0.25  # below the activity at the peak
UNUSUAL_HEART_RATE_PERCENT = 40  # percent above baseline
UNUSUAL_ACTIVITY_LIMIT = 0.25  # "low activity" for the unusual-heart-rate flag


class BaseAnalyzer:  # Base interface for session analyzers

    def analyze(self, session):
        raise NotImplementedError


class FitnessAnalyzer(BaseAnalyzer):  # Analyze one session and return a result dictionary

    def analyze(self, session):
        windows = session.observations
        usable_count = len(windows)
        summaries = self._summaries(windows)
        comparison = self._baseline_comparison(session.participant, summaries)
        recovery = self._recovery(windows)
        flags = []
        reasons = []

        if usable_count < MINIMUM_USABLE_OBSERVATIONS:
            classification = "insufficient data"
            reasons.append(
                f"Only {usable_count} usable observation(s); at least {MINIMUM_USABLE_OBSERVATIONS} "
                "are needed for a reliable classification."
            )
        else:
            classification, class_reasons = self._classify(summaries, recovery)
            reasons.extend(class_reasons)
            reasons.extend(self._baseline_reasons(comparison))
            flags.extend(self._flags(summaries, comparison))

        if session.rejected_count:
            reasons.append(
                f"{session.rejected_count} row(s) of this session were rejected (see rejected_records.txt)."
            )

        return {
            "session_id": session.session_id,
            "participant_id": session.participant_id,
            "classification": classification,
            "total_rows": usable_count + session.rejected_count,
            "usable_rows": usable_count,
            "rejected_rows": session.rejected_count,
            "summaries": summaries,
            "baseline_comparison": comparison,
            "recovery": recovery,
            "flags": flags,
            "reasons": reasons,
        }

    def _summaries(self, windows):
        summaries = {}
        for field in ("heart_rate", "skin_response", "temperature", "activity_level", "signal_quality"):
            values = [getattr(window, field) for window in windows]
            summaries[field] = {
                "average": calculate_average(values),
                "minimum": calculate_minimum(values),
                "maximum": calculate_maximum(values),
            }
        return summaries

    def _baseline_comparison(self, participant, summaries):
        reference = participant.reference_profile if participant else None
        baselines = {
            "heart_rate": reference.baseline_heart_rate if reference else None,
            "skin_response": reference.baseline_skin_response if reference else None,
            "temperature": reference.baseline_temperature if reference else None,
        }
        result = {}
        for field, baseline in baselines.items():
            comparison = compare_to_baseline(summaries[field]["average"], baseline)
            comparison["baseline"] = baseline
            result[field] = comparison
        return result

    def _recovery(self, windows):
        # Recovery: after the heart-rate peak, the final third of the session is clearly lower in both
        # heart rate and activity than at the peak window.
        empty = {
            "detected": False,
            "peak_heart_rate": None,
            "final_heart_rate": None,
            "heart_rate_decline": None,
            "activity_decline": None,
        }
        if len(windows) < MINIMUM_USABLE_OBSERVATIONS:
            return empty

        peak = max(windows, key=lambda window: window.heart_rate)
        peak_index = windows.index(peak)
        tail_size = max(1, len(windows) // 3)
        tail = windows[-tail_size:]

        final_heart_rate = calculate_average([window.heart_rate for window in tail])
        final_activity = calculate_average([window.activity_level for window in tail])
        peak_before_tail = peak_index < len(windows) - tail_size

        detected = (
            peak_before_tail
            and calculate_recovery([peak.heart_rate], [w.heart_rate for w in tail], RECOVERY_HEART_RATE_DROP)
            and calculate_recovery([peak.activity_level], [w.activity_level for w in tail], RECOVERY_ACTIVITY_DROP)
        )
        return {
            "detected": detected,
            "peak_heart_rate": peak.heart_rate,
            "final_heart_rate": final_heart_rate,
            "heart_rate_decline": peak.heart_rate - final_heart_rate,
            "activity_decline": peak.activity_level - final_activity,
        }

    def _classify(self, summaries, recovery):
        average_activity = summaries["activity_level"]["average"]
        if recovery["detected"]:
            return "recovering", [
                f"Heart rate fell from a peak of {recovery['peak_heart_rate']:.0f} bpm to "
                f"{recovery['final_heart_rate']:.1f} bpm and activity fell by "
                f"{recovery['activity_decline']:.2f} towards the end of the session."
            ]
        if average_activity >= HIGH_ACTIVITY_THRESHOLD:
            return "high activity", [
                f"Average activity {average_activity:.2f} is at or above {HIGH_ACTIVITY_THRESHOLD}."
            ]
        if average_activity >= MODERATE_ACTIVITY_THRESHOLD:
            return "moderate activity", [
                f"Average activity {average_activity:.2f} is between {MODERATE_ACTIVITY_THRESHOLD} "
                f"and {HIGH_ACTIVITY_THRESHOLD}, and no recovery trend was found."
            ]
        return "resting", [
            f"Average activity {average_activity:.2f} is below {MODERATE_ACTIVITY_THRESHOLD}, "
            "and no recovery trend was found."
        ]

    def _baseline_reasons(self, comparison):
        heart_rate = comparison["heart_rate"]
        if heart_rate["percent_change"] is None:
            return []
        return [
            f"Average heart rate is {heart_rate['percent_change']:+.1f}% compared with the "
            f"personal baseline of {heart_rate['baseline']:.0f} bpm."
        ]

    def _flags(self, summaries, comparison):
        flags = []
        percent = comparison["heart_rate"]["percent_change"]
        if (
            percent is not None
            and percent > UNUSUAL_HEART_RATE_PERCENT
            and summaries["activity_level"]["average"] < UNUSUAL_ACTIVITY_LIMIT
        ):
            flags.append(
                f"unusual: average heart rate is {percent:.0f}% above baseline despite low activity"
            )
        return flags