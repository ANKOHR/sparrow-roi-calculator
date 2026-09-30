"""Record post-build observations for comparison against each prediction."""
from .model import number
from .store import timestamp


def record_actual(store, process, minutes, notes=""):
    value = number(minutes, "actual minutes per run", True)
    data = store.read()
    store.require(data, process)
    actual = {"minutes_per_run": str(value), "notes": notes, "observed_date": timestamp()}
    data["actuals"][process] = actual
    store.write(data)
    return actual
