#!/usr/bin/env python3
"""Wait until one public deployment exposes the exact local market snapshot."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


def read_remote(url: str) -> dict:
    response = requests.get(
        url,
        params={"verify": time.time_ns()},
        headers={
            "Cache-Control": "no-cache",
            "User-Agent": "market-pulse-updater",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--health", required=True, type=Path)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    expected = json.loads(args.health.read_text(encoding="utf-8"))
    required = ("status", "latestDate", "rows", "marketSha256")
    missing = [key for key in required if not expected.get(key)]
    if missing:
        raise SystemExit(f"Local health file lacks verification fields: {missing}")

    expected_key = tuple(expected.get(key) for key in required)
    last = "no response"
    for attempt in range(1, 46):
        try:
            actual = read_remote(args.url)
            actual_key = tuple(actual.get(key) for key in required)
            if actual_key == expected_key:
                print(f"{args.label}: exact snapshot verified on attempt {attempt}")
                return 0
            last = (
                f"status={actual.get('status')} date={actual.get('latestDate')} "
                f"rows={actual.get('rows')} hash={actual.get('marketSha256')}"
            )
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        print(f"{args.label} attempt {attempt}: {last}")
        time.sleep(20)

    raise RuntimeError(
        f"{args.label}: production verification timed out ({last})"
    )


if __name__ == "__main__":
    raise SystemExit(main())
