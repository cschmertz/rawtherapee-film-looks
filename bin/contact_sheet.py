#!/usr/bin/env python3
"""Build labeled, color-managed contact sheets from a specific render set."""

from __future__ import annotations

import argparse
import io
import os
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageCms, ImageDraw, ImageFont


TILE_H = 900
GUTTER = 12
LABEL_H = 56
RENDER_RE = re.compile(r"^(?P<base>.+)_(?P<number>\d{2})\.jpg$", re.IGNORECASE)
PROFILE_RE = re.compile(r" (?P<number>\d{2}) - (?P<label>.+)\.pp3$")


def _labels(look_dir: Path | None) -> dict[str, str]:
    labels: dict[str, str] = {}
    if look_dir is None:
        return labels
    for path in sorted((look_dir / "rawtherapee").glob("*.pp3")):
        match = PROFILE_RE.search(path.name)
        if match:
            labels[match.group("number")] = match.group("label")
    return labels


def _font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    except OSError:
        return ImageFont.load_default()


def _open_as_srgb(path: Path, srgb_profile: ImageCms.ImageCmsProfile) -> Image.Image:
    with Image.open(path) as source:
        source.load()
        image = source.convert("RGB")
        embedded = source.info.get("icc_profile")
    if not embedded:
        return image
    try:
        input_profile = ImageCms.ImageCmsProfile(io.BytesIO(embedded))
        return ImageCms.profileToProfile(
            image, input_profile, srgb_profile, outputMode="RGB"
        )
    except (ImageCms.PyCMSError, OSError, TypeError, ValueError):
        return image


def _save_sheet(image: Image.Image, destination: Path, icc_profile: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.", suffix=".jpg", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        image.save(
            temporary,
            format="JPEG",
            quality=88,
            subsampling=1,
            optimize=True,
            icc_profile=icc_profile,
        )
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def build_contact_sheets(
    renders_dir: str | Path,
    look_dir: str | Path | None = None,
    *,
    renders: list[Path] | None = None,
    replace_bases: set[str] | None = None,
) -> list[Path]:
    directory = Path(renders_dir)
    labels = _labels(Path(look_dir) if look_dir is not None else None)
    render_paths = (
        sorted(renders)
        if renders is not None
        else sorted(directory.glob("*_[0-9][0-9].jpg"))
    )
    grouped: dict[str, list[tuple[str, Path]]] = {}
    for path in render_paths:
        match = RENDER_RE.match(path.name)
        if match:
            grouped.setdefault(match.group("base"), []).append(
                (match.group("number"), path)
            )

    output_dir = directory / "contact"
    output_dir.mkdir(parents=True, exist_ok=True)
    affected = replace_bases if replace_bases is not None else set(grouped)
    for base in affected:
        if len(grouped.get(base, [])) < 2:
            stale = output_dir / f"{base}_contact.jpg"
            if stale.exists():
                stale.unlink()
                print(f"removed stale contact sheet: {stale}")

    font = _font()
    srgb_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    srgb_bytes = srgb_profile.tobytes()
    outputs: list[Path] = []
    for base in sorted(grouped):
        items = sorted(grouped[base], key=lambda item: item[0])
        if len(items) < 2:
            continue
        tiles: list[tuple[str, Image.Image]] = []
        for number, path in items:
            image = _open_as_srgb(path, srgb_profile)
            image.thumbnail((TILE_H * 4, TILE_H), Image.Resampling.LANCZOS)
            label = f"{number} {labels.get(number, '')}".strip()
            tiles.append((label, image))

        width = sum(tile.size[0] for _, tile in tiles) + GUTTER * (len(tiles) + 1)
        height = TILE_H + LABEL_H + GUTTER * 2
        sheet = Image.new("RGB", (width, height), (18, 18, 18))
        draw = ImageDraw.Draw(sheet)
        x = GUTTER
        for label, tile in tiles:
            y = GUTTER + (TILE_H - tile.size[1]) // 2
            sheet.paste(tile, (x, y))
            draw.text(
                (x + 8, GUTTER + TILE_H + 10),
                label,
                fill=(230, 225, 215),
                font=font,
            )
            x += tile.size[0] + GUTTER
        destination = output_dir / f"{base}_contact.jpg"
        _save_sheet(sheet, destination, srgb_bytes)
        outputs.append(destination)
        print(destination)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("renders_dir", type=Path)
    parser.add_argument("look_dir", type=Path, nargs="?")
    args = parser.parse_args()
    build_contact_sheets(args.renders_dir, args.look_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
