#!/usr/bin/env python3
"""Validate every look, profile, effect dose, and local CLUT reference."""

from __future__ import annotations

import argparse

from presetlib import repository_root, validate_repository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-assets",
        action="store_true",
        help="treat intentionally unbundled CLUTs as errors when absent",
    )
    args = parser.parse_args()
    root = repository_root()
    errors, warnings = validate_repository(root, strict_assets=args.strict_assets)
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    if errors:
        print(f"validation failed: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"validation passed: {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
