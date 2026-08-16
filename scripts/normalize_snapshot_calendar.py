#!/usr/bin/env python3
"""Remove recent weekend rows before a market snapshot is published."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path


BOND_COLUMNS: tuple[str, ...] = (
    "US10Y",
    "JP10Y",
    "GB10Y",
    "DE10Y",
    "CH10Y",
    "AU10Y",
    "KR10Y",
)
MARKET_PATHS: tuple[str, ...] = (
    "data/market.csv",
    "webapp/data/market.csv",
    "webapp/public/market.csv",
)


def normalize_market_csv(path: Path, tail_days: int) -> tuple[int, list[date]]:
    if tail_days < 1:
        raise ValueError("tail_days must be positive")

    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames or "Date" not in fieldnames:
        raise ValueError(f"{path} has no Date column")
    missing = [column for column in BOND_COLUMNS if column not in fieldnames]
    if missing:
        raise ValueError(f"{path} is missing bond columns: {', '.join(missing)}")

    parsed_dates: list[date] = []
    for row in rows:
        raw = (row.get("Date") or "").strip()
        if not raw:
            continue
        parsed_dates.append(date.fromisoformat(raw))
    if not parsed_dates:
        raise ValueError(f"{path} has no valid Date rows")

    # Anchor the cleanup window to the latest date that will remain after all
    # weekend rows are removed. This keeps the normalizer's cutoff identical to
    # the validator's cutoff, including the oldest boundary day.
    business_dates = [parsed for parsed in parsed_dates if parsed.weekday() < 5]
    latest_market = max(business_dates) if business_dates else max(parsed_dates)
    cutoff = latest_market - timedelta(days=tail_days - 1)
    cleared = 0
    cleared_dates: set[date] = set()
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        raw = (row.get("Date") or "").strip()
        if not raw:
            normalized_rows.append(row)
            continue
        parsed = date.fromisoformat(raw)
        if parsed < cutoff or parsed.weekday() < 5:
            normalized_rows.append(row)
            continue
        for column in BOND_COLUMNS:
            if (row.get(column) or "").strip():
                row[column] = ""
                cleared += 1

        # Provider timestamps can place Friday's final quote on Saturday and
        # can also create weekend-only FX or bond rows. A daily market snapshot
        # must remain keyed to exchange business dates, so remove every recent
        # weekend row instead of retaining a partially populated synthetic day.
        cleared_dates.add(parsed)
        continue

    if cleared or len(normalized_rows) != len(rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as target:
            writer = csv.DictWriter(
                target,
                fieldnames=fieldnames,
                lineterminator="\n",
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(normalized_rows)
            temporary = Path(target.name)
        os.replace(temporary, path)

    return cleared, sorted(cleared_dates)


def synchronize_market_files(repo: Path, tail_days: int) -> tuple[int, list[date]]:
    canonical = repo / MARKET_PATHS[0]
    if not canonical.is_file():
        raise ValueError(f"market snapshot is missing: {canonical}")

    cleared, cleared_dates = normalize_market_csv(canonical, tail_days)
    for relative in MARKET_PATHS[1:]:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(canonical, target)
    return cleared, cleared_dates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--tail-days", type=int, default=35)
    args = parser.parse_args()

    cleared, cleared_dates = synchronize_market_files(
        args.repo.resolve(),
        args.tail_days,
    )
    date_text = ", ".join(item.isoformat() for item in cleared_dates) or "none"
    print(
        f"snapshot calendar normalized; cleared={cleared}; "
        f"weekendDates={date_text}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
