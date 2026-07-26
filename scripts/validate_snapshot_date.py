#!/usr/bin/env python3
"""Reject snapshots whose final market row is a weekend or future date."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def latest_date(path: Path) -> date:
    latest: date | None = None
    with path.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            raw = (row.get("Date") or "").strip()
            if not raw:
                continue
            parsed = date.fromisoformat(raw)
            if latest is None or parsed > latest:
                latest = parsed
    if latest is None:
        raise ValueError("market snapshot has no valid Date rows")
    return latest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    latest = latest_date(args.csv_path)
    today_jst = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    if latest > today_jst:
        raise SystemExit(
            f"snapshot latestDate={latest} is later than JST date={today_jst}"
        )
    if latest.weekday() >= 5:
        raise SystemExit(
            f"snapshot latestDate={latest} is a weekend; refusing to publish"
        )

    print(f"snapshot calendar validation passed; latestDate={latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
