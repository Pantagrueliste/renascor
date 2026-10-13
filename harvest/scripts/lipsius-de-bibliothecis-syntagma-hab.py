import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "lipsius-de-bibliothecis-syntagma-hab"
ED = "ed000001"
PATH = "texts/tei-transcript.xml"
problems = []
h = Harvest(RID)
data = hab.fetch(h, ED, PATH, problems)
if data is not None:
    root = hab.parse(data)
    hab.normalise(root)
    h.add(PATH.split("/")[-1], hab.serialise(root), language="Latin", year=1602,
          source="Justus Lipsius, De Bibliothecis Syntagma (1602), HAB Wolfenbüttel", url=hab.HAB + ED + "/" + PATH)
print(h.finish(method="Direct download of the Latin TEI transcript (texts/tei-transcript.xml); apparatus variants (later editions) dropped, footnotes left out by RQ's counter; German translation not taken.", coverage="all: the single Latin TEI transcript.", problems=problems))
