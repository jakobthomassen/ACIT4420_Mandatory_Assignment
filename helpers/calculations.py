"""Small reusable calculation functions."""


def calculate_average(values): # Return the arithmetic mean, or None when no values are available
    values = list(values)
    return sum(values) / len(values) if values else None


def calculate_minimum(values): # Return the minimum value, or None when no values are available
    values = list(values)
    return min(values) if values else None


def calculate_maximum(values): # Return the maximum value, or None when no values are available
    values = list(values)
    return max(values) if values else None


def compare_to_baseline(value, baseline): # Return absolute and percentage differences from a reference value
    if value is None or baseline is None or baseline == 0:
        return {"difference": None, "percent_change": None}

    difference = value - baseline
    percent_change = difference / baseline * 100
    return {
        "difference": difference,
        "percent_change": percent_change,
    }


def calculate_recovery(start_values, end_values, minimum_decline): # Check whether two measures both decline enough for activity to be considered recovery
    if not start_values or not end_values:
        return False

    start_average = calculate_average(start_values)
    end_average = calculate_average(end_values)
    return start_average - end_average >= minimum_decline
