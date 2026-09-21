"""Shared numerical and UTC validation."""

import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from numbers import Integral

from .models import TradeError


def number(value, name, *, positive=True):
    if isinstance(value, (bool, str)):
        raise TradeError(f"{name} must be a finite number")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TradeError(f"{name} must be a finite number") from exc
    if not math.isfinite(value) or (value <= 0 if positive else value < 0):
        raise TradeError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return value


def integer(value, name, *, minimum=0):
    if isinstance(value, Integral) and not isinstance(value, bool):
        if value < minimum:
            raise TradeError(f"{name} must be an integer >= {minimum}")
        return int(value)
    result = number(value, name, positive=False)
    if not result.is_integer() or result < minimum:
        raise TradeError(f"{name} must be an integer >= {minimum}")
    return int(result)


def quantize(value, step, *, floor=False):
    step = Decimal(str(number(step, "step")))
    units = (Decimal(str(value)) / step).to_integral_value(
        rounding=ROUND_FLOOR if floor else ROUND_HALF_UP
    )
    return float(units * step)


def utc(value, name="datetime"):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TradeError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def date_range(start, end):
    start, end = utc(start, "start"), utc(end, "end")
    if start > end:
        raise TradeError("start must not be after end")
    return start, end
