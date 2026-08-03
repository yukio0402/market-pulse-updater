#!/usr/bin/env python3
"""Reject future dates and recent weekend observations in market snapshots."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


BOND_COLUMNS: tuple[str, ...] = (
    "US10Y",
    "JP10Y",
    "GB10Y",
    "DE10Y",
    "CH10Y",
    "AU10Y",
    "KR10Y",
)


def _numeric(raw: str | None) -> bool:
    if raw is None or not raw.strip():
        return False
    try:
        return math.isfinite(float(raw))
    except ValueError:
        return False


def snapshot_calendar_errors(
    path: Path,
    *,
    today_jst: date,
    weekend_tail_days: int = 35,
) -> tuple[list[str], date, dict[str, date]]:
    if weekend_tail_days < 1:
        raise ValueError("weekend_tail_days must be positive")

    dated_rows: list[tuple[date, dict[str, str]]] = []
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        missing = [column for column in BOND_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"market snapshot is missing bond columns: {', '.join(missing)}")
        for row in reader:
            raw = (row.get("Date") or "").strip()
            if not raw:
                continue
            parsed = date.fromisoformat(raw)
            dated_rows.append((parsed, row))
    if not dated_rows:
        raise ValueError("market snapshot has no valid Date rows")

    latest = max(parsed for parsed, _ in dated_rows)
    errors: list[str] = []
    if latest > today_jst:
        errors.append(
            f"snapshot latestDate={latest} is later than JST date={today_jst}"
        )
    if latest.weekday() >= 5:
        errors.append(
            f"snapshot latestDate={latest} is a weekend; refusing to publish"
        )

    latest_bond_dates: dict[str, date] = {}
    for column in BOND_COLUMNS:
        observations = [
            parsed
            for parsed, row in dated_rows
            if _numeric(row.get(column))
        ]
        if not observations:
            errors.append(f"{column} has no numeric observations")
            continue
        latest_bond = max(observations)
        latest_bond_dates[column] = latest_bond
        if latest_bond > today_jst:
            errors.append(
                f"{column} latest observation {latest_bond} is later than JST date={today_jst}"
            )
        if latest_bond.weekday() >= 5:
            errors.append(
                f"{column} latest observation {latest_bond} is a weekend"
            )

    cutoff = latest - timedelta(days=weekend_tail_days - 1)
    weekend_hits: list[str] = []
    for parsed, row in dated_rows:
        if parsed < cutoff or parsed.weekday() < 5:
            continue
        populated = [column for column in BOND_COLUMNS if _numeric(row.get(column))]
        if populated:
            weekend_hits.append(f"{parsed}:{','.join(populated)}")
    if weekend_hits:
        preview = "; ".join(weekend_hits[:4])
        suffix = "" if len(weekend_hits) <= 4 else f"; +{len(weekend_hits) - 4} more"
        errors.append(
            f"recent weekend bond observations found ({preview}{suffix})"
        )

    return errors, latest, latest_bond_dates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--weekend-tail-days", type=int, default=35)
    args = parser.parse_args()

    today_jst = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    errors, latest, bond_dates = snapshot_calendar_errors(
        args.csv_path,
        today_jst=today_jst,
        weekend_tail_days=args.weekend_tail_days,
    )
    if errors:
        raise SystemExit("\n".join(errors))

    bond_text = ", ".join(
        f"{column}={bond_dates[column]}"
        for column in BOND_COLUMNS
        if column in bond_dates
    )
    print(
        f"snapshot calendar validation passed; latestDate={latest}; "
        f"bondLatest={bond_text}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
