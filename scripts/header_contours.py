"""Topographic contour lines for the Renascor header (deterministic). Usage: python3 scripts/header_contours.py out.svg"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
W, H = 1440, 300
rng = np.random.default_rng(1450)
x, y = np.meshgrid(np.linspace(0, W, 360), np.linspace(0, H, 90))
z = np.zeros_like(x)
for _ in range(14):                         # a few hills and basins
    cx, cy = rng.uniform(-100, W + 100), rng.uniform(-80, H + 80)
    sx, sy = rng.uniform(120, 340), rng.uniform(70, 190)
    z += rng.uniform(-1, 1.4) * np.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2))
z += 0.25 * np.sin(x / 210 + 1.3) * np.cos(y / 120)
levels = np.linspace(z.min(), z.max(), 22)[1:-1]
cs = plt.contour(x, y, z, levels=levels)
paths = []
for i, segs in enumerate(cs.allsegs):
    for seg in segs:
        if len(seg) < 6: continue
        seg = seg[::2] if len(seg) > 40 else seg
        d = "M" + " ".join(f"{px:.0f} {py:.0f}" for px, py in seg)
        cls = ' class="m"' if i % 5 == 2 else ''
        paths.append(f'<path{cls} d="{d}"/>')
svg = (f'<svg class="head-art" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" '
       f'aria-hidden="true" focusable="false">' + "".join(paths) + "</svg>")
open(__import__("sys").argv[1], "w").write(svg)
print(len(svg), "bytes,", len(paths), "paths")
