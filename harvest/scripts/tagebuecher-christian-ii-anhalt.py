import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import re
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "tagebuecher-christian-ii-anhalt"
ED = "ed000228"
problems = []
h = Harvest(RID)
files = [p for p in hab.mets_files(h, ED) if re.fullmatch(r"\d{4}_\d\d\.xml", p)]
for p in files:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    hab.normalise(root)  # deleted words dropped; editorial translations/notes are <note>, dropped by RQ's counter
    h.add(p, hab.serialise(root), language="German", year=int(p[:4]),
          source="Tagebücher Christian II. von Anhalt-Bernburg, HAB Wolfenbüttel", url=hab.HAB + ED + "/" + p)
problems.append("one record per monthly file (the resource's own division; about 10,000 diary entries inside); main language German with French and Latin passages")
print(h.finish(
    method="Monthly TEI files (YYYY_MM.xml) listed in mets.xml, fetched one by one; index, register and note elements (translations, comments) dropped by RQ's counter; year from the file name.",
    coverage="all: %d monthly files listed in mets.xml (1621-1656)." % len(files), problems=problems))
