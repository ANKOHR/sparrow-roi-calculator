"""Atomic JSON storage with provenance and exact process matching."""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .errors import BaselineMissingError, DuplicateBaselineError, StoreCorruptError, StoreIOError, ValidationError
from .model import name, number


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def empty():
    return {"version": 1, "synthetic": False, "baselines": {}, "models": [], "actuals": {}, "hypotheticals": []}


class Store:
    def __init__(self, path=".src-baselines.json"):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            assert data["version"] == 1 and isinstance(data["synthetic"], bool)
            assert isinstance(data["baselines"], dict) and isinstance(data["models"], list)
            assert isinstance(data["actuals"], dict) and isinstance(data["hypotheticals"], list)
            for key, baseline in data["baselines"].items():
                assert key == name(baseline["process"])
                self.validate_baseline(baseline)
            for entry in data["models"]:
                self.validate_baseline(entry["baseline"])
                from .model import compute
                assert entry["result"] == compute(entry["baseline"], entry["result"]["automation"], entry["result"]["new_minutes_per_run"])
            for key, actual in data["actuals"].items():
                assert key in data["baselines"]
                number(actual["minutes_per_run"], "actual minutes", True)
                assert isinstance(actual["notes"], str) and isinstance(actual["observed_date"], str)
            for entry in data["hypotheticals"]:
                assert entry["header"] == "HYPOTHETICAL SCENARIO - NOT BASED ON MEASURED DATA"
                self.validate_baseline(entry["baseline"])
                from .model import compute
                assert entry["result"] == compute(entry["baseline"], entry["result"]["automation"], entry["result"]["new_minutes_per_run"])
            return data
        except OSError as exc:
            raise StoreIOError(f"cannot read store '{self.path}': {exc}") from None
        except (ValueError, KeyError, TypeError, AssertionError, ValidationError) as exc:
            raise StoreCorruptError(f"invalid store '{self.path}': malformed JSON or invalid schema ({exc})") from None

    @staticmethod
    def validate_baseline(baseline):
        name(baseline["process"])
        number(baseline["minutes_per_run"], "minutes per run")
        number(baseline["runs_per_week"], "runs per week")
        if baseline["hourly_rate"] is not None:
            number(baseline["hourly_rate"], "hourly rate")
        for field in ("observed_by", "observed_date", "notes"):
            assert isinstance(baseline[field], str)

    def write(self, data):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False, newline="\n") as stream:
                temporary = stream.name
                json.dump(data, stream, indent=2, sort_keys=True, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise StoreIOError(f"cannot write store '{self.path}': {exc}") from None
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def require(data, process):
        if process not in data["baselines"]:
            raise BaselineMissingError(f"no measured baseline for process '{process}'; record one with src baseline")
        return data["baselines"][process]

    def baseline(self, process, minutes, runs, hourly_rate=None, notes="", observed_by="not supplied", update=False):
        name(process)
        baseline = {"process": process, "minutes_per_run": str(number(minutes, "minutes per run")), "runs_per_week": str(number(runs, "runs per week")), "hourly_rate": None if hourly_rate is None else str(number(hourly_rate, "hourly rate")), "notes": notes, "observed_by": observed_by, "observed_date": timestamp()}
        data = self.read()
        if process in data["baselines"]:
            if not update:
                raise DuplicateBaselineError(f"baseline for '{process}' already exists; use --update")
            baseline["replacement_note"] = f"replaced at {baseline['observed_date']}; previous observed date {data['baselines'][process]['observed_date']}"
        data["baselines"][process] = baseline
        self.write(data)
        return baseline
