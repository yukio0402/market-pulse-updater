#!/usr/bin/env python3
"""Refresh optional JSON while retaining the last valid payload on failure."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def valid_payload(path: Path, required_key: str) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    value = payload.get(required_key) if isinstance(payload, dict) else None
    return isinstance(value, list) and bool(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--required-key", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    cwd = args.cwd.resolve()
    output = cwd / args.output
    previous = output.read_bytes() if output.is_file() else None
    try:
        result = subprocess.run(
            [sys.executable, str(cwd / args.script)],
            cwd=cwd,
            check=False,
            timeout=args.timeout,
        )
        refreshed = result.returncode == 0 and valid_payload(output, args.required_key)
    except subprocess.TimeoutExpired:
        refreshed = False

    if refreshed:
        print(f"Optional JSON refreshed: {args.output}")
        return 0

    if previous is not None:
        output.write_bytes(previous)
        print(f"Optional JSON retained after refresh failure: {args.output}")
    else:
        output.unlink(missing_ok=True)
        print(f"Optional JSON unavailable: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
