from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.normalize_snapshot_calendar import BOND_COLUMNS, synchronize_market_files
from scripts.validate_snapshot_date import snapshot_calendar_errors


class SnapshotCalendarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        self.market = self.repo / "data/market.csv"
        self.market.parent.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_rows(self, rows: list[dict[str, str]]) -> None:
        fieldnames = ["Date", "SP500", *BOND_COLUMNS]
        with self.market.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_recent_weekend_bonds_are_removed_and_mirrors_match(self) -> None:
        self.write_rows(
            [
                {"Date": "2026-07-31", **{column: "1.0" for column in BOND_COLUMNS}},
                {"Date": "2026-08-01", **{column: "1.1" for column in BOND_COLUMNS}},
                {"Date": "2026-08-02", **{column: "1.2" for column in BOND_COLUMNS}},
                {"Date": "2026-08-03", "SP500": "7000"},
            ]
        )

        cleared, dates = synchronize_market_files(self.repo, tail_days=35)

        self.assertEqual(cleared, 14)
        self.assertEqual(dates, [date(2026, 8, 1), date(2026, 8, 2)])
        canonical = self.market.read_bytes()
        self.assertEqual(canonical, (self.repo / "webapp/data/market.csv").read_bytes())
        self.assertEqual(canonical, (self.repo / "webapp/public/market.csv").read_bytes())
        self.assertNotIn(b"2026-08-01", canonical)
        self.assertNotIn(b"2026-08-02", canonical)

        errors, latest, bond_dates = snapshot_calendar_errors(
            self.market,
            today_jst=date(2026, 8, 3),
        )
        self.assertEqual(errors, [])
        self.assertEqual(latest, date(2026, 8, 3))
        self.assertEqual(set(bond_dates.values()), {date(2026, 7, 31)})

    def test_empty_recent_weekend_rows_are_removed(self) -> None:
        self.write_rows(
            [
                {"Date": "2026-07-04", **{column: "0.8" for column in BOND_COLUMNS}},
                {"Date": "2026-07-05", **{column: "0.9" for column in BOND_COLUMNS}},
                {
                    "Date": "2026-08-07",
                    "SP500": "7000",
                    **{column: "1.0" for column in BOND_COLUMNS},
                },
                {"Date": "2026-08-08"},
                {"Date": "2026-08-09"},
            ]
        )

        cleared, dates = synchronize_market_files(self.repo, tail_days=35)

        self.assertEqual(cleared, 14)
        self.assertEqual(
            dates,
            [
                date(2026, 7, 4),
                date(2026, 7, 5),
                date(2026, 8, 8),
                date(2026, 8, 9),
            ],
        )
        with self.market.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual([row["Date"] for row in rows], ["2026-08-07"])

        errors, latest, bond_dates = snapshot_calendar_errors(
            self.market,
            today_jst=date(2026, 8, 9),
        )
        self.assertEqual(errors, [])
        self.assertEqual(latest, date(2026, 8, 7))
        self.assertEqual(set(bond_dates.values()), {date(2026, 8, 7)})

    def test_recent_weekend_market_values_are_removed(self) -> None:
        self.write_rows(
            [
                {
                    "Date": "2026-07-11",
                    **{column: "0.9" for column in BOND_COLUMNS},
                },
                {
                    "Date": "2026-08-14",
                    "SP500": "7000",
                    **{column: "1.0" for column in BOND_COLUMNS},
                },
                {
                    "Date": "2026-08-15",
                    "SP500": "7010",
                    **{column: "1.1" for column in BOND_COLUMNS},
                },
            ]
        )

        cleared, dates = synchronize_market_files(self.repo, tail_days=35)

        self.assertEqual(cleared, 14)
        self.assertEqual(dates, [date(2026, 7, 11), date(2026, 8, 15)])
        with self.market.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual([row["Date"] for row in rows], ["2026-08-14"])
        self.assertEqual(rows[0]["SP500"], "7000")

        errors, latest, bond_dates = snapshot_calendar_errors(
            self.market,
            today_jst=date(2026, 8, 16),
        )
        self.assertEqual(errors, [])
        self.assertEqual(latest, date(2026, 8, 14))
        self.assertEqual(set(bond_dates.values()), {date(2026, 8, 14)})

    def test_recent_weekend_bonds_fail_validation(self) -> None:
        self.write_rows(
            [
                {"Date": "2026-07-31", **{column: "1.0" for column in BOND_COLUMNS}},
                {"Date": "2026-08-02", **{column: "1.2" for column in BOND_COLUMNS}},
                {"Date": "2026-08-03", "SP500": "7000"},
            ]
        )

        errors, _, _ = snapshot_calendar_errors(
            self.market,
            today_jst=date(2026, 8, 3),
        )

        self.assertTrue(any("latest observation 2026-08-02 is a weekend" in item for item in errors))
        self.assertTrue(any("recent weekend bond observations" in item for item in errors))

    def test_future_market_date_fails_validation(self) -> None:
        self.write_rows(
            [
                {"Date": "2026-08-03", **{column: "1.0" for column in BOND_COLUMNS}},
                {"Date": "2026-08-04", "SP500": "7000"},
            ]
        )

        errors, _, _ = snapshot_calendar_errors(
            self.market,
            today_jst=date(2026, 8, 3),
        )

        self.assertIn(
            "snapshot latestDate=2026-08-04 is later than JST date=2026-08-03",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
