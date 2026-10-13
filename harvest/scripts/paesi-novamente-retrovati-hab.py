import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "paesi-novamente-retrovati-hab"
ED = "ed000145"
problems = []
h = Harvest(RID)
for path, lang, year, src in [
    ("tei-transcript-pnr.xml", "Italian", 1507, "Paesi novamente retrovati (Vicenza, 1507)"),
    ("tei-transcript-nul.xml", "German", 1508, "Newe unbekanthe landte (Nuremberg, 1508)"),
]:
    data = hab.fetch(h, ED, path, problems)
    if data is None:
        continue
    root = hab.parse(data)
    hab.normalise(root, front_back_to_div=False)  # orig/abbr kept (diplomatic), reg/expan dropped
    h.add(path, hab.serialise(root), language=lang, year=year, source=src + ", HAB Wolfenbüttel",
          url=hab.HAB + ED + "/" + path)
print(h.finish(
    method="Direct download of the two TEI transcriptions; in each, the diplomatic reading (choice/orig, abbr) is kept and the regularised reading (reg, expan) dropped; editorial notes, indexes and the modern translation are not taken.",
    coverage="all: both transcriptions (Italian 1507 and German 1508).", problems=problems))
