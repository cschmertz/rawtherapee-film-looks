#!/usr/bin/env python3
"""Build side-by-side contact sheets of a look's variants for each photo.

Usage: contact_sheet.py <renders-dir> [look-dir]
Variant numbers come from the render filenames (<base>_NN.jpg); if a look
dir is given, tile labels use its pp3 names ("Fuji Film 01 - Classic
Chrome.pp3" -> "01 Classic Chrome").
Writes <renders-dir>/contact/<base>_contact.jpg.
"""
import os, sys, re, glob
from PIL import Image, ImageDraw, ImageFont

TILE_H = 900
GUTTER, LABEL_H = 12, 56

rdir = sys.argv[1]
names = {}
if len(sys.argv) > 2:
    for p in glob.glob(os.path.join(sys.argv[2], 'rawtherapee', '*.pp3')):
        m = re.search(r' (\d\d) - (.+)\.pp3$', os.path.basename(p))
        if m:
            names[m.group(1)] = m.group(2)

outdir = os.path.join(rdir, 'contact')
os.makedirs(outdir, exist_ok=True)

try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 34)
except Exception:
    font = ImageFont.load_default()

renders = glob.glob(os.path.join(rdir, '*_[0-9][0-9].jpg'))
bases = sorted({os.path.basename(f)[:-7] for f in renders})
for base in bases:
    tiles = []
    for f in sorted(f for f in renders if os.path.basename(f)[:-7] == base):
        nn = os.path.basename(f)[-6:-4]
        im = Image.open(f).convert('RGB')
        im.thumbnail((TILE_H * 4, TILE_H), Image.LANCZOS)
        tiles.append((f'{nn} {names.get(nn, "")}'.strip(), im))
    if len(tiles) < 2:
        continue
    W = sum(t.size[0] for _, t in tiles) + GUTTER * (len(tiles) + 1)
    H = TILE_H + LABEL_H + GUTTER * 2
    sheet = Image.new('RGB', (W, H), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    x = GUTTER
    for label, t in tiles:
        sheet.paste(t, (x, GUTTER))
        draw.text((x + 8, GUTTER + TILE_H + 10), label, fill=(230, 225, 215), font=font)
        x += t.size[0] + GUTTER
    out = os.path.join(outdir, f'{base}_contact.jpg')
    sheet.save(out, quality=88)
    print(out)
