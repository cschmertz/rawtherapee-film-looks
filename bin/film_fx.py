#!/usr/bin/env python3
"""Film effects: halation glow + grain. Replaces add_grain.py.

Usage: film_fx.py in.jpg out.jpg [grain_strength] [grain_size] [halation]
Halation is applied first (warm glow bleeding from bright highlights),
then grain on top — matching the physical order in real film emulsion.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

def add_halation(rgb, strength=0.55):
    h, w = rgb.shape[:2]
    # mask on brightest channel, not luma — red neon must bloom like film
    bright = rgb.max(axis=2) / 255.0
    mask = np.clip((bright - 0.72) / 0.28, 0, 1) ** 2
    radius = max(6.0, w * 0.004)
    glow = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0
    tint = np.array([1.0, 0.55, 0.25], dtype=np.float32)  # warm red-orange
    g = glow[..., None] * tint[None, None, :] * (255.0 * strength)
    return 255.0 - (255.0 - rgb) * (255.0 - np.clip(g, 0, 255)) / 255.0  # screen

def add_grain(rgb, strength=8.0, size=1.6, seed=None):
    h, w = rgb.shape[:2]
    rng = np.random.default_rng(seed)
    gh, gw = max(1, int(h / size)), max(1, int(w / size))
    noise = rng.standard_normal((gh, gw)).astype(np.float32)
    if (gh, gw) != (h, w):
        noise = np.asarray(
            Image.fromarray(noise, mode='F').resize((w, h), Image.BILINEAR))
    lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0
    weight = 0.15 + 0.85 * (4.0 * lum * (1.0 - lum)) ** 0.6
    return rgb + (noise * weight * strength)[..., None]

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    g_str = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
    g_size = float(sys.argv[4]) if len(sys.argv) > 4 else 1.6
    hal = float(sys.argv[5]) if len(sys.argv) > 5 else 0.55
    im = Image.open(src)
    exif = im.info.get('exif', b'')
    icc = im.info.get('icc_profile')
    rgb = np.asarray(im.convert('RGB'), dtype=np.float32)
    if hal > 0:
        rgb = add_halation(rgb, hal)
    rgb = add_grain(rgb, g_str, g_size)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(
        dst, quality=90, subsampling=1, exif=exif, icc_profile=icc)
    print(f'{dst}: grain={g_str}/{g_size} halation={hal}')
