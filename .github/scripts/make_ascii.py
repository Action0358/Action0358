"""Regenerate assets/ascii-art.txt from a logo.

The current art is the GitHub mark. To rebuild it, or to swap in another
logo, rasterise the SVG first -- the alpha channel is what gets sampled:

  curl -sL https://cdn.jsdelivr.net/npm/simple-icons@13/icons/github.svg \
    | sed 's/<svg /<svg fill="black" /' > logo.svg
  chrome --headless --screenshot=logo.png --window-size=900,900 \
    --default-background-color=00000000 file://$PWD/logo.svg
  python make_ascii.py logo.png 44 > ../../assets/ascii-art.txt

Width is in characters; rows are derived from the aspect ratio.
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC, COLS = sys.argv[1], int(sys.argv[2])
ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 0
CELL = 0.44
RAMP = "  .:~=+*#%@"

im = Image.open(SRC).convert("RGBA")
bg = Image.new("RGBA", im.size, (255, 255, 255, 0))
im = Image.alpha_composite(bg, im)
a = np.asarray(im, dtype=np.float32)
ink = a[..., 3] / 255.0 * (1.0 - a[..., :3].mean(axis=2) / 255.0 * 0.0)

ys, xs = np.nonzero(ink > 0.15)
im2 = Image.fromarray((ink * 255).astype(np.uint8)).crop(
    (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
)
w, h = im2.size
rows = ROWS or max(1, int(round(COLS * (h / w) * CELL)))
v = np.asarray(im2.resize((COLS, rows), Image.LANCZOS), dtype=np.float32) / 255.0
v = np.clip(v * 1.15, 0, 1)

idx = (v * (len(RAMP) - 1)).round().astype(int)
lines = ["".join(RAMP[i] for i in r).rstrip() for r in idx]
print("\n".join(lines))
sys.stderr.write(f"{COLS}x{rows}\n")
