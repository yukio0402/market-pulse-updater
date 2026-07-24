#!/usr/bin/env python3
"""Copy one validated market snapshot into the family repository."""

from __future__ import annotations

import hashlib
import argparse
import shutil
from pathlib import Path


SNAPSHOT_FILES = (
    "data/market.csv",
    "data/analyst_targets.csv",
    "webapp/public/market.csv",
    "webapp/public/analyst_targets.csv",
    "webapp/public/health.json",
    "webapp/public/trillion_static.json",
    "webapp/data/market.csv",
    "webapp/data/analyst_targets.csv",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_repo", type=Path)
    parser.add_argument("target_repo", type=Path)
    parser.add_argument("--files", nargs="+")
    args = parser.parse_args()
    source_root = args.source_repo.resolve()
    target_root = args.target_repo.resolve()
    files = tuple(args.files) if args.files else SNAPSHOT_FILES

    for relative in files:
        source = source_root / relative
        target = target_root / relative
        if not source.is_file():
            raise SystemExit(f"Snapshot source is missing: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise SystemExit(f"Snapshot copy verification failed: {relative}")

    print(f"Synchronized and verified {len(files)} snapshot files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
