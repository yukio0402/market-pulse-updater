#!/usr/bin/env python3
"""Commit and push a fixed generated-file set as one fail-closed snapshot."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(repo: Path, *args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--message", required=True)
    parser.add_argument("--files", required=True, nargs="+")
    args = parser.parse_args()

    repo = args.repo.resolve()
    allowed = {Path(item).as_posix() for item in args.files}
    missing = [item for item in allowed if not (repo / item).is_file()]
    if missing:
        raise SystemExit(f"Required generated files are missing: {missing}")

    changed = set(
        filter(
            None,
            run(repo, "diff", "--name-only", "HEAD", capture=True).splitlines(),
        )
    )
    unexpected = sorted(changed - allowed)
    if unexpected:
        raise SystemExit(f"Unexpected tracked changes; refusing to publish: {unexpected}")

    run(repo, "add", "--", *sorted(allowed))
    if subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--quiet"],
        check=False,
    ).returncode == 0:
        print(f"{repo.name}: no generated changes")
        return 0

    run(repo, "fetch", "origin", "main")
    local_head = run(repo, "rev-parse", "HEAD", capture=True)
    remote_head = run(repo, "rev-parse", "origin/main", capture=True)
    if local_head != remote_head:
        raise SystemExit(
            f"{repo.name}: origin/main moved during generation; "
            "refusing to publish a snapshot built from older code"
        )

    run(repo, "config", "user.name", "github-actions[bot]")
    run(
        repo,
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    run(repo, "commit", "-m", args.message)
    run(repo, "push", "origin", "HEAD:main")
    print(f"{repo.name}: published {run(repo, 'rev-parse', 'HEAD', capture=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
