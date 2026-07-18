#!/usr/bin/env python3
"""Add halation and deterministic luminance grain with bounded memory use."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


TINT = np.array([1.0, 0.55, 0.25], dtype=np.float32)
NOISE_SCALE = 32.0
TILE_ROWS = 256


def _halation_in_place(rgb: np.ndarray, strength: float) -> None:
    if strength <= 0:
        return
    height, width = rgb.shape[:2]
    values = np.arange(256, dtype=np.float32)
    mask_lut = np.clip((values - 255.0 * 0.72) / (255.0 * 0.28), 0, 1) ** 2
    mask_lut = np.round(mask_lut * 255).astype(np.uint8)
    bright = rgb.max(axis=2)
    mask = mask_lut[bright]
    del bright

    radius = max(6.0, width * 0.004)
    glow_image = Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius))
    glow = np.asarray(glow_image, dtype=np.uint8)
    del mask, glow_image

    for top in range(0, height, TILE_ROWS):
        bottom = min(height, top + TILE_ROWS)
        block = rgb[top:bottom].astype(np.float32)
        dose = glow[top:bottom].astype(np.float32)[..., None] * TINT
        dose *= strength
        np.clip(dose, 0, 255, out=dose)
        block = 255.0 - (255.0 - block) * (255.0 - dose) / 255.0
        rgb[top:bottom] = np.clip(block, 0, 255).astype(np.uint8)


def _grain_map(height: int, width: int, size: float, seed: int | None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    grain_height = max(1, int(height / size))
    grain_width = max(1, int(width / size))
    noise = rng.standard_normal((grain_height, grain_width), dtype=np.float32)
    noise *= NOISE_SCALE
    noise += 128.0
    np.clip(noise, 0, 255, out=noise)
    low_resolution = noise.astype(np.uint8)
    del noise
    if (grain_height, grain_width) == (height, width):
        return low_resolution
    resized = Image.fromarray(low_resolution, mode="L").resize(
        (width, height), Image.Resampling.BILINEAR
    )
    return np.asarray(resized, dtype=np.uint8)


def _grain_in_place(
    rgb: np.ndarray, strength: float, size: float, seed: int | None
) -> None:
    if strength <= 0:
        return
    height, width = rgb.shape[:2]
    noise_map = _grain_map(height, width, size, seed)
    for top in range(0, height, TILE_ROWS):
        bottom = min(height, top + TILE_ROWS)
        block = rgb[top:bottom].astype(np.float32)
        luminance = 0.2126 * block[..., 0]
        luminance += 0.7152 * block[..., 1]
        luminance += 0.0722 * block[..., 2]
        luminance /= 255.0
        weight = 0.15 + 0.85 * (4.0 * luminance * (1.0 - luminance)) ** 0.6
        noise = noise_map[top:bottom].astype(np.float32)
        noise -= 128.0
        noise /= NOISE_SCALE
        block += (noise * weight * strength)[..., None]
        rgb[top:bottom] = np.clip(block, 0, 255).astype(np.uint8)


def add_halation(rgb: np.ndarray, strength: float = 0.55) -> np.ndarray:
    """Return a halated uint8 RGB array without changing the caller's array."""
    result = np.clip(rgb, 0, 255).astype(np.uint8, copy=True)
    _halation_in_place(result, strength)
    return result


def add_grain(
    rgb: np.ndarray, strength: float = 8.0, size: float = 1.6, seed: int | None = None
) -> np.ndarray:
    """Return a grained uint8 RGB array without changing the caller's array."""
    result = np.clip(rgb, 0, 255).astype(np.uint8, copy=True)
    _grain_in_place(result, strength, size, seed)
    return result


def _metadata(image: Image.Image) -> tuple[bytes, bytes | None]:
    exif = image.info.get("exif", b"")
    if not exif:
        try:
            values = image.getexif()
            exif = values.tobytes() if values else b""
        except (AttributeError, OSError, ValueError):
            exif = b""
    return exif, image.info.get("icc_profile")


def _atomic_jpeg_save(
    image: Image.Image,
    destination: Path,
    *,
    exif: bytes = b"",
    icc_profile: bytes | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.", suffix=".jpg", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    options: dict[str, object] = {
        "quality": 92,
        "subsampling": 0,
        "optimize": True,
    }
    if exif:
        options["exif"] = exif
    if icc_profile:
        options["icc_profile"] = icc_profile
    try:
        image.save(temporary, format="JPEG", **options)
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def process_image(
    source: str | Path,
    destination: str | Path,
    *,
    grain_strength: float = 8.0,
    grain_size: float = 1.6,
    halation: float = 0.55,
    seed: int | None = None,
) -> Path:
    source_path = Path(source)
    destination_path = Path(destination)
    if grain_strength < 0:
        raise ValueError("grain strength must be non-negative")
    if grain_size <= 0:
        raise ValueError("grain size must be positive")
    if halation < 0:
        raise ValueError("halation must be non-negative")

    with Image.open(source_path) as image:
        exif, icc_profile = _metadata(image)
        rgb = np.array(image.convert("RGB"), dtype=np.uint8, copy=True)
    _halation_in_place(rgb, halation)
    _grain_in_place(rgb, grain_strength, grain_size, seed)
    finished = Image.fromarray(rgb, mode="RGB")
    _atomic_jpeg_save(
        finished, destination_path, exif=exif, icc_profile=icc_profile
    )
    print(
        f"{destination_path}: grain={grain_strength}/{grain_size} "
        f"halation={halation} seed={'random' if seed is None else seed}"
    )
    return destination_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply warm highlight halation followed by luminance grain."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("grain_strength", type=float, nargs="?", default=8.0)
    parser.add_argument("grain_size", type=float, nargs="?", default=1.6)
    parser.add_argument("halation", type=float, nargs="?", default=0.55)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    process_image(
        args.source,
        args.destination,
        grain_strength=args.grain_strength,
        grain_size=args.grain_size,
        halation=args.halation,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
