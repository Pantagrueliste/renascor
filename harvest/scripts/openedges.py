import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, glob, os, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("openedges")
zp = h.dir / "files/oe.zip"
if not zp.exists():
    h.get("https://spraakbanken.gu.se/resurser/data/OpenEDGeS_v1.01.zip", "files/oe.zip", binary=True)
base = glob.glob(str(h.dir / "files/x/OpenEDGeS*/Texts"))[0]
names = {"nl": "Dutch", "de": "German"}
for lg, L in names.items():
    for f in sorted(glob.glob(f"{base}/{lg}/*-allverses.txt")):
        fn = os.path.basename(f)
        y = int(re.match(r"[a-z]{2}_(\d{4})_", fn).group(1))
        raw = open(f, encoding="utf-8").read().replace("{", "").replace("}", "")
        h.add(fn, raw, language=L, year=y, source="OpenEDGeS v1.01", url="https://sprakbanken.se/en/resources/openedges")
print(h.finish(method="Downloaded OpenEDGeS_v1.01.zip from Språkbanken; used the one-verse-per-line *-allverses.txt of each Dutch and German Bible (one record per Bible edition, year from the file name = publication year); braces (expansion markers) stripped.",
  coverage="All 19 Dutch and German Bibles of the public subset (8 Dutch + 4 German in window). English and Swedish Bibles in the archive were not harvested (outside the catalogued Dutch/German scope). Pivot NBV not included (copyright).",
  problems=["Catalogue says 10 texts/7.1M words; archive has 12 in-window Dutch/German Bibles (nl 1477,1528,1542,1548,1560,1562,1637,1648; de 1460,1478,1545,1661).", "nl_1360_Hernse, nl_1399_NNNT, 1790+ are out of window (kept in staging)."]))
