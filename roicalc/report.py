"""Deterministic reports sharing the model's Decimal computation."""
import json
from decimal import Decimal, ROUND_HALF_UP
from .model import compute

HONESTY = "HONESTY NOTE: measured figures derive from recorded baselines shown with their provenance. Hypothetical figures are labelled HYPOTHETICAL and are not measurements. No baseline, no number."


def display(value):
    return format(Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), ".1f")


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def result_lines(result):
    lines = [f"Automation: {safe(result['automation'])}; new minutes/run: {display(result['new_minutes_per_run'])}", f"Saved minutes/run: {display(result['saved_minutes_per_run'])}", "", "| Period | Minutes saved | Hours saved |", "| --- | ---: | ---: |"]
    for period, values in result["time"].items():
        lines.append(f"| {period} | {display(values['minutes'])} | {display(values['hours'])} |")
    if "money" in result:
        lines += ["", "Money (GBP): " + "; ".join(f"{key} {value}" for key, value in result["money"].items())]
    if "note" in result:
        lines.append(result["note"])
    if "flag" in result:
        lines.append(result["flag"])
    return lines


def render(data, fmt="md", process=None):
    measured = []
    for entry in data["models"]:
        if process is not None and entry["baseline"]["process"] != process:
            continue
        item = dict(entry)
        actual = data["actuals"].get(entry["baseline"]["process"])
        if actual:
            item["actual"] = actual
            item["actual_result"] = compute(entry["baseline"], entry["result"]["automation"], actual["minutes_per_run"])
        measured.append(item)
    baselines = [value for key, value in sorted(data["baselines"].items()) if process is None or key == process]
    hypothetical = [entry for entry in data["hypotheticals"] if process is None or entry["baseline"]["process"] == process]
    payload = {"honesty_note": HONESTY, "synthetic": data["synthetic"], "baselines": baselines, "measured_models": measured, "hypothetical_scenarios": hypothetical}
    if fmt == "json":
        return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    lines = ["# Sparrow ROI Calculator", "", HONESTY, ""]
    if data["synthetic"]:
        lines += ["SYNTHETIC FIXTURE - fictional business, not prospect measurements", ""]
    lines += ["## Recorded baselines", ""]
    for baseline in baselines:
        lines += provenance(baseline)
    lines += ["## Measured models", ""]
    for entry in measured:
        lines += [f"### {safe(entry['baseline']['process'])}", ""] + provenance(entry["baseline"]) + result_lines(entry["result"]) + [""]
        if "actual" in entry:
            lines += ["Predicted vs actual savings", "", "| Period | Predicted minutes | Actual minutes | Predicted hours | Actual hours |", "| --- | ---: | ---: | ---: | ---: |"]
            for period in ("weekly", "monthly", "yearly"):
                pred, act = entry["result"]["time"][period], entry["actual_result"]["time"][period]
                lines.append(f"| {period} | {display(pred['minutes'])} | {display(act['minutes'])} | {display(pred['hours'])} | {display(act['hours'])} |")
            if "money" in entry["result"]:
                lines += ["", "| Period | Predicted GBP | Actual GBP |", "| --- | ---: | ---: |"]
                for period in ("weekly", "monthly", "yearly"):
                    lines.append(f"| {period} | {entry['result']['money'][period]} | {entry['actual_result']['money'][period]} |")
            lines += [f"Actual minutes/run: {display(entry['actual']['minutes_per_run'])}; observed date: {safe(entry['actual']['observed_date'])}; notes: {safe(entry['actual']['notes'])}", entry["actual_result"].get("flag", ""), ""]
    lines += ["## HYPOTHETICAL scenarios", ""]
    for entry in hypothetical:
        lines += [entry["header"], f"### {safe(entry['baseline']['process'])}"] + result_lines(entry["result"]) + [""]
    return "\n".join(lines) + "\n"


def provenance(baseline):
    lines = [f"Process: {safe(baseline['process'])}; baseline minutes/run: {baseline['minutes_per_run']}; runs/week: {baseline['runs_per_week']}", f"Observed by: {safe(baseline['observed_by'])}; observed date: {safe(baseline['observed_date'])}; notes: {safe(baseline['notes'])}"]
    if baseline.get("hourly_rate") is not None:
        lines.append(f"Recorded hourly rate (GBP): {baseline['hourly_rate']}")
    if "replacement_note" in baseline:
        lines.append(safe(baseline["replacement_note"]))
    return lines + [""]
