import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest
h = Harvest("briefwisseling-constantijn-huygens")
rep = h.finish(method="Not harvested. Probed robots.txt and the start page only.",
  coverage="Nothing harvested (0 of the 9,237 letters).",
  problems=["resources.huygens.knaw.nl returns 403 Forbidden to a non-browser user agent (including this project's identified UA), and its robots.txt disallows /retro/* and /retroboeken/* (the OCR viewer that serves the text of Worp's edition), the metadata exports (*.xls/*.csv) and all search URLs. Only the start page and robots.txt were read (once, with a generic UA, to learn the rules); no crawling or workaround was attempted.",
            "Even if reachable, the text is OCR of Worp's 1911-1917 printed edition with his introductions, notes and indexes mixed in, so period text could not be isolated cleanly. Possible alternative route: the public-domain Worp volumes on archive.org/DBNL (not tried, would be a different source)."])
print(json.dumps(rep)[:300])
