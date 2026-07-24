#!/usr/bin/env python3
"""Verify exact static JSON bytes on both Cloudflare deployments."""

from __future__ import annotations

import argparse
import hashlib
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def asset_url(health_url: str, filename: str) -> str:
    return urllib.parse.urljoin(health_url, filename)


def wait_for(
    label: str,
    health_url: str,
    auth: tuple[str, str],
    expected: dict[str, str],
) -> str:
    last = "no response"
    for attempt in range(1, 31):
        mismatches: list[str] = []
        try:
            for filename, expected_hash in expected.items():
                response = requests.get(
                    asset_url(health_url, filename),
                    params={"verify": time.time_ns()},
                    headers={
                        "Cache-Control": "no-cache",
                        "User-Agent": "market-pulse-updater",
                    },
                    auth=auth,
                    timeout=20,
                )
                response.raise_for_status()
                actual_hash = digest(response.content)
                if actual_hash != expected_hash:
                    mismatches.append(filename)
            if not mismatches:
                return f"{label}: static feeds verified on attempt {attempt}"
            last = f"hash mismatch: {', '.join(mismatches)}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        print(f"{label} attempt {attempt}: {last}")
        time.sleep(20)
    raise RuntimeError(f"{label}: static feed verification timed out ({last})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--company-url", required=True)
    parser.add_argument("--family-url", required=True)
    parser.add_argument("--company-user", required=True)
    parser.add_argument("--company-password", required=True)
    parser.add_argument("--family-user", required=True)
    parser.add_argument("--family-password", required=True)
    parser.add_argument("--files", required=True, nargs="+")
    args = parser.parse_args()

    expected = {}
    for filename in args.files:
        path = args.source / filename
        if not path.is_file():
            raise SystemExit(f"Required static feed is missing: {path}")
        expected[filename] = digest(path.read_bytes())

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(
                wait_for,
                "company",
                args.company_url,
                (args.company_user, args.company_password),
                expected,
            ),
            executor.submit(
                wait_for,
                "family",
                args.family_url,
                (args.family_user, args.family_password),
                expected,
            ),
        )
        for future in futures:
            print(future.result())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
