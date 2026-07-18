#!/usr/bin/env python3
"""Resize for web/social: longest side 2048px, output sharpening after resize.

Usage: web_export.py in.jpg out.jpg [long_edge]
"""
import sys
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
edge = int(sys.argv[3]) if len(sys.argv) > 3 else 2048

im = Image.open(src)
exif = im.info.get('exif', b'')
icc = im.info.get('icc_profile')
im = im.convert('RGB')
im.thumbnail((edge, edge), Image.LANCZOS)
im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
im.save(dst, quality=88, subsampling=1, exif=exif, icc_profile=icc)
print(f'{dst}: {im.size[0]}x{im.size[1]}')
