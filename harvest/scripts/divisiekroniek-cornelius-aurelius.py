import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0,HARVEST_DIR + "")
from hlib import Harvest
h=Harvest("divisiekroniek-cornelius-aurelius")
# resources.huygens.knaw.nl returns 403 to the identified UA; not circumvented.
print(h.finish(method="Not harvested.",coverage="None (0 of 899 transcription pages).",problems=["resources.huygens.knaw.nl answers HTTP 403 Forbidden to the identified harvest user agent (including robots.txt and the start page); it serves pages only to browser-like agents. Spoofing a browser agent would circumvent the server's bot filtering, so no pages were fetched. No bulk export or alternative route found."]))
