#!/usr/bin/env python3
"""Reliable film-look pipeline implementation used by process.sh."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from contact_sheet import build_contact_sheets
from film_fx import process_image
from presetlib import PresetError, load_look, materialize_profile, repository_root
from web_export import export_image


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Nikon NEFs through a film look and apply halation/grain.",
        usage="%(prog)s <photo-folder> [look] [NN|all] [--web] [--random-grain]",
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("selection", nargs="*", help="look name and/or two-digit variant")
    parser.add_argument("--web", action="store_true", help="also create 2048px web exports")
    parser.add_argument(
        "--random-grain",
        action="store_true",
        help="randomize grain instead of deriving a repeatable seed from the source",
    )
    args = parser.parse_args(argv)

    args.look = "boardwalk"
    args.which = "all"
    seen_look = False
    seen_variant = False
    for token in args.selection:
        if token == "all" or (len(token) == 2 and token.isdigit()):
            if seen_variant:
                parser.error("variant was specified more than once")
            args.which = token
            seen_variant = True
        else:
            if seen_look:
                parser.error("look was specified more than once")
            args.look = token
            seen_look = True
    return args


def source_digest(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def render_seed(digest: bytes, look: str, variant: str) -> int:
    value = hashlib.sha256(digest + b"\0" + look.encode() + b"\0" + variant.encode()).digest()
    return int.from_bytes(value[:8], "big")


def rawtherapee_cli(root: Path) -> Path:
    override = os.environ.get("RAWTHERAPEE_CLI")
    path = Path(override).expanduser() if override else root / "bin" / "rtcli"
    if not path.is_file():
        raise PresetError(
            f"RawTherapee CLI not found at {path}; run 'python3 bin/doctor.py'"
        )
    if not os.access(path, os.X_OK):
        raise PresetError(f"RawTherapee CLI is not executable: {path}")
    return path


def run_rawtherapee(cli: Path, source: Path, profile: Path, destination: Path) -> None:
    command = [
        str(cli),
        "-Y",
        "-o",
        str(destination),
        "-tz",
        "-b8",
        "-p",
        str(profile),
        "-c",
        str(source),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = "\n".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())
        suffix = f"\n{details}" if details else " (no diagnostic output)"
        raise RuntimeError(
            f"RawTherapee failed for {source.name} with {profile.name} "
            f"(exit {result.returncode}){suffix}"
        )
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError(
            f"RawTherapee reported success but did not create {destination}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repository_root()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        raise PresetError(f"photo folder does not exist or is not a directory: {folder}")

    sources = sorted(
        (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".nef"),
        key=lambda path: path.name.casefold(),
    )
    if not sources:
        raise PresetError(f"no .NEF files found in {folder}")

    look = load_look(root, args.look, require_cluts=False)
    if args.which != "all" and args.which not in look.presets:
        choices = ", ".join(sorted(look.presets))
        raise PresetError(
            f"look {look.name!r} has no variant {args.which}; choose: {choices} or all"
        )
    variants = (
        sorted(look.presets)
        if args.which == "all"
        else [args.which]
    )
    missing_cluts = [
        root / "cluts" / look.presets[number].clut_name
        for number in variants
        if look.presets[number].clut_name
        and not (root / "cluts" / look.presets[number].clut_name).is_file()
    ]
    if missing_cluts:
        formatted = "\n".join(f"  - {path}" for path in missing_cluts)
        raise PresetError(f"selected variant(s) require missing CLUTs:\n{formatted}")

    cli = rawtherapee_cli(root)
    output = folder / "renders" / look.name
    output.mkdir(parents=True, exist_ok=True)
    contact_dir = output / "contact"
    for source in sources:
        stale_sheet = contact_dir / f"{source.stem}_contact.jpg"
        if stale_sheet.exists():
            stale_sheet.unlink()
            print(f"invalidated contact sheet before rendering: {stale_sheet}")
    generated: list[Path] = []

    with tempfile.TemporaryDirectory(prefix=".pipeline-", dir=output) as temp_name:
        temp_dir = Path(temp_name)
        profiles: dict[str, Path] = {}
        for number in variants:
            preset = look.presets[number]
            profiles[number] = materialize_profile(
                preset, root, temp_dir / "profiles" / preset.path.name
            )

        for source in sources:
            digest = None if args.random_grain else source_digest(source)
            for number in variants:
                preset = look.presets[number]
                dose = look.effects[number]
                intermediate = temp_dir / f"{source.stem}_{number}.tif"
                destination = output / f"{source.stem}_{number}.jpg"
                print(f"rendering {source.name} -> {look.name} {number} {preset.label}")
                run_rawtherapee(cli, source, profiles[number], intermediate)
                seed = None if digest is None else render_seed(digest, look.name, number)
                process_image(
                    intermediate,
                    destination,
                    grain_strength=dose.grain_strength,
                    grain_size=dose.grain_size,
                    halation=dose.halation,
                    seed=seed,
                )
                generated.append(destination)

                web_path = output / "web" / destination.name
                if args.web:
                    web_path.parent.mkdir(parents=True, exist_ok=True)
                    export_image(destination, web_path)
                elif web_path.exists():
                    web_path.unlink()
                    print(f"removed stale web export: {web_path}")
            print(f"{source.stem} done")

    sheets = build_contact_sheets(
        output,
        look.path,
        renders=generated,
        replace_bases={source.stem for source in sources},
    )
    print(
        f"complete: {len(sources)} source(s), {len(generated)} render(s), "
        f"{len(sheets)} contact sheet(s) -> {output}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PresetError, RuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
