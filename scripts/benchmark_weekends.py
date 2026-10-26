"""Blank only SMH/SOXX on weekend Date keys; preserve every other cell and row."""
from __future__ import annotations
from datetime import date

BENCHMARK_COLUMNS = ("SMH", "SOXX")

def is_weekend_date(value: str) -> bool:
    return date.fromisoformat(value).weekday() >= 5

def clear_weekend_benchmark_values(frame):
    """Return a DataFrame copy; callers supply the final ISO Date column.

    This is a calendar-only correction. Weekday prices, adjustment definitions,
    column/row order, date keys and all other columns remain unchanged.
    """
    result = frame.copy()
    columns = [name for name in BENCHMARK_COLUMNS if name in result.columns]
    if not columns:
        return result
    if "Date" not in result.columns:
        raise ValueError("benchmark calendar cleanup requires Date")
    weekend = result["Date"].map(is_weekend_date)
    for column in columns:
        result.loc[weekend, column] = float("nan")
    return result
