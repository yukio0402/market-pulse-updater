#!/usr/bin/env python3
"""Wait until both public deployments expose the exact local market snapshot."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
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


def wait_for(label: str, url: str, expected: dict) -> str:
    last = "no response"
    for attempt in range(1, 46):
        try:
            actual = read_remote(url)
            actual_key = (
                actual.get("status"),
                actual.get("latestDate"),
                actual.get("rows"),
                actual.get("marketSha256"),
            )
            expected_key = (
                expected.get("status"),
                expected.get("latestDate"),
                expected.get("rows"),
                expected.get("marketSha256"),
            )
            if actual_key == expected_key:
                return f"{label}: exact snapshot verified on attempt {attempt}"
            last = (
                f"status={actual.get('status')} date={actual.get('latestDate')} "
                f"rows={actual.get('rows')} hash={actual.get('marketSha256')}"
            )
        except Exception as exc:  # Network/deployment delay is expected while polling.
            last = f"{type(exc).__name__}: {exc}"
        print(f"{label} attempt {attempt}: {last}")
        time.sleep(20)
    raise RuntimeError(f"{label}: production verification timed out ({last})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", required=True, type=Path)
    parser.add_argument("--company-url", required=True)
    parser.add_argument("--family-url", required=True)
    args = parser.parse_args()

    expected = json.loads(args.health.read_text(encoding="utf-8"))
    required = ("status", "latestDate", "rows", "marketSha256")
    missing = [key for key in required if not expected.get(key)]
    if missing:
        raise SystemExit(f"Local health file lacks verification fields: {missing}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(wait_for, "company", args.company_url, expected),
            executor.submit(wait_for, "family", args.family_url, expected),
        )
        for future in futures:
            print(future.result())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
