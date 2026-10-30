"""Generate local abstract tech-styled images to use as per-item inline covers.

Zero network / zero API cost: pure Pillow compositing. Produces a fixed set of
color-varied 16:9 banners under output/covers/ that to_docx reuses (cycling)
after the daily AI cover.

Usage:
    python -m src.inline_imgs --count 8      # generate 8 variant banners
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
DIR = OUT / "covers"

# (name, primary RGB) -- several palettes to vary per item
PALETTES = [
    ("cyan",    (0, 180, 220)),
    ("violet",  (130, 90, 220)),
    ("amber",   (230, 150, 40)),
    ("green",   (40, 190, 120)),
    ("rose",    (220, 80, 140)),
    ("steel",   (90, 120, 190)),
    ("teal",    (0, 170, 170)),
    ("indigo",  (75, 70, 200)),
]


def draw_banner(color, path, w=1280, h=720, seed=None):
    rnd = random.Random(seed)
    img = Image.new("RGB", (w, h), _shade(color, 0.12))
    dr = ImageDraw.Draw(img)
    # soft radial glow
    for _ in range(6):
        cx = rnd.randint(0, w); cy = rnd.randint(0, h)
        r = rnd.randint(120, 340)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_shade(color, rnd.uniform(0.30, 0.55)))
    # circuit-like polylines
    for _ in range(14):
        pts = []
        x = rnd.randint(-100, 100)
        y = rnd.randint(0, h)
        for _ in range(6):
            x += rnd.randint(60, 200)
            y += rnd.randint(-140, 140)
            pts.append((max(0, min(w, x)), max(0, min(h, y))))
        dr.line(pts, fill=_shade(color, rnd.uniform(0.45, 0.75)), width=rnd.randint(2, 5))
    # nodes
    for _ in range(40):
        x = rnd.randint(0, w); y = rnd.randint(0, h)
        r = rnd.randint(2, 6)
        dr.ellipse([x - r, y - r, x + r, y + r], fill=_shade(color, rnd.uniform(0.5, 0.9)))
    img.save(str(path), "PNG")


def _shade(rgb, f):
    return tuple(max(0, min(255, int(c * f))) for c in rgb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=len(PALETTES))
    args = ap.parse_args()
    DIR.mkdir(parents=True, exist_ok=True)
    palettes = PALETTES[:args.count]
    for i, (name, col) in enumerate(palettes, 1):
        out = DIR / ("inline_%02d_%s.png" % (i, name))
        draw_banner(col, out, seed=i * 101)
    print("wrote %d inline banners -> %s" % (len(palettes), DIR))


if __name__ == "__main__":
    main()
