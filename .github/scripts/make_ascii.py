"""One-off generator for assets/ascii-art.txt.

Converts a photo into the monospace portrait used in the profile SVGs. CROP and
POLY are hand-traced for one specific source image; retrace them if the photo
changes. Run: python make_ascii.py [cols] [gamma] [detail_weight]
"""

import sys
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

SRC = "/Users/daiyunozaki/Desktop/IMG_1617.JPG"
COLS = int(sys.argv[1]) if len(sys.argv) > 1 else 42
GAMMA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.75
CELL = 0.44
CROP = (200, 330, 1050, 1880)

# light -> dark
RAMP = "  .:~=+*#%@"

rgb = Image.open(SRC).convert("RGB").crop(CROP)
w, h = rgb.size
rows = int(round(COLS * (h / w) * CELL))
arr = np.asarray(rgb, dtype=np.float32)
R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
V = arr.max(axis=2) / 255.0

# --- subject mask: dark clothing/hair, or warm skin ---
warm = (R - B) > 28
mask = ((V < 0.46) | (warm & (V > 0.40))).astype(np.uint8) * 255

# coarse hand-traced region around the subject, so the painted backdrop
# behind him can never join the silhouette
POLY = [(470, 335), (800, 335), (840, 600), (930, 720), (1045, 930),
        (1050, 1350), (1010, 1650), (950, 1880), (430, 1880), (400, 1450),
        (390, 1080), (300, 970), (215, 850), (360, 470), (430, 410)]
region = Image.new("L", (w, h), 0)
ImageDraw.Draw(region).polygon(
    [(x - CROP[0], y - CROP[1]) for x, y in POLY], fill=255
)
mask = (mask & np.asarray(region)).astype(np.uint8)
m = Image.fromarray(mask)
m = m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MedianFilter(9))
m = m.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MaxFilter(7))
mask = np.asarray(m) > 127

# keep only the largest connected blob (drops painting speckle)
lab = np.zeros(mask.shape, dtype=np.int32)
cur = 0
best, best_n = 0, 0
stack = []
ys, xs = np.nonzero(mask)
for y0, x0 in zip(ys, xs):
    if lab[y0, x0]:
        continue
    cur += 1
    n = 0
    stack.append((y0, x0))
    lab[y0, x0] = cur
    while stack:
        y, x = stack.pop()
        n += 1
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                lab[yy, xx] = cur
                stack.append((yy, xx))
    if n > best_n:
        best, best_n = cur, n
mask = lab == best

gray = np.asarray(rgb.convert("L"), dtype=np.float32) / 255.0

# tone inside the subject, normalised over the subject's own range
sub = gray[mask]
lo, hi = np.percentile(sub, 2), np.percentile(sub, 98)
tone = np.clip((hi - gray) / max(hi - lo, 1e-3), 0, 1)

# local detail so facial features survive the downscale
blur = np.asarray(rgb.convert("L").filter(ImageFilter.GaussianBlur(w / 60)), dtype=np.float32)
det = np.clip(0.5 + (blur - np.asarray(rgb.convert("L"), dtype=np.float32)) / 90.0, 0, 1)

DW = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
val = np.clip(0.78 * tone + DW * (det - 0.5) * 2, 0, 1)
val = np.where(mask, np.maximum(val, 0.30), 0.0)

# downscale value and coverage separately, then blank low-coverage cells
def shrink(a):
    return np.asarray(
        Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize(
            (COLS, rows), Image.BOX
        ),
        dtype=np.float32,
    ) / 255.0

v = shrink(val)
cov = shrink(mask.astype(np.float32))
v = np.where(cov > 0.22, np.clip(v / np.maximum(cov, 0.35), 0, 1) ** GAMMA, 0.0)

idx = (v * (len(RAMP) - 1)).round().astype(int)
lines = ["".join(RAMP[i] for i in row).rstrip() for row in idx]
while lines and not lines[0].strip():
    lines.pop(0)
while lines and not lines[-1].strip():
    lines.pop()

with open("art.txt", "w") as f:
    f.write("\n".join(lines) + "\n")

font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 16)
cw = font.getlength("M")
prev = Image.new("RGB", (int(cw * COLS) + 20, 20 * len(lines) + 20), "#161b22")
d = ImageDraw.Draw(prev)
for i, ln in enumerate(lines):
    d.text((10, 10 + i * 20), ln, font=font, fill="#c9d1d9")
prev.save("preview.png")
print(f"{COLS}x{len(lines)}")
print("\n".join(lines))
