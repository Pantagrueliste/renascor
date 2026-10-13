import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "fonteny-livre-d-enigmes"
ED = "ed000166"
PATH = "tei-transcript-fr-or.xml"
problems = []
h = Harvest(RID)
data = hab.fetch(h, ED, PATH, problems)
if data is not None:
    root = hab.parse(data)
    hab.normalise(root)
    h.add(PATH.split("/")[-1], hab.serialise(root), language="French", year=1600,
          source="Jacques de Fonteny, Livre d'Enigmes (HAB Wolfenbüttel)", url=hab.HAB + ED + "/" + PATH)
problems.append("year is approximate: the manuscript is dated c. 1600 (early 17th century) in the catalogue; 1600 used")
print(h.finish(method="Direct download of the original-spelling TEI transcript (tei-transcript-fr-or.xml); regularised version tei-transcript-fr.xml, introduction and commentary not taken; deleted words and regularisations dropped.", coverage="all: the single original-spelling TEI file.", problems=problems))
