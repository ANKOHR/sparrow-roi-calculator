"""Hypothetical computation has no store dependency."""
from .model import compute, name, number

HEADER = "HYPOTHETICAL SCENARIO - NOT BASED ON MEASURED DATA"


def scenario(process, minutes, runs, automation, new_minutes, hourly_rate=None):
    baseline = {"process": name(process), "minutes_per_run": str(number(minutes, "minutes per run")), "runs_per_week": str(number(runs, "runs per week")), "hourly_rate": None if hourly_rate is None else str(number(hourly_rate, "hourly rate")), "notes": "hypothetical inputs, not measurements", "observed_by": "not measured", "observed_date": "not measured"}
    return {"header": HEADER, "baseline": baseline, "result": compute(baseline, automation, new_minutes)}
