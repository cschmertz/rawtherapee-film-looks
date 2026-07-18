#!/usr/bin/env python3
"""Resize for web/social and sharpen after resizing."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter


def _metadata(image: Image.Image) -> tuple[bytes, bytes | None]:
    exif = image.info.get("exif", b"")
    if not exif:
        try:
            values = image.getexif()
            exif = values.tobytes() if values else b""
        except (AttributeError, OSError, ValueError):
            exif = b""
    return exif, image.info.get("icc_profile")


def export_image(source: str | Path, destination: str | Path, edge: int = 2048) -> Path:
    if edge <= 0:
        raise ValueError("long edge must be positive")
    source_path = Path(source)
    destination_path = Path(destination)
    with Image.open(source_path) as opened:
        exif, icc_profile = _metadata(opened)
        image = opened.convert("RGB")
    image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination_path.stem}.", suffix=".jpg", dir=destination_path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    options: dict[str, object] = {
        "quality": 88,
        "subsampling": 1,
        "optimize": True,
    }
    if exif:
        options["exif"] = exif
    if icc_profile:
        options["icc_profile"] = icc_profile
    try:
        image.save(temporary, format="JPEG", **options)
        temporary.chmod(0o644)
        os.replace(temporary, destination_path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"{destination_path}: {image.size[0]}x{image.size[1]}")
    return destination_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("long_edge", type=int, nargs="?", default=2048)
    args = parser.parse_args()
    export_image(args.source, args.destination, args.long_edge)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
