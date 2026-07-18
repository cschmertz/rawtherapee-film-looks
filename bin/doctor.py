#!/usr/bin/env python3
"""Check whether this checkout is ready to render presets."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from presetlib import repository_root, validate_repository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-rt-version",
        action="store_true",
        help="check the RawTherapee CLI file without launching it",
    )
    args = parser.parse_args()
    root = repository_root()
    failures = 0

    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        print("error: Python 3.8 or newer is required")
        failures += 1

    for module, display in (("numpy", "numpy"), ("PIL", "Pillow")):
        try:
            loaded = __import__(module)
            version = getattr(loaded, "__version__", "installed")
            print(f"{display}: {version}")
        except ImportError:
            print(f"error: {display} is not installed; run python3 -m pip install -r requirements.txt")
            failures += 1

    override = os.environ.get("RAWTHERAPEE_CLI")
    cli = Path(override).expanduser() if override else root / "bin" / "rtcli"
    if not cli.is_file() or not os.access(cli, os.X_OK):
        print(f"error: RawTherapee CLI is missing or not executable: {cli}")
        failures += 1
    elif args.skip_rt_version:
        print(f"RawTherapee CLI: {cli}")
    else:
        try:
            result = subprocess.run(
                [str(cli), "-v"], capture_output=True, text=True, check=False
            )
        except OSError as exc:
            print(f"error: could not launch RawTherapee CLI: {exc}")
            failures += 1
        else:
            details = (result.stdout or result.stderr).strip()
            if result.returncode and "RawTherapee, version" not in details:
                print(
                    f"error: RawTherapee CLI exited {result.returncode}: "
                    f"{details or 'no output'}"
                )
                failures += 1
            else:
                version_line = next(
                    (
                        line.strip()
                        for line in details.splitlines()
                        if "RawTherapee, version" in line
                    ),
                    details or str(cli),
                )
                print(f"RawTherapee CLI: {version_line}")
                match = re.search(r"version\s+(\d+)\.(\d+)", version_line)
                if not match:
                    print("error: could not determine the RawTherapee version")
                    failures += 1
                elif tuple(map(int, match.groups())) < (5, 12):
                    print("error: RawTherapee 5.12 or newer is required")
                    failures += 1

    errors, warnings = validate_repository(root)
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
        failures += 1

    if failures:
        print(f"doctor found {failures} blocking problem(s)")
        return 1
    print("doctor passed: this checkout is ready to render")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
