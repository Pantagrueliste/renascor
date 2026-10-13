import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "dasypodius-dictionarium-latinogermanicum"
ED = "ed000008"
PARTS = ["tei-transcript_01-contents.xml", "tei-transcript_02-ab.xml", "tei-transcript_03-ch.xml",
         "tei-transcript_04-io.xml", "tei-transcript_05-pz.xml"]
problems = []
h = Harvest(RID)
roots = []
for p in PARTS:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    hab.normalise(root, front_back_to_div=True)  # title page and preface count; 1536 variant readings (rdg) dropped
    roots.append(root)
if roots:
    raw = hab.combine(roots, year=1535, title="Dasypodius, Dictionarium Latinogermanicum (Strasbourg, 1535)")
    h.add("dasypodius-1535.xml", raw, language="Latin", year=1535,
          source="Dasypodius, Dictionarium Latinogermanicum (1535), HAB Wolfenbüttel",
          url=hab.HAB + ED + "/")
problems.append("one record for the whole dictionary (5 TEI part files combined); entries are Latin headwords with German glosses, main language recorded as Latin")
print(h.finish(
    method="Downloaded the five TEI part files listed in mets.xml (the master tei-transcript.xml returns 404) and combined their text into one record; 1536 variant readings (app/rdg) dropped, notes dropped by RQ's counter.",
    coverage="all: contents/preface and A-Z (1535 text).", problems=problems))
