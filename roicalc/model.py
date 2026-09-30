"""Shared Decimal arithmetic; monthly means weekly times 52/12."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from .errors import ValidationError


def number(value, name, allow_zero=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{name} must be a finite number") from None
    if not result.is_finite() or result < 0 or (result == 0 and not allow_zero):
        raise ValidationError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return result


def name(value, field="process"):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be non-empty")
    return value


def compute(baseline, automation, minutes):
    name(automation, "automation")
    new = number(minutes, "new minutes per run", True)
    old = number(baseline["minutes_per_run"], "minutes per run")
    runs = number(baseline["runs_per_week"], "runs per week")
    with localcontext() as ctx:
        ctx.prec = 50
        saved = old - new
        weekly = saved * runs
        periods = {"weekly": weekly, "monthly": weekly * Decimal(52) / Decimal(12), "yearly": weekly * 52}
        result = {"process": baseline["process"], "automation": automation, "new_minutes_per_run": str(new), "saved_minutes_per_run": str(saved), "time": {key: {"minutes": str(value), "hours": str(value / 60)} for key, value in periods.items()}}
        if baseline.get("hourly_rate") is not None:
            rate = number(baseline["hourly_rate"], "hourly rate")
            result["money"] = {key: format((value / 60 * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f") for key, value in periods.items()}
            result["currency"] = "GBP"
        else:
            result["note"] = "no hourly rate recorded; time savings only"
        if saved <= 0:
            result["flag"] = "automation not faster than manual"
        return result


def record_model(store, process, automation, minutes):
    data = store.read()
    baseline = store.require(data, process)
    result = compute(baseline, automation, minutes)
    data["models"].append({"baseline": dict(baseline), "result": result})
    store.write(data)
    return result
