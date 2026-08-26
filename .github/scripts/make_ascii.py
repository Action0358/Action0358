"""Regenerate assets/ascii-art.txt from the GitHub mark.

The mark is a filled disc with the cat knocked out of it, so sampling ink
directly gives you the disc, not the Octocat. A flood fill will not isolate
the cat either -- its legs break the bottom of the circle, so the interior is
open to the outside. Filling each row between its leftmost and rightmost ink
recovers the disc, and subtracting the ink leaves the cat.

  curl -sL https://cdn.jsdelivr.net/npm/simple-icons@13/icons/github.svg \
    | sed 's/<svg /<svg fill="black" /' > logo.svg
  chrome --headless --screenshot=logo.png --window-size=900,900 \
    --default-background-color=00000000 file://$PWD/logo.svg
  python make_ascii.py logo.png 42 > ../../assets/ascii-art.txt

For a logo that is a positive shape rather than a knockout, pass --solid to
skip the subtraction. Width is in characters; rows follow the aspect ratio.
"""

import sys

import numpy as np
from PIL import Image

CELL = 0.44  # character width / line height for Consolas 16px on 20px leading
RAMP = "  .:~=+*#%@"  # light -> dark

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC, COLS = args[0], int(args[1])
SOLID = "--solid" in sys.argv

ink = np.asarray(Image.open(SRC).convert("RGBA"))[..., 3] > 128

if SOLID:
    shape = ink
else:
    filled = np.logical_and(
        np.maximum.accumulate(ink, axis=1),
        np.maximum.accumulate(ink[:, ::-1], axis=1)[:, ::-1],
    )
    shape = filled & ~ink

ys, xs = np.nonzero(shape)
box = Image.fromarray((shape * 255).astype(np.uint8)).crop(
    (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
)
w, h = box.size
rows = max(1, round(COLS * (h / w) * CELL))

v = np.asarray(box.resize((COLS, rows), Image.LANCZOS), dtype=np.float32) / 255.0
idx = (np.clip(v * 1.15, 0, 1) * (len(RAMP) - 1)).round().astype(int)
print("\n".join("".join(RAMP[i] for i in r).rstrip() for r in idx))
