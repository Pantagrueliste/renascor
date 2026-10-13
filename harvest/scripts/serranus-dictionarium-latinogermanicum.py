import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "serranus-dictionarium-latinogermanicum"
ED = "ed000215"
problems = []
h = Harvest(RID)
parts = [p for p in hab.mets_files(h, ED) if p.startswith("part_") and p not in ("part_front.xml", "part_back.xml")]
roots = []
for p in parts:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    hab.normalise(root)
    roots.append(root)
if roots:
    raw = hab.combine(roots, year=1538, title="Serranus, Dictionarium Latinogermanicum (Nuremberg, 1538)")
    h.add("serranus-1538.xml", raw, language="Latin", year=1538,
          source="Serranus, Dictionarium Latinogermanicum (1538), HAB Wolfenbüttel", url=hab.HAB + ED + "/")
problems.append("one record for the whole dictionary (letter part files combined); Latin headwords with German glosses, main language recorded as Latin")
problems.append("part_front.xml and part_back.xml (owner's marginal notes, blank pages) not taken: not part of the printed text")
print(h.finish(
    method="Downloaded the letter part files (part_a ... part_z) listed in mets.xml (the master tei-transcript.xml only holds XInclude references) and combined their text into one record.",
    coverage="all letter parts A-Z (%d files); front and back matter parts left out." % len(parts), problems=problems))
