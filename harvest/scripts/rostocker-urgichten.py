import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("rostocker-urgichten")
rep = h.finish(method="Attempted https://opendata.uni-halle.de/handle/1981185920/13873: the server answers every HTML/file request with an Anubis proof-of-work bot challenge; OAI-PMH serves only Dublin Core metadata (no file links, mets not supported). Challenge was not circumvented.",
  coverage="Nothing harvested (0 of 50 items).",
  problems=["Item and bitstream downloads are protected against automated access (Anubis bot wall); needs manual browser download of the TEI files."])
print(rep["texts_total"])
