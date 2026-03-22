"""
Money helpers: store in integer cents, display as decimal.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def to_cents(value: float | int | str | Decimal | None) -> int:
    if value is None:
        return 0
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def from_cents(cents: int | None) -> float:
    if cents is None:
        return 0.0
    return float(Decimal(cents) / 100)
