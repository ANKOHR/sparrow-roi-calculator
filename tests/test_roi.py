import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
import pytest
from roicalc.store import Store
from roicalc.model import record_model, compute
from roicalc.errors import BaselineMissingError, DuplicateBaselineError, ValidationError, StoreCorruptError, StoreIOError
from roicalc.actuals import record_actual
from roicalc.fixtures import generate
from roicalc.report import render


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path / "store.json")
    result.baseline("invoice data entry", "45", "5", "30", "measured Tuesday", "Henry Williams")
    return result


def cli(*args):
    return subprocess.run([sys.executable, "-m", "roicalc", *map(str, args)], capture_output=True, text=True)


def test_baseline_records_measured_values(store):
    b = store.read()["baselines"]["invoice data entry"]
    assert b["minutes_per_run"] == "45" and b["runs_per_week"] == "5"
    assert b["hourly_rate"] == "30" and b["observed_by"] == "Henry Williams"
    assert b["notes"] == "measured Tuesday" and b["observed_date"].endswith("+00:00")


def test_model_hand_computed_savings(store):
    r = record_model(store, "invoice data entry", "import", "5")
    assert Decimal(r["time"]["weekly"]["minutes"]) == Decimal(200)
    assert Decimal(r["time"]["monthly"]["minutes"]).quantize(Decimal(".01")) == Decimal("866.67")
    assert r["money"] == {"weekly": "100.00", "monthly": "433.33", "yearly": "5200.00"}


def test_model_without_baseline_errors(store, tmp_path):
    before = store.path.read_bytes()
    with pytest.raises(BaselineMissingError):
        record_model(store, "missing", "import", "5")
    result = cli("model", "--store", store.path, "--process", "missing", "--automation", "import", "--minutes-per-run", "5")
    assert result.returncode != 0 and "BaselineMissingError" in result.stderr
    assert "record one with src baseline" in result.stderr
    assert store.path.read_bytes() == before
    absent = Store(tmp_path / "absent.json")
    with pytest.raises(BaselineMissingError):
        record_model(absent, "missing", "import", "5")
    assert not absent.path.exists()


def test_hypothetical_labelled_and_store_untouched(store):
    before = store.path.read_bytes()
    args = ["scenario", "--store", store.path, "--process", "new", "--minutes-per-run", "45", "--runs-per-week", "5", "--automation", "portal", "--new-minutes-per-run", "5"]
    result = cli(*args, "--hypothetical")
    assert result.returncode == 0 and result.stdout.startswith("HYPOTHETICAL SCENARIO - NOT BASED ON MEASURED DATA")
    assert store.path.read_bytes() == before
    assert "--hypothetical" in cli(*args).stderr
    store.path.write_text("garbage")
    assert cli(*args, "--hypothetical").returncode == 0


def test_money_omitted_when_no_hourly_rate(store):
    store.baseline("filing", "20", "2")
    r = record_model(store, "filing", "script", "5")
    assert "money" not in r and "hourly_rate" not in r
    report = render(store.read(), process="filing")
    assert "Money (GBP)" not in report
    assert "no hourly rate recorded; time savings only" in report


@pytest.mark.parametrize("minutes,expected", [("50", "-25"), ("45", "0")])
def test_negative_savings_reported_honestly(store, minutes, expected):
    r = record_model(store, "invoice data entry", "slow", minutes)
    assert r["time"]["weekly"]["minutes"] == expected
    assert "automation not faster than manual" in render(store.read())


@pytest.mark.parametrize("minutes,runs,rate", [("0", "5", None), ("-1", "5", None), ("1", "0", None), ("1", "-2", None), ("1", "1", "0"), ("NaN", "1", None), ("Infinity", "1", None), ("abc", "1", None)])
def test_reject_non_positive_minutes_and_runs(tmp_path, minutes, runs, rate):
    s = Store(tmp_path / "bad.json")
    with pytest.raises(ValidationError):
        s.baseline("process", minutes, runs, rate)
    assert not s.path.exists()


def test_duplicate_baseline_requires_update_flag(store):
    with pytest.raises(DuplicateBaselineError):
        store.baseline("invoice data entry", "10", "2")
    b = store.baseline("invoice data entry", "10", "2", update=True)
    assert b["minutes_per_run"] == "10" and "replaced at" in b["replacement_note"]


