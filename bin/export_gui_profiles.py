#!/usr/bin/env python3
"""Export GUI-loadable profiles with CLUT paths resolved for this machine."""

from __future__ import annotations

import argparse
from pathlib import Path

from presetlib import discover_look_names, load_look, materialize_profile, repository_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("looks", nargs="*", help="defaults to every available look")
    args = parser.parse_args()
    root = repository_root()
    destination = args.destination.expanduser().resolve()
    names = args.looks or discover_look_names(root)
    count = 0
    for name in names:
        look = load_look(root, name, require_cluts=True)
        for preset in look.presets.values():
            target = destination / name / preset.path.name
            materialize_profile(preset, root, target)
            count += 1
            print(target)
    print(f"exported {count} profile(s) to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
