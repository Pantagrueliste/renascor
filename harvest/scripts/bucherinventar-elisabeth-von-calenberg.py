import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "bucherinventar-elisabeth-von-calenberg"
ED = "ed000082"
PATH = "tei-transcript.xml"
problems = []
h = Harvest(RID)
data = hab.fetch(h, ED, PATH, problems)
if data is not None:
    root = hab.parse(data)
    hab.normalise(root, bibl_to_seg=True)
    h.add(PATH.split("/")[-1], hab.serialise(root), language="German", year=1539,
          source="Das Bücherinventar der Elisabeth von Calenberg (1539), HAB Wolfenbüttel", url=hab.HAB + ED + "/" + PATH)
print(h.finish(method="Direct download of the single TEI transcript (diglib.hab.de); inventory entries (listBibl/bibl) renamed to seg so that they count as text; variant readings (app/rdg) dropped; footnotes and bibliographies are left out by RQ's counter.", coverage="all: the single TEI file (69 book entries, inventory of 1539).", problems=problems))