def test_decimal_rounding(store):
    b = dict(store.read()["baselines"]["invoice data entry"], minutes_per_run="60", runs_per_week="1", hourly_rate="2.675")
    r = compute(b, "instant", "0")
    assert r["money"]["weekly"] == "2.68"
    assert all(len(v.split(".")[1]) == 2 for v in r["money"].values())


def test_actuals_predicted_vs_actual(store):
    record_model(store, "invoice data entry", "import", "5")
    record_actual(store, "invoice data entry", "6", "one month later")
    text = render(store.read())
    assert "Predicted vs actual" in text and "200.0 | 195.0" in text
    assert "100.00 | 97.50" in text and "one month later" in text


@pytest.mark.parametrize("fmt", ["md", "json"])
def test_determinism(store, fmt):
    record_model(store, "invoice data entry", "import", "5")
    assert render(store.read(), fmt) == render(store.read(), fmt)


def test_fixture_determinism(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a)
    generate(b)
    for file in ("baselines.json", "roi.md", "roi.json"):
        assert (a / file).read_bytes() == (b / file).read_bytes()
    data = Store(a / "baselines.json").read()
    assert data["synthetic"] and "HYPOTHETICAL" in (a / "roi.md").read_text()


def test_case_exact_match(store):
    with pytest.raises(BaselineMissingError):
        record_model(store, "Invoice Data Entry", "import", "5")


@pytest.mark.parametrize("content", ["garbage", "{}", '{"version":1}', '[]'])
def test_corrupt_store_untouched(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(StoreCorruptError):
        Store(path).read()
    r = cli("report", "--store", path)
    assert r.returncode == 1 and "StoreCorruptError" in r.stderr and "Traceback" not in r.stderr
    assert path.read_text() == content


def test_two_models_preserved(store):
    record_model(store, "invoice data entry", "first", "5")
    record_model(store, "invoice data entry", "second", "10")
    store.baseline("invoice data entry", "60", "1", update=True)
    data = store.read()
    assert len(data["models"]) == 2
    assert all(x["baseline"]["minutes_per_run"] == "45" for x in data["models"])
    assert "first" in render(data) and "second" in render(data)


def test_atomic_failure_preserves_original(store, monkeypatch):
    import roicalc.store as module
    before = store.path.read_bytes()
    def fail(*args):
        raise OSError("simulated rename failure")
    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(StoreIOError):
        store.baseline("new", "1", "1")
    assert store.path.read_bytes() == before
    assert list(store.path.parent.iterdir()) == [store.path]


def test_cli_smoke(tmp_path):
    path = tmp_path / "demo" / "baselines.json"
    commands = [
        ["fixtures", "--out", path.parent, "--store", path],
        ["baseline", "--store", path, "--process", "extra", "--minutes-per-run", "45", "--runs-per-week", "5", "--hourly-rate", "30", "--observed-by", "Henry"],
        ["model", "--store", path, "--process", "extra", "--automation", "import", "--minutes-per-run", "5"],
        ["scenario", "--hypothetical", "--process", "idea", "--minutes-per-run", "45", "--runs-per-week", "5", "--automation", "form", "--new-minutes-per-run", "5"],
        ["actual", "--store", path, "--process", "extra", "--minutes-per-run", "6"],
        ["report", "--store", path, "--format", "md", "--out", tmp_path / "report.md"],
    ]
    for command in commands:
        result = cli(*command)
        assert result.returncode == 0, result.stderr
    report = (tmp_path / "report.md").read_text()
    assert "100.00" in report and "433.33" in report and "HYPOTHETICAL SCENARIO" in report
    for fmt in ("md", "json"):
        a = cli("report", "--store", path, "--format", fmt)
        b = cli("report", "--store", path, "--format", fmt)
        assert a.stdout == b.stdout
    j = json.loads(cli("report", "--store", path, "--format", "json", "--process", "extra").stdout)
    assert len(j["measured_models"]) == 1 and not j["hypothetical_scenarios"]


def test_empty_process_and_invalid_actual(store):
    with pytest.raises(ValidationError):
        store.baseline(" ", "1", "1")
    with pytest.raises(ValidationError):
        record_actual(store, "invoice data entry", "-1")
    with pytest.raises(BaselineMissingError):
        record_actual(store, "missing", "1")
