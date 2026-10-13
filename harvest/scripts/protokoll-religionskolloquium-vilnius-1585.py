import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "protokoll-religionskolloquium-vilnius-1585"
ED = "ed000004"
PATH = "tei-transcript.xml"
problems = []
h = Harvest(RID)
data = hab.fetch(h, ED, PATH, problems)
if data is not None:
    root = hab.parse(data)
    hab.normalise(root)
    h.add(PATH.split("/")[-1], hab.serialise(root), language="Latin", year=1585,
          source="Protokoll des Religionskolloquiums in Vilnius, 14 June 1585, HAB Wolfenbüttel", url=hab.HAB + ED + "/" + PATH)
print(h.finish(method="Direct download of the Latin TEI transcript; regularised name forms (reg) and deletions dropped; German translation and introduction not taken.", coverage="all: the single Latin TEI transcript.", problems=problems))
