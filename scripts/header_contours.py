"""Topographic contour lines for the Renascor header (deterministic).

Usage: python3 scripts/header_contours.py out.svg
Fractal terrain (several octaves of smoothed noise, with ridges), contours at
equal intervals and an index contour every fifth line, as on a topographic map.
"""
import sys
import numpy as np
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W, H, STEP = 1440, 300, 2          # viewBox and grid step (px)
LEVELS, INDEX_EVERY = 46, 5
rng = np.random.default_rng(1450)
ny, nx = H // STEP + 1, W // STEP + 1


def octave(sigma, amp):
    n = gaussian_filter(rng.standard_normal((ny, nx)), sigma, mode="wrap")
    return amp * n / n.std()


z = octave(60, 1.0) + octave(30, 0.5) + octave(14, 0.22) + octave(6, 0.07)
ridges = 1 - np.abs(octave(40, 1.0))                       # sharp crests, soft valleys
z = z + 0.55 * ridges
y = np.arange(ny)[:, None] / ny
z = z + 0.6 * np.sin(np.arange(nx)[None, :] / nx * 2.4 + 0.4) * (0.4 + y)  # a broad slope

levels = np.linspace(np.percentile(z, 1), np.percentile(z, 99.5), LEVELS)
cs = plt.contour(np.arange(nx) * STEP, np.arange(ny) * STEP, z, levels=levels)


def simplify(pts, tol=1.1):
    """Ramer-Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = np.hypot(*ab) or 1.0
    d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n
    i = int(d.argmax())
    if d[i] > tol:
        return np.vstack([simplify(pts[: i + 1], tol)[:-1], simplify(pts[i:], tol)])
    return np.vstack([a, b])


def smooth_path(pts):
    """Quadratic curves through midpoints: smooth lines from a polyline."""
    p = [(round(x), round(y)) for x, y in pts]
    if len(p) < 3:
        return "M" + " ".join(f"{x} {y}" for x, y in p)
    d = [f"M{p[0][0]} {p[0][1]}"]
    for (x0, y0), (x1, y1) in zip(p[1:-1], p[2:]):
        d.append(f"Q{x0} {y0} {(x0 + x1) / 2:g} {(y0 + y1) / 2:g}")
    d.append(f"L{p[-1][0]} {p[-1][1]}")
    return "".join(d)


paths = []
for i, segs in enumerate(cs.allsegs):
    major = i % INDEX_EVERY == 0
    for seg in segs:
        if len(seg) < 8:
            continue
        seg = simplify(np.asarray(seg))
        cls = ' class="m"' if major else ""
        paths.append(f'<path{cls} d="{smooth_path(seg)}"/>')

svg = (f'<svg class="head-art" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" '
       'aria-hidden="true" focusable="false">' + "".join(paths) + "</svg>")
open(sys.argv[1], "w").write(svg)
print(f"{len(svg)} bytes, {len(paths)} paths")
