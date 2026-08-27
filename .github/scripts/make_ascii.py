"""Regenerate assets/ascii-art.txt from assets/octocat.png.

The source is shaded artwork on a white background, not a flat logo, so the
conversion keeps its tones: the body lands on dense characters, the face on
light ones. Two things need handling first -- the background is white rather
than transparent, and the cyan ground shadow is decoration we don't want.

  python make_ascii.py 46 > ../../assets/ascii-art.txt

Width is in characters; rows follow the aspect ratio. Raising DETAIL sharpens
the face at the cost of noise; raising FLOOR keeps light areas from dropping
out into blank space, which would leave the head looking hollow.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

SRC = Path(__file__).resolve().parents[2] / "assets" / "octocat.png"
COLS = int(sys.argv[1]) if len(sys.argv) > 1 else 46
DETAIL = 0.55
FLOOR = 0.42
CELL = 0.44  # character width / line height for Consolas 16px on 20px leading
RAMP = "  .:~=+*#%@"  # light -> dark

im = Image.open(SRC).convert("RGBA")
im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
a = np.asarray(im, dtype=np.float32)
R, G, B = a[..., 0], a[..., 1], a[..., 2]

cyan = (B > R + 40) & (G > R + 40)  # the ground shadow
white = (R > 232) & (G > 232) & (B > 232)  # the backdrop
mask = ~cyan & ~white

ys, xs = np.nonzero(mask)
box = tuple(int(v) for v in (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
w, h = box[2] - box[0], box[3] - box[1]
rows = max(1, round(COLS * (h / w) * CELL))

gray = a[..., :3].mean(axis=2)
lo, hi = np.percentile(gray[mask], 2), np.percentile(gray[mask], 98)
tone = np.clip((hi - gray) / max(hi - lo, 1e-3), 0, 1)

blur = np.asarray(
    Image.fromarray(gray.astype(np.uint8)).filter(ImageFilter.GaussianBlur(w / 55)),
    dtype=np.float32,
)
detail = np.clip(0.5 + (blur - gray) / 70.0, 0, 1)

val = np.clip(0.80 * tone + DETAIL * (detail - 0.5) * 2, 0, 1)
val = np.where(mask, np.maximum(val, FLOOR), 0.0)


def shrink(x):
    img = Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.crop(box).resize((COLS, rows), Image.BOX), np.float32) / 255


# scale value by coverage so partly-covered edge cells don't read as solid
v, cover = shrink(val), shrink(mask.astype(np.float32))
v = np.where(cover > 0.25, np.clip(v / np.maximum(cover, 0.4), 0, 1), 0.0)

idx = (v * (len(RAMP) - 1)).round().astype(int)
print("\n".join("".join(RAMP[i] for i in r).rstrip() for r in idx))
