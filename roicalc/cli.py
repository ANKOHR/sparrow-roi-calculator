"""Command line interface for measured and hypothetical ROI."""
import argparse
import json
import sys
from pathlib import Path
from .errors import ROIError, StoreIOError
from .store import Store
from .model import record_model
from .scenario import scenario
from .actuals import record_actual
from .report import render, result_lines
from .fixtures import generate


def parser():
    root = argparse.ArgumentParser(prog="src", description="No baseline, no number. Hypotheticals stay labelled.")
    root.add_argument("--store", default=".src-baselines.json")
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("baseline", "model", "scenario", "actual", "report", "fixtures"):
        p = sub.add_parser(command)
        p.add_argument("--store", default=argparse.SUPPRESS)
        if command in ("baseline", "model", "scenario", "actual"):
            p.add_argument("--process", required=True)
            p.add_argument("--minutes-per-run", required=True)
        if command in ("baseline", "scenario"):
            p.add_argument("--runs-per-week", required=True)
            p.add_argument("--hourly-rate")
        if command in ("baseline", "actual"):
            p.add_argument("--notes", default="")
        if command == "baseline":
            p.add_argument("--observed-by", default="not supplied")
            p.add_argument("--update", action="store_true")
        if command in ("model", "scenario"):
            p.add_argument("--automation", required=True)
        if command == "scenario":
            p.add_argument("--hypothetical", action="store_true", required=True)
            p.add_argument("--new-minutes-per-run", required=True)
        if command == "report":
            p.add_argument("--format", choices=("md", "json"), default="md")
            p.add_argument("--process")
            p.add_argument("--out")
        if command == "fixtures":
            p.add_argument("--out", required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        store = Store(args.store)
        if args.command == "baseline":
            print(json.dumps(store.baseline(args.process, args.minutes_per_run, args.runs_per_week, args.hourly_rate, args.notes, args.observed_by, args.update), indent=2))
        elif args.command == "model":
            print("\n".join(result_lines(record_model(store, args.process, args.automation, args.minutes_per_run))))
        elif args.command == "scenario":
            entry = scenario(args.process, args.minutes_per_run, args.runs_per_week, args.automation, args.new_minutes_per_run, args.hourly_rate)
            print(entry["header"] + "\n" + "\n".join(result_lines(entry["result"])))
        elif args.command == "actual":
            print(json.dumps(record_actual(store, args.process, args.minutes_per_run, args.notes), indent=2))
        elif args.command == "report":
            output = render(store.read(), args.format, args.process)
            if args.out:
                Path(args.out).write_text(output, encoding="utf-8", newline="\n")
            else:
                print(output, end="")
        else:
            path = generate(args.out, args.store if args.store != ".src-baselines.json" else None)
            print(f"SYNTHETIC fixture written to {path}")
        return 0
    except ROIError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"StoreIOError: {exc}", file=sys.stderr)
        return 1
