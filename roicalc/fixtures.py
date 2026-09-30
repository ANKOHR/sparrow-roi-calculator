"""Deterministic fictional business fixture."""
from pathlib import Path
from .store import Store, empty
from .model import compute
from .scenario import scenario
from .report import render


def generate(out, store_path=None):
    directory = Path(out)
    directory.mkdir(parents=True, exist_ok=True)
    data = empty()
    data["synthetic"] = True
    for process, minutes, runs, rate in [("invoice data entry", "45", "5", "30"), ("weekly filing", "20", "2", None)]:
        baseline = {"process": process, "minutes_per_run": minutes, "runs_per_week": runs, "hourly_rate": rate, "observed_by": "SYNTHETIC: fictional Finch Office", "observed_date": "2026-09-30T12:00:00+00:00", "notes": "SYNTHETIC fixture measurement, not real prospect data"}
        data["baselines"][process] = baseline
        data["models"].append({"baseline": dict(baseline), "result": compute(baseline, "CSV import script" if rate else "filing script", "5")})
    data["actuals"]["invoice data entry"] = {"minutes_per_run": "6", "notes": "SYNTHETIC post-build observation", "observed_date": "2026-10-30T12:00:00+00:00"}
    data["hypotheticals"].append(scenario("supplier onboarding", "45", "5", "portal form", "5", "30"))
    target = Path(store_path) if store_path else directory / "baselines.json"
    Store(target).write(data)
    for fmt in ("md", "json"):
        (directory / f"roi.{fmt}").write_text(render(data, fmt), encoding="utf-8", newline="\n")
    return target
