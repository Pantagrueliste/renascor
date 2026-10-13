import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, random
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("map-of-early-modern-london")
base = "https://mapoflondon.uvic.ca/xml/original/"
idx = h.get(base, "files/original_index.html")
rows = re.findall(r'<a href="([^"?/][^"]*)\.xml">[^<]*</a></td><td align="right">[^<]*</td><td align="right">([^<]*)<', idx)
def kb(x):
    x = x.strip(); return float(x[:-1]) * (1 if x[-1] == "K" else 1024) if x[-1] in "KM" else float(x) / 1024
sz = {n: kb(x) for n, x in rows}
pool = [n for n in sz if re.fullmatch(r"[A-Z]+\d+", n) and 7 <= sz[n] < 15 and not (h.dir/f"files/original/{n}.xml").exists()]
random.seed(1); pick = random.sample(pool, 50)
hits = []
for n in pick:
    raw = h.get(base + n + ".xml", f"files/original/{n}.xml")
    head = raw[: raw.find("</profileDesc>")] if "</profileDesc>" in raw else raw[:30000]
    if "mdtPrimarySource" in head: hits.append(n)
print(len(pool), "pool;", len(hits), "primary in sample of 50:", hits)
